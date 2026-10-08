"""Stateless advice tests use in-process fake runners, never paid Codex."""

import asyncio
import os
import signal
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from openai_codex_sdk.abort import AbortError

from novelai_api.advice import AdviceFailure, AdviceService, ToolUseAttempt
from novelai_api.app import create_app
from novelai_api.auth import create_token
from novelai_api.codex_advice import (
    CodexAdviceRunner,
    DISABLED_FEATURES,
    OUTPUT_SCHEMA,
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


def test_configured_runner_is_wired_by_default(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = []

    class ConfiguredRunner:
        def __init__(self, api_key: str):
            created.append((self, api_key))
            self.closed = False

        async def run(self, text: str) -> dict:
            return {"suggestion": f"Advice for {text}"}

        async def close(self) -> None:
            self.closed = True

    monkeypatch.setattr("novelai_api.app.CodexAdviceRunner", ConfiguredRunner)
    settings = Settings(database.path, "https://testserver", codex_api_key="configured-test-key")
    assert "configured-test-key" not in repr(settings)
    with TestClient(create_app(settings, database), base_url=settings.public_origin) as client:
        login(client, database)
        response = advice(client, {"input": "lighting"})
        assert response.status_code == 200
        assert response.json() == {"suggestion": "Advice for lighting"}
    assert created[0][1] == "configured-test-key"
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


def isolated_runner(tmp_path: Path, sdk: FakeCodex) -> CodexAdviceRunner:
    async def fake_login(_cli_path, environment, api_key):
        assert api_key == "test-only-key"
        assert all("KEY" not in name for name in environment)
        assert "test-only-key" not in str(environment)
        (Path(environment["CODEX_HOME"]) / "auth.json").write_text("test-only-auth")

    return CodexAdviceRunner(
        "test-only-key",
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
        assert sdk.options["codex_path_override"] == "/fake/pinned/codex"
        assert "base_url" not in sdk.options
        assert "api_key" not in sdk.options
        assert sdk.options["env"]["HOME"] == sdk.options["env"]["CODEX_HOME"]
        assert set(sdk.options["env"]) == {"CODEX_HOME", "HOME", "TMPDIR", "PATH", "LANG"}
        assert not list(tmp_path.iterdir())

    asyncio.run(exercise())


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
    "output", ['not json', '{"suggestion":"ok","extra":1}', '{"suggestion":""}']
)
def test_sdk_rejects_non_schema_output(tmp_path: Path, output: str) -> None:
    async def events():
        yield sdk_event("item.completed", "agent_message", output)
        yield sdk_event("turn.completed")

    sdk = FakeCodex(events)
    runner = isolated_runner(tmp_path, sdk)

    async def exercise():
        with pytest.raises(AdviceFailure) as failure:
            await AdviceService(runner).advise("lighting")
        assert failure.value.code == "advice_failed"
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
