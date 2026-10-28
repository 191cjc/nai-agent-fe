"""Stateless advice tests use in-process fake runners, never paid Codex."""

import asyncio
import logging
import os
import signal
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from openai_codex_sdk.abort import AbortError
from openai_codex_sdk.exec import CodexExec, CodexExecArgs
from openai_codex_sdk.parsing import parse_thread_event

from novelai_api.advice import AdviceFailure, AdviceService, ToolUseAttempt
from novelai_api.app import create_app
from novelai_api.auth import create_token
from novelai_api.codex_advice import (
    DISABLED_FEATURES,
    OUTPUT_SCHEMA,
    CodexAdviceRunner,
    _cli_path,
    _login_with_api_key,
)
from novelai_api.config import Settings
from novelai_api.db import Database


class FakeRunner:
    def __init__(self, *, payload=None, failure=None):
        self.payload = payload if payload is not None else {"suggestion": "Try softer lighting."}
        self.failure = failure
        self.calls: list[str] = []

    async def run(self, text: str) -> dict:
        self.calls.append(text)
        if self.failure is not None:
            raise self.failure
        return self.payload


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "api.sqlite3")
    database.migrate()
    return database


def client_for(database: Database, runner=None) -> TestClient:
    return TestClient(
        create_app(
            Settings(database.path, "https://testserver"),
            database,
            advice_runner=runner,
        ),
        base_url="https://testserver",
    )


def login(client: TestClient, database: Database) -> None:
    _token_id, token = create_token(database, "alice")
    response = client.post(
        "/api/auth/session", json={"token": token}, headers={"Origin": "https://testserver"}
    )
    assert response.status_code == 200


def advice(client: TestClient, payload: dict):
    return client.post("/api/advice", json=payload, headers={"Origin": "https://testserver"})


def test_advice_requires_session_and_never_reads_page_state(database: Database) -> None:
    runner = FakeRunner()
    with client_for(database, runner) as client:
        assert advice(client, {"input": "lighting"}).status_code == 401
        login(client, database)
        response = advice(client, {"input": "lighting"})
        assert response.status_code == 200
        assert response.json() == {"suggestion": "Try softer lighting."}
        assert response.headers["Cache-Control"] == "no-store"
        assert runner.calls == ["lighting"]
        assert advice(client, {"input": "hello", "prompt": "private form state"}).status_code == 422
        assert advice(client, {"input": "   "}).status_code == 422
        assert runner.calls == ["lighting"]
        with database.connect() as connection:
            dump = "\n".join(connection.iterdump())
        assert "lighting" not in dump
        assert "Try softer lighting." not in dump


def test_no_runtime_is_explicitly_unavailable(database: Database) -> None:
    with client_for(database) as client:
        login(client, database)
        response = advice(client, {"input": "unseen"})
        assert response.status_code == 503
        assert response.json()["code"] == "advice_unavailable"


def test_endpoint_and_model_without_key_do_not_enable_advice(database: Database) -> None:
    settings = Settings(
        database.path,
        "https://testserver",
        codex_base_url="https://advice.example.test/v1",
        codex_model="provider/example-model",
    )
    with TestClient(create_app(settings, database), base_url=settings.public_origin) as client:
        login(client, database)
        response = advice(client, {"input": "unseen"})
        assert response.status_code == 503
        assert response.json()["code"] == "advice_unavailable"


@pytest.mark.parametrize(
    ("base_url", "model"),
    [(None, None), ("https://advice.example.test/v1", "provider/example-model")],
)
def test_configured_runner_is_wired_by_default(
    database: Database, monkeypatch: pytest.MonkeyPatch, base_url: str | None, model: str | None
) -> None:
    created = []

    class ConfiguredRunner:
        def __init__(self, api_key: str, *, base_url: str | None, model: str | None):
            created.append((self, api_key, base_url, model))
            self.closed = False

        async def run(self, text: str) -> dict:
            return {"suggestion": f"Advice for {text}"}

        async def close(self) -> None:
            self.closed = True

    monkeypatch.setattr("novelai_api.app.CodexAdviceRunner", ConfiguredRunner)
    settings = Settings(
        database.path,
        "https://testserver",
        codex_api_key="configured-test-key",
        codex_base_url=base_url,
        codex_model=model,
    )
    assert "configured-test-key" not in repr(settings)
    with TestClient(create_app(settings, database), base_url=settings.public_origin) as client:
        login(client, database)
        response = advice(client, {"input": "lighting"})
        assert response.status_code == 200
        assert response.json() == {"suggestion": "Advice for lighting"}
    assert created[0][1:] == ("configured-test-key", base_url, model)
    assert created[0][0].closed


@pytest.mark.parametrize(
    ("payload", "failure", "error_code"),
    [
        ({"suggestion": "fine", "tool_calls": [{"name": "shell"}]}, None, "advice_failed"),
        ({"suggestion": " "}, None, "advice_failed"),
        (None, ToolUseAttempt("shell tool requested"), "advice_tool_attempt"),
        (None, RuntimeError("secret upstream traceback"), "advice_failed"),
    ],
)
def test_unexpected_output_and_tool_attempt_fail_closed(
    database: Database, payload: dict | None, failure: Exception | None, error_code: str
) -> None:
    runner = FakeRunner(payload=payload, failure=failure)
    with client_for(database, runner) as client:
        login(client, database)
        response = advice(client, {"input": "keep it private"})
        assert response.status_code == 502
        assert response.json()["code"] == error_code
        assert "secret upstream traceback" not in response.text
        assert "shell tool requested" not in response.text


@pytest.mark.parametrize(
    ("failure", "error_code", "diagnostic"),
    [
        (RuntimeError("private-upstream-sentinel"), "advice_failed", "RuntimeError"),
        (ToolUseAttempt("private-upstream-sentinel"), "advice_tool_attempt", "tool use"),
        (TimeoutError("private-upstream-sentinel"), "advice_timeout", "timed out"),
    ],
)
def test_advice_failure_diagnostics_do_not_expose_private_text(
    caplog: pytest.LogCaptureFixture, failure: Exception, error_code: str, diagnostic: str
) -> None:
    caplog.set_level(logging.WARNING, logger="novelai_api.advice")
    runner = FakeRunner(payload={"suggestion": "private-output-sentinel"}, failure=failure)

    async def exercise():
        with pytest.raises(AdviceFailure) as caught:
            await AdviceService(runner).advise("private-input-sentinel")
        assert caught.value.code == error_code

    asyncio.run(exercise())
    assert diagnostic in caplog.text
    for secret in (
        "private-upstream-sentinel", "private-input-sentinel", "private-output-sentinel"
    ):
        assert secret not in caplog.text
    assert caplog.records
    assert all(record.exc_info is None and record.stack_info is None for record in caplog.records)


def test_timeout_cancels_runner_and_runs_cleanup() -> None:
    cleaned = asyncio.Event()

    class WaitingRunner:
        async def run(self, text: str) -> dict:
            try:
                await asyncio.sleep(60)
            finally:
                cleaned.set()

    async def exercise():
        with pytest.raises(AdviceFailure) as exception:
            await AdviceService(WaitingRunner(), timeout=0.02).advise("lighting")
        assert exception.value.code == "advice_timeout"
        assert cleaned.is_set()

    asyncio.run(exercise())


def test_bounded_concurrency_allows_only_two_requests() -> None:
    release = asyncio.Event()
    entered = asyncio.Event()
    seen: list[str] = []

    class WaitingRunner:
        async def run(self, text: str) -> dict:
            seen.append(text)
            if len(seen) == 2:
                entered.set()
            await release.wait()
            return {"suggestion": "okay"}

    async def exercise():
        service = AdviceService(WaitingRunner())
        active = [asyncio.create_task(service.advise(str(index))) for index in range(2)]
        await asyncio.wait_for(entered.wait(), timeout=1)
        try:
            with pytest.raises(AdviceFailure) as exception:
                await service.advise("third")
            assert exception.value.code == "advice_busy"
        finally:
            release.set()
        assert all(result.suggestion == "okay" for result in await asyncio.gather(*active))
        assert seen == ["0", "1"]

    asyncio.run(exercise())


def sdk_event(event_type: str, item_type: str | None = None, text: str = ""):
    item = SimpleNamespace(type=item_type, text=text) if item_type else None
    return SimpleNamespace(type=event_type, item=item)


class FakeCodex:
    def __init__(self, events):
        self.events = events
        self.options = None
        self.thread_options = None
        self.prompt = None
        self.turn_options = None

    def create(self, options):
        self.options = options
        return self

    def start_thread(self, options):
        self.thread_options = options
        return self

    async def run_streamed(self, prompt, options):
        self.prompt = prompt
        self.turn_options = options
        return SimpleNamespace(events=self.events())


def isolated_runner(
    tmp_path: Path, sdk: FakeCodex, *, base_url: str | None = None, model: str | None = None
) -> CodexAdviceRunner:
    async def fake_login(_cli_path, environment, api_key):
        assert api_key == "test-only-key"
        assert all("KEY" not in name for name in environment)
        assert "test-only-key" not in str(environment)
        (Path(environment["CODEX_HOME"]) / "auth.json").write_text("test-only-auth")

    return CodexAdviceRunner(
        "test-only-key",
        base_url=base_url,
        model=model,
        codex_factory=sdk.create,
        cli_path="/fake/pinned/codex",
        workspace_parent=tmp_path,
        authenticator=fake_login,
    )


def test_sdk_runner_uses_one_isolated_structured_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "inherited-secret")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://inherited.example")
    monkeypatch.setenv("CODEX_HOME", "/inherited/home")

    async def events():
        yield sdk_event("thread.started")
        yield sdk_event("turn.started")
        yield sdk_event("item.completed", "agent_message", '{"suggestion":"Use a lower CFG."}')
        yield sdk_event("turn.completed")

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)

    async def exercise():
        assert await runner.run("How can I improve lighting?") == {
            "suggestion": "Use a lower CFG."
        }
        assert sdk.prompt == "How can I improve lighting?"
        assert sdk.turn_options["output_schema"] == OUTPUT_SCHEMA
        assert sdk.thread_options["sandbox_mode"] == "read-only"
        assert sdk.thread_options["network_access_enabled"] is False
        assert sdk.thread_options["web_search_enabled"] is False
        assert sdk.thread_options["approval_policy"] == "never"
        assert sdk.thread_options["skip_git_repo_check"] is True
        assert "model" not in sdk.thread_options
        assert sdk.options["codex_path_override"] == "/fake/pinned/codex"
        assert "base_url" not in sdk.options
        assert "api_key" not in sdk.options
        assert sdk.options["env"]["HOME"] == sdk.options["env"]["CODEX_HOME"]
        assert set(sdk.options["env"]) == {"CODEX_HOME", "HOME", "TMPDIR", "PATH", "LANG"}
        assert not list(tmp_path.iterdir())

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "commentary", ["I will suggest lighting tags.", '{"suggestion":"intermediate advice"}']
)
def test_sdk_returns_final_message_after_commentary(tmp_path: Path, commentary: str) -> None:
    async def events():
        for index, (phase, text) in enumerate(
            [("commentary", commentary), ("final_answer", '{"suggestion":"rim lighting"}')]
        ):
            yield parse_thread_event({
                "type": "item.completed",
                "item": {"id": str(index), "type": "agent_message", "phase": phase, "text": text},
            })
        yield parse_thread_event({
            "type": "turn.completed",
            "usage": {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0},
        })

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)
    assert asyncio.run(runner.run("lighting")) == {"suggestion": "rim lighting"}
    assert not list(tmp_path.iterdir())


# Exact non-fatal warnings the pinned CLI 0.152.1 emits before every turn.
CLI_WARNINGS = [
    "`[features].web_search_request` is deprecated because web search is enabled by default.",
    "Under-development features enabled: skip_host_skill_discovery.",
    "Model metadata for `example-model` not found. Defaulting to fallback metadata.",
]


def test_sdk_ignores_cli_warning_items_and_returns_advice(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    async def events():
        yield parse_thread_event({"type": "thread.started", "thread_id": "thread"})
        for index, message in enumerate(CLI_WARNINGS):
            yield parse_thread_event({
                "type": "item.completed",
                "item": {"id": f"warning-{index}", "type": "error", "message": message},
            })
        yield parse_thread_event({"type": "turn.started"})
        yield sdk_event("item.completed", "agent_message", '{"suggestion":"rim lighting"}')
        yield sdk_event("turn.completed")

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)
    caplog.set_level(logging.WARNING)
    result = asyncio.run(AdviceService(runner).advise("lighting"))
    assert result.suggestion == "rim lighting"
    assert not sdk.turn_options["signal"].aborted
    assert not caplog.records
    assert not list(tmp_path.iterdir())


def test_sdk_warnings_never_release_advice_without_a_completed_turn(tmp_path: Path) -> None:
    async def events():
        yield sdk_event("item.completed", "error", "")
        yield sdk_event("item.completed", "agent_message", '{"suggestion":"partial"}')

    runner = isolated_runner(tmp_path, FakeCodex(events))
    with pytest.raises(AdviceFailure) as failure:
        asyncio.run(AdviceService(runner).advise("lighting"))
    assert failure.value.code == "advice_failed"


@pytest.mark.parametrize("event_type", ["item.started", "item.updated"])
def test_sdk_rejects_error_items_that_are_not_completed_warnings(
    tmp_path: Path, event_type: str, caplog: pytest.LogCaptureFixture,
) -> None:
    async def events():
        yield sdk_event(event_type, "error")
        yield sdk_event("item.completed", "agent_message", '{"suggestion":"ignore"}')
        yield sdk_event("turn.completed")

    runner = isolated_runner(tmp_path, FakeCodex(events))
    caplog.set_level(logging.WARNING)
    with pytest.raises(AdviceFailure) as failure:
        asyncio.run(AdviceService(runner).advise("lighting"))
    assert failure.value.code == "advice_tool_attempt"
    assert "rejected observed tool use (error)" in caplog.text


@pytest.mark.parametrize(
    ("base_url", "model"),
    [
        ("https://advice.example.test:8443/v1/", None),
        (None, "provider/example-model:2026.10"),
        ("https://advice.example.test/v1", "provider/example-model"),
    ],
)
def test_sdk_configured_endpoint_and_model_preserve_isolation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    base_url: str | None,
    model: str | None,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "inherited-test-secret")
    monkeypatch.setenv("CODEX_API_KEY", "another-inherited-test-secret")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://inherited.example.test/v1")
    monkeypatch.setenv("HTTPS_PROXY", "https://inherited-proxy.example.test")
    observed = {}

    async def events():
        runtime = Path(sdk.options["env"]["CODEX_HOME"])
        work = Path(sdk.thread_options["working_directory"])
        observed["config"] = (runtime / "config.toml").read_text()
        observed["instructions"] = (work / "AGENTS.md").read_text()
        yield sdk_event("item.completed", "agent_message", '{"suggestion":"中文解释"}')
        yield sdk_event("turn.completed")

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk, base_url=base_url, model=model)
    assert asyncio.run(runner.run("only this section text")) == {"suggestion": "中文解释"}
    # The pinned CLI ignores OPENAI_BASE_URL; the endpoint must be in its config file.
    assert "base_url" not in sdk.options
    assert tomllib.loads(observed["config"]).get("openai_base_url") == (
        base_url.rstrip("/") if base_url else None
    )
    assert sdk.thread_options.get("model") == model
    assert ("model" in sdk.thread_options) is (model is not None)
    assert "api_key" not in sdk.options
    assert set(sdk.options["env"]) == {"CODEX_HOME", "HOME", "TMPDIR", "PATH", "LANG"}
    assert sdk.prompt == "only this section text"
    assert "only this section text" not in observed["config"] + observed["instructions"]
    assert "test-only-key" not in str(sdk.options) + str(sdk.thread_options)
    assert "test-only-key" not in observed["config"] + observed["instructions"]
    assert sdk.thread_options["sandbox_mode"] == "read-only"
    assert sdk.thread_options["network_access_enabled"] is False
    assert sdk.thread_options["web_search_enabled"] is False
    assert sdk.thread_options["approval_policy"] == "never"
    assert not list(tmp_path.iterdir())


def test_pinned_sdk_builds_configured_execution_without_inheriting_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "inherited-test-secret")
    monkeypatch.setenv("CODEX_API_KEY", "inherited-test-secret")
    monkeypatch.setenv("HTTPS_PROXY", "https://inherited-proxy.example.test")
    environment = {
        "CODEX_HOME": "/fake/private/runtime",
        "HOME": "/fake/private/runtime",
        "TMPDIR": "/fake/private/tmp",
        "PATH": os.defpath,
        "LANG": "C.UTF-8",
    }
    execution = CodexExec("/fake/pinned/codex", environment)
    args = CodexExecArgs(
        input="only submitted text",
        base_url="https://advice.example.test/v1",
        model="provider/example-model:2026.10",
        sandbox_mode="read-only",
        network_access_enabled=False,
        web_search_enabled=False,
        approval_policy="never",
    )
    child_environment = execution._build_env(args)
    assert child_environment == {
        **environment,
        "OPENAI_BASE_URL": "https://advice.example.test/v1",
        "CODEX_INTERNAL_ORIGINATOR_OVERRIDE": "codex_sdk_py",
    }
    command = execution._build_command_args(args)
    assert command[:2] == ["exec", "--experimental-json"]
    assert command[command.index("--model") + 1] == "provider/example-model:2026.10"
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert 'approval_policy="never"' in command
    assert "sandbox_workspace_write.network_access=false" in command
    assert "features.web_search_request=false" in command
    assert "inherited-test-secret" not in str(command) + str(child_environment)


@pytest.mark.parametrize(
    ("options", "setting"),
    [
        ({"base_url": "https://advice.example.test:invalid/v1"}, "NAI_CODEX_BASE_URL"),
        ({"model": "model\nunsafe"}, "NAI_CODEX_MODEL"),
    ],
)
def test_direct_runner_rejects_invalid_provider_options(options: dict, setting: str) -> None:
    with pytest.raises(ValueError, match=setting):
        CodexAdviceRunner("test-only-key", **options)


def test_sdk_config_disables_named_capabilities_and_hides_prompt(tmp_path: Path) -> None:
    observed = {}

    async def events():
        runtime = Path(sdk.options["env"]["CODEX_HOME"])
        work = Path(sdk.thread_options["working_directory"])
        observed["config"] = (runtime / "config.toml").read_text()
        observed["instructions"] = (work / "AGENTS.md").read_text()
        observed["auth"] = (runtime / "auth.json").read_text()
        yield sdk_event("item.completed", "agent_message", '{"suggestion":"Add rim light."}')
        yield sdk_event("turn.completed")

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)
    asyncio.run(runner.run("private user text"))
    assert observed["auth"] == "test-only-auth"
    assert "private user text" not in observed["config"] + observed["instructions"]
    assert "test-only-key" not in observed["config"] + observed["instructions"]
    assert 'sandbox_mode = "read-only"' in observed["config"]
    assert 'approval_policy = "never"' in observed["config"]
    assert 'web_search = "disabled"' in observed["config"]
    assert "skip_host_skill_discovery = true" in observed["config"]
    assert tomllib.loads(observed["config"])["features"]["shell_tool"] is False
    for feature in DISABLED_FEATURES:
        assert f"{feature} = false" in observed["config"]
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "item_type",
    [
        "command_execution",
        "file_change",
        "mcp_tool_call",
        "web_search",
        "image_view",
        "unknown_tool",
    ],
)
def test_sdk_rejects_observed_tool_events(tmp_path: Path, item_type: str) -> None:
    async def events():
        yield sdk_event("item.started", item_type)
        yield sdk_event("item.completed", "agent_message", '{"suggestion":"ignore"}')
        yield sdk_event("turn.completed")

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)

    async def exercise():
        with pytest.raises(AdviceFailure) as failure:
            await AdviceService(runner).advise("do not use tools")
        assert failure.value.code == "advice_tool_attempt"
        assert sdk.turn_options["signal"].aborted
        assert not list(tmp_path.iterdir())

    asyncio.run(exercise())


@pytest.mark.parametrize("reported_version", ["codex-cli 0.152.1", "codex-cli 0.156.0"])
def test_cli_lookup_checks_pin_without_credentials(
    monkeypatch: pytest.MonkeyPatch, reported_version: str
) -> None:
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout=reported_version)

    monkeypatch.setattr(Path, "is_file", lambda _path: True)
    monkeypatch.setattr(os, "access", lambda _path, _mode: True)
    monkeypatch.setattr("novelai_api.codex_advice.subprocess.run", fake_run)
    if reported_version == "codex-cli 0.152.1":
        assert _cli_path() == observed["command"][0]
    else:
        with pytest.raises(RuntimeError, match="version does not match"):
            _cli_path()
    assert observed["command"][1:] == ["--version"]
    assert observed["kwargs"]["env"] == {"PATH": os.defpath, "LANG": "C.UTF-8"}
    assert observed["kwargs"]["timeout"] == 2


@pytest.mark.parametrize("event_type", ["item.updated", "item.completed"])
@pytest.mark.parametrize("after_completion", [False, True])
def test_sdk_rejects_tool_events_at_any_stream_position(
    tmp_path: Path, event_type: str, after_completion: bool
) -> None:
    async def events():
        yield parse_thread_event({
            "type": "item.completed",
            "item": {
                "id": "commentary", "type": "agent_message", "phase": "commentary",
                "text": '{"suggestion":"intermediate advice"}',
            },
        })
        yield sdk_event("item.completed", "agent_message", '{"suggestion":"ignore"}')
        if after_completion:
            yield sdk_event("turn.completed")
        yield sdk_event(event_type, "mcp_tool_call")
        if not after_completion:
            yield sdk_event("turn.completed")

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)

    async def exercise():
        with pytest.raises(AdviceFailure) as failure:
            await AdviceService(runner).advise("only this text")
        assert failure.value.code == "advice_tool_attempt"
        assert sdk.turn_options["signal"].aborted
        assert not list(tmp_path.iterdir())

    asyncio.run(exercise())


@pytest.mark.skipif(os.name != "posix", reason="Uses POSIX process signals")
def test_sdk_tool_event_stops_cli_before_workspace_cleanup(tmp_path: Path) -> None:
    cli = tmp_path / "fake-codex"
    pid_file = tmp_path / "cli.pid"
    cli.write_text(
        "#!/usr/bin/python3\n"
        "import os\n"
        "import time\n"
        f"open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n"
        "print('{\"type\":\"item.started\",\"item\":{\"id\":\"1\","
        "\"type\":\"command_execution\",\"command\":\"echo bad\","
        "\"aggregated_output\":\"\",\"status\":\"in_progress\"}}', flush=True)\n"
        "time.sleep(10)\n"
    )
    cli.chmod(0o700)

    async def fake_login(_cli_path, _environment, _api_key):
        pass

    runner = CodexAdviceRunner(
        "test-only-key",
        cli_path=str(cli),
        workspace_parent=tmp_path,
        authenticator=fake_login,
    )

    async def exercise():
        with pytest.raises(ToolUseAttempt):
            await runner.run("text")
        process_id = int(pid_file.read_text())
        try:
            with pytest.raises(ProcessLookupError):
                os.kill(process_id, 0)
        finally:
            try:
                os.kill(process_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
        assert not list(tmp_path.glob("nai-advice-*"))

    asyncio.run(exercise())


@pytest.mark.skipif(os.name != "posix", reason="Uses POSIX process signals")
@pytest.mark.parametrize("interrupt", ["timeout", "cancel", "shutdown"])
def test_sdk_interruption_stops_cli_before_workspace_cleanup(
    tmp_path: Path, interrupt: str
) -> None:
    cli = tmp_path / "fake-codex"
    pid_file = tmp_path / "cli.pid"
    cli.write_text(
        "#!/usr/bin/python3\n"
        "import os\n"
        "import time\n"
        f"open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n"
        "print('{\"type\":\"turn.started\"}', flush=True)\n"
        "time.sleep(10)\n"
    )
    cli.chmod(0o700)

    async def fake_login(_cli_path, _environment, _api_key):
        pass

    runner = CodexAdviceRunner(
        "test-only-key",
        cli_path=str(cli),
        workspace_parent=tmp_path,
        authenticator=fake_login,
    )

    async def wait_for_pid() -> int:
        for _ in range(100):
            if pid_file.exists():
                return int(pid_file.read_text())
            await asyncio.sleep(0.01)
        raise AssertionError("Fake CLI did not start")

    async def exercise():
        if interrupt == "timeout":
            with pytest.raises(AdviceFailure) as failure:
                await AdviceService(runner, timeout=0.2).advise("text")
            assert failure.value.code == "advice_timeout"
            process_id = int(pid_file.read_text())
        else:
            active = asyncio.create_task(runner.run("text"))
            process_id = await wait_for_pid()
            if interrupt == "cancel":
                active.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await active
            else:
                await runner.close()
                with pytest.raises(AbortError):
                    await active
        try:
            with pytest.raises(ProcessLookupError):
                os.kill(process_id, 0)
        finally:
            try:
                os.kill(process_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
        assert not list(tmp_path.glob("nai-advice-*"))

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "output",
    ['not json', '{"suggestion":"ok","extra":1}', '{"suggestion":""}', None, "x" * 4097],
)
@pytest.mark.parametrize("commentary", [None, '{"suggestion":"valid intermediate advice"}'])
def test_sdk_rejects_non_schema_final_output(
    tmp_path: Path, output: str | None, commentary: str | None
) -> None:
    async def events():
        if commentary is not None:
            yield sdk_event("item.completed", "agent_message", commentary)
        yield parse_thread_event({
            "type": "item.completed",
            "item": {
                "id": "final", "type": "agent_message", "phase": "final_answer", "text": output
            },
        })
        yield sdk_event("turn.completed")

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)

    async def exercise():
        with pytest.raises(AdviceFailure) as failure:
            await AdviceService(runner).advise("lighting")
        assert failure.value.code == "advice_failed"
        assert not list(tmp_path.iterdir())

    asyncio.run(exercise())


@pytest.mark.parametrize("ending", ["missing", "failed", "unknown", "over_limit", "late_message"])
def test_sdk_does_not_release_messages_without_a_valid_complete_turn(
    tmp_path: Path, ending: str
) -> None:
    async def events():
        yield sdk_event("item.completed", "agent_message", '{"suggestion":"intermediate"}')
        yield sdk_event("item.completed", "agent_message", '{"suggestion":"final"}')
        if ending == "missing":
            return
        if ending == "failed":
            yield sdk_event("turn.failed")
        elif ending == "unknown":
            yield sdk_event("unknown.event")
        else:
            if ending == "over_limit":
                for _ in range(254):
                    yield sdk_event("item.updated", "reasoning")
            yield sdk_event("turn.completed")
            if ending == "late_message":
                yield sdk_event("item.completed", "agent_message", '{"suggestion":"late"}')

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)

    async def exercise():
        with pytest.raises(AdviceFailure) as failure:
            await AdviceService(runner).advise("lighting")
        assert failure.value.code == "advice_failed"
        assert sdk.turn_options["signal"].aborted
        assert not list(tmp_path.iterdir())

    asyncio.run(exercise())


def test_sdk_timeout_aborts_signal_and_waits_for_stream_cleanup(tmp_path: Path) -> None:
    entered = asyncio.Event()
    cleaned = asyncio.Event()

    async def events():
        try:
            entered.set()
            yield sdk_event("turn.started")
            await asyncio.sleep(60)
        finally:
            await asyncio.sleep(0.01)
            cleaned.set()

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)

    async def exercise():
        with pytest.raises(AdviceFailure) as failure:
            await AdviceService(runner, timeout=0.02).advise("lighting")
        assert failure.value.code == "advice_timeout"
        assert entered.is_set() and cleaned.is_set()
        assert sdk.turn_options["signal"].aborted
        assert not list(tmp_path.iterdir())

    asyncio.run(exercise())


def test_sdk_request_cancellation_aborts_and_cleans_up(tmp_path: Path) -> None:
    entered = asyncio.Event()
    cleaned = asyncio.Event()

    async def events():
        try:
            entered.set()
            yield sdk_event("turn.started")
            await asyncio.sleep(60)
        finally:
            await asyncio.sleep(0.01)
            cleaned.set()

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)

    async def exercise():
        active = asyncio.create_task(runner.run("lighting"))
        await asyncio.wait_for(entered.wait(), 1)
        active.cancel()
        with pytest.raises(asyncio.CancelledError):
            await active
        assert cleaned.is_set()
        assert sdk.turn_options["signal"].aborted
        assert not list(tmp_path.iterdir())

    asyncio.run(exercise())


def test_sdk_shutdown_aborts_active_turn_and_waits_for_cleanup(tmp_path: Path) -> None:
    entered = asyncio.Event()
    cleaned = asyncio.Event()

    async def events():
        try:
            entered.set()
            yield sdk_event("turn.started")
            await sdk.turn_options["signal"].wait()
            yield sdk_event("turn.failed")
        finally:
            await asyncio.sleep(0.01)
            cleaned.set()

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)

    async def exercise():
        active = asyncio.create_task(runner.run("lighting"))
        await asyncio.wait_for(entered.wait(), 1)
        await runner.close()
        with pytest.raises(RuntimeError):
            await active
        assert cleaned.is_set()
        assert sdk.turn_options["signal"].aborted
        assert not list(tmp_path.iterdir())
        with pytest.raises(RuntimeError):
            await runner.run("again")

    asyncio.run(exercise())


def test_isolated_cli_login_uses_stdin_and_no_key_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed = {}

    class FakeProcess:
        returncode = 0

        async def communicate(self, data):
            observed["stdin"] = data
            (tmp_path / "auth.json").write_text("fake auth")

    async def spawn(*args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    environment = {"CODEX_HOME": str(tmp_path), "HOME": str(tmp_path)}
    asyncio.run(_login_with_api_key("/fake/codex", environment, "test-only-key"))
    assert observed["args"] == ("/fake/codex", "login", "--with-api-key")
    assert observed["stdin"] == b"test-only-key\n"
    assert observed["kwargs"]["env"] == environment
    assert observed["kwargs"]["stdout"] == asyncio.subprocess.DEVNULL
    assert observed["kwargs"]["stderr"] == asyncio.subprocess.DEVNULL
    if os.name == "posix":
        assert (tmp_path / "auth.json").stat().st_mode & 0o777 == 0o600


def test_cancelled_cli_login_kills_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered = asyncio.Event()
    process = SimpleNamespace(returncode=None, killed=False)

    async def communicate(_data):
        entered.set()
        await asyncio.sleep(60)

    def kill():
        process.killed = True
        process.returncode = -9

    async def wait():
        return process.returncode

    process.communicate = communicate
    process.kill = kill
    process.wait = wait

    async def spawn(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)

    async def exercise():
        login_task = asyncio.create_task(
            _login_with_api_key("/fake/codex", {"CODEX_HOME": str(tmp_path)}, "key")
        )
        await asyncio.wait_for(entered.wait(), 1)
        login_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await login_task
        assert process.killed

    asyncio.run(exercise())
