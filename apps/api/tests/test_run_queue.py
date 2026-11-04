"""Queued runs per owner and lane; fakes only, never a paid provider."""

import threading
import time

from fastapi.testclient import TestClient
from test_character_runs import png
from test_dataset_runs import dataset
from test_generations import ORIGIN, login
from test_gpt_images import GptFake, gpt_run
from test_style_runs import ScriptedProvider, database, owner, pump, request  # noqa: F401

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.dataset_plan import DatasetRunCreate
from novelai_api.db import Database
from novelai_api.generations import GenerationManager, ReferenceImageUse, ResultCache
from novelai_api.reference_images import ReferenceImageStore
from novelai_api.style_experiments import StyleExperimentService


def experiment_ids(calls) -> list[str]:
    return [str(call.experiment.id) for call in calls]


def wait_until(condition, service: StyleExperimentService | None = None) -> None:
    deadline = time.monotonic() + 3
    while not condition():
        assert time.monotonic() < deadline
        if service is not None:
            service.tick()
        time.sleep(0.005)


def test_same_lane_runs_execute_strictly_in_creation_order(database: Database) -> None:  # noqa: F811
    user = owner(database)
    gate = threading.Event()
    provider = ScriptedProvider(gate=gate)
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        first = service.store.create(user, request(seed=5))
        second = service.store.create(user, request(seed=6))
        assert (first.queue_position, second.queue_position) == (0, 1)
        service.tick()
        assert provider.started.wait(timeout=2)
        service.tick()
        # The queued run claims nothing (no history, no paid call) while it waits.
        waiting = service.store.get(user, second.id)
        assert (waiting.status, waiting.current_job_id, waiting.next_ordinal) == (
            "running", None, "1",
        )
        assert waiting.queue_position == 1
        gate.set()
        done = pump(service, user, first.id)
        assert done.status == "completed"
        assert service.store.get(user, second.id).queue_position == 0
        assert pump(service, user, second.id).status == "completed"
    finally:
        gate.set()
        service.stop()
        manager.stop()
    total = int(first.total)
    assert experiment_ids(provider.calls) == [first.id] * total + [second.id] * total


def test_gpt_lane_runs_while_novelai_lane_is_busy(database: Database) -> None:  # noqa: F811
    user = owner(database)
    images = ReferenceImageStore(database)
    image = images.add(user, png(), source="upload")
    gate = threading.Event()
    nai, gpt = ScriptedProvider(gate=gate), GptFake()
    manager = GenerationManager(database, nai, cache=ResultCache(), gpt_provider=gpt)
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        style = service.store.create(user, request(seed=5))
        character = service.store.create(
            user, gpt_run([image.id]),
            references=[ReferenceImageUse(id=image.id, sha256=image.sha256)],
        )
        assert (style.lane, character.lane) == ("novelai", "gpt")
        assert (style.queue_position, character.queue_position) == (0, 0)
        service.tick()
        assert nai.started.wait(timeout=2)
        # NovelAI's first group is still blocked; the GPT run finishes regardless.
        finished = pump(service, user, character.id)
        assert finished.status == "completed" and finished.succeeded_count == "2"
        assert service.store.get(user, style.id).processed_count == "0"
        gate.set()
        assert pump(service, user, style.id).status == "completed"
    finally:
        gate.set()
        service.stop()
        manager.stop()
    assert nai.threads == {"nai-gen_0"}
    assert len(gpt.calls) == 2


def test_stopping_a_queued_run_never_claims_and_promotes_the_next(
    database: Database,  # noqa: F811
) -> None:
    user = owner(database)
    gate = threading.Event()
    provider = ScriptedProvider(gate=gate)
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        first = service.store.create(user, request(seed=5))
        queued = service.store.create(user, request(seed=6))
        third = service.store.create(user, request(seed=7))
        service.tick()
        assert provider.started.wait(timeout=2)
        stopped = service.store.stop(user, queued.id)
        assert (stopped.status, stopped.processed_count, stopped.queue_position) == (
            "stopped", "0", None,
        )
        assert service.store.get(user, third.id).queue_position == 1
        gate.set()
        pump(service, user, first.id)
        pump(service, user, third.id)
    finally:
        gate.set()
        service.stop()
        manager.stop()
    assert queued.id not in experiment_ids(provider.calls)
    assert service.store.get(user, queued.id).next_ordinal == "1"


def test_queue_is_owner_scoped_and_restart_keeps_order(database: Database) -> None:  # noqa: F811
    user, other = owner(database), owner(database, "bob")
    store = StyleExperimentService(
        database, GenerationManager(database, ScriptedProvider(), cache=ResultCache()),
    ).store
    first = store.create(user, request())
    theirs = store.create(other, request())
    second = store.create(user, DatasetRunCreate.model_validate(
        {**dataset().model_dump(mode="json"), "name": "第二组"},
    ))
    # Same-second creations keep insertion order.
    with database.connect(write=True) as connection:
        connection.execute("UPDATE style_experiment_runs SET created_at = 100")
    restarted = StyleExperimentService(
        Database(database.path),
        GenerationManager(database, ScriptedProvider(), cache=ResultCache()),
    ).store
    assert [(run.id, run.queue_position) for run in restarted.queue(user)] == [
        (first.id, 0), (second.id, 1),
    ]
    assert [run.name for run in restarted.queue(user)] == [None, "第二组"]
    assert [(run.id, run.queue_position) for run in restarted.queue(other)] == [(theirs.id, 0)]


def test_queue_api_lists_named_runs_and_requires_login(database: Database) -> None:  # noqa: F811
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=ScriptedProvider(gate=threading.Event()), result_cache=ResultCache(),
    )
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/api/style-experiment-runs/queue").status_code == 401
        login(client, database, "alice")
        first = client.post("/api/style-experiment-runs",
                            json=request().model_dump(mode="json"), headers=ORIGIN)
        assert first.status_code == 202 and first.json()["queue_position"] == 0
        second = client.post("/api/style-experiment-runs",
                             json=request().model_dump(mode="json"), headers=ORIGIN)
        assert second.status_code == 202 and second.json()["queue_position"] == 1
        runs = client.get("/api/style-experiment-runs/queue").json()["runs"]
        assert [(run["id"], run["queue_position"], run["lane"]) for run in runs] == [
            (first.json()["id"], 0, "novelai"), (second.json()["id"], 1, "novelai"),
        ]
        assert client.get("/api/style-experiment-runs/active").json()["run"]["id"] == (
            first.json()["id"]
        )
        for run in runs:
            client.post(f"/api/style-experiment-runs/{run['id']}/stop", headers=ORIGIN)
        assert client.get("/api/style-experiment-runs/queue").json()["runs"] == []
