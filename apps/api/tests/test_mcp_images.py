"""Every MCP generation test uses MockTransport; no paid server is contacted."""

import base64
import json
import zlib
from gzip import compress as gzip_compress
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

import novelai_api._http_response as http_response
import novelai_api.mcp_images as mcp_images
from novelai_api.app import create_app
from novelai_api.auth import create_token
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import GenerationRequest, ProviderFailure
from novelai_api.mcp_images import NovelAiMcpProvider

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j"
    "RZkAAAAASUVORK5CYII="
)
PARAMETERS = GenerationRequest(
    positive_prompt="blue_hair",
    negative_prompt="blurry",
    model="fixture-model",
    width=512,
    height=512,
    steps=28,
    cfg_scale=5.0,
    sampler="fixture-sampler",
    seed=77,
    sample_count=2,
    quality=True,
)
SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {},
        "negative_prompt": {},
        "model": {},
        "width": {},
        "height": {},
        "steps": {},
        "scale": {},
        "sampler": {},
        "seed": {},
        "n_samples": {},
        "quality": {},
    },
    "required": ["prompt"],
}
CHARACTER_SCHEMA = {
    "anyOf": [
        {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        {"type": "null"},
    ],
    "default": None,
}


def native_parameters() -> GenerationRequest:
    return GenerationRequest.model_validate({
        **PARAMETERS.model_dump(),
        "model": "nai-diffusion-5-full",
        "style_prompt": " watercolor ",
        "positive_prompt": " garden, 2girls ",
        "character_prompts": [{"prompt": " blue hair "}, {"prompt": "red hair, glasses"}],
    })


def mock_mcp(*, schema=SCHEMA, result=None, tool_status=200, tool_content_type="application/json"):
    calls = []

    def handler(request: httpx.Request):
        assert request.method == "POST"
        assert request.url.path == "/novel-ai-v5"
        assert request.headers["Authorization"] == "Bearer fake-mcp-token"
        assert "text/event-stream" in request.headers["Accept"]
        payload = json.loads(request.content)
        calls.append(payload)
        method = payload["method"]
        if method == "notifications/initialized":
            assert request.headers["Mcp-Session-Id"] == "test-session"
            return httpx.Response(202)
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {"protocolVersion": "2025-06-18"},
            }
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream", "Mcp-Session-Id": "test-session"},
                content=("event: message\r\ndata: " + json.dumps(response) + "\r\n\r\n"),
            )
        assert request.headers["Mcp-Session-Id"] == "test-session"
        if method == "tools/list":
            response = {"tools": [{"name": "generate_image", "inputSchema": schema}]}
        else:
            assert method == "tools/call"
            if tool_status != 200:
                return httpx.Response(tool_status, text="private upstream payload")
            response = result if result is not None else {
                "content": [
                    {"type": "text", "text": "server-only /private/image/path"},
                    {
                        "type": "image", "mimeType": "image/png",
                        "data": base64.b64encode(PNG).decode(),
                    },
                    {
                        "type": "image", "mimeType": "image/png",
                        "data": base64.b64encode(PNG).decode(),
                    },
                ]
            }
        return httpx.Response(
            200,
            headers={"Content-Type": tool_content_type},
            json={"jsonrpc": "2.0", "id": payload["id"], "result": response},
        )

    return httpx.MockTransport(handler), calls


def provider_for(transport: httpx.MockTransport) -> NovelAiMcpProvider:
    return NovelAiMcpProvider(
        "https://mcp.example/novel-ai-v5", "fake-mcp-token", transport=transport
    )


class TrackingStream(httpx.SyncByteStream):
    def __init__(self, chunks: list[bytes], *, on_chunk=None, on_eof=None):
        self.chunks = chunks
        self.on_chunk = on_chunk
        self.on_eof = on_eof
        self.read_count = 0
        self.closed = False

    def __iter__(self):
        for chunk in self.chunks:
            self.read_count += 1
            if self.on_chunk is not None:
                self.on_chunk()
            yield chunk
        if self.on_eof is not None:
            self.on_eof()

    def close(self):
        self.closed = True


def streamed_mcp(method: str | None, respond):
    base, calls = mock_mcp()

    def handler(request: httpx.Request):
        response = base.handle_request(request)
        actual_method = json.loads(request.content)["method"]
        if actual_method == method or (
            method is None and actual_method != "notifications/initialized"
        ):
            return respond(response)
        return response

    return httpx.MockTransport(handler), calls


@pytest.mark.parametrize("method", ["initialize", "tools/call"])
def test_tiny_slow_chunks_stop_at_rpc_deadline_without_retry(
    monkeypatch: pytest.MonkeyPatch, method: str,
) -> None:
    clock = [0.0]
    monkeypatch.setattr(mcp_images.time, "monotonic", lambda: clock[0])

    def advance_clock() -> None:
        clock[0] += 1.0

    slow = TrackingStream([b" "] * 20, on_chunk=advance_clock)
    transport, calls = streamed_mcp(method, lambda _: httpx.Response(200, stream=slow))
    provider = provider_for(transport)
    provider.timeout = 3.0
    failure = "outcome_unknown" if method == "tools/call" else "invalid_mcp_response"
    with pytest.raises(ProviderFailure, match=failure):
        provider.generate(PARAMETERS)
    assert slow.read_count == 3
    assert slow.closed
    assert [call["method"] for call in calls].count("tools/call") == (method == "tools/call")


@pytest.mark.parametrize("method", ["initialize", "notifications/initialized", "tools/call"])
def test_rpc_deadline_includes_opening_response(
    monkeypatch: pytest.MonkeyPatch, method: str,
) -> None:
    clock = [0.0]
    monkeypatch.setattr(mcp_images.time, "monotonic", lambda: clock[0])
    stream = TrackingStream([b"private upstream response"])

    def delayed_response(_response: httpx.Response) -> httpx.Response:
        clock[0] += 4.0
        return httpx.Response(200, stream=stream)

    transport, calls = streamed_mcp(method, delayed_response)
    provider = provider_for(transport)
    provider.timeout = 3.0
    failure = "outcome_unknown" if method == "tools/call" else "invalid_mcp_response"
    with pytest.raises(ProviderFailure, match=failure):
        provider.generate(PARAMETERS)
    assert stream.read_count == 0
    assert stream.closed
    assert [call["method"] for call in calls].count("tools/call") == (method == "tools/call")


@pytest.mark.parametrize("phase", ["eof", "parse"])
def test_paid_rpc_checks_deadline_after_eof_and_parsing(
    monkeypatch: pytest.MonkeyPatch, phase: str,
) -> None:
    clock = [0.0]
    monkeypatch.setattr(mcp_images.time, "monotonic", lambda: clock[0])

    def advance_clock() -> None:
        clock[0] += 4.0

    original_loads = json.loads

    def slow_loads(body, *args, **kwargs):
        message = original_loads(body, *args, **kwargs)
        if isinstance(message, dict) and message.get("id") == 3 and "result" in message:
            advance_clock()
        return message

    if phase == "parse":
        monkeypatch.setattr(mcp_images.json, "loads", slow_loads)
    streams = []

    def respond(response: httpx.Response) -> httpx.Response:
        stream = TrackingStream(
            [response.content], on_eof=advance_clock if phase == "eof" else None,
        )
        streams.append(stream)
        return httpx.Response(200, stream=stream)

    transport, calls = streamed_mcp("tools/call", respond)
    provider = provider_for(transport)
    provider.timeout = 3.0
    with pytest.raises(ProviderFailure, match="outcome_unknown"):
        provider.generate(PARAMETERS)
    assert streams[0].closed
    assert [call["method"] for call in calls].count("tools/call") == 1


@pytest.mark.parametrize("method", ["initialize", "tools/call"])
def test_raw_stream_read_timeout_keeps_transport_error_mapping(method: str) -> None:
    def timeout() -> None:
        raise httpx.ReadTimeout("private upstream timeout")

    stream = TrackingStream([b" "], on_chunk=timeout)
    transport, calls = streamed_mcp(method, lambda _: httpx.Response(200, stream=stream))
    failure = "outcome_unknown" if method == "tools/call" else "provider_unavailable"
    with pytest.raises(ProviderFailure, match=failure) as exception:
        provider_for(transport).generate(PARAMETERS)
    assert "private" not in str(exception.value)
    assert stream.closed
    assert [call["method"] for call in calls].count("tools/call") == (method == "tools/call")


@pytest.mark.parametrize("method", ["initialize", "tools/call"])
def test_compressed_expansion_is_capped_before_allocating_the_full_body(
    monkeypatch: pytest.MonkeyPatch, method: str,
) -> None:
    cap = 1024
    bomb = TrackingStream([gzip_compress(b" " * 100000), b"private upstream tail"])
    original_decompressobj = zlib.decompressobj
    allocations = []

    class TrackingDecoder:
        def __init__(self, *args, **kwargs):
            self.decoder = original_decompressobj(*args, **kwargs)

        def decompress(self, data, max_length=0):
            decoded = self.decoder.decompress(data, max_length)
            allocations.append(len(decoded))
            return decoded

        def __getattr__(self, name):
            return getattr(self.decoder, name)

    monkeypatch.setattr(http_response.zlib, "decompressobj", TrackingDecoder)
    monkeypatch.setattr(mcp_images, "MAX_RESPONSE_BYTES", cap)
    transport, calls = streamed_mcp(
        method,
        lambda _: httpx.Response(200, stream=bomb, headers={"Content-Encoding": "gzip"}),
    )
    failure = "outcome_unknown" if method == "tools/call" else "invalid_mcp_response"
    with pytest.raises(ProviderFailure, match=failure) as exception:
        provider_for(transport).generate(PARAMETERS)
    assert allocations and max(allocations) <= cap + 1
    assert bomb.read_count == 1
    assert bomb.closed
    assert "private" not in str(exception.value)
    assert "fake-mcp-token" not in str(exception.value)
    assert [call["method"] for call in calls].count("tools/call") == (method == "tools/call")


@pytest.mark.parametrize("method", ["initialize", "tools/call"])
def test_identity_response_stops_before_reading_beyond_cap(
    monkeypatch: pytest.MonkeyPatch, method: str,
) -> None:
    monkeypatch.setattr(mcp_images, "MAX_RESPONSE_BYTES", 1024)
    oversized = TrackingStream([b" " * 512, b" " * 512, b"x", b"private upstream tail"])
    transport, calls = streamed_mcp(method, lambda _: httpx.Response(200, stream=oversized))
    failure = "outcome_unknown" if method == "tools/call" else "invalid_mcp_response"
    with pytest.raises(ProviderFailure, match=failure):
        provider_for(transport).generate(PARAMETERS)
    assert oversized.read_count == 3
    assert oversized.closed
    assert [call["method"] for call in calls].count("tools/call") == (method == "tools/call")


@pytest.mark.parametrize(
    ("encoding", "compress"),
    [
        ("identity", lambda body: body),
        ("gzip", gzip_compress),
        ("deflate", zlib.compress),
        ("deflate", lambda body: zlib.compress(body)[2:-4]),
    ],
)
@pytest.mark.parametrize("content_type", ["application/json", "text/event-stream"])
def test_streamed_json_and_sse_decode_at_the_exact_cap(
    monkeypatch: pytest.MonkeyPatch, encoding: str, compress, content_type: str,
) -> None:
    monkeypatch.setattr(mcp_images, "MAX_RESPONSE_BYTES", 1024)
    streams = []

    def respond(response: httpx.Response) -> httpx.Response:
        body = response.content
        if response.headers.get("Content-Type") == "text/event-stream":
            body = body.split(b"data: ", 1)[1].strip()
        if content_type == "text/event-stream":
            body = b"event: message\ndata: " + body + b"\n\n"
        assert len(body) < 1024
        encoded = compress(body.ljust(1024))
        # Split the compression header into single-byte transport chunks.
        stream = TrackingStream([encoded[:1], encoded[1:2], encoded[2:]])
        streams.append(stream)
        return httpx.Response(
            200,
            stream=stream,
            headers={
                "Content-Type": content_type,
                "Content-Encoding": encoding,
                "Mcp-Session-Id": "test-session",
            },
        )

    transport, calls = streamed_mcp(None, respond)
    images = provider_for(transport).generate(PARAMETERS)
    assert [image.data for image in images] == [PNG, PNG]
    assert len(streams) == 3
    assert all(stream.closed and stream.read_count == 3 for stream in streams)
    assert [call["method"] for call in calls].count("tools/call") == 1


@pytest.mark.parametrize("method", ["initialize", "tools/call"])
@pytest.mark.parametrize(
    "body",
    [
        b"private upstream invalid gzip",
        gzip_compress(b"private upstream truncated body")[:-4],
        gzip_compress(b"private upstream body") + b"private trailing data",
    ],
)
def test_invalid_compression_is_safe_and_never_retries(method: str, body: bytes) -> None:
    stream = TrackingStream([body])
    transport, calls = streamed_mcp(
        method,
        lambda _: httpx.Response(200, stream=stream, headers={"Content-Encoding": "gzip"}),
    )
    failure = "outcome_unknown" if method == "tools/call" else "invalid_mcp_response"
    with pytest.raises(ProviderFailure, match=failure) as exception:
        provider_for(transport).generate(PARAMETERS)
    assert "private" not in str(exception.value)
    assert "fake-mcp-token" not in str(exception.value)
    assert stream.closed
    assert [call["method"] for call in calls].count("tools/call") == (method == "tools/call")


def test_mcp_provider_is_only_configured_with_server_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = Database(tmp_path / "test.sqlite3")
    provider = provider_for(mock_mcp()[0])
    configured = []

    def build_provider(url: str, token: str) -> NovelAiMcpProvider:
        configured.append((url, token))
        return provider

    monkeypatch.setattr("novelai_api.app.NovelAiMcpProvider", build_provider)
    without_token = create_app(Settings(database.path, "https://testserver"), database)
    assert without_token.state.generations.provider is None
    assert configured == []

    settings = Settings(
        database.path,
        "https://testserver",
        novelai_mcp_url="https://mcp.example/novel-ai-v5",
        novelai_mcp_token="server-only-token",
    )
    with_token = create_app(settings, database)
    assert with_token.state.generations.provider is provider
    assert configured == [("https://mcp.example/novel-ai-v5", "server-only-token")]


def test_verified_schema_calls_exactly_one_paid_tool_and_ignores_remote_paths() -> None:
    transport, calls = mock_mcp()
    images = provider_for(transport).generate(PARAMETERS)
    assert len(images) == 2
    assert all(image.data == PNG for image in images)
    assert [call["method"] for call in calls] == [
        "initialize", "notifications/initialized", "tools/list", "tools/call"
    ]
    assert calls[-1]["params"] == {
        "name": "generate_image",
        "arguments": {
            "prompt": "blue_hair",
            "negative_prompt": "blurry",
            "model": "fixture-model",
            "width": 512,
            "height": 512,
            "steps": 28,
            "scale": 5.0,
            "sampler": "fixture-sampler",
            "seed": 77,
            "n_samples": 2,
            "quality": True,
        },
    }


@pytest.mark.parametrize(
    "character_schema",
    [
        CHARACTER_SCHEMA,
        {"type": "array", "items": {"type": "object"}},
        {
            "type": "array", "minItems": 1, "maxItems": 6,
            "title": "Characters", "description": "Independent captions", "default": [],
            "items": {"type": "object", "title": "Character", "default": {}},
        },
    ],
)
def test_native_characters_keep_boundaries_order_and_centered_provider_defaults(
    character_schema: dict,
) -> None:
    schema = {
        **SCHEMA,
        "properties": {**SCHEMA["properties"], "character_prompts": character_schema},
    }
    transport, calls = mock_mcp(schema=schema)
    images = provider_for(transport).generate(native_parameters())
    assert [image.data for image in images] == [PNG, PNG]
    assert [call["method"] for call in calls] == [
        "initialize", "notifications/initialized", "tools/list", "tools/call"
    ]
    assert calls[-1]["params"] == {
        "name": "generate_image",
        "arguments": {
            "prompt": "watercolor, garden, 2girls",
            "negative_prompt": "blurry",
            "model": "nai-diffusion-5-full",
            "width": 512,
            "height": 512,
            "steps": 28,
            "scale": 5.0,
            "sampler": "fixture-sampler",
            "seed": 77,
            "n_samples": 2,
            "quality": True,
            "character_prompts": [
                {
                    "prompt": " blue hair ", "negative_prompt": "",
                    "x": 0.5, "y": 0.5, "enabled": True,
                },
                {
                    "prompt": "red hair, glasses", "negative_prompt": "",
                    "x": 0.5, "y": 0.5, "enabled": True,
                },
            ],
        },
    }


def test_native_character_coordinates_are_forwarded_exactly_in_order() -> None:
    parameters = GenerationRequest.model_validate({
        **native_parameters().model_dump(),
        "character_prompts": [
            {"prompt": "left character", "x": 0.1, "y": 0.9},
            {"prompt": "right character", "x": 0.73, "y": 0.27},
            {"prompt": "old centered character"},
        ],
    })
    schema = {
        **SCHEMA,
        "properties": {**SCHEMA["properties"], "character_prompts": CHARACTER_SCHEMA},
    }
    transport, calls = mock_mcp(schema=schema)
    provider_for(transport).generate(parameters)
    paid_calls = [call for call in calls if call["method"] == "tools/call"]
    assert len(paid_calls) == 1
    assert paid_calls[0]["params"]["arguments"]["character_prompts"] == [
        {
            "prompt": "left character", "negative_prompt": "",
            "x": 0.1, "y": 0.9, "enabled": True,
        },
        {
            "prompt": "right character", "negative_prompt": "",
            "x": 0.73, "y": 0.27, "enabled": True,
        },
        {
            "prompt": "old centered character", "negative_prompt": "",
            "x": 0.5, "y": 0.5, "enabled": True,
        },
    ]


@pytest.mark.parametrize(
    ("style", "shared", "expected"),
    [
        ("", "  original text  ", "  original text  "),
        (" \t", "  original text  ", "  original text  "),
        (" watercolor ", " garden ", "watercolor, garden"),
        (" watercolor ", "", "watercolor"),
    ],
)
def test_flat_style_composition_retains_legacy_payload_and_editable_model(
    style: str, shared: str, expected: str,
) -> None:
    parameters = GenerationRequest.model_validate({
        **PARAMETERS.model_dump(), "style_prompt": style, "positive_prompt": shared,
    })
    transport, calls = mock_mcp()
    provider_for(transport).generate(parameters)
    arguments = calls[-1]["params"]["arguments"]
    assert arguments["prompt"] == expected
    assert arguments["model"] == "fixture-model"
    assert len(arguments) == 11
    assert "style_prompt" not in arguments
    assert "character_prompts" not in arguments


@pytest.mark.parametrize("native", [False, True])
def test_workspace_experiment_metadata_never_changes_provider_arguments(native: bool) -> None:
    base = native_parameters() if native else PARAMETERS
    parameters = GenerationRequest.model_validate({
        **base.model_dump(),
        "experiment": {
            "id": str(uuid4()), "ordinal": "1", "total": "9" * 1000,
            "weights": [{"tag_index": 0, "label": "artist:fixture", "weight": "1.0"}],
        },
    })
    schema = {
        **SCHEMA,
        "properties": {**SCHEMA["properties"], "character_prompts": CHARACTER_SCHEMA},
    } if native else SCHEMA
    plain_transport, plain_calls = mock_mcp(schema=schema)
    experiment_transport, experiment_calls = mock_mcp(schema=schema)
    provider_for(plain_transport).generate(base)
    provider_for(experiment_transport).generate(parameters)
    assert experiment_calls[-1]["params"]["arguments"] == plain_calls[-1]["params"]["arguments"]
    assert len(experiment_calls[-1]["params"]["arguments"]) == (12 if native else 11)


@pytest.mark.parametrize(
    "character_schema",
    [
        None,
        {},
        {"type": "string"},
        {"type": "object"},
        {"type": "array"},
        {"type": "array", "items": {}},
        {"type": "array", "items": {"type": "string"}},
        {"anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}]},
        {"type": "array", "maxItems": 1, "items": {"type": "object"}},
        {"type": "array", "minItems": 3, "items": {"type": "object"}},
        {"type": "array", "maxItems": "6", "items": {"type": "object"}},
        {"type": "array", "uniqueItems": True, "items": {"type": "object"}},
        {"type": "array", "items": {"type": "object", "required": ["unknown_field"]}},
        {"type": "array", "items": {"type": "object", "additionalProperties": False}},
        {
            "type": "array",
            "items": {"type": "object", "properties": {"prompt": {"type": "integer"}}},
        },
        {"type": "string", "anyOf": [{"type": "array", "items": {"type": "object"}}]},
    ],
)
def test_unsupported_character_schema_fails_before_paid_tool(character_schema) -> None:
    properties = dict(SCHEMA["properties"])
    if character_schema is not None:
        properties["character_prompts"] = character_schema
    transport, calls = mock_mcp(schema={**SCHEMA, "properties": properties})
    with pytest.raises(ProviderFailure, match="^unsupported_character_prompts$"):
        provider_for(transport).generate(native_parameters())
    assert [call["method"] for call in calls] == [
        "initialize", "notifications/initialized", "tools/list"
    ]


def test_uncertain_native_paid_response_never_retries_or_falls_back_to_flat() -> None:
    schema = {
        **SCHEMA,
        "properties": {**SCHEMA["properties"], "character_prompts": CHARACTER_SCHEMA},
    }
    transport, calls = mock_mcp(schema=schema, tool_status=503)
    with pytest.raises(ProviderFailure, match="^outcome_unknown$"):
        provider_for(transport).generate(native_parameters())
    paid_calls = [call for call in calls if call["method"] == "tools/call"]
    assert len(paid_calls) == 1
    assert len(paid_calls[0]["params"]["arguments"]["character_prompts"]) == 2


def test_incompatible_schema_or_unsupported_enum_never_calls_paid_tool() -> None:
    schema = {**SCHEMA, "properties": {"prompt": {}}}
    transport, calls = mock_mcp(schema=schema)
    with pytest.raises(ProviderFailure, match="incompatible_mcp_server"):
        provider_for(transport).generate(PARAMETERS)
    assert "tools/call" not in [call["method"] for call in calls]

    schema = {
        **SCHEMA,
        "properties": {**SCHEMA["properties"], "model": {"enum": ["other-model"]}},
    }
    transport, calls = mock_mcp(schema=schema)
    with pytest.raises(ProviderFailure, match="unsupported_setting"):
        provider_for(transport).generate(PARAMETERS)
    assert "tools/call" not in [call["method"] for call in calls]


@pytest.mark.parametrize(
    ("result", "failure"),
    [
        ({"isError": True, "content": [{"type": "text", "text": "insufficient Anlas"}]},
         "insufficient_balance"),
        ({"content": [{"type": "image", "mimeType": "image/png", "data": "invalid!"}]},
         "invalid_result"),
        ({"content": [{"type": "image", "mimeType": "text/html", "data": "aGVsbG8="}]},
         "invalid_result"),
        ({"content": []}, "invalid_result"),
    ],
)
def test_paid_result_failures_are_safe_and_not_retried(result: dict, failure: str) -> None:
    transport, calls = mock_mcp(result=result)
    with pytest.raises(ProviderFailure, match=failure):
        provider_for(transport).generate(PARAMETERS)
    assert [call["method"] for call in calls].count("tools/call") == 1


def test_paid_http_error_has_unknown_outcome_without_retry() -> None:
    transport, calls = mock_mcp(tool_status=503)
    with pytest.raises(ProviderFailure, match="outcome_unknown"):
        provider_for(transport).generate(PARAMETERS)
    assert [call["method"] for call in calls].count("tools/call") == 1


def test_uncertain_paid_timeout_never_retries() -> None:
    calls = []

    def handler(request: httpx.Request):
        if json.loads(request.content)["method"] == "tools/call":
            calls.append("tools/call")
            raise httpx.ReadTimeout("secret upstream timeout", request=request)
        base, _recorded = mock_mcp()
        return base.handle_request(request)

    with pytest.raises(ProviderFailure, match="outcome_unknown"):
        provider_for(httpx.MockTransport(handler)).generate(PARAMETERS)
    assert calls == ["tools/call"]


def test_mocked_provider_auth_errors_cannot_leak_token() -> None:
    transport, calls = mock_mcp(tool_status=401)
    with pytest.raises(ProviderFailure, match="provider_auth_error") as exception:
        provider_for(transport).generate(PARAMETERS)
    assert "fake-mcp-token" not in str(exception.value)
    assert [call["method"] for call in calls].count("tools/call") == 1


def test_wrong_endpoint_html_fails_before_paid_call() -> None:
    def handler(_request: httpx.Request):
        return httpx.Response(200, text="<html>not an MCP endpoint</html>")

    with pytest.raises(ProviderFailure, match="invalid_mcp_response"):
        provider_for(httpx.MockTransport(handler)).generate(PARAMETERS)


@pytest.mark.parametrize(
    ("parameters", "schema"),
    [
        (PARAMETERS, SCHEMA),
        (
            native_parameters(),
            {
                **SCHEMA,
                "properties": {**SCHEMA["properties"], "character_prompts": CHARACTER_SCHEMA},
            },
        ),
    ],
    ids=["legacy", "native"],
)
def test_mocked_mcp_adapter_runs_through_api_without_live_service(
    tmp_path: Path, parameters: GenerationRequest, schema: dict,
) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.migrate()
    transport, calls = mock_mcp(schema=schema)
    settings = Settings(database.path, "https://testserver")
    with TestClient(
        create_app(settings, database, image_provider=provider_for(transport)),
        base_url="https://testserver",
    ) as client:
        _id, token = create_token(database, "alice")
        assert client.post(
            "/api/auth/session", json={"token": token}, headers={"Origin": "https://testserver"}
        ).status_code == 200
        response = client.post(
            "/api/generations", json=parameters.model_dump(),
            headers={"Origin": "https://testserver"},
        )
        assert response.status_code == 202
        job_id = response.json()["id"]
        import time

        for _attempt in range(100):
            job = client.get(f"/api/generations/{job_id}").json()
            if job["status"] in ("succeeded", "failed"):
                break
            time.sleep(0.01)
        assert job["status"] == "succeeded"
        assert job["parameters"] == parameters.model_dump()
        assert client.get("/api/generations").json()["items"][0]["parameters"] == (
            parameters.model_dump()
        )
        assert len(job["image_urls"]) == 2
        assert len(calls) == 4
