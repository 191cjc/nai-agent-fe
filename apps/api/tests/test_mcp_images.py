"""Every MCP generation test uses MockTransport; no paid server is contacted."""

import base64
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

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


def test_mocked_mcp_adapter_runs_through_api_without_live_service(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.migrate()
    transport, calls = mock_mcp()
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
            "/api/generations", json=PARAMETERS.model_dump(),
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
        assert len(job["image_urls"]) == 2
        assert len(calls) == 4
