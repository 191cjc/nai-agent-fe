"""Read-only account tests use only fake transports, clocks and disposable SQLite."""

import asyncio
import json
import threading
import zlib
from gzip import compress as gzip_compress
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import novelai_api.account_balance as account_module
import novelai_api.app as app_module
import novelai_api.mcp_account as mcp_account
from novelai_api.account_balance import (
    MAX_SAFE_INTEGER,
    AccountBalance,
    BalanceFailure,
    BalanceService,
)
from novelai_api.app import create_app
from novelai_api.auth import create_token
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.mcp_account import NovelAiMcpBalanceProvider

BALANCE = AccountBalance(fixed=100, purchased=23, total=123, fetched_at=1234567890)
SUBSCRIPTION = {
    "trainingStepsLeft": {"fixedTrainingStepsLeft": 100, "purchasedTrainingSteps": 23},
    "paymentProcessorData": "private-account-sentinel",
    "usage": {"percent": 12},
}
SCHEMA = {"type": "object", "properties": {}, "additionalProperties": False}


def mock_account(*, result=None, schema=SCHEMA, protocol="2025-06-18", override=None):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "https://mcp.example/endpoint"
        assert request.headers["Authorization"] == "Bearer token-sentinel"
        assert request.headers["Accept-Encoding"] == "gzip, deflate"
        payload = json.loads(request.content)
        calls.append(payload)
        method = payload["method"]
        if method != "initialize":
            assert request.headers["Mcp-Session-Id"] == "account-session"
            assert request.headers["MCP-Protocol-Version"] == "2025-06-18"
        if override is not None:
            overridden = override(request, payload)
            if overridden is not None:
                return overridden
        if method == "notifications/initialized":
            assert "id" not in payload
            return httpx.Response(202)
        if method == "initialize":
            data = {"protocolVersion": protocol}
        elif method == "tools/list":
            data = {"tools": [{"name": "get_subscription", "inputSchema": schema}]}
        else:
            assert method == "tools/call"
            assert payload["params"] == {"name": "get_subscription", "arguments": {}}
            data = result if result is not None else {
                "structuredContent": SUBSCRIPTION,
                "content": [{"type": "text", "text": "ignored private content"}],
                "isError": False,
            }
        return httpx.Response(
            200, headers={"Mcp-Session-Id": "account-session"},
            json={"jsonrpc": "2.0", "id": payload["id"], "result": data},
        )

    return httpx.MockTransport(handler), calls


def provider_for(transport, *, clock=lambda: 0, wall_clock=lambda: BALANCE.fetched_at):
    return NovelAiMcpBalanceProvider(
        "https://mcp.example/endpoint", "token-sentinel", transport=transport,
        clock=clock, wall_clock=wall_clock,
    )


def test_subscription_is_strict_allowlist_and_only_one_read_only_call() -> None:
    transport, calls = mock_account()
    balance = provider_for(transport).fetch()
    assert balance == BALANCE
    assert list(balance.model_dump()) == ["fixed", "purchased", "total", "fetched_at"]
    assert "private" not in balance.model_dump_json()
    assert [call["method"] for call in calls] == [
        "initialize", "notifications/initialized", "tools/list", "tools/call",
    ]


def test_json_text_fallback_and_true_zero() -> None:
    subscription = {"trainingStepsLeft": {
        "fixedTrainingStepsLeft": 0, "purchasedTrainingSteps": 0,
    }}
    transport, _ = mock_account(result={"content": [{
        "type": "text", "text": json.dumps(subscription),
    }]})
    result = provider_for(transport).fetch()
    assert result.fixed == result.purchased == result.total == 0


@pytest.mark.parametrize("value", [True, False, "1", 1.0, None, -1, MAX_SAFE_INTEGER + 1])
@pytest.mark.parametrize("field", ["fixedTrainingStepsLeft", "purchasedTrainingSteps"])
def test_invalid_balances_never_become_zero(field, value) -> None:
    steps = {**SUBSCRIPTION["trainingStepsLeft"], field: value}
    transport, calls = mock_account(result={"structuredContent": {"trainingStepsLeft": steps}})
    with pytest.raises(BalanceFailure) as failure:
        provider_for(transport).fetch()
    assert failure.value.code == "balance_bad_response"
    assert sum(call["method"] == "tools/call" for call in calls) == 1


@pytest.mark.parametrize("result", [
    {"structuredContent": None, "content": [{"type": "text", "text": json.dumps(SUBSCRIPTION)}]},
    {"structuredContent": {}},
    {"structuredContent": {"trainingStepsLeft": None}},
    {"structuredContent": {"trainingStepsLeft": {"fixedTrainingStepsLeft": 0}}},
    {"structuredContent": {"trainingStepsLeft": {
        "fixedTrainingStepsLeft": MAX_SAFE_INTEGER, "purchasedTrainingSteps": 1,
    }}},
    {"structuredContent": SUBSCRIPTION, "isError": True},
    {"structuredContent": SUBSCRIPTION, "isError": "false"},
    {"content": []},
    {"content": [{"type": "text", "text": "not JSON private-sentinel"}]},
    {"content": [{"type": "image", "data": "private-sentinel"}]},
    {"content": [{"type": "text", "text": "{}"}, {"type": "text", "text": "{}"}]},
])
def test_bad_subscription_never_falls_back_or_leaks(result) -> None:
    transport, _ = mock_account(result=result)
    with pytest.raises(BalanceFailure) as failure:
        provider_for(transport).fetch()
    assert failure.value.code == "balance_bad_response"
    assert "sentinel" not in str(failure.value)


@pytest.mark.parametrize("schema", [
    None, {"type": "string"}, {"type": "object"},
    {**SCHEMA, "required": ["user_id"]},
    {**SCHEMA, "properties": {"user_id": {"type": "string"}}},
    {**SCHEMA, "additionalProperties": {}}, {**SCHEMA, "oneOf": []},
])
def test_unverified_tool_schema_refuses_before_tool_call(schema) -> None:
    transport, calls = mock_account(schema=schema)
    with pytest.raises(BalanceFailure) as failure:
        provider_for(transport).fetch()
    assert failure.value.code == "balance_unavailable"
    assert all(call["method"] != "tools/call" for call in calls)


def test_missing_tool_or_wrong_protocol_never_invokes_any_tool() -> None:
    for kwargs in (
        {"protocol": "wrong"},
        {"override": lambda _request, payload: httpx.Response(200, json={
            "jsonrpc": "2.0", "id": payload["id"], "result": {"tools": []},
        }) if payload["method"] == "tools/list" else None},
    ):
        transport, calls = mock_account(**kwargs)
        with pytest.raises(BalanceFailure):
            provider_for(transport).fetch()
        assert all(call["method"] != "tools/call" for call in calls)


@pytest.mark.parametrize("changes", [
    {"id": True}, {"id": 3.0}, {"id": 20}, {"jsonrpc": "1.0"},
    {"result": None}, {"error": {"message": "private-account-sentinel"}},
])
def test_strict_rpc_envelope(changes) -> None:
    def override(_request, payload):
        if payload["method"] == "tools/call":
            return httpx.Response(200, json={
                "jsonrpc": "2.0", "id": payload["id"],
                "result": {"structuredContent": SUBSCRIPTION}, **changes,
            })
        return None

    transport, calls = mock_account(override=override)
    with pytest.raises(BalanceFailure) as failure:
        provider_for(transport).fetch()
    assert failure.value.code == "balance_bad_response"
    assert len(calls) == 4


@pytest.mark.parametrize("status,code", [
    (401, "balance_auth_error"), (403, "balance_auth_error"),
    (429, "balance_rate_limited"), (408, "balance_timeout"), (504, "balance_timeout"),
    (500, "balance_unavailable"), (503, "balance_unavailable"),
    (400, "balance_bad_response"), (302, "balance_bad_response"),
])
def test_http_status_is_safe_and_never_retried_or_redirected(status, code) -> None:
    def override(_request, payload):
        if payload["method"] == "tools/call":
            return httpx.Response(
                status, headers={"Location": "https://private.example/path"},
                text="private-account-sentinel token-sentinel",
            )
        return None

    transport, calls = mock_account(override=override)
    with pytest.raises(BalanceFailure) as failure:
        provider_for(transport).fetch()
    assert failure.value.code == code
    assert "sentinel" not in str(failure.value)
    assert len(calls) == 4


@pytest.mark.parametrize("exception,code", [
    (httpx.ReadTimeout("private-sentinel"), "balance_timeout"),
    (httpx.ConnectError("private-sentinel"), "balance_unavailable"),
])
def test_transport_failure_is_safe_and_never_retried(exception, code) -> None:
    def override(_request, payload):
        if payload["method"] == "tools/call":
            raise exception
        return None

    transport, calls = mock_account(override=override)
    with pytest.raises(BalanceFailure) as failure:
        provider_for(transport).fetch()
    assert failure.value.code == code
    assert len(calls) == 4


class RawStream(httpx.SyncByteStream):
    def __init__(self, chunks, on_chunk=lambda: None):
        self.chunks = chunks
        self.on_chunk = on_chunk
        self.read_count = 0

    def __iter__(self):
        for chunk in self.chunks:
            self.read_count += 1
            self.on_chunk()
            yield chunk


@pytest.mark.parametrize("encoding", ["identity", "gzip", "deflate", "raw-deflate"])
def test_bounded_raw_sse_and_compression(encoding) -> None:
    def override(_request, payload):
        if payload["method"] != "tools/call":
            return None
        body = ("event: message\r\ndata: " + json.dumps({
            "jsonrpc": "2.0", "id": payload["id"], "result": {"structuredContent": SUBSCRIPTION},
        }) + "\r\n\r\n").encode()
        encoded = body
        if encoding == "gzip":
            encoded = gzip_compress(body)
        elif encoding == "deflate":
            encoded = zlib.compress(body)
        elif encoding == "raw-deflate":
            compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
            encoded = compressor.compress(body) + compressor.flush()
        return httpx.Response(200, headers={
            "Content-Type": "text/event-stream; charset=utf-8",
            "Content-Encoding": "deflate" if encoding == "raw-deflate" else encoding,
        }, stream=RawStream([encoded[i:i + 1] for i in range(len(encoded))]))

    transport, _ = mock_account(override=override)
    assert provider_for(transport).fetch() == BALANCE


@pytest.mark.parametrize("encoding,body", [
    ("identity", b"x" * (mcp_account.MAX_RESPONSE_BYTES + 1)),
    ("gzip", gzip_compress(b"x" * (mcp_account.MAX_RESPONSE_BYTES + 1))),
    ("gzip", gzip_compress(b"{}")[:-2]),
    ("deflate", b"broken compressed data"),
    ("br", b"{}"),
])
def test_decoded_cap_and_invalid_compression_fail_without_retry(encoding, body) -> None:
    def override(_request, payload):
        if payload["method"] == "tools/call":
            return httpx.Response(200, headers={
                "Content-Type": "application/json", "Content-Encoding": encoding,
            }, stream=RawStream([body]))
        return None

    transport, calls = mock_account(override=override)
    with pytest.raises(BalanceFailure) as failure:
        provider_for(transport).fetch()
    assert failure.value.code == "balance_bad_response"
    assert len(calls) == 4


def test_whole_handshake_has_one_cooperative_deadline_and_decreasing_http_timeouts() -> None:
    now = [0.0]
    timeouts = []

    def override(request, _payload):
        timeouts.append(request.extensions["timeout"])
        now[0] += 6.0
        return None

    transport, calls = mock_account(override=override)
    with pytest.raises(BalanceFailure) as failure:
        provider_for(transport, clock=lambda: now[0]).fetch()
    assert failure.value.code == "balance_timeout"
    assert [timeout["read"] for timeout in timeouts] == [15.0, 9.0, 3.0]
    assert all(timeout["connect"] <= 5.0 for timeout in timeouts)
    assert all(call["method"] != "tools/call" for call in calls)


def test_tiny_raw_chunks_check_deadline_before_next_read() -> None:
    now = [0.0]
    stream = RawStream([b"x"] * 20, on_chunk=lambda: now.__setitem__(0, now[0] + 5))

    def override(_request, payload):
        if payload["method"] == "tools/call":
            return httpx.Response(200, headers={"Content-Type": "application/json"}, stream=stream)
        return None

    transport, calls = mock_account(override=override)
    with pytest.raises(BalanceFailure) as failure:
        provider_for(transport, clock=lambda: now[0]).fetch()
    assert failure.value.code == "balance_timeout"
    assert stream.read_count == 3
    assert len(calls) == 4


class FakeProvider:
    def __init__(self, *, failure=None):
        self.calls = 0
        self.failure = failure
        self.thread_id = None

    def fetch(self):
        self.calls += 1
        self.thread_id = threading.get_ident()
        if self.failure is not None:
            raise self.failure
        return BALANCE


def test_success_cache_retains_fetch_time_and_expired_failure_is_not_fresh() -> None:
    async def scenario():
        now = [0.0]
        provider = FakeProvider()
        service = BalanceService(provider, clock=lambda: now[0])
        assert await service.get() == BALANCE
        assert provider.thread_id != threading.get_ident()
        now[0] = 4.999
        assert await service.get() == BALANCE
        assert provider.calls == 1
        now[0] = 5.0
        provider.failure = BalanceFailure("balance_timeout")
        with pytest.raises(BalanceFailure, match="timed out"):
            await service.get()
        assert provider.calls == 2
        provider.failure = None
        assert await service.get() == BALANCE
        assert provider.calls == 3
        await service.close()
        with pytest.raises(BalanceFailure):
            await service.get()

    asyncio.run(scenario())


@pytest.mark.parametrize("failed", [False, True])
def test_concurrent_calls_share_result_failure_and_survive_waiter_cancellation(
    monkeypatch: pytest.MonkeyPatch, failed: bool,
) -> None:
    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()

        async def controlled_thread(function):
            started.set()
            await release.wait()
            return function()

        monkeypatch.setattr(account_module.asyncio, "to_thread", controlled_thread)
        provider = FakeProvider(failure=BalanceFailure("balance_auth_error") if failed else None)
        service = BalanceService(provider)
        first = asyncio.create_task(service.get())
        second = asyncio.create_task(service.get())
        third = asyncio.create_task(service.get())
        await started.wait()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        release.set()
        results = await asyncio.gather(second, third, return_exceptions=True)
        assert provider.calls == 1
        if failed:
            assert all(isinstance(result, BalanceFailure) for result in results)
            assert results[0] is results[1]
            provider.failure = None
            assert await service.get() == BALANCE
            assert provider.calls == 2
        else:
            assert results == [BALANCE, BALANCE]
        await service.close()

    asyncio.run(scenario())


def test_shutdown_waits_for_owned_fetch_even_after_all_waiters_cancel(monkeypatch) -> None:
    async def scenario():
        started, release, closing = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def controlled_thread(function):
            started.set()
            await release.wait()
            return function()

        monkeypatch.setattr(account_module.asyncio, "to_thread", controlled_thread)
        provider = FakeProvider(failure=BalanceFailure())
        service = BalanceService(provider)
        caller = asyncio.create_task(service.get())
        await started.wait()
        caller.cancel()
        with pytest.raises(asyncio.CancelledError):
            await caller

        async def close():
            closing.set()
            await service.close()

        close_task = asyncio.create_task(close())
        await closing.wait()
        assert not close_task.done()
        release.set()
        await close_task
        assert service._inflight is None
        assert service._cached is None
        assert provider.calls == 1

    asyncio.run(scenario())


def login(client: TestClient, database: Database) -> None:
    _token_id, token = create_token(database, "balance-user")
    response = client.post(
        "/api/auth/session", json={"token": token}, headers={"Origin": "https://testserver"},
    )
    assert response.status_code == 200


def test_route_authenticates_before_balance_and_never_persists_account_data(tmp_path: Path) -> None:
    database = Database(tmp_path / "account.sqlite3")
    database.migrate()
    provider = FakeProvider()
    with TestClient(create_app(
        Settings(database.path, "https://testserver"), database, balance_provider=provider,
    ), base_url="https://testserver") as client:
        response = client.get("/api/account/balance")
        assert response.status_code == 401
        assert response.headers["Cache-Control"] == "no-store"
        assert provider.calls == 0
        login(client, database)
        response = client.get("/api/account/balance")
        assert response.status_code == 200
        assert response.json() == BALANCE.model_dump()
        assert response.headers["Cache-Control"] == "no-store"
        assert client.get("/api/account/balance").json() == BALANCE.model_dump()
        assert provider.calls == 1
        with database.connect() as connection:
            dump = "\n".join(connection.iterdump())
        assert "fetched_at" not in dump


@pytest.mark.parametrize("code", [
    "balance_auth_error", "balance_rate_limited", "balance_timeout", "balance_bad_response",
    "balance_unavailable",
])
def test_safe_route_errors_are_independent_and_no_store(tmp_path: Path, code: str) -> None:
    database = Database(tmp_path / "account.sqlite3")
    database.migrate()
    failure = BalanceFailure(code)
    with TestClient(create_app(
        Settings(database.path, "https://testserver"), database,
        balance_provider=FakeProvider(failure=failure),
    ), base_url="https://testserver") as client:
        login(client, database)
        response = client.get("/api/account/balance")
        assert response.status_code == failure.status
        assert response.json() == {
            "code": code, "message": failure.message, "retryable": failure.retryable,
        }
        assert response.headers["Cache-Control"] == "no-store"
        assert client.get("/api/generations").json()["items"] == []


def test_default_balance_provider_is_lazy_and_missing_configuration_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "account.sqlite3")
    database.migrate()
    constructed = []
    provider = FakeProvider()

    def construct(url, token):
        constructed.append((url, token))
        return provider

    monkeypatch.setattr(app_module, "NovelAiMcpBalanceProvider", construct)
    settings = Settings(
        database.path, "https://testserver", novelai_mcp_url="https://mcp.example/api",
        novelai_mcp_token="private-token-sentinel",
    )
    app = create_app(settings, database)
    app.openapi()
    assert provider.calls == 0
    assert constructed == [(settings.novelai_mcp_url, settings.novelai_mcp_token)]
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database)
        assert client.get("/api/account/balance").json() == BALANCE.model_dump()
    with TestClient(create_app(
        Settings(database.path, "https://testserver"), database,
    ), base_url="https://testserver") as client:
        login(client, database)
        response = client.get("/api/account/balance")
        assert response.status_code == 503
        assert response.json()["code"] == "balance_unavailable"


@pytest.mark.parametrize("changes", [
    {"total": 0}, {"fixed": True}, {"purchased": 1.0}, {"fetched_at": -1},
    {"fetched_at": MAX_SAFE_INTEGER + 1}, {"payment_data": "private"},
])
def test_response_model_refuses_unsafe_or_extra_data(changes) -> None:
    with pytest.raises(ValidationError):
        AccountBalance.model_validate({**BALANCE.model_dump(), **changes})
