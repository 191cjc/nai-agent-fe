"""Deleting a whole saved experiment / training set; fakes only, no paid calls."""

import time
from uuid import uuid4

from fastapi.testclient import TestClient
from test_character_runs import ReferenceProvider
from test_dataset_runs import dataset
from test_discards import finished_job
from test_generations import ORIGIN, login
from test_style_runs import database  # noqa: F401

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.image_results import DiskResultStore
from novelai_api.security import SESSION_COOKIE


def counts(db: Database, run_id: str) -> tuple[int, int, int, int]:
    with db.connect() as connection:
        def one(sql: str, *args) -> int:
            return connection.execute(sql, args).fetchone()[0]

        return (
            one("SELECT COUNT(*) FROM generation_jobs WHERE json_extract(settings_json, "
                "'$.experiment.id') = ?", run_id),
            one("SELECT COUNT(*) FROM style_experiment_runs WHERE id = ?", run_id),
            one("SELECT COUNT(*) FROM experiment_names WHERE run_id = ?", run_id),
            one("SELECT COUNT(*) FROM discarded_images"),
        )


def wait_run(client: TestClient, run_id: str) -> None:
    deadline = time.monotonic() + 3
    while client.get(f"/api/style-experiment-runs/{run_id}").json()["status"] != "completed":
        assert time.monotonic() < deadline
        time.sleep(0.01)


def test_delete_training_set_removes_rows_files_and_keeps_other_history(
    database: Database,  # noqa: F811
) -> None:
    images = database.path.parent / "generation-images"
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=ReferenceProvider(), result_cache=DiskResultStore(images),
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        _token, _alice, alice_session = login(client, database, "alice")
        manual = finished_job(client, samples=1)
        payload = {**dataset().model_dump(mode="json"), "name": "要删的"}
        run_id = client.post("/api/dataset-runs", json=payload, headers=ORIGIN).json()["id"]
        wait_run(client, run_id)
        groups = client.get(f"/api/style-experiments/{run_id}", params={"limit": 10}).json()
        job_ids = [item["id"] for item in groups["items"]]
        first_image = groups["items"][0]["image_urls"][0]
        assert client.put(f"/api/generations/{job_ids[0]}/images/0/discard",
                          headers=ORIGIN).status_code == 204
        assert client.put(f"/api/generations/{manual}/images/0/discard",
                          headers=ORIGIN).status_code == 204
        assert all((images / job_id).exists() for job_id in job_ids)
        assert counts(database, run_id) == (3, 1, 1, 2)

        url = f"/api/style-experiments/{run_id}"
        assert client.delete(url).status_code == 403
        login(client, database, "bob")
        assert client.delete(url, headers=ORIGIN).status_code == 404
        client.cookies.set(SESSION_COOKIE, alice_session)
        deleted = client.delete(url, headers=ORIGIN)
        assert deleted.status_code == 200
        assert deleted.json() == {"deleted_groups": 3, "deleted_images": 6}
        # Only the manual record's discard mark survives.
        assert counts(database, run_id) == (0, 0, 0, 1)
        assert not any((images / job_id).exists() for job_id in job_ids)
        assert client.get(first_image).status_code == 404
        assert client.get(url).status_code == 404
        assert run_id not in [item["id"] for item in
                              client.get("/api/style-experiments").json()["items"]]
        assert client.get(f"/api/generations/{manual}").json()["status"] == "succeeded"
        assert client.delete(url, headers=ORIGIN).status_code == 404
        assert client.delete(f"/api/style-experiments/{uuid4()}",
                             headers=ORIGIN).status_code == 404


def test_active_runs_and_running_groups_refuse_deletion(database: Database) -> None:  # noqa: F811
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=ReferenceProvider(), result_cache=DiskResultStore(
            database.path.parent / "generation-images",
        ),
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        _token, alice, _session = login(client, database, "alice")
        run_id = client.post("/api/dataset-runs", json=dataset().model_dump(mode="json"),
                             headers=ORIGIN).json()["id"]
        wait_run(client, run_id)
        store = app.state.experiments.store
        with database.connect(write=True) as connection:
            connection.execute(
                "UPDATE style_experiment_runs SET status = 'running' WHERE id = ?", (run_id,),
            )
        refused = client.delete(f"/api/style-experiments/{run_id}", headers=ORIGIN)
        assert refused.status_code == 409 and refused.json()["code"] == "experiment_run_active"
        with database.connect(write=True) as connection:
            connection.execute(
                "UPDATE style_experiment_runs SET status = 'completed' WHERE id = ?", (run_id,),
            )
            connection.execute(
                "UPDATE generation_jobs SET status = 'running' WHERE rowid = ("
                "SELECT rowid FROM generation_jobs WHERE json_extract(settings_json, "
                "'$.experiment.id') = ? LIMIT 1)", (run_id,),
            )
        refused = client.delete(f"/api/style-experiments/{run_id}", headers=ORIGIN)
        assert refused.status_code == 409 and refused.json()["code"] == "job_active"
        assert counts(database, run_id)[:2] == (3, 1)
        assert store.get(alice, run_id) is not None
