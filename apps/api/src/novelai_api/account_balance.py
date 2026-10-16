"""Read-only configured-account balance and short, process-local singleflight cache."""

import asyncio
import time
from collections.abc import Callable
from contextlib import suppress
from typing import Annotated, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_SAFE_INTEGER = 9_007_199_254_740_991
SafeCount = Annotated[int, Field(strict=True, ge=0, le=MAX_SAFE_INTEGER)]


class AccountBalance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fixed: SafeCount
    purchased: SafeCount
    total: SafeCount
    fetched_at: SafeCount

    @model_validator(mode="after")
    def exact_total(self) -> Self:
        if self.fixed + self.purchased != self.total:
            raise ValueError("Balance total must be an exact safe sum")
        return self


class BalanceFailure(Exception):
    """Only fixed, safe public diagnostics; never retain upstream account data."""

    def __init__(self, code: str = "balance_unavailable") -> None:
        failures = {
            "balance_unavailable": (503, "Image service balance unavailable", True),
            "balance_auth_error": (502, "Image service balance authentication failed", False),
            "balance_rate_limited": (429, "Image service balance rate limited", True),
            "balance_timeout": (504, "Image service balance request timed out", True),
            "balance_bad_response": (502, "Image service balance response invalid", False),
        }
        self.status, self.message, self.retryable = failures[code]
        self.code = code
        super().__init__(self.message)


class BalanceProvider(Protocol):
    def fetch(self) -> AccountBalance: ...


class BalanceService:
    def __init__(
        self, provider: BalanceProvider | None, *, clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._provider = provider
        self._clock = clock
        self._cached: AccountBalance | None = None
        self._expires_at = 0.0
        self._inflight: asyncio.Task[AccountBalance] | None = None
        self._closed = False

    async def get(self) -> AccountBalance:
        if self._closed or self._provider is None:
            raise BalanceFailure()
        if self._cached is not None and self._clock() < self._expires_at:
            return self._cached
        # No suspension between observing and assigning the shared task: all
        # callers on this app's event loop join the same success or failure.
        if self._inflight is None or self._inflight.done():
            self._inflight = asyncio.create_task(self._refresh())
            self._inflight.add_done_callback(self._observe_failure)
        return await asyncio.shield(self._inflight)

    async def _refresh(self) -> AccountBalance:
        assert self._provider is not None
        try:
            result = await asyncio.to_thread(self._provider.fetch)
            if not isinstance(result, AccountBalance):
                raise BalanceFailure("balance_bad_response")
        except BalanceFailure:
            raise
        except Exception:
            raise BalanceFailure() from None
        if not self._closed:
            self._cached = result
            self._expires_at = self._clock() + 5.0
        return result

    @staticmethod
    def _observe_failure(task: asyncio.Task[AccountBalance]) -> None:
        # A disconnected caller must not cancel the shared query or leave an
        # unobserved exception when every waiter has gone away.
        if not task.cancelled():
            task.exception()

    async def close(self) -> None:
        self._closed = True
        self._cached = None
        if self._inflight is not None:
            # Cancelling to_thread would abandon its synchronous transport.
            # Let the owned, independently bounded read-only query finish.
            with suppress(BalanceFailure):
                await asyncio.shield(self._inflight)
        self._inflight = None
