"""Several in-flight groups per GPT run; fakes only, never a paid provider."""

import sqlite3
import threading
import time
from uuid import uuid4

import pytest
from test_character_runs import png
from test_gpt_images import GPT_INPUT
from test_style_runs import database, owner, pump  # noqa: F401

from novelai_api.config import Settings, _concurrency
from novelai_api.dataset_plan import DatasetRunCreate
from novelai_api.db import Database
from novelai_api.generations import (
    GeneratedImage,
    GenerationManager,
    ReferenceImageUse,
    ResultCache,
)
from novelai_api.reference_images import ReferenceImageStore
from novelai_api.style_experiments import StyleExperimentService


class GatedGpt:
    """Blocks every call until released and records peak concurrency."""

    def __init__(self):
        self.gate = threading.Event()
        self.lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.ordinals = []

    def generate(self, parameters):
        raise AssertionError("GPT groups use generate_with_request")

    def generate_with_request(self, parameters, record_request, *, references=(), vibe_tokens=None):
        with self.lock:
            self.ordinals.append(parameters.experiment.ordinal)
            self.active += 1
            self.peak = max(self.peak, self.active)
        record_request({"provider": "fake"})
        try:
            assert self.gate.wait(timeout=4)
            return [GeneratedImage(png(), "image/png")] * parameters.sample_count
        finally:
            with self.lock:
                self.active -= 1


def gpt_items(reference_id: str, count: int) -> DatasetRunCreate:
    return DatasetRunCreate.model_validate({
        "id": str(uuid4()),
        "parameters": {**GPT_INPUT, "style_prompt": "anime coloring", "seed": 3},
        "items": [{"id": f"i{index}", "prompt": f"pose {index}"} for index in range(count)],
        "character": {"traits": "1girl", "mode": "gpt", "reference_ids": [reference_id]},
    })


def setup(database: Database, parallelism: int, count: int):  # noqa: F811
    user = owner(database)
    image = ReferenceImageStore(database).add(user, png(), source="upload")
    gpt = GatedGpt()
    manager = GenerationManager(
        database, None, cache=ResultCache(), gpt_provider=gpt, gpt_parallelism=parallelism,
    )
    service = StyleExperimentService(database, manager)
    run = service.store.create(
        user, gpt_items(str(image.id), count),
        references=[ReferenceImageUse(id=image.id, sha256=image.sha256)],
    )
    return user, gpt, manager, service, run


def wait_for(condition) -> None:
    deadline = time.monotonic() + 3
    while not condition():
        assert time.monotonic() < deadline
        time.sleep(0.005)


def test_gpt_run_keeps_lane_parallelism_groups_in_flight(database: Database) -> None:  # noqa: F811
    user, gpt, manager, service, run = setup(database, 3, 5)
    manager.start()
    try:
        service.tick()
        wait_for(lambda: gpt.active == 3)
        state = service.store.get(user, run.id)
        assert (state.in_flight_count, state.next_ordinal, state.current_ordinal) == (3, "4", "1")
        service.tick()
        assert gpt.active == 3 and service.store.get(user, run.id).next_ordinal == "4"
        gpt.gate.set()
        ended = pump(service, user, run.id)
    finally:
        gpt.gate.set()
        service.stop()
        manager.stop()
    assert (ended.status, ended.processed_count, ended.succeeded_count) == ("completed", "5", "5")
    assert (ended.in_flight_count, ended.current_job_id) == (0, None)
    assert sorted(gpt.ordinals) == ["1", "2", "3", "4", "5"] and gpt.peak == 3


def test_stop_lets_in_flight_groups_finish_and_claims_nothing_more(
    database: Database,  # noqa: F811
) -> None:
    user, gpt, manager, service, run = setup(database, 3, 6)
    manager.start()
    try:
        service.tick()
        wait_for(lambda: gpt.active == 3)
        stopping = service.store.stop(user, run.id)
        assert (stopping.status, stopping.in_flight_count) == ("stopping", 3)
        gpt.gate.set()
        ended = pump(service, user, run.id)
    finally:
        gpt.gate.set()
        service.stop()
        manager.stop()
    assert (ended.status, ended.processed_count, ended.next_ordinal) == ("stopped", "3", "4")
    assert sorted(gpt.ordinals) == ["1", "2", "3"]


def test_restart_counts_every_interrupted_group_once_and_never_repeats(
    database: Database,  # noqa: F811
) -> None:
    user, gpt, manager, service, run = setup(database, 3, 5)
    manager.start()
    service.tick()
    wait_for(lambda: gpt.active == 3)
    # Simulate a crash: forget the live workers without letting them persist results.
    service.stop()
    manager._working.clear()
    with database.connect(write=True) as connection:
        connection.execute("UPDATE generation_jobs SET status = 'running'")
    restarted_gpt = GatedGpt()
    restarted_gpt.gate.set()
    restarted = GenerationManager(
        database, None, cache=ResultCache(), gpt_provider=restarted_gpt, gpt_parallelism=3,
    )
    again = StyleExperimentService(database, restarted)
    restarted.start()
    try:
        ended = pump(again, user, run.id)
    finally:
        gpt.gate.set()
        again.stop()
        restarted.stop()
        manager.stop()
    assert (ended.status, ended.processed_count, ended.failed_count) == ("completed", "5", "3")
    assert sorted(restarted_gpt.ordinals) == ["4", "5"]


def test_schema9_current_group_moves_into_in_flight_table(tmp_path) -> None:
    upgraded = Database(tmp_path / "upgrade.sqlite3")
    upgraded.migrate()
    user = owner(upgraded)
    with upgraded.connect(write=True) as connection:
        connection.execute("DROP TABLE style_experiment_inflight")
        connection.execute("ALTER TABLE style_experiment_runs DROP COLUMN parallelism")
        connection.execute("PRAGMA user_version = 9")
        connection.execute(
            "INSERT INTO style_experiment_runs (user_id, id, definition_json, total, seed, "
            "status, created_at, updated_at, current_ordinal, current_job_id, next_ordinal) "
            "VALUES (?, 'r', '{}', '4', 1, 'running', 1, 1, '2', 'job-2', '3')", (user,),
        )
    upgraded.migrate()
    with sqlite3.connect(upgraded.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 11
        assert connection.execute(
            "SELECT run_id, job_id, ordinal FROM style_experiment_inflight",
        ).fetchall() == [("r", "job-2", "2")]
    assert upgraded.check_ready()


def test_concurrency_setting_bounds(tmp_path) -> None:
    assert _concurrency(None) == 8 and _concurrency("") == 8 and _concurrency("12") == 12
    for bad in ("0", "17", "-1", "x"):
        with pytest.raises(ValueError):
            Settings(tmp_path / "s.sqlite3", "https://x.example",
                     gpt_image_concurrency=_concurrency(bad))
    with pytest.raises(ValueError):
        GenerationManager(Database(tmp_path / "m.sqlite3"), None, gpt_parallelism=17)


def test_owner_concurrency_caps_and_changes_while_running(database: Database) -> None:  # noqa: F811
    user = owner(database)
    image = ReferenceImageStore(database).add(user, png(), source="upload")
    gpt = GatedGpt()
    manager = GenerationManager(
        database, None, cache=ResultCache(), gpt_provider=gpt, gpt_parallelism=4,
    )
    service = StyleExperimentService(database, manager)
    request = DatasetRunCreate.model_validate({
        **gpt_items(str(image.id), 8).model_dump(mode="json"), "gpt_concurrency": 2,
    })
    run = service.store.create(
        user, request, references=[ReferenceImageUse(id=image.id, sha256=image.sha256)],
    )
    assert run.parallelism == 2
    manager.start()
    try:
        service.tick()
        wait_for(lambda: gpt.active == 2)
        service.tick()
        assert gpt.active == 2
        raised = service.store.set_parallelism(user, run.id, 3)
        assert raised.parallelism == 3
        service.tick()
        wait_for(lambda: gpt.active == 3)
        # Above the server's lane parallelism the scheduler still uses the server cap.
        service.store.set_parallelism(user, run.id, 16)
        service.tick()
        wait_for(lambda: gpt.active == 4)
        service.tick()
        assert gpt.active == 4
        gpt.gate.set()
        ended = pump(service, user, run.id)
    finally:
        gpt.gate.set()
        service.stop()
        manager.stop()
    assert ended.status == "completed" and gpt.peak == 4
    assert service.store.set_parallelism(user, run.id, 2) == "finished"
    assert service.store.set_parallelism(user, str(uuid4()), 2) is None


def test_gpt_concurrency_validation_and_api(database: Database) -> None:  # noqa: F811
    from fastapi.testclient import TestClient
    from test_character_runs import character_run
    from test_generations import ORIGIN, login
    from test_style_runs import request as style_request

    from novelai_api.app import create_app

    with pytest.raises(ValueError):
        DatasetRunCreate.model_validate({
            **character_run([str(uuid4())]).model_dump(mode="json"), "gpt_concurrency": 2,
        })
    gpt = GatedGpt()
    app = create_app(
        Settings(database.path, "https://testserver", gpt_image_concurrency=3), database,
        image_provider=None, result_cache=ResultCache(), gpt_image_provider=gpt,
    )
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        assert client.get("/api/capabilities").json()["gpt_concurrency_max"] == 3
        uploaded = client.post("/api/reference-images", content=png(),
                               headers={"Content-Type": "image/png", **ORIGIN}).json()
        body = gpt_items(uploaded["id"], 3).model_dump(mode="json")
        too_high = client.post("/api/dataset-runs", json={**body, "gpt_concurrency": 4},
                               headers=ORIGIN)
        assert too_high.status_code == 422
        assert too_high.json()["code"] == "gpt_concurrency_too_high"
        created = client.post("/api/dataset-runs", json={**body, "gpt_concurrency": 1},
                              headers=ORIGIN)
        assert created.status_code == 202 and created.json()["parallelism"] == 1
        path = f"/api/style-experiment-runs/{created.json()['id']}/parallelism"
        assert client.put(path, json={"parallelism": 2}).status_code == 403
        assert client.put(path, json={"parallelism": 4}, headers=ORIGIN).json()["code"] == (
            "gpt_concurrency_too_high"
        )
        changed = client.put(path, json={"parallelism": 2}, headers=ORIGIN)
        assert changed.status_code == 200 and changed.json()["parallelism"] == 2
        style = client.post("/api/style-experiment-runs",
                            json=style_request().model_dump(mode="json"), headers=ORIGIN)
        assert client.put(
            f"/api/style-experiment-runs/{style.json()['id']}/parallelism",
            json={"parallelism": 2}, headers=ORIGIN,
        ).json()["code"] == "parallelism_unsupported"
        login(client, database, "bob")
        assert client.put(path, json={"parallelism": 2}, headers=ORIGIN).status_code == 404
        gpt.gate.set()
