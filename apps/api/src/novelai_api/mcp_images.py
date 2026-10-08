"""NovelAI Streamable HTTP MCP adapter with one non-retried paid tool call."""

import base64
import binascii
import json
import re
import time
from collections.abc import Sequence
from typing import Any

import httpx

from .generations import (
    MAX_IMAGE_BYTES,
    GeneratedImage,
    GenerationRequest,
    ProviderFailure,
)


MAX_RESPONSE_BYTES = 48 * 1024 * 1024
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
    ):
        self.url = url
        self.token = token
        self.transport = transport
        self.timeout = timeout

    def generate(self, parameters: GenerationRequest) -> Sequence[GeneratedImage]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json, text/event-stream",
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
            try:
                with client.stream("POST", self.url, json=payload, headers=headers) as response:
                    if response.status_code != 200 and not (
                        notification and response.status_code in (202, 204)
                    ):
                        self._check_status(response.status_code, paid=paid)
                    session_id = response.headers.get("Mcp-Session-Id", session_id)
                    if notification:
                        return {}
                    chunks: list[bytes] = []
                    size = 0
                    deadline = time.monotonic() + self.timeout
                    for chunk in response.iter_bytes(chunk_size=65536):
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES or time.monotonic() >= deadline:
                            failure = "outcome_unknown" if paid else "invalid_mcp_response"
                            raise ProviderFailure(failure)
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    if "text/event-stream" in response.headers.get("Content-Type", ""):
                        message = _parse_sse(body, request_id)
                    else:
                        try:
                            message = json.loads(body)
                        except (UnicodeError, ValueError) as exception:
                            raise ProviderFailure("invalid_mcp_response") from exception
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
                    if isinstance(tool, dict) and tool.get("name") == "generate_image"
                ),
                None,
            )
            if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
                raise ProviderFailure("incompatible_mcp_server")
            properties = schema["properties"]
            if not REQUIRED_FIELDS.issubset(properties):
                raise ProviderFailure("incompatible_mcp_server")
            arguments = {
                "prompt": parameters.positive_prompt,
                "negative_prompt": parameters.negative_prompt,
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
            for field in ("model", "sampler"):
                field_schema = properties[field]
                choices = field_schema.get("enum") if isinstance(field_schema, dict) else None
                if isinstance(choices, list) and arguments[field] not in choices:
                    raise ProviderFailure("unsupported_setting")
            required = schema.get("required", [])
            if not isinstance(required, list) or not set(required).issubset(arguments):
                raise ProviderFailure("incompatible_mcp_server")
            result = send(
                client,
                "tools/call",
                {"name": "generate_image", "arguments": arguments},
                paid=True,
            )
        if result.get("isError") is True:
            content = result.get("content")
            text = (
                " ".join(
                    item["text"][:256].lower()
                    for item in content
                    if isinstance(item, dict) and isinstance(item.get("text"), str)
                )
                if isinstance(content, list)
                else ""
            )
            if "anlas" in text or "insufficient" in text or "balance" in text:
                raise ProviderFailure("insufficient_balance")
            raise ProviderFailure("provider_error")
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
