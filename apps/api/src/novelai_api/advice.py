"""Stateless advice request and response boundary."""

import asyncio
import logging
import re
from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class TraitTranslation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tag: str = Field(min_length=1, max_length=1000)
    translation: str = Field(min_length=1, max_length=300)

    @field_validator("translation")
    @classmethod
    def chinese_translation(cls, value: str) -> str:
        if not re.search(r"[\u3400-\u9fff]", value):
            raise ValueError("Trait translation must include Chinese")
        return value


class TraitAdviceResult(AdviceResult):
    suggestion: str = Field(min_length=1, max_length=1000)
    translations: list[TraitTranslation] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def aligned_tags(self) -> "TraitAdviceResult":
        tags = [tag.strip() for tag in self.suggestion.split(",")]
        if (
            not re.fullmatch(r"[\x20-\x7e]+", self.suggestion)
            or any(not tag for tag in tags)
            or tags != [item.tag for item in self.translations]
        ):
            raise ValueError("Trait translations must match the English tags in order")
        return self


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


class ImageInputUnsupported(Exception):
    """The configured advice model rejected attached images."""


class AdviceRunner(Protocol):
    async def run(self, text: str) -> dict: ...


TRAIT_TIMEOUT_SECONDS = 90.0


def trait_advice_text(traits: str) -> str:
    current = traits.strip() or "(empty)"
    return f"Current character trait tags:\n{current}"


class AdviceService:
    def __init__(self, runner: AdviceRunner | None, *, timeout: float = 45.0):
        self.runner = runner
        self.timeout = timeout
        self._capacity = asyncio.Semaphore(2)

    async def advise(
        self, text: str, *, images: Sequence[bytes] = (), timeout: float | None = None,
    ) -> AdviceResult | TraitAdviceResult:
        if self.runner is None:
            raise AdviceFailure(503, "advice_unavailable", "AI advice is not configured")
        if self._capacity.locked():
            raise AdviceFailure(429, "advice_busy", "AI advice is busy", retryable=True)
        async with self._capacity:
            try:
                # Image turns attach only the owner's chosen reference images (trait advice).
                turn = self.runner.run(text, images=images) if images else self.runner.run(text)
                payload = await asyncio.wait_for(turn, timeout=timeout or self.timeout)
                result_type = TraitAdviceResult if images else AdviceResult
                return result_type.model_validate(payload)
            except TimeoutError as exception:
                logger.warning("AI advice timed out")
                raise AdviceFailure(504, "advice_timeout", "AI advice timed out") from exception
            except ToolUseAttempt as exception:
                logger.warning("AI advice rejected observed tool use (%s)", exception.item_type)
                raise AdviceFailure(
                    502, "advice_tool_attempt", "AI advice unavailable"
                ) from exception
            except ImageInputUnsupported as exception:
                logger.warning("AI advice model rejected image input")
                raise AdviceFailure(
                    502, "advice_image_unsupported", "AI advice model does not accept images",
                ) from exception
            except asyncio.CancelledError:
                raise
            except Exception as exception:
                logger.warning("AI advice failed (%s)", type(exception).__name__)
                raise AdviceFailure(502, "advice_failed", "AI advice unavailable") from exception
