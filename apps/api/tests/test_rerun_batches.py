"""Durable re-run batches of training-set groups; disposable SQLite and fakes only."""

import sqlite3
import uuid

from fastapi.testclient import TestClient
from test_character_runs import ReferenceProvider, database  # noqa: F401
from test_generations import INPUT, login
from test_reruns import ORIGIN, finished_run, wait

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import ResultCache


def app_for(database: Database, provider: ReferenceProvider | None = None):  # noqa: F811
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=provider or ReferenceProvider(), result_cache=ResultCache(),
    )
    app.state.experiments._interval = 0.01
    return app


def groups(client: TestClient, run_id: str) -> list[dict]:
    return client.get(f"/api/style-experiments/{run_id}", params={"limit": 50}).json()["items"]


def run_state(client: TestClient, run_id: str) -> dict:
    return client.get(f"/api/style-experiment-runs/{run_id}").json()


def test_batch_runs_on_the_server_with_edits_and_discards(database: Database) -> None:  # noqa: F811
    provider = ReferenceProvider()
    app = app_for(database, provider)
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        run = finished_run(client, seed=11, sample_count=2)
        sources = groups(client, run["id"])
        calls = len(provider.calls)
        batch = {
            "id": str(uuid.uuid4()), "experiment_id": run["id"], "name": "set · 重跑",
            "items": [
                {"job_id": sources[0]["id"], "discard_index": 1},
                {"job_id": sources[1]["id"], "prompt": "1girl, parted bangs"},
                {"job_id": sources[2]["id"], "style_prompt": "ink"},
            ],
        }
        assert client.post("/api/rerun-batches", json=batch).status_code == 403  # Origin
        created = client.post("/api/rerun-batches", json=batch, headers=ORIGIN)
        assert created.status_code == 202
        state = created.json()
        assert (state["kind"], state["total"], state["lane"], state["name"]) == (
            "rerun", "3", "novelai", "set · 重跑")
        assert state["rerun_experiment_id"] == run["id"]
        assert [item["job_id"] for item in state["rerun_items"]] == [
            source["id"] for source in sources[:3]]
        done = wait(client, f"/api/style-experiment-runs/{state['id']}",
                    lambda body: body["status"] == "completed")
        assert (done["succeeded_count"], done["failed_count"]) == ("3", "0")
        assert len(provider.calls) == calls + 3

        # Same id, same batch: idempotent; same id, other items: conflict.
        again = client.post("/api/rerun-batches", json=batch, headers=ORIGIN)
        assert again.status_code == 202 and again.json()["id"] == state["id"]
        changed = {**batch, "items": batch["items"][:1]}
        assert client.post("/api/rerun-batches", json=changed, headers=ORIGIN).status_code == 409

        after = groups(client, run["id"])
        reruns = [group for group in after if group["parameters"]["experiment"].get("rerun_of")]
        by_source = {group["parameters"]["experiment"]["rerun_of"]: group for group in reruns}
        assert set(by_source) == {source["id"] for source in sources[:3]}
        assert all(group["parameters"]["sample_count"] == 1 for group in reruns)
        assert by_source[sources[1]["id"]]["parameters"]["positive_prompt"] == (
            "1girl, parted bangs")
        assert by_source[sources[2]["id"]]["parameters"]["style_prompt"] == "ink"
        assert client.get(f"/api/generations/{sources[0]['id']}").json()[
            "discarded_images"] == [1]
        # The batch never shows up as a training set of its own.
        listed = client.get("/api/style-experiments").json()["items"]
        assert state["id"] not in [item["id"] for item in listed]

        login(client, database, "bob")
        stranger = {**batch, "id": str(uuid.uuid4())}
        assert client.post("/api/rerun-batches", json=stranger, headers=ORIGIN).status_code == 404


def test_batch_validates_every_item_before_queueing(database: Database) -> None:  # noqa: F811
    app = app_for(database)
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        first = finished_run(client)
        second = finished_run(client)
        mine = groups(client, first["id"])[0]
        other = groups(client, second["id"])[0]
        ordinary = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        wait(client, f"/api/generations/{ordinary}", lambda job: job["status"] == "succeeded")

        def post(*items: dict) -> dict:
            response = client.post("/api/rerun-batches", headers=ORIGIN, json={
                "id": str(uuid.uuid4()), "experiment_id": first["id"], "items": list(items)})
            return {"status": response.status_code, **response.json()}

        for item, code in (
            ({"job_id": other["id"]}, "rerun_source_missing"),
            ({"job_id": ordinary}, "rerun_source_missing"),
            ({"job_id": "missing"}, "rerun_source_missing"),
            ({"job_id": mine["id"], "discard_index": 5}, "rerun_image_missing"),
            ({"job_id": mine["id"], "style_prompt": " "}, "rerun_invalid"),
        ):
            refused = post({"job_id": mine["id"]}, item)
            assert (refused["status"], refused["code"]) == (422, code)
            assert refused["message"].startswith("Item 2:")
        assert post()["status"] == 422  # Empty batch
        assert client.get("/api/style-experiment-runs/queue").json()["runs"] == []

        style = client.post("/api/rerun-batches", headers=ORIGIN, json={
            "id": str(uuid.uuid4()), "experiment_id": str(uuid.uuid4()),
            "items": [{"job_id": mine["id"]}]})
        assert style.status_code == 404


def test_stopped_batch_continues_and_skips_deleted_sources(
    database: Database,  # noqa: F811
) -> None:
    provider = ReferenceProvider()
    app = app_for(database, provider)
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        run = finished_run(client, seed=3)
        sources = groups(client, run["id"])
        app.state.experiments.stop()  # Hold the scheduler so nothing is claimed yet.
        batch_id = str(uuid.uuid4())
        created = client.post("/api/rerun-batches", headers=ORIGIN, json={
            "id": batch_id, "experiment_id": run["id"], "name": "fix",
            "items": [{"job_id": source["id"]} for source in sources[:3]]})
        assert created.json()["queue_position"] == 0
        stopped = client.post(f"/api/style-experiment-runs/{batch_id}/stop", headers=ORIGIN)
        assert stopped.json()["status"] == "stopped"

        continued_id = str(uuid.uuid4())
        continued = client.post(f"/api/style-experiment-runs/{batch_id}/continue",
                                json={"id": continued_id}, headers=ORIGIN).json()
        assert (continued["kind"], continued["total"], continued["name"]) == (
            "rerun", "3", "fix（续）")
        # The owner deletes one source group before the server reaches it.
        assert client.delete(f"/api/generations/{sources[1]['id']}",
                             headers=ORIGIN).status_code in (200, 204)
        calls = len(provider.calls)
        app.state.experiments.start()
        done = wait(client, f"/api/style-experiment-runs/{continued_id}",
                    lambda body: body["status"] == "completed")
        assert (done["succeeded_count"], done["failed_count"]) == ("2", "1")
        assert done["error_code"] in (None, "rerun_source_missing")
        assert len(provider.calls) == calls + 2
        assert run_state(client, batch_id)["status"] == "stopped"

        with sqlite3.connect(database.path) as connection:
            inflight = connection.execute(
                "SELECT COUNT(*) FROM style_experiment_inflight").fetchone()[0]
        assert inflight == 0
