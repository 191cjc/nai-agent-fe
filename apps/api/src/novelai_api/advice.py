"""Stateless advice request and response boundary."""

import asyncio
import logging
import re
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


class AdviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str = Field(min_length=1, max_length=4000)

    @field_validator("input")
    @classmethod
    def nonempty_input(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Advice input cannot be blank")
        return value


class AdviceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggestion: str = Field(min_length=1, max_length=3000)

    @field_validator("suggestion")
    @classmethod
    def nonempty_suggestion(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Advice output cannot be blank")
        return value


class ToolUseAttempt(Exception):
    def __init__(self, message: str = "Unexpected Codex item", *, item_type: object = None):
        # Only a short identifier-like type is kept for diagnostics, never item text.
        self.item_type = (
            item_type if isinstance(item_type, str)
            and re.fullmatch(r"[a-z][a-z0-9_.-]{0,39}", item_type) else "unknown"
        )
        super().__init__(message)


class AdviceFailure(Exception):
    def __init__(self, status: int, code: str, message: str, *, retryable: bool = False):
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class AdviceRunner(Protocol):
    async def run(self, text: str) -> dict: ...


class AdviceService:
    def __init__(self, runner: AdviceRunner | None, *, timeout: float = 45.0):
        self.runner = runner
        self.timeout = timeout
        self._capacity = asyncio.Semaphore(2)

    async def advise(self, text: str) -> AdviceResult:
        if self.runner is None:
            raise AdviceFailure(503, "advice_unavailable", "AI advice is not configured")
        if self._capacity.locked():
            raise AdviceFailure(429, "advice_busy", "AI advice is busy", retryable=True)
        async with self._capacity:
            try:
                payload = await asyncio.wait_for(self.runner.run(text), timeout=self.timeout)
                return AdviceResult.model_validate(payload)
            except TimeoutError as exception:
                logger.warning("AI advice timed out")
                raise AdviceFailure(504, "advice_timeout", "AI advice timed out") from exception
            except ToolUseAttempt as exception:
                logger.warning("AI advice rejected observed tool use (%s)", exception.item_type)
                raise AdviceFailure(
                    502, "advice_tool_attempt", "AI advice unavailable"
                ) from exception
            except asyncio.CancelledError:
                raise
            except Exception as exception:
                logger.warning("AI advice failed (%s)", type(exception).__name__)
                raise AdviceFailure(502, "advice_failed", "AI advice unavailable") from exception
