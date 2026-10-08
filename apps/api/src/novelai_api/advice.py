"""Stateless advice request and response boundary."""

import asyncio
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    pass


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
                raise AdviceFailure(504, "advice_timeout", "AI advice timed out") from exception
            except ToolUseAttempt as exception:
                raise AdviceFailure(
                    502, "advice_tool_attempt", "AI advice unavailable"
                ) from exception
            except asyncio.CancelledError:
                raise
            except Exception as exception:
                raise AdviceFailure(502, "advice_failed", "AI advice unavailable") from exception
