"""Character dataset groups rendered by the relay's GPT image model (independent of NovelAI)."""

import base64
import binascii
import json
import logging
import re
import time
from collections.abc import Callable, Sequence
from typing import Any

import httpx

from ._http_response import (
    InvalidResponseBody,
    ResponseDeadlineExceeded,
    check_deadline,
    read_bounded_body,
)
from .generations import (
    MAX_IMAGE_BYTES,
    GeneratedImage,
    GenerationRequest,
    ProviderFailure,
    VibeTokens,
)
from .prompt_comments import compile_prompt_comments
from .prompt_weights import strip_prompt_weights

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 96 * 1024 * 1024
POLICY_WORDS = re.compile(r"safety|moderation|content[ _-]?policy|policy", re.IGNORECASE)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def gpt_prompt(parameters: GenerationRequest) -> str:
    """Deterministic English instruction around the frozen traits, item and style (no weights)."""
    item = parameters.experiment.item.prompt.strip() if (
        parameters.experiment is not None and parameters.experiment.item is not None
    ) else ""
    positive = parameters.positive_prompt.strip()
    traits = positive[:-len(item)].rstrip(", ") if item and positive.endswith(item) else positive
    style = (
        compile_prompt_comments(parameters.style_prompt)
        if parameters.prompt_comments else parameters.style_prompt
    ).strip()
    # GPT reads plain text: NovelAI weights would be noise, negative groups the opposite intent.
    traits, item, style = (strip_prompt_weights(text) for text in (traits, item, style))
    lines = [
        "Use the attached reference image(s) only to identify the same character.",
        "Preserve the character identity, facial features, hair, eyes, outfit, accessories "
        "and weapon design and colours.",
        "Create a new image following the requested scene and pose. Pose, limb placement, "
        "expression, gaze, camera angle and framing must follow the scene and pose "
        "instructions, independently of the references.",
        f"Character: {traits}",
    ]
    if item:
        lines.append(f"Scene and pose: {item}")
    if style:
        lines.append(f"Art style: {style}")
    lines.append(
        "Draw one character in one view only. No turnaround sheet, panels, text, watermark "
        "or signature."
    )
    return "\n".join(lines)


class GptImageProvider:
    """One multipart /images/edits call per group; never retried after sending."""

    def __init__(
        self, base_url: str, api_key: str, model: str, *,
        transport: httpx.BaseTransport | None = None, timeout: float = 600.0,
    ):
        self.url = base_url.rstrip("/") + "/images/edits"
        self.api_key = api_key
        self.model = model
        self.transport = transport
        self.timeout = timeout

    def generate(self, parameters: GenerationRequest) -> Sequence[GeneratedImage]:
        raise ProviderFailure("unsupported_reference_mode")

    def generate_with_request(
        self, parameters: GenerationRequest, record_request: Callable[[dict[str, Any]], None],
        *, references: Sequence[bytes] = (), vibe_tokens: VibeTokens | None = None,
    ) -> Sequence[GeneratedImage]:
        reference = parameters.reference
        if (
            reference is None or reference.mode != "gpt" or not references
            or len(references) != len(reference.images)
        ):
            raise ProviderFailure("reference_unavailable")
        fields = {
            "model": self.model, "prompt": gpt_prompt(parameters),
            "size": f"{parameters.width}x{parameters.height}",
            "n": str(parameters.sample_count),
            **({"quality": reference.gpt_quality} if reference.gpt_quality else {}),
        }
        files = [
            ("image[]", (
                f"reference-{index}.{'png' if data.startswith(PNG_SIGNATURE) else 'jpg'}",
                data, "image/png" if data.startswith(PNG_SIGNATURE) else "image/jpeg",
            ))
            for index, data in enumerate(references, 1)
        ]
        # Recorded before the paid call; images only as digests, never the key.
        record_request({
            **fields, "provider": "gpt-image",
            "images": [
                {"sha256": image.sha256, "byte_size": len(data)}
                for image, data in zip(reference.images, references, strict=True)
            ],
        })
        deadline = time.monotonic() + self.timeout
        try:
            with httpx.Client(
                transport=self.transport, timeout=httpx.Timeout(self.timeout, connect=10.0),
                follow_redirects=False,
            ) as client, client.stream(
                "POST", self.url, data=fields, files=files,
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
            ) as response:
                body = read_bounded_body(
                    response, max_bytes=MAX_RESPONSE_BYTES, deadline=deadline,
                    clock=time.monotonic,
                )
                status = response.status_code
            check_deadline(deadline, time.monotonic)
        except httpx.ConnectError as exception:
            # Nothing reached the relay: a definite, unpaid failure.
            raise ProviderFailure("provider_unavailable") from exception
        except (
            httpx.TimeoutException, httpx.RequestError, ResponseDeadlineExceeded,
            InvalidResponseBody,
        ) as exception:
            raise ProviderFailure("outcome_unknown") from exception
        try:
            payload = json.loads(body)
        except (UnicodeError, ValueError) as exception:
            raise ProviderFailure(
                "invalid_result" if status == 200 else "outcome_unknown",
            ) from exception
        if status != 200:
            self._raise_status(status, payload)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise ProviderFailure("invalid_result")
        images = []
        for item in data:
            encoded = item.get("b64_json") if isinstance(item, dict) else None
            if not isinstance(encoded, str) or len(encoded) > (MAX_IMAGE_BYTES + 3) * 4 // 3 + 4:
                raise ProviderFailure("invalid_result")
            try:
                image = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error) as exception:
                raise ProviderFailure("invalid_result") from exception
            if not image.startswith(PNG_SIGNATURE):
                raise ProviderFailure("invalid_result")
            images.append(GeneratedImage(data=image, mime_type="image/png"))
        if len(images) != parameters.sample_count:
            raise ProviderFailure("invalid_result")
        return images

    def _raise_status(self, status: int, payload: Any) -> None:
        error = payload.get("error") if isinstance(payload, dict) else None
        message = ""
        if isinstance(error, dict):
            message = " ".join(
                str(error.get(key)) for key in ("code", "type", "message") if error.get(key)
            )
        elif isinstance(payload, dict):
            message = " ".join(
                str(payload.get(key)) for key in ("code", "message") if payload.get(key)
            )
        # The relay's error text never contains the key or images; keep a bounded copy.
        logger.warning(
            "GPT image request failed (HTTP %s): %s", status,
            re.sub(r"[^\x20-\x7e]+", " ", message.replace(self.api_key, "<key>"))[:300]
            or "(no message)",
        )
        if status in (401, 403):
            raise ProviderFailure("provider_auth_error")
        if status == 429:
            raise ProviderFailure("provider_rate_limited")
        if status == 402 or "quota" in message.lower() or "balance" in message.lower():
            raise ProviderFailure("insufficient_balance")
        if status == 400 and POLICY_WORDS.search(message):
            raise ProviderFailure("content_policy")
        if 400 <= status < 500:
            raise ProviderFailure("invalid_request")
        raise ProviderFailure("outcome_unknown")
