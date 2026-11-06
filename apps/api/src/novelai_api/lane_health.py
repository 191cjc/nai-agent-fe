"""Per-lane provider outage backoff for durable runs.

A pre-payment transient failure (nothing was billed) pauses new run claims on its lane so a
provider outage cannot burn through every queued item. The failed group itself stays failed;
groups are never retried. Ordinary single generations are not gated.
"""

import logging
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

# Codes that mean the provider never accepted the paid call.
TRANSIENT_FAILURES = frozenset({"provider_unavailable", "provider_rate_limited"})
BASE_DELAY = 15.0
MAX_DELAY = 600.0


class LaneHealth:
    def __init__(
        self,
        lane: str,
        probe: Callable[[], bool] | None = None,
        *,
        clock: Callable[[], float] = time.time,
        base_delay: float = BASE_DELAY,
        max_delay: float = MAX_DELAY,
    ):
        self.lane = lane
        self._probe = probe
        self._clock = clock
        self._base = base_delay
        self._max = max_delay
        self._lock = threading.Lock()
        self._failures = 0
        self._until: float | None = None

    def _open(self, reason: str) -> None:
        # Caller holds the lock.
        self._failures += 1
        delay = min(self._base * 2 ** (self._failures - 1), self._max)
        self._until = self._clock() + delay
        logger.warning(
            "Provider lane %s paused for %.0fs after %s (consecutive=%d)",
            self.lane, delay, reason, self._failures,
        )

    def report(self, error_code: str | None) -> None:
        """Record one finished group: None for success, else its error code."""
        with self._lock:
            if error_code is None:
                if self._failures:
                    logger.warning("Provider lane %s recovered", self.lane)
                self._failures = 0
                self._until = None
            elif error_code in TRANSIENT_FAILURES:
                self._open(error_code)

    def paused_until(self) -> float | None:
        """Epoch seconds the current pause lasts until, or None when claims may proceed."""
        with self._lock:
            return self._until

    def ready(self) -> bool:
        """True when a new run group may be claimed; probes once each cooldown expires."""
        with self._lock:
            if self._until is None:
                return True
            if self._clock() < self._until:
                return False
            probe = self._probe
            if probe is None:
                # Half-open: let claims through; the next outcome decides.
                self._until = None
                return True
        try:
            healthy = probe()
        except Exception:
            healthy = False
        with self._lock:
            if self._until is None:
                return True  # A concurrent success already cleared the pause.
            if healthy:
                logger.warning("Provider lane %s probe succeeded; resuming", self.lane)
                self._until = None
                return True
            self._open("failed probe")
            return False
