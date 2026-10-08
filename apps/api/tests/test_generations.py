"""In-process fake provider exercises generation without paid service calls."""

import base64
import sqlite3
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from novelai_api.app import create_app
from novelai_api.auth import create_token, revoke_token
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import (
    GeneratedImage,
    GenerationRequest,
    JobStore,
    ResultCache,
)
from novelai_api.security import SESSION_COOKIE


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j"
    "RZkAAAAASUVORK5CYII="
)
ORIGIN = {"Origin": "https://testserver"}
INPUT = {
    "positive_prompt": "blue hair",
    "negative_prompt": "blurry",
    "model": "fixture-model",
    "width": 512,
    "height": 512,
    "steps": 28,
    "cfg_scale": 5.0,
    "sampler": "fixture-sampler",
    "sample_count": 2,
    "quality": True,
}


class FakeProvider:
    def __init__(self, images=None, *, failure: str | None = None, gate=None):
        self.images = images if images is not None else [
            GeneratedImage(PNG, "image/png"), GeneratedImage(PNG, "image/png")
        ]
        self.failure = failure
        self.gate = gate
        self.started = threading.Event()
        self.calls: list[GenerationRequest] = []

    def generate(self, parameters: GenerationRequest):
        self.calls.append(parameters)
        self.started.set()
        if self.gate is not None:
            assert self.gate.wait(timeout=3)
        if self.failure:
            raise RuntimeError(self.failure)
        return self.images


@pytest.fixture
def database(tmp_path: Path) -> Database:
    instance = Database(tmp_path / "data" / "test.sqlite3")
    instance.migrate()
    return instance


def client_for(database: Database, provider=None, cache=None):
    return TestClient(
        create_app(
            Settings(database.path, "https://testserver"),
            database,
            image_provider=provider,
            result_cache=cache,
        ),
        base_url="https://testserver",
    )


def login(client: TestClient, database: Database, label: str):
    token_id, token = create_token(database, label)
    response = client.post("/api/auth/session", json={"token": token}, headers=ORIGIN)
    assert response.status_code == 200
    return token_id, response.json()["id"], client.cookies.get(SESSION_COOKIE)


def wait_finished(client: TestClient, job_id: str) -> dict:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/api/generations/{job_id}")
        if response.json()["status"] in ("succeeded", "failed"):
            return response.json()
        time.sleep(0.01)
    pytest.fail("Fake generation did not complete")


def test_images_temporary_history_and_download(database: Database) -> None:
    provider = FakeProvider()
    with client_for(database, provider) as client:
        _token_id, user_id, _session = login(client, database, "alice")
        result = client.post("/api/generations", json=INPUT, headers=ORIGIN)
        assert result.status_code == 202
        job_id = result.json()["id"]
        job = wait_finished(client, job_id)
        assert job["status"] == "succeeded"
        assert job["effective_seed"] >= 1
        assert job["parameters"]["seed"] == job["effective_seed"]
        assert provider.calls[0].seed == job["effective_seed"]
        assert len(job["image_urls"]) == 2
        assert job["result_expires_at"] is not None
        for url in job["image_urls"]:
            response = client.get(url)
            assert response.status_code == 200
            assert response.content == PNG
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["content-disposition"].startswith("inline;")
        history = client.get("/api/generations").json()
        assert history["next_offset"] is None
        assert len(history["items"]) == 1
        assert history["items"][0]["parameters"]["positive_prompt"] == "blue hair"
        assert "image_urls" not in history["items"][0]
        with database.connect() as connection:
            stored_user = connection.execute("SELECT user_id FROM generation_jobs").fetchone()[0]
            assert stored_user == user_id
        for path in database.path.parent.iterdir():
            if path.is_file():
                assert PNG not in path.read_bytes()

    with client_for(database) as restarted:
        restarted.cookies.set(SESSION_COOKIE, _session)
        job = restarted.get(f"/api/generations/{job_id}").json()
        assert job["status"] == "succeeded"
        assert job["image_urls"] == []
        assert job["image_count"] == 2
        assert restarted.get(f"/api/generation-results/{job_id}/images/0").status_code == 404


def test_history_is_owner_scoped_and_delete_is_individual(database: Database) -> None:
    with client_for(database, FakeProvider()) as client:
        alice_token, _alice_id, alice_session = login(client, database, "alice")
        first = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        wait_finished(client, first)
        second = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        wait_finished(client, second)
        _bob_token, _bob_id, _bob_session = login(client, database, "bob")
        assert client.get("/api/generations").json()["items"] == []
        assert client.get(f"/api/generations/{first}").status_code == 404
        assert client.get(f"/api/generation-results/{first}/images/0").status_code == 404
        assert client.delete(f"/api/generations/{first}", headers=ORIGIN).status_code == 404
        client.cookies.set(SESSION_COOKIE, alice_session)
        page = client.get("/api/generations?limit=1").json()
        assert len(page["items"]) == 1
        assert page["next_offset"] == 1
        assert client.get("/api/generations?limit=1&offset=1").json()["items"]
        with database.connect(write=True) as connection:
            connection.execute("UPDATE generation_jobs SET created_at = 1 WHERE id = ?", (first,))
        assert len(client.get("/api/generations").json()["items"]) == 2
        assert client.delete(f"/api/generations/{first}", headers=ORIGIN).status_code == 204
        assert client.get(f"/api/generations/{first}").status_code == 404
        assert client.get(f"/api/generation-results/{first}/images/0").status_code == 404
        assert client.get(f"/api/generations/{second}").status_code == 200
        revoke_token(database, alice_token)
        assert client.get(f"/api/generations/{second}").status_code == 401
        assert client.get(f"/api/generation-results/{second}/images/0").status_code == 401


def test_result_ttl_removes_links_but_not_history(database: Database) -> None:
    now = [100.0]
    cache = ResultCache(clock=lambda: now[0])
    with client_for(database, FakeProvider(), cache) as client:
        login(client, database, "alice")
        job_id = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        assert len(wait_finished(client, job_id)["image_urls"]) == 2
        now[0] += 601
        response = client.get(f"/api/generations/{job_id}").json()
        assert response["status"] == "succeeded"
        assert response["image_urls"] == []
        assert client.get(f"/api/generation-results/{job_id}/images/0").status_code == 404
        assert client.get("/api/generations").json()["items"][0]["status"] == "succeeded"


@pytest.mark.parametrize(
    ("images", "failure"),
    [
        ([GeneratedImage(PNG, "image/png")], None),
        ([GeneratedImage(b"invalid", "image/png")] * 2, None),
        ([GeneratedImage(PNG, "text/html")] * 2, None),
        (None, "secret upstream traceback"),
    ],
)
def test_bad_results_and_upstream_errors_fail_closed(database: Database, images, failure) -> None:
    provider = FakeProvider(images, failure=failure)
    with client_for(database, provider) as client:
        login(client, database, "alice")
        job_id = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        job = wait_finished(client, job_id)
        assert job["status"] == "failed"
        assert job["image_count"] == 0
        assert job["image_urls"] == []
        if failure is not None:
            assert failure not in str(job)
        assert len(provider.calls) == 1


def test_bounded_queue_and_active_job_cannot_be_deleted(database: Database) -> None:
    gate = threading.Event()
    provider = FakeProvider(gate=gate)
    with client_for(database, provider) as client:
        login(client, database, "alice")
        try:
            first = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
            assert provider.started.wait(timeout=2)
            queued = [
                client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
                for _ in range(2)
            ]
            assert client.post("/api/generations", json=INPUT, headers=ORIGIN).status_code == 429
            assert client.delete(f"/api/generations/{first}", headers=ORIGIN).status_code == 409
            assert len(client.get("/api/generations").json()["items"]) == 3
        finally:
            gate.set()
        for job_id in [first, *queued]:
            assert wait_finished(client, job_id)["status"] == "succeeded"
        assert len(provider.calls) == 3


def test_disabled_provider_and_invalid_request_do_not_persist(database: Database) -> None:
    with client_for(database) as client:
        login(client, database, "alice")
        unavailable = client.post("/api/generations", json=INPUT, headers=ORIGIN)
        assert unavailable.status_code == 503
        assert unavailable.json()["code"] == "provider_unavailable"
        invalid = client.post(
            "/api/generations", json={**INPUT, "width": 513}, headers=ORIGIN
        )
        assert invalid.status_code == 422
        assert client.get("/api/generations").json()["items"] == []


def test_restart_marks_queued_job_unknown_without_retry(database: Database) -> None:
    token_id, token = create_token(database, "alice")
    with database.connect() as connection:
        user_id = connection.execute(
            "SELECT user_id FROM access_tokens WHERE id = ?", (token_id,)
        ).fetchone()[0]
    pending = JobStore(database).create(user_id, GenerationRequest(**INPUT, seed=77))
    provider = FakeProvider()
    with client_for(database, provider) as client:
        response = client.post("/api/auth/session", json={"token": token}, headers=ORIGIN)
        assert response.status_code == 200
        job = client.get(f"/api/generations/{pending}").json()
        assert job["status"] == "failed"
        assert job["error_code"] == "outcome_unknown"
        assert provider.calls == []


def test_v1_to_v2_migration_keeps_existing_auth(tmp_path: Path) -> None:
    from importlib.resources import files

    path = tmp_path / "previous.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            files("novelai_api").joinpath("migrations", "0001_auth.sql").read_text()
        )
    database = Database(path)
    _token_id, token = create_token(database, "alice")
    database.migrate()
    database.migrate()
    with client_for(database) as client:
        response = client.post("/api/auth/session", json={"token": token}, headers=ORIGIN)
        assert response.status_code == 200
        assert client.get("/api/generations").json()["items"] == []


def test_sqlite_online_backup_restores_history_without_images(database: Database) -> None:
    with client_for(database, FakeProvider()) as client:
        _token_id, _user_id, session = login(client, database, "alice")
        job_id = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        assert wait_finished(client, job_id)["status"] == "succeeded"
        target = database.path.parent / "snapshot.sqlite3"
        database.backup(target)
        assert target.stat().st_mode & 0o777 == 0o600
        with pytest.raises(FileExistsError):
            database.backup(target)
    snapshot = Database(target)
    with client_for(snapshot) as restored:
        restored.cookies.set(SESSION_COOKIE, session)
        history = restored.get("/api/generations").json()["items"]
        assert len(history) == 1
        assert history[0]["id"] == job_id
        assert restored.get(f"/api/generations/{job_id}").json()["image_urls"] == []
    assert PNG not in target.read_bytes()
