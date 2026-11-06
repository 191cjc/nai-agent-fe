"""Durable scheduler and crash-window tests use only disposable SQLite and fakes."""

import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from importlib.resources import files
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_generations import INPUT, NATIVE_INPUT, ORIGIN, PNG, login

from novelai_api.app import create_app
from novelai_api.auth import create_token, issue_session
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import (
    GeneratedImage,
    GenerationManager,
    GenerationRequest,
    JobStore,
    ProviderFailure,
    ResultCache,
)
from novelai_api.image_results import DiskResultStore
from novelai_api.security import SESSION_COOKIE
from novelai_api.style_experiments import (
    RunConflict,
    RunCreate,
    RunStore,
    StyleExperimentService,
    group_parameters,
)


class ScriptedProvider:
    def __init__(self, outcomes=(), *, gate=None):
        self.outcomes = list(outcomes)
        self.gate = gate
        self.started = threading.Event()
        self.calls = []
        self.threads = set()

    def generate(self, parameters):
        index = len(self.calls)
        self.calls.append(parameters)
        self.threads.add(threading.current_thread().name)
        self.started.set()
        if self.gate is not None and index == 0:
            assert self.gate.wait(timeout=4)
        outcome = self.outcomes[index] if index < len(self.outcomes) else None
        if outcome == "invalid_result":
            return [GeneratedImage(b"invalid", "image/png")] * parameters.sample_count
        if outcome is not None:
            raise ProviderFailure(outcome)
        return [GeneratedImage(PNG, "image/png")] * parameters.sample_count


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "state" / "runs.sqlite3")
    database.migrate()
    return database


def owner(database: Database, label="alice") -> str:
    token_id, _token = create_token(database, label)
    with database.connect() as connection:
        return connection.execute(
            "SELECT user_id FROM access_tokens WHERE id = ?", (token_id,),
        ).fetchone()[0]


def request(*, run_id=None, seed=None, maximum="1.0", **changes) -> RunCreate:
    parameters = {
        **NATIVE_INPUT, "positive_prompt": "scene", "style_prompt": "artist:fixture",
        "seed": seed, **changes,
    }
    return RunCreate.model_validate({
        "id": str(run_id or uuid4()), "parameters": parameters,
        "ranges": [{"tag_index": 0, "min": "0.8", "max": maximum, "step": "0.1"}],
    })


def rewrite_legacy_definition(database: Database, user: str, run_id: str, *, style_only=False):
    """Fixture a definition persisted by the old version; never use new-plan validation."""
    with database.connect(write=True) as connection:
        definition = json.loads(connection.execute(
            "SELECT definition_json FROM style_experiment_runs WHERE user_id = ? AND id = ?",
            (user, run_id),
        ).fetchone()[0])
        definition["plan_version"] = 1
        definition["parameters"].pop("auto_character_position", None)
        if style_only:
            definition["parameters"]["positive_prompt"] = ""
        frozen = json.dumps(definition, sort_keys=True, separators=(",", ":"))
        connection.execute(
            "UPDATE style_experiment_runs SET definition_json = ? WHERE user_id = ? AND id = ?",
            (frozen, user, run_id),
        )
    return frozen


def pump(service: StyleExperimentService, user: str, run_id: str, *, terminal=True):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        service.tick()
        state = service.store.get(user, run_id)
        reached = (
            state.status in ("completed", "stopped") if terminal
            else state.current_job_id is not None
        )
        if reached:
            return state
        time.sleep(0.005)
    pytest.fail("Fake durable style run did not reach expected state")


@pytest.mark.parametrize(
    ("style", "expected"),
    [
        ("a,b,kept", ["kept", "b,kept", "a,kept", "a,b,kept"]),
        ("a,b", ["", "b", "a", "a,b"]),
    ],
)
def test_new_zero_weight_groups_submit_omissions_with_full_metadata(
    database: Database, style: str, expected: list[str],
) -> None:
    user = owner(database)
    provider = ScriptedProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    payload = request(seed=77, style_prompt=style).model_dump(mode="json")
    payload["ranges"] = [
        {"tag_index": index, "min": "-0.000", "max": "1", "step": "1"} for index in (0, 1)
    ]
    manager.start()
    try:
        run = service.store.create(user, RunCreate.model_validate(payload))
        assert run._plan_version == 2 and "plan_version" not in run.model_dump()
        ended = pump(service, user, run.id)
        assert ended.succeeded_count == "4" and ended.failed_count == "0"
        assert [call.style_prompt for call in provider.calls] == expected
        assert [call.experiment.ordinal for call in provider.calls] == ["1", "2", "3", "4"]
        actual_weights = [[weight.weight for weight in call.experiment.weights]
                          for call in provider.calls]
        assert actual_weights == [
            ["0.0", "0.0"], ["0.0", "1.0"], ["1.0", "0.0"], ["1.0", "1.0"],
        ]
        assert all(call.seed == 77 and call.positive_prompt == "scene" for call in provider.calls)
        assert all([weight.label for weight in call.experiment.weights] == ["a", "b"]
                   for call in provider.calls)
        assert all(call.character_prompts == run.parameters.character_prompts
                   for call in provider.calls)
        saved = sorted(manager.store.list(user, limit=100, offset=0).items,
                       key=lambda item: int(item.parameters.experiment.ordinal))
        for item, call in zip(saved, provider.calls, strict=True):
            assert item.parameters == call
            assert item.effective_seed == 77 and item.status == "succeeded"
            assert item.parameters.base_prompt == call.base_prompt
    finally:
        service.stop()
        manager.stop()


def test_new_all_zero_style_only_run_is_rejected_without_state_or_provider(database: Database):
    provider = ScriptedProvider()
    app = create_app(Settings(database.path, "https://testserver"), database,
                     image_provider=provider, result_cache=ResultCache())
    payload = request(positive_prompt="").model_dump(mode="json")
    payload["ranges"] = [{"tag_index": 0, "min": "0", "max": "1", "step": "1"}]
    with TestClient(app, base_url="https://testserver") as client:
        _token, user, _session = login(client, database, "alice")
        assert client.post("/api/style-experiment-runs", json=payload,
                           headers=ORIGIN).status_code == 422
        assert client.get("/api/style-experiment-runs/active").json() == {"run": None}
        assert app.state.generations.store.list(user, limit=100, offset=0).items == []
        with database.connect() as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM style_experiment_runs",
            ).fetchone()[0] == 0
        assert provider.calls == []


def test_legacy_same_definition_keeps_version_and_restart_never_repeats_ordinal(database: Database):
    user = owner(database)
    store = RunStore(database)
    payload = request(seed=77).model_dump(mode="json")
    payload["ranges"] = [{"tag_index": 0, "min": "-0.1", "max": "0.1", "step": "0.1"}]
    original = RunCreate.model_validate(payload)
    run = store.create(user, original)
    frozen = rewrite_legacy_definition(database, user, run.id)
    # A normalized retry cannot switch a legacy run to the new zero renderer.
    payload["ranges"] = [{"tag_index": 0, "min": "-00.1000", "max": "+.100", "step": ".100"}]
    attached = store.create(user, RunCreate.model_validate(payload))
    assert attached._plan_version == 1
    assert attached.model_dump() == run.model_dump()
    assert "plan_version" not in attached.model_dump()
    job = store.claim(user, run.id, "1", group_parameters(attached))
    assert JobStore(database).mark_running(job)
    provider = ScriptedProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        ended = pump(service, user, run.id)
        assert ended.processed_count == "3" and ended.failed_count == "1"
        assert [call.experiment.ordinal for call in provider.calls] == ["2", "3"]
        assert [call.style_prompt for call in provider.calls] == [
            "0.0::artist:fixture::", "0.1::artist:fixture::",
        ]
        assert all(call.seed == 77 for call in provider.calls)
        with database.connect() as connection:
            assert connection.execute(
                "SELECT definition_json FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user, run.id),
            ).fetchone()[0] == frozen
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 11
        assert store.create(user, original).model_dump() == ended.model_dump()
        payload["parameters"]["width"] = 1024
        with pytest.raises(RunConflict, match="experiment_run_conflict"):
            store.create(user, RunCreate.model_validate(payload))
    finally:
        service.stop()
        manager.stop()


def test_legacy_all_zero_style_only_run_survives_loading_stop_and_restart(database: Database):
    user = owner(database)
    store = RunStore(database)
    payload = request(seed=77).model_dump(mode="json")
    payload["ranges"] = [{"tag_index": 0, "min": "0", "max": "0", "step": "1"}]
    valid = RunCreate.model_validate(payload)
    stopped = store.create(user, valid)
    rewrite_legacy_definition(database, user, stopped.id, style_only=True)
    loaded = store.active(user)
    assert loaded._plan_version == 1 and loaded.parameters.positive_prompt == ""
    assert group_parameters(loaded).base_prompt == "0.0::artist:fixture::"
    assert store.stop(user, stopped.id).status == "stopped"
    payload["id"] = str(uuid4())
    running = store.create(user, RunCreate.model_validate(payload))
    rewrite_legacy_definition(database, user, running.id, style_only=True)
    provider = ScriptedProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        ended = pump(service, user, running.id)
        assert ended.succeeded_count == "1"
        assert len(provider.calls) == 1
        assert provider.calls[0].base_prompt == "0.0::artist:fixture::"
        assert provider.calls[0].experiment.weights[0].weight == "0.0"
        assert provider.calls[0].seed == 77
        assert store.get(user, stopped.id).status == "stopped"
    finally:
        service.stop()
        manager.stop()


@pytest.mark.parametrize("change", [{"plan_version": 3}, {"unexpected_definition_field": 1}])
def test_definition_compatibility_does_not_ignore_unknown_version_or_other_keys(
    database: Database, change: dict,
) -> None:
    user = owner(database)
    store = RunStore(database)
    original = request(seed=77)
    run = store.create(user, original)
    with database.connect(write=True) as connection:
        definition = json.loads(connection.execute(
            "SELECT definition_json FROM style_experiment_runs WHERE user_id = ? AND id = ?",
            (user, run.id),
        ).fetchone()[0])
        definition.update(change)
        connection.execute(
            "UPDATE style_experiment_runs SET definition_json = ? WHERE user_id = ? AND id = ?",
            (json.dumps(definition), user, run.id),
        )
    with pytest.raises(RunConflict, match="experiment_run_conflict"):
        store.create(user, original)


@pytest.mark.parametrize("version", [None, 1, 2])
def test_legacy_omitted_mode_is_idempotent_only_for_manual_and_preserves_raw_definition(
    database: Database, version: int | None,
) -> None:
    user = owner(database)
    store = RunStore(database)
    original = request(seed=77)
    run = store.create(user, original)
    with database.connect(write=True) as connection:
        definition = json.loads(connection.execute(
            "SELECT definition_json FROM style_experiment_runs WHERE user_id = ? AND id = ?",
            (user, run.id),
        ).fetchone()[0])
        definition["parameters"].pop("auto_character_position")
        if version is None:
            definition.pop("plan_version")
        else:
            definition["plan_version"] = version
        # Retain even historical whitespace, as well as renderer selection.
        frozen = json.dumps(definition, indent=2)
        connection.execute(
            "UPDATE style_experiment_runs SET definition_json = ? WHERE user_id = ? AND id = ?",
            (frozen, user, run.id),
        )
    attached = store.create(user, original)
    assert attached.parameters.auto_character_position is False
    assert attached.parameters.character_prompts == run.parameters.character_prompts
    assert attached._plan_version == (version or 1)
    for change in ({"auto_character_position": True}, {"width": 1024}):
        changed = original.model_copy(deep=True)
        changed.parameters = original.parameters.model_copy(update=change)
        with pytest.raises(RunConflict, match="^experiment_run_conflict$"):
            store.create(user, changed)
    with database.connect() as connection:
        assert connection.execute(
            "SELECT definition_json FROM style_experiment_runs WHERE user_id = ? AND id = ?",
            (user, run.id),
        ).fetchone()[0] == frozen
    assert RunStore(database).get(user, run.id).parameters.auto_character_position is False


@pytest.mark.parametrize("automatic", [False, True])
def test_new_saved_mode_changes_conflict_in_both_directions(database: Database, automatic: bool):
    user = owner(database)
    store = RunStore(database)
    original = request(seed=77, auto_character_position=automatic)
    run = store.create(user, original)
    assert store.create(user, original).model_dump() == run.model_dump()
    changed = original.model_copy(deep=True)
    changed.parameters.auto_character_position = not automatic
    with pytest.raises(RunConflict, match="^experiment_run_conflict$"):
        store.create(user, changed)
    assert store.get(user, run.id).parameters.auto_character_position is automatic


@pytest.mark.parametrize("automatic", [False, True])
@pytest.mark.parametrize("seed", [None, 77])
def test_failures_continue_with_one_seed_frozen_settings_and_single_paid_executor(
    database: Database, monkeypatch: pytest.MonkeyPatch, seed, automatic: bool,
) -> None:
    user = owner(database)
    provider = ScriptedProvider(["outcome_unknown", "invalid_result", None])
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    random = Mock(return_value=122)
    monkeypatch.setattr("novelai_api.style_experiments.secrets.randbelow", random)
    manager.start()
    try:
        original = request(seed=seed, auto_character_position=automatic)
        run = service.store.create(user, original)
        # The persisted snapshot must not follow edits to the creator's model.
        original.parameters.character_prompts[0].x = 0.8
        original.parameters.width = 1024
        original.parameters.auto_character_position = not automatic
        ended = pump(service, user, run.id)
        assert ended.status == "completed"
        assert (ended.processed_count, ended.succeeded_count, ended.failed_count) == ("3", "1", "2")
        assert ended.next_ordinal == "4" and ended.current_job_id is None
        assert [call.experiment.ordinal for call in provider.calls] == ["1", "2", "3"]
        assert [call.experiment.weights[0].weight for call in provider.calls] == [
            "0.8", "0.9", "1.0",
        ]
        assert [call.style_prompt for call in provider.calls] == [
            "0.8::artist:fixture::", "0.9::artist:fixture::", "artist:fixture",
        ]
        assert all(call.seed == (seed or 123) for call in provider.calls)
        assert all(call.width == 512 and call.sample_count == 2 for call in provider.calls)
        assert all(call.character_prompts[0].x == 0.1 for call in provider.calls)
        assert all(call.character_prompts[1].y == 0.27 for call in provider.calls)
        assert all(call.auto_character_position is automatic for call in provider.calls)
        assert ended.parameters.auto_character_position is automatic
        assert ended.parameters.style_prompt == "artist:fixture"
        assert ended.parameters.seed == seed
        assert len(provider.threads) == 1
        assert random.call_count == int(seed is None)
        assert manager.cache._results
        assert len(manager.store.list(user, limit=100, offset=0).items) == 3
        service.tick()
        assert service.store.get(user, run.id).processed_count == "3"
        assert len(provider.calls) == 3
    finally:
        service.stop()
        manager.stop()


@pytest.mark.parametrize("refusal", ["provider", "storage"])
def test_definite_admission_refusals_create_distinct_failed_groups_and_continue(
    database: Database, refusal: str,
) -> None:
    user = owner(database)
    provider = ScriptedProvider() if refusal == "storage" else None
    cache = DiskResultStore(database.path.parent / "images", disk_free=lambda _path: 0)
    manager = GenerationManager(database, provider, cache=cache)
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        run = service.store.create(user, request(seed=77))
        for expected in range(1, 4):
            service.tick()
            state = service.store.get(user, run.id)
            assert state.processed_count == str(expected)
            assert state.failed_count == str(expected)
            assert state.succeeded_count == "0"
        assert state.status == "completed"
        jobs = manager.store.list(user, limit=100, offset=0).items
        assert sorted(item.parameters.experiment.ordinal for item in jobs) == ["1", "2", "3"]
        assert all(item.effective_seed == 77 for item in jobs)
        expected_code = (
            "provider_unavailable" if refusal == "provider" else "result_storage_unavailable"
        )
        assert all(item.error_code == expected_code for item in jobs)
        assert cache._reservations == {}
        assert provider is None or provider.calls == []
    finally:
        service.stop()
        manager.stop()


def test_immediate_refusal_scheduler_does_not_spin_or_require_an_observer(
    database: Database,
) -> None:
    user = owner(database)
    manager = GenerationManager(database, None, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        run = service.store.create(user, request(maximum="2.0"))
        service.start()
        deadline = time.monotonic() + 1
        while (
            service.store.get(user, run.id).processed_count == "0" and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        time.sleep(0.1)
        # No page/GET/job observer drives progress, but rejections are paced at 1s.
        state = service.store.get(user, run.id)
        assert state.processed_count == "1" and state.status == "running"
    finally:
        service.stop()
        manager.stop()


def test_full_shared_queue_waits_without_skipping_a_combination(database: Database) -> None:
    user = owner(database)
    gate = threading.Event()
    provider = ScriptedProvider(gate=gate)
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        regular = GenerationRequest(**INPUT, seed=55)
        ordinary = [manager.submit(user, regular) for _ in range(3)]
        assert provider.started.wait(timeout=2)
        run = service.store.create(user, request(seed=77, maximum="0.8"))
        service.tick()
        waiting = service.store.get(user, run.id)
        assert waiting.next_ordinal == "1" and waiting.current_job_id is None
        assert waiting.failed_count == "0"
        assert len(manager.store.list(user, limit=100, offset=0).items) == 3
        gate.set()
        ended = pump(service, user, run.id)
        assert ended.succeeded_count == "1"
        assert len(provider.calls) == 4
        assert provider.calls[-1].experiment.ordinal == "1"
        assert all(manager.store.get(user, job).status == "succeeded" for job in ordinary)
        assert len(provider.threads) == 1
    finally:
        gate.set()
        service.stop()
        manager.stop()


def test_queue_slots_rotate_between_continuously_active_owners(database: Database) -> None:
    class ControlledCapacity:
        def __init__(self):
            self.store = JobStore(database)
            self.pending = {}

        def submit(self, user_id, parameters, *, create):
            if len(self.pending) == 3:
                return None
            job_id = create(user_id, parameters)
            if job_id is not None:
                self.pending[job_id] = parameters
            return job_id

        def is_inflight(self, job_id):
            return job_id in self.pending

        def parallelism(self, lane):
            return 1

        def lane_ready(self, lane):
            return True

        def lane_paused_until(self, lane):
            return None

        def finish_all(self):
            for job_id, parameters in self.pending.items():
                assert self.store.mark_running(job_id)
                assert self.store.finish(job_id, image_count=parameters.sample_count)
            self.pending.clear()

    manager = ControlledCapacity()
    service = StyleExperimentService(database, manager)
    runs = [(user, service.store.create(user, request(maximum="2.0")))
            for user in (owner(database, f"owner-{index}") for index in range(6))]
    for _ in range(8):
        service.tick()
        assert len(manager.pending) == 3
        manager.finish_all()
    # Every owner gets repeated opportunities while all six runs stay active.
    # A fixed sorted traversal only ever admits the same first three owners.
    for user, run in runs:
        saved = manager.store.list(user, limit=100, offset=0).items
        assert len(saved) >= 3
        assert service.store.get(user, run.id).status == "running"
        assert sorted(int(item.parameters.experiment.ordinal) for item in saved) == (
            list(range(1, len(saved) + 1))
        )


def test_stop_before_claim_and_after_terminal_are_idempotent(database: Database) -> None:
    user = owner(database)
    manager = GenerationManager(database, ScriptedProvider(), cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        run = service.store.create(user, request())
        stopped = service.store.stop(user, run.id)
        assert stopped.status == "stopped"
        assert service.store.stop(user, run.id).model_dump() == stopped.model_dump()
        service.tick()
        assert manager.provider.calls == []
        assert manager.store.list(user, limit=100, offset=0).items == []
        next_run = service.store.create(user, request(maximum="0.8"))
        ended = pump(service, user, next_run.id)
        assert ended.status == "completed"
        assert service.store.stop(user, ended.id).model_dump() == ended.model_dump()
    finally:
        service.stop()
        manager.stop()


def test_stop_during_paid_group_allows_only_current_to_finish(database: Database) -> None:
    user = owner(database)
    gate = threading.Event()
    provider = ScriptedProvider(gate=gate)
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        run = service.store.create(user, request(seed=77))
        service.tick()
        assert provider.started.wait(timeout=2)
        stopping = service.store.stop(user, run.id)
        assert stopping.status == "stopping" and stopping.current_ordinal == "1"
        gate.set()
        stopped = pump(service, user, run.id)
        assert stopped.status == "stopped"
        assert (stopped.processed_count, stopped.next_ordinal) == ("1", "2")
        assert len(provider.calls) == 1
        service.tick()
        assert len(provider.calls) == 1
    finally:
        gate.set()
        service.stop()
        manager.stop()


def test_stop_wins_before_claim_transaction_and_releases_admission(
    database: Database, monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = owner(database)
    provider = ScriptedProvider()
    manager = GenerationManager(
        database, provider, cache=DiskResultStore(database.path.parent / "images"),
    )
    service = StyleExperimentService(database, manager)
    manager.start()
    entered, proceed = threading.Event(), threading.Event()
    original = service.store.claim

    def held_claim(*args, **kwargs):
        entered.set()
        assert proceed.wait(timeout=2)
        return original(*args, **kwargs)

    monkeypatch.setattr(service.store, "claim", held_claim)
    worker = None
    try:
        run = service.store.create(user, request())
        worker = threading.Thread(target=service.tick)
        worker.start()
        assert entered.wait(timeout=2)
        assert service.store.stop(user, run.id).status == "stopped"
        proceed.set()
        worker.join(timeout=2)
        assert not worker.is_alive()
        assert provider.calls == []
        assert manager.cache._reservations == {}
        assert manager.store.list(user, limit=100, offset=0).items == []
    finally:
        proceed.set()
        if worker is not None:
            worker.join(timeout=2)
        service.stop()
        manager.stop()


@pytest.mark.parametrize("automatic", [False, True])
@pytest.mark.parametrize("window", ["queued", "running", "terminal", "settled", "unattached"])
def test_restart_reconciles_each_crash_window_without_repeating_an_ordinal(
    database: Database, window: str, automatic: bool,
) -> None:
    user = owner(database)
    store = RunStore(database)
    definition = request(seed=77, auto_character_position=automatic)
    run = store.create(user, definition)
    definition.parameters.auto_character_position = not automatic
    definition.parameters.character_prompts[0].x = 0.8
    first = group_parameters(run)
    if window == "unattached":
        with database.connect(write=True) as connection:
            job_id = JobStore.create_in_transaction(connection, user, first, run_claim=True)
    else:
        job_id = store.claim(user, run.id, "1", first)
    jobs = JobStore(database)
    old_provider = ScriptedProvider()
    if window in ("running", "terminal", "settled"):
        assert jobs.mark_running(job_id)
        old_provider.generate(first)
    if window in ("terminal", "settled"):
        assert jobs.finish(job_id, image_count=2)
    if window == "settled":
        assert store.reconcile(user, run.id).processed_count == "1"
    new_provider = ScriptedProvider()
    manager = GenerationManager(database, new_provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        ended = pump(service, user, run.id)
        assert ended.status == "completed" and ended.processed_count == "3"
        assert [call.experiment.ordinal for call in new_provider.calls] == ["2", "3"]
        assert all(call.seed == 77 for call in new_provider.calls)
        assert all(call.auto_character_position is automatic for call in new_provider.calls)
        assert all(call.character_prompts == first.character_prompts for call in new_provider.calls)
        assert ended.parameters.auto_character_position is automatic
        assert len(old_provider.calls) <= 1
        saved = jobs.list(user, limit=100, offset=0).items
        assert len(saved) == 3
        assert all(item.parameters.auto_character_position is automatic for item in saved)
        assert all(item.parameters.character_prompts == first.character_prompts for item in saved)
        assert ended.failed_count == ("0" if window in ("terminal", "settled") else "1")
        service.tick()
        assert service.store.get(user, run.id).processed_count == "3"
    finally:
        service.stop()
        manager.stop()


def test_restart_with_stop_request_settles_current_without_new_provider_work(
    database: Database,
) -> None:
    user = owner(database)
    store = RunStore(database)
    run = store.create(user, request())
    store.claim(user, run.id, "1", group_parameters(run))
    assert store.stop(user, run.id).status == "stopping"
    provider = ScriptedProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        stopped = pump(service, user, run.id)
        assert stopped.status == "stopped"
        assert stopped.failed_count == "1"
        assert provider.calls == []
    finally:
        service.stop()
        manager.stop()


def test_enqueue_uncertainty_counts_once_and_continues_without_late_paid_retry(
    database: Database, monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = owner(database)
    provider = ScriptedProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    queued = []
    original = manager._executors["novelai"].submit

    def fail_first(*args):
        if not queued:
            queued.append(args)
            raise RuntimeError("fixture failure after accepting work")
        return original(*args)

    monkeypatch.setattr(manager._executors["novelai"], "submit", fail_first)
    try:
        run = service.store.create(user, request())
        ended = pump(service, user, run.id)
        assert ended.failed_count == "1" and ended.succeeded_count == "2"
        work, *arguments = queued[0]
        work(*arguments)
        assert [call.experiment.ordinal for call in provider.calls] == ["2", "3"]
        assert manager.store.list(user, limit=100, offset=0).items
    finally:
        service.stop()
        manager.stop()


def test_terminal_database_write_failure_does_not_strand_or_repeat_paid_group(
    database: Database, monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = owner(database)
    provider = ScriptedProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    first_id = []
    finish = manager.store.finish

    def unavailable_finish(job_id, **kwargs):
        if not first_id:
            first_id.append(job_id)
        if job_id == first_id[0]:
            raise sqlite3.OperationalError("fixture outage during terminal write")
        return finish(job_id, **kwargs)

    monkeypatch.setattr(manager.store, "finish", unavailable_finish)
    try:
        run = service.store.create(user, request())
        ended = pump(service, user, run.id)
        assert ended.failed_count == "1" and ended.succeeded_count == "2"
        assert [call.experiment.ordinal for call in provider.calls] == ["1", "2", "3"]
        assert manager.store.get(user, first_id[0]).error_code == "outcome_unknown"
        assert manager._working == {}
    finally:
        service.stop()
        manager.stop()


def test_history_delete_guard_and_final_counters_do_not_depend_on_remaining_rows(
    database: Database,
) -> None:
    user = owner(database)
    manager = GenerationManager(database, ScriptedProvider(), cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        definition = request()
        run = service.store.create(user, definition)
        service.tick()
        deadline = time.monotonic() + 2
        state = service.store.get(user, run.id)
        while manager.store.get(user, state.current_job_id).status != "succeeded":
            assert time.monotonic() < deadline
            time.sleep(0.005)
        first = state.current_job_id
        assert manager.store.delete(user, first) == "experiment_active"
        service.store.reconcile(user, run.id)
        assert manager.store.delete(user, first) == "experiment_active"
        ended = pump(service, user, run.id)
        assert manager.store.delete(user, first) == "deleted"
        assert service.store.create(user, definition).model_dump() == ended.model_dump()
        assert service.store.get(user, run.id).processed_count == "3"
    finally:
        service.stop()
        manager.stop()


def test_concurrent_idempotent_create_one_active_owner_and_used_id_refusal(
    database: Database, monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = owner(database)
    store = RunStore(database)
    definition = request()
    random = Mock(return_value=100)
    monkeypatch.setattr("novelai_api.style_experiments.secrets.randbelow", random)
    barrier = threading.Barrier(2)

    def create():
        barrier.wait(timeout=2)
        return store.create(user, definition)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create(), range(2)))
    assert results[0].model_dump() == results[1].model_dump()
    assert random.call_count == 1
    assert store.create(user, request()).queue_position == 1
    with pytest.raises(RunConflict, match="experiment_run_conflict"):
        store.create(user, request(run_id=definition.id, width=1024))
    store.stop(user, str(definition.id))
    used_id = str(uuid4())
    parameters = GenerationRequest(**{
        **INPUT, "seed": 77,
        "experiment": {"id": used_id, "ordinal": "1", "total": "1", "weights": [
            {"tag_index": 0, "label": "x", "weight": "1.0"},
        ]},
    })
    JobStore(database).create(user, parameters)
    with pytest.raises(RunConflict, match="experiment_run_conflict"):
        store.create(user, request(run_id=used_id))


def test_api_reconnect_owner_origin_validation_and_legacy_injection(database: Database) -> None:
    provider = ScriptedProvider()
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=provider, result_cache=ResultCache(),
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/api/style-experiment-runs/active").status_code == 401
        _token, alice, session = login(client, database, "alice")
        payload = request().model_dump(mode="json")
        assert client.post("/api/style-experiment-runs", json=payload).status_code == 403
        invalid = {**payload, "ranges": [{"tag_index": 0, "min": "0", "max": "1", "step": "0"}]}
        assert client.post(
            "/api/style-experiment-runs", json=invalid, headers=ORIGIN,
        ).status_code == 422
        assert client.get("/api/style-experiment-runs/active").json() == {"run": None}
        created = client.post("/api/style-experiment-runs", json=payload, headers=ORIGIN)
        assert created.status_code == 202
        run_id = created.json()["id"]
        assert created.json()["parameters"]["character_prompts"] == (
            NATIVE_INPUT["character_prompts"]
        )
        assert client.get(f"/api/style-experiment-runs/{run_id}").status_code == 200
        second = client.post("/api/style-experiment-runs", json=payload, headers=ORIGIN)
        assert second.status_code == 202
        legacy = {
            **INPUT, "experiment": {"id": run_id, "ordinal": "99", "total": "99", "weights": [
                {"tag_index": 0, "label": "x", "weight": "1.0"},
            ]},
        }
        injection = client.post("/api/generations", json=legacy, headers=ORIGIN)
        assert injection.status_code == 409
        assert injection.json()["code"] == "experiment_conflict"
        login(client, database, "bob")
        assert client.get("/api/style-experiment-runs/active").json() == {"run": None}
        assert client.get(f"/api/style-experiment-runs/{run_id}").status_code == 404
        assert client.post(
            f"/api/style-experiment-runs/{run_id}/stop", headers=ORIGIN,
        ).status_code == 404
        # Removing the authenticated observer does not stop the authorized run.
        assert client.delete("/api/auth/session", headers=ORIGIN).status_code == 204
        deadline = time.monotonic() + 3
        while app.state.experiments.store.get(alice, run_id).status != "completed":
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert len(provider.calls) == 3
        client.cookies.clear()
        client.cookies.set(SESSION_COOKIE, session)
        attached = client.get(f"/api/style-experiment-runs/{run_id}").json()
        assert attached["processed_count"] == "3" and attached["seed"] == created.json()["seed"]


def test_logging_out_the_run_owner_detaches_without_stopping_and_login_reattaches(
    database: Database,
) -> None:
    gate = threading.Event()
    provider = ScriptedProvider(gate=gate)
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=provider, result_cache=ResultCache(),
    )
    app.state.experiments._interval = 0.01
    _token_id, token = create_token(database, "alice")
    with TestClient(app, base_url="https://testserver") as client:
        try:
            logged_in = client.post("/api/auth/session", json={"token": token}, headers=ORIGIN)
            user = logged_in.json()["id"]
            created = client.post(
                "/api/style-experiment-runs", json=request().model_dump(mode="json"),
                headers=ORIGIN,
            ).json()
            assert provider.started.wait(timeout=2)
            assert client.delete("/api/auth/session", headers=ORIGIN).status_code == 204
            assert client.get("/api/style-experiment-runs/active").status_code == 401
            gate.set()
            deadline = time.monotonic() + 3
            while app.state.experiments.store.get(user, created["id"]).status != "completed":
                assert time.monotonic() < deadline
                time.sleep(0.01)
            assert client.post(
                "/api/auth/session", json={"token": token}, headers=ORIGIN,
            ).status_code == 200
            attached = client.get(f"/api/style-experiment-runs/{created['id']}").json()
            assert attached["status"] == "completed" and attached["processed_count"] == "3"
            assert attached["seed"] == created["seed"]
            assert len(provider.calls) == 3
        finally:
            gate.set()


def test_v2_migration_and_backup_preserve_auth_jobs_and_private_run_state(tmp_path: Path) -> None:
    database = Database(tmp_path / "previous.sqlite3")
    with sqlite3.connect(database.path) as connection:
        for filename in ("0001_auth.sql", "0002_generations.sql"):
            connection.executescript(
                files("novelai_api").joinpath("migrations", filename).read_text(),
            )
    token_id, token = create_token(database, "alice")
    session, user = issue_session(database, token)
    with database.connect() as connection:
        owner_id = connection.execute(
            "SELECT user_id FROM access_tokens WHERE id = ?", (token_id,),
        ).fetchone()[0]
    old_job = JobStore(database).create(owner_id, GenerationRequest(**INPUT, seed=77))
    assert not database.check_ready()
    database.migrate()
    database.migrate()
    assert database.check_ready()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 11
        assert connection.execute("SELECT COUNT(*) FROM browser_sessions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM generation_jobs").fetchone()[0] == 1
    run = RunStore(database).create(owner_id, request(seed=77))
    snapshot = tmp_path / "snapshot.sqlite3"
    database.backup(snapshot)
    restored = Database(snapshot)
    # Read-only drill: do not start a cloned scheduler against a copied active run.
    assert RunStore(restored).get(owner_id, run.id).model_dump() == run.model_dump()
    assert JobStore(restored).get(owner_id, old_job).effective_seed == 77
    assert session and user["id"] == owner_id
    assert PNG not in snapshot.read_bytes()
    assert snapshot.stat().st_mode & 0o777 == 0o600
    with restored.connect() as connection:
        persisted = json.loads(connection.execute(
            "SELECT definition_json FROM style_experiment_runs",
        ).fetchone()[0])
        assert persisted["plan_version"] == 2
