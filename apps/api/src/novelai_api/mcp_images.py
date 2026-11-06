"""NovelAI Streamable HTTP MCP adapter with one non-retried paid tool call."""

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

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 48 * 1024 * 1024
MAX_VIBE_TOKEN_CHARS = 8 * 1024 * 1024
VIBE_TOKEN = re.compile(r"[A-Za-z0-9+/=_-]{16,}")
PROTOCOL_VERSION = "2025-06-18"
REQUIRED_FIELDS = frozenset(
    {
        "prompt",
        "negative_prompt",
        "model",
        "width",
        "height",
        "steps",
        "scale",
        "sampler",
        "seed",
        "n_samples",
        "quality",
    }
)
IMAGE_TO_IMAGE_FIELDS = REQUIRED_FIELDS | {"image", "strength", "noise"}
# NovelAI Precise Reference (director reference) request fields, one entry per image.
PRECISE_FIELDS = frozenset(
    {
        "director_reference_images",
        "director_reference_descriptions",
        "director_reference_information_extracted",
        "director_reference_strength_values",
        "director_reference_secondary_strength_values",
    }
)
# Newer novelai-image MCP servers (4.x) take one Precise Reference image under their
# own names, convert fidelity themselves and letterbox the image (2026-11-04).
NATIVE_PRECISE_FIELDS = frozenset(
    {
        "precise_reference",
        "precise_reference_mode",
        "precise_reference_strength",
        "precise_reference_fidelity",
    }
)
SCHEMA_ANNOTATIONS = frozenset(
    {
        "title", "description", "default", "$comment", "examples", "deprecated",
        "readOnly", "writeOnly",
    }
)


def _accepts_boolean(schema: Any) -> bool:
    """Recognize only the verified boolean or nullable boolean forms."""
    if not isinstance(schema, dict):
        return False
    validation_keys = set(schema) - SCHEMA_ANNOTATIONS
    if validation_keys == {"type"}:
        return schema["type"] == "boolean"
    if validation_keys != {"anyOf"}:
        return False
    alternatives = schema["anyOf"]
    return (
        isinstance(alternatives, list)
        and len(alternatives) == 2
        and all(
            isinstance(option, dict)
            and set(option) - SCHEMA_ANNOTATIONS == {"type"}
            and option["type"] in ("boolean", "null")
            for option in alternatives
        )
        and {option["type"] for option in alternatives} == {"boolean", "null"}
    )


def _accepts_character_objects(schema: Any, count: int) -> bool:
    """Recognize the deployed untyped object contract; reject unverified constraints."""
    if not isinstance(schema, dict):
        return False
    validation_keys = set(schema) - SCHEMA_ANNOTATIONS
    if "anyOf" in schema:
        alternatives = schema["anyOf"]
        return (
            validation_keys == {"anyOf"}
            and isinstance(alternatives, list)
            and any(_accepts_character_objects(option, count) for option in alternatives)
        )
    if not validation_keys.issubset({"type", "items", "minItems", "maxItems"}):
        return False
    minimum = schema.get("minItems", 0)
    maximum = schema.get("maxItems", count)
    if type(minimum) is not int or type(maximum) is not int or not 0 <= minimum <= count <= maximum:
        return False
    items = schema.get("items")
    return (
        schema.get("type") == "array"
        and isinstance(items, dict)
        and items.get("type") == "object"
        and (set(items) - SCHEMA_ANNOTATIONS).issubset({"type", "additionalProperties"})
        and items.get("additionalProperties", True) is True
    )


def _parse_sse(body: bytes, request_id: int) -> dict:
    try:
        text = body.decode("utf-8")
        events = [event for event in re.split(r"\r?\n\r?\n", text) if event.strip()]
        for event in events:
            data = "\n".join(
                line[5:].lstrip() for line in event.splitlines() if line.startswith("data:")
            )
            if data:
                message = json.loads(data)
                if isinstance(message, dict) and message.get("id") == request_id:
                    return message
    except (ValueError, UnicodeError) as exception:
        raise ProviderFailure("invalid_mcp_response") from exception
    raise ProviderFailure("invalid_mcp_response")


class NovelAiMcpProvider:
    def __init__(
        self,
        url: str,
        token: str,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 180.0,
        image_to_image_timeout: float = 600.0,
    ):
        self.url = url
        self.token = token
        self.transport = transport
        self.timeout = timeout
        # Upstream image_to_image took ~132 s for one image (2026-10-29); a short deadline
        # would turn slow paid calls into outcome_unknown.
        self.image_to_image_timeout = max(timeout, image_to_image_timeout)

    def probe(self) -> bool:
        """Unpaid reachability check: one MCP initialize, short deadline, no tool call."""
        try:
            with httpx.Client(
                transport=self.transport, timeout=httpx.Timeout(10.0, connect=5.0),
                follow_redirects=False,
            ) as client:
                response = client.post(
                    self.url,
                    json={
                        "jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {
                            "protocolVersion": PROTOCOL_VERSION,
                            "capabilities": {},
                            "clientInfo": {"name": "novelai-workspace", "version": "0.1.0"},
                        },
                    },
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/json, text/event-stream",
                        "Content-Type": "application/json",
                    },
                )
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    def generate(self, parameters: GenerationRequest) -> Sequence[GeneratedImage]:
        return self.generate_with_request(parameters, lambda _arguments: None)

    def generate_with_request(
        self, parameters: GenerationRequest, record_request: Callable[[dict[str, Any]], None],
        *, references: Sequence[bytes] = (), vibe_tokens: VibeTokens | None = None,
    ) -> Sequence[GeneratedImage]:
        reference = parameters.reference
        if (reference is None) != (not references) or (
            reference is not None and len(references) != len(reference.images)
        ):
            raise ProviderFailure("reference_unavailable")
        tool_name = (
            "image_to_image" if reference is not None and reference.mode == "img2img"
            else "generate_image"
        )
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json, text/event-stream",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
        }
        session_id: str | None = None
        request_id = 0

        def send(
            client: httpx.Client,
            method: str,
            params: dict[str, Any] | None = None,
            *,
            paid: bool = False,
            notification: bool = False,
            timeout: float | None = None,
        ) -> dict:
            nonlocal request_id, session_id
            if not notification:
                request_id += 1
            payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
            if not notification:
                payload["id"] = request_id
            if params is not None:
                payload["params"] = params
            if session_id:
                headers["Mcp-Session-Id"] = session_id
                headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
            limit = timeout or self.timeout
            deadline = time.monotonic() + limit
            try:
                with client.stream(
                    "POST", self.url, json=payload, headers=headers,
                    timeout=httpx.Timeout(limit, connect=5.0),
                ) as response:
                    check_deadline(deadline, time.monotonic)
                    if response.status_code != 200 and not (
                        notification and response.status_code in (202, 204)
                    ):
                        self._check_status(response.status_code, paid=paid)
                    session_id = response.headers.get("Mcp-Session-Id", session_id)
                    if notification:
                        return {}
                    body = read_bounded_body(
                        response,
                        max_bytes=MAX_RESPONSE_BYTES,
                        deadline=deadline,
                        clock=time.monotonic,
                    )
                    if "text/event-stream" in response.headers.get("Content-Type", ""):
                        message = _parse_sse(body, request_id)
                    else:
                        try:
                            message = json.loads(body)
                        except (UnicodeError, ValueError) as exception:
                            raise ProviderFailure("invalid_mcp_response") from exception
                    check_deadline(deadline, time.monotonic)
            except (ResponseDeadlineExceeded, InvalidResponseBody) as exception:
                failure = "outcome_unknown" if paid else "invalid_mcp_response"
                raise ProviderFailure(failure) from exception
            except (httpx.TimeoutException, httpx.RequestError) as exception:
                failure = "outcome_unknown" if paid else "provider_unavailable"
                raise ProviderFailure(failure) from exception
            if not isinstance(message, dict) or message.get("id") != request_id:
                raise ProviderFailure("invalid_mcp_response")
            if "error" in message:
                remote_error = message.get("error")
                if isinstance(remote_error, dict) and remote_error.get("code") == -32602:
                    raise ProviderFailure("invalid_request")
                raise ProviderFailure("provider_error")
            result = message.get("result")
            if not isinstance(result, dict):
                raise ProviderFailure("invalid_mcp_response")
            return result

        with httpx.Client(
            transport=self.transport,
            timeout=httpx.Timeout(self.timeout, connect=5.0),
            follow_redirects=False,
        ) as client:
            result = send(
                client,
                "initialize",
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "novelai-workspace", "version": "0.1.0"},
                },
            )
            if result.get("protocolVersion") != PROTOCOL_VERSION:
                raise ProviderFailure("incompatible_mcp_server")
            send(client, "notifications/initialized", notification=True)
            available = send(client, "tools/list", {})
            tools = available.get("tools")
            if not isinstance(tools, list):
                raise ProviderFailure("incompatible_mcp_server")
            schema = next(
                (
                    tool.get("inputSchema")
                    for tool in tools
                    if isinstance(tool, dict) and tool.get("name") == tool_name
                ),
                None,
            )
            if reference is not None and (
                not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict)
                or (reference.mode == "img2img"
                    and not IMAGE_TO_IMAGE_FIELDS.issubset(schema["properties"]))
                or (reference.mode == "precise"
                    and not PRECISE_FIELDS.issubset(schema["properties"])
                    and not NATIVE_PRECISE_FIELDS.issubset(schema["properties"]))
                or (reference.mode == "vibe" and (
                    "references" not in schema["properties"]
                    # V4/V4.5 vibes must be pre-encoded; raw images make NovelAI fail (500).
                    or not any(
                        isinstance(tool, dict) and tool.get("name") == "encode_vibe"
                        and "reference" in ((tool.get("inputSchema") or {}).get("properties") or {})
                        for tool in tools
                    )
                ))
            ):
                raise ProviderFailure("unsupported_reference_mode")
            if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
                raise ProviderFailure("incompatible_mcp_server")
            properties = schema["properties"]
            if not REQUIRED_FIELDS.issubset(properties):
                raise ProviderFailure("incompatible_mcp_server")
            arguments = {
                "prompt": parameters.base_prompt,
                "negative_prompt": parameters.effective_negative_prompt,
                "model": parameters.model,
                "width": parameters.width,
                "height": parameters.height,
                "steps": parameters.steps,
                "scale": parameters.cfg_scale,
                "sampler": parameters.sampler,
                "seed": parameters.seed,
                "n_samples": parameters.sample_count,
                "quality": parameters.quality,
            }
            characters = parameters.effective_character_prompts
            if characters:
                if not _accepts_character_objects(
                    properties.get("character_prompts"), len(characters)
                ):
                    raise ProviderFailure("unsupported_character_prompts")
                supports_position_mode = _accepts_boolean(properties.get("auto_character_position"))
                if parameters.auto_character_position and not supports_position_mode:
                    raise ProviderFailure("unsupported_auto_character_position")
                if supports_position_mode:
                    arguments["auto_character_position"] = parameters.auto_character_position
                arguments["character_prompts"] = [
                    {
                        "prompt": character.prompt,
                        "negative_prompt": "",
                        "enabled": True,
                        **({} if parameters.auto_character_position else {
                            "x": character.x, "y": character.y,
                        }),
                    }
                    for character in characters
                ]
            if parameters.prompt_comments:
                # Compile comments before removing physical line boundaries; editor
                # source and literal backslash escapes remain unchanged.
                for prompt_fields in (arguments, *arguments.get("character_prompts", [])):
                    for field in ("prompt", "negative_prompt"):
                        prompt_fields[field] = re.sub(r"[\r\n]+", " ", prompt_fields[field])
            for field in ("model", "sampler"):
                field_schema = properties[field]
                choices = field_schema.get("enum") if isinstance(field_schema, dict) else None
                if isinstance(choices, list) and arguments[field] not in choices:
                    raise ProviderFailure("unsupported_setting")
            encoded = [base64.b64encode(data).decode("ascii") for data in references]
            if reference is not None and reference.mode == "img2img":
                arguments.update(
                    image=encoded[0], strength=reference.strength, noise=reference.noise,
                )
                if "extra_noise_seed" in properties:
                    arguments["extra_noise_seed"] = parameters.seed
            native_precise = NATIVE_PRECISE_FIELDS.issubset(properties)
            if reference is not None and reference.mode == "precise" and native_precise:
                arguments.update(
                    precise_reference=encoded[0],
                    precise_reference_mode=reference.precise_type,
                    precise_reference_strength=reference.precise_strength,
                    # The server applies NovelAI's complement itself (1.0 = closest).
                    precise_reference_fidelity=reference.precise_fidelity,
                )
            elif reference is not None and reference.mode == "precise":
                arguments.update(
                    director_reference_images=[encoded[0]],
                    director_reference_descriptions=[{
                        "caption": {"base_caption": reference.precise_type, "char_captions": []},
                        "legacy_uc": False,
                    }],
                    director_reference_information_extracted=[1.0],
                    director_reference_strength_values=[reference.precise_strength],
                    # NovelAI sends fidelity as its complement (fidelity 1.0 -> 0.0).
                    director_reference_secondary_strength_values=[
                        round(1.0 - reference.precise_fidelity, 6)
                    ],
                )
            if reference is not None and reference.mode == "vibe" and (
                reference.reference_strength is not None
            ):
                if "reference_strengths" not in properties:
                    raise ProviderFailure("unsupported_reference_mode")
                arguments["reference_strengths"] = (
                    [reference.reference_strength] * len(reference.images)
                )
            required = schema.get("required", [])
            if not isinstance(required, list) or not set(required).issubset(arguments):
                raise ProviderFailure("incompatible_mcp_server")
            # Persist the exact allowlisted body before the sole paid call, including
            # uncertain outcomes. Headers, credentials and editor metadata stay out;
            # image payloads are recorded only as their frozen digests and sizes.
            snapshot = dict(arguments)
            if reference is not None:
                digests = [
                    {"sha256": image.sha256, "byte_size": len(data)}
                    for image, data in zip(reference.images, references, strict=True)
                ]
                if reference.mode == "img2img":
                    snapshot["image"] = digests[0]
                elif reference.mode == "precise" and native_precise:
                    snapshot["precise_reference"] = digests[0]
                elif reference.mode == "precise":
                    snapshot["director_reference_images"] = digests
                else:
                    snapshot["references"] = [
                        {**digest, "information_extracted": reference.vibe_information}
                        for digest in digests
                    ]
            # Recorded before any paid call (vibe encoding included).
            record_request(snapshot)
            if reference is not None and reference.mode == "vibe":
                tokens = []
                for image, data in zip(reference.images, encoded, strict=True):
                    information = reference.vibe_information
                    token = (
                        vibe_tokens.get(image.sha256, parameters.model, information)
                        if vibe_tokens is not None else None
                    )
                    if token is None:
                        token = self._vibe_token(send(
                            client, "tools/call",
                            {"name": "encode_vibe", "arguments": {
                                "reference": data, "information_extracted": information,
                                "model": parameters.model,
                            }},
                            paid=True,
                        ))
                        if vibe_tokens is not None:
                            vibe_tokens.put(image.sha256, parameters.model, information, token)
                    tokens.append(token)
                arguments["references"] = tokens
            result = send(
                client,
                "tools/call",
                {"name": tool_name, "arguments": arguments},
                paid=True,
                timeout=self.image_to_image_timeout if tool_name == "image_to_image" else None,
            )
        self._raise_tool_error(result, tool_name)
        content = result.get("content")
        if not isinstance(content, list):
            raise ProviderFailure("invalid_result")
        images: list[GeneratedImage] = []
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "image":
                continue
            if item.get("mimeType") != "image/png" or not isinstance(item.get("data"), str):
                raise ProviderFailure("invalid_result")
            data = item["data"]
            if len(data) > (MAX_IMAGE_BYTES + 3) * 4 // 3 + 4:
                raise ProviderFailure("invalid_result")
            try:
                image = base64.b64decode(data, validate=True)
            except (ValueError, binascii.Error) as exception:
                raise ProviderFailure("invalid_result") from exception
            images.append(GeneratedImage(data=image, mime_type="image/png"))
        if len(images) != parameters.sample_count:
            raise ProviderFailure("invalid_result")
        return images

    @staticmethod
    def _raise_tool_error(result: dict, tool_name: str) -> None:
        if result.get("isError") is not True:
            return
        content = result.get("content")
        text = (
            " ".join(
                item["text"][:256]
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            )
            if isinstance(content, list)
            else ""
        )
        # Upstream error text names no credentials; keep a bounded single-line copy for
        # diagnosis (it never echoes request images or tokens).
        logger.warning(
            "NovelAI tool %s failed: %s", tool_name,
            re.sub(r"[^\x20-\x7e]+", " ", text)[:300] or "(no message)",
        )
        lowered = text.lower()
        if "anlas" in lowered or "insufficient" in lowered or "balance" in lowered:
            raise ProviderFailure("insufficient_balance")
        raise ProviderFailure("provider_error")

    @classmethod
    def _vibe_token(cls, result: dict) -> str:
        cls._raise_tool_error(result, "encode_vibe")
        candidates: list[Any] = []
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            candidates.extend(structured.values())
        content = result.get("content")
        if isinstance(content, list):
            candidates.extend(
                item.get("text") for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            )
        for candidate in candidates:
            if isinstance(candidate, str):
                token = candidate.strip()
                if len(token) <= MAX_VIBE_TOKEN_CHARS and VIBE_TOKEN.fullmatch(token):
                    return token
        raise ProviderFailure("invalid_result")

    @staticmethod
    def _check_status(status: int, *, paid: bool) -> None:
        if status in (401, 403):
            raise ProviderFailure("provider_auth_error")
        if status == 402:
            raise ProviderFailure("insufficient_balance")
        if status == 422:
            raise ProviderFailure("invalid_request")
        if status == 429:
            raise ProviderFailure("provider_rate_limited")
        if paid:
            raise ProviderFailure("outcome_unknown")
        raise ProviderFailure("provider_unavailable")
