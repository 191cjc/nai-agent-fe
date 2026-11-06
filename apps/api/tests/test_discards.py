"""Per-image discard marks for dataset review; disposable SQLite and fakes only."""

import sqlite3
import time

from fastapi.testclient import TestClient
from test_character_runs import ReferenceProvider, database, owner, png  # noqa: F401
from test_generations import INPUT, login

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import ResultCache
from novelai_api.security import SESSION_COOKIE

ORIGIN = {"Origin": "https://testserver"}


def finished_job(client: TestClient, samples=3) -> str:
    job_id = client.post(
        "/api/generations", json={**INPUT, "sample_count": samples}, headers=ORIGIN,
    ).json()["id"]
    deadline = time.monotonic() + 3
    while client.get(f"/api/generations/{job_id}").json()["status"] != "succeeded":
        assert time.monotonic() < deadline
        time.sleep(0.01)
    return job_id


def test_discard_restore_isolation_validation_and_cascade(database: Database) -> None:  # noqa: F811
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=ReferenceProvider(), result_cache=ResultCache(),
    )
    with TestClient(app, base_url="https://testserver") as client:
        _token, _alice, alice_session = login(client, database, "alice")
        job_id = finished_job(client)
        url = f"/api/generations/{job_id}/images/1/discard"
        assert client.put(url).status_code == 403  # Origin required
        assert client.put(url, headers=ORIGIN).status_code == 204
        assert client.put(url, headers=ORIGIN).status_code == 204  # idempotent
        assert client.put(f"/api/generations/{job_id}/images/2/discard",
                          headers=ORIGIN).status_code == 204
        view = client.get(f"/api/generations/{job_id}").json()
        assert view["discarded_images"] == [1, 2] and len(view["image_urls"]) == 3
        assert client.delete(url, headers=ORIGIN).status_code == 204
        assert client.delete(url, headers=ORIGIN).status_code == 204
        assert client.get(f"/api/generations/{job_id}").json()["discarded_images"] == [2]
        for bad in (3, 8, -1):
            assert client.put(f"/api/generations/{job_id}/images/{bad}/discard",
                              headers=ORIGIN).status_code in (404, 422)
        assert client.put("/api/generations/missing/images/0/discard",
                          headers=ORIGIN).status_code == 404

        login(client, database, "bob")
        assert client.put(url, headers=ORIGIN).status_code == 404
        assert client.get(f"/api/generations/{job_id}").status_code == 404

        client.cookies.clear()
        client.cookies.set(SESSION_COOKIE, alice_session)
        assert client.delete(f"/api/generations/{job_id}", headers=ORIGIN).status_code == 204
    with sqlite3.connect(database.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM discarded_images").fetchone()[0] == 0


def test_experiment_pages_carry_marks_and_failed_jobs_cannot_be_marked(
    database: Database,  # noqa: F811
) -> None:
    from test_dataset_runs import dataset

    provider = ReferenceProvider()
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=provider, result_cache=ResultCache(),
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        run = client.post("/api/dataset-runs", json=dataset().model_dump(mode="json"),
                          headers=ORIGIN).json()
        deadline = time.monotonic() + 3
        while client.get(f"/api/style-experiment-runs/{run['id']}").json()["status"] != (
            "completed"
        ):
            assert time.monotonic() < deadline
            time.sleep(0.01)
        page = client.get(f"/api/style-experiments/{run['id']}", params={"limit": 10}).json()
        second = page["items"][1]["id"]
        assert client.put(f"/api/generations/{second}/images/0/discard",
                          headers=ORIGIN).status_code == 204
        page = client.get(f"/api/style-experiments/{run['id']}", params={"limit": 10}).json()
        assert [item["discarded_images"] for item in page["items"]] == [[], [0], []]

        provider_failure = client.post(
            "/api/generations", json={**INPUT, "sample_count": 1, "positive_prompt": "x"},
            headers=ORIGIN,
        ).json()["id"]
        with sqlite3.connect(database.path) as connection:
            connection.execute(
                "UPDATE generation_jobs SET status = 'failed', image_count = 0 WHERE id = ?",
                (provider_failure,),
            )
        deadline = time.monotonic() + 3
        while client.get(f"/api/generations/{provider_failure}").json()["status"] != "failed":
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert client.put(f"/api/generations/{provider_failure}/images/0/discard",
                          headers=ORIGIN).status_code == 404


def test_migration_to_schema7_preserves_rows(tmp_path) -> None:
    upgraded = Database(tmp_path / "upgrade.sqlite3")
    upgraded.migrate()
    user = owner(upgraded)
    with upgraded.connect(write=True) as connection:
        connection.execute("DROP TABLE style_experiment_inflight")
        connection.execute("ALTER TABLE style_experiment_runs DROP COLUMN parallelism")
        connection.execute("DROP TABLE experiment_names")
        connection.execute("DROP INDEX style_experiment_active_queue")
        connection.execute("ALTER TABLE style_experiment_runs DROP COLUMN lane")
        connection.execute(
            "CREATE UNIQUE INDEX style_experiment_one_active_owner ON "
            "style_experiment_runs(user_id) WHERE status IN ('running', 'stopping')",
        )
        connection.execute("DROP TABLE caption_overrides")
        connection.execute("DROP TABLE discarded_images")
        connection.execute("PRAGMA user_version = 6")
        connection.execute(
            "INSERT INTO generation_jobs (id, user_id, positive_prompt, negative_prompt, "
            "settings_json, effective_seed, status, created_at, updated_at) "
            "VALUES ('j', ?, 'p', '', '{}', 1, 'failed', 1, 1)", (user,),
        )
    upgraded.migrate()
    with sqlite3.connect(upgraded.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 12
        assert connection.execute("SELECT COUNT(*) FROM generation_jobs").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM discarded_images").fetchone()[0] == 0
    assert upgraded.check_ready()


def test_manual_only_history_skips_experiment_and_dataset_groups(
    database: Database,  # noqa: F811
) -> None:
    from test_dataset_runs import dataset

    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=ReferenceProvider(), result_cache=ResultCache(),
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        manual = finished_job(client, samples=1)
        run = client.post("/api/dataset-runs", json=dataset().model_dump(mode="json"),
                          headers=ORIGIN).json()
        deadline = time.monotonic() + 3
        while client.get(f"/api/style-experiment-runs/{run['id']}").json()["status"] != (
            "completed"
        ):
            assert time.monotonic() < deadline
            time.sleep(0.01)
        everything = client.get("/api/generations", params={"limit": 10}).json()["items"]
        # Same-second timestamps make the relative order of manual/run rows unstable.
        assert len(everything) == 4
        assert sum(1 for item in everything if item["parameters"].get("experiment")) == 3
        latest_manual = client.get(
            "/api/generations", params={"limit": 1, "manual_only": "true"},
        ).json()
        assert [item["id"] for item in latest_manual["items"]] == [manual]
        assert latest_manual["next_offset"] is None


def test_experiment_cover_is_first_succeeded_undiscarded_group(
    database: Database,  # noqa: F811
) -> None:
    from test_dataset_runs import dataset

    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=ReferenceProvider(), result_cache=ResultCache(),
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        run = client.post("/api/dataset-runs", json=dataset().model_dump(mode="json"),
                          headers=ORIGIN).json()
        deadline = time.monotonic() + 3
        while client.get(f"/api/style-experiment-runs/{run['id']}").json()["status"] != (
            "completed"
        ):
            assert time.monotonic() < deadline
            time.sleep(0.01)
        items = client.get(f"/api/style-experiments/{run['id']}", params={"limit": 10}).json()
        first, second, third = (item["id"] for item in items["items"])

        def cover() -> str | None:
            listed = client.get("/api/style-experiments", params={"limit": 10}).json()
            detail = client.get(f"/api/style-experiments/{run['id']}", params={"limit": 1}).json()
            assert listed["items"][0]["cover_job_id"] == detail["summary"]["cover_job_id"]
            return detail["summary"]["cover_job_id"]

        assert cover() == first
        with sqlite3.connect(database.path) as connection:
            connection.execute(
                "UPDATE generation_jobs SET status = 'failed', image_count = 0 WHERE id = ?",
                (first,),
            )
        assert cover() == second
        url = f"/api/generations/{second}/images/0/discard"
        assert client.put(url, headers=ORIGIN).status_code == 204
        assert cover() == third
        assert client.delete(url, headers=ORIGIN).status_code == 204
        assert cover() == second
        with sqlite3.connect(database.path) as connection:
            connection.execute("UPDATE generation_jobs SET status = 'failed', image_count = 0")
        assert cover() is None
