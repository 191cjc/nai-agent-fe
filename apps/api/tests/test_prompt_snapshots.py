"""Prompt libraries use private SQLite, owner isolation and fake HTTP sessions."""

import json
import os
import sqlite3
from importlib.resources import files
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from test_generations import INPUT, ORIGIN, login
from test_style_runs import request as run_request

from novelai_api.app import create_app
from novelai_api.auth import create_token, current_user, issue_session
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import GenerationRequest, JobStore
from novelai_api.prompt_snapshots import PromptSnapshotCreate, PromptSnapshotStore
from novelai_api.style_experiments import RunStore


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "private" / "snapshots.sqlite3")
    database.migrate()
    return database


def client_for(database):
    return TestClient(
        create_app(Settings(database.path, "https://testserver"), database),
        base_url="https://testserver",
    )


def snapshot(*, id=None, name="My snapshot", text=" garden "):
    return {
        "id": str(id or uuid4()),
        "name": name,
        "entries": [
            {"scope": "shared", "section": "scene", "text": text},
            {
                "scope": "character",
                "character_index": 5,
                "section": "upper_clothing",
                "text": " blue shirt, blue shirt ",
            },
        ],
    }


def test_crud_idempotency_exact_text_conflicts_and_provider_job_seed_independence(
    database,
    monkeypatch,
):
    app = create_app(Settings(database.path, "https://testserver"), database)
    monkeypatch.setattr(
        app.state.generations,
        "submit",
        Mock(side_effect=AssertionError("Snapshots cannot submit generation work")),
    )
    with TestClient(app, base_url="https://testserver") as client:
        _, user, _ = login(client, database, "alice")
        for target in (
            "novelai_api.generations.secrets.randbelow",
            "novelai_api.style_experiments.secrets.randbelow",
        ):
            monkeypatch.setattr(target, Mock(side_effect=AssertionError("No snapshot seed")))
        payload = snapshot()
        response = client.post("/api/prompt-snapshots", json=payload, headers=ORIGIN)
        assert response.status_code == 201
        created = response.json()
        assert created == {**payload, "created_at": created["created_at"]}
        assert isinstance(created["created_at"], int)
        assert response.headers["Cache-Control"] == "no-store"
        repeated = client.post("/api/prompt-snapshots", json=payload, headers=ORIGIN)
        assert repeated.status_code == 201 and repeated.json() == created
        for change in (
            {"name": "Changed"},
            {"entries": list(reversed(payload["entries"]))},
            {"entries": [{"scope": "shared", "section": "scene", "text": "garden"}]},
        ):
            conflict = client.post(
                "/api/prompt-snapshots", json={**payload, **change}, headers=ORIGIN
            )
            assert conflict.status_code == 409
            assert conflict.json() == {
                "code": "prompt_snapshot_conflict",
                "message": "Prompt snapshot already exists or changed",
                "retryable": False,
            }
            assert conflict.headers["Cache-Control"] == "no-store"
        detail = client.get(f"/api/prompt-snapshots/{payload['id']}")
        assert detail.status_code == 200 and detail.json() == created
        assert detail.headers["Cache-Control"] == "no-store"
        assert client.get("/api/prompt-snapshots").json() == {
            "items": [
                {
                    "id": payload["id"],
                    "name": payload["name"],
                    "created_at": created["created_at"],
                    "entry_count": 2,
                }
            ],
            "next_offset": None,
        }
        with database.connect() as connection:
            for table in ("generation_jobs", "style_experiment_runs"):
                assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        persisted = PromptSnapshotStore(Database(database.path)).get(user, payload["id"])
        assert persisted.model_dump(mode="json") == created
        backup = database.path.parent / "snapshot-backup.sqlite3"
        database.backup(backup)
        assert (
            PromptSnapshotStore(Database(backup)).get(user, payload["id"]).model_dump(mode="json")
            == created
        )
        deleted = client.delete(f"/api/prompt-snapshots/{payload['id']}", headers=ORIGIN)
        assert deleted.status_code == 204 and deleted.content == b""
        assert deleted.headers["Cache-Control"] == "no-store"
        assert client.get(f"/api/prompt-snapshots/{payload['id']}").status_code == 404
        assert (
            client.delete(f"/api/prompt-snapshots/{payload['id']}", headers=ORIGIN).status_code
            == 404
        )
        assert client.get("/api/prompt-snapshots").json() == {"items": [], "next_offset": None}


def test_owner_scoped_same_uuid_does_not_expose_or_conflict_with_foreign_library(database):
    payload = snapshot()
    with client_for(database) as client:
        login(client, database, "alice")
        alice = client.post("/api/prompt-snapshots", json=payload, headers=ORIGIN).json()
        login(client, database, "bob")
        assert client.get("/api/prompt-snapshots").json() == {"items": [], "next_offset": None}
        for response in (
            client.get(f"/api/prompt-snapshots/{payload['id']}"),
            client.delete(f"/api/prompt-snapshots/{payload['id']}", headers=ORIGIN),
        ):
            assert response.status_code == 404
            assert response.json()["message"] == "Prompt snapshot not found"
            assert response.headers["Cache-Control"] == "no-store"
        bob = client.post(
            "/api/prompt-snapshots",
            json={**payload, "name": "Bob's own name"},
            headers=ORIGIN,
        )
        assert bob.status_code == 201
        assert bob.json()["id"] == alice["id"]
        assert client.get("/api/prompt-snapshots").json()["items"][0]["name"] == "Bob's own name"
        assert (
            client.delete(f"/api/prompt-snapshots/{payload['id']}", headers=ORIGIN).status_code
            == 204
        )
        with database.connect() as connection:
            assert (
                connection.execute("SELECT name FROM prompt_snapshots").fetchone()[0]
                == alice["name"]
            )


def test_auth_origin_no_store_and_invalid_paths(database):
    payload = snapshot()
    path = f"/api/prompt-snapshots/{payload['id']}"
    with client_for(database) as client:
        for response in (
            client.get("/api/prompt-snapshots"),
            client.get(path),
            client.post("/api/prompt-snapshots", json=payload, headers=ORIGIN),
            client.delete(path, headers=ORIGIN),
        ):
            assert response.status_code == 401
            assert response.headers["Cache-Control"] == "no-store"
        login(client, database, "alice")
        for headers in ({}, {"Origin": "https://foreign.example"}, {"Origin": "null"}):
            for response in (
                client.post("/api/prompt-snapshots", json=payload, headers=headers),
                client.delete(path, headers=headers),
            ):
                assert response.status_code == 403
                assert response.json()["code"] == "forbidden_origin"
                assert response.headers["Cache-Control"] == "no-store"
        for response in (
            client.get("/api/prompt-snapshots/not-a-uuid"),
            client.delete("/api/prompt-snapshots/not-a-uuid", headers=ORIGIN),
        ):
            assert response.status_code == 422
            assert response.headers["Cache-Control"] == "no-store"
        assert client.get("/api/prompt-snapshots").json()["items"] == []


def test_pagination_ties_descending_uuid_summaries_without_text_and_restart(database, monkeypatch):
    monkeypatch.setattr("novelai_api.prompt_snapshots.time.time", lambda: 1234567890)
    with client_for(database) as client:
        login(client, database, "alice")
        ids = [str(UUID(int=index)) for index in range(1, 24)]
        for snapshot_id in ids:
            response = client.post(
                "/api/prompt-snapshots",
                json=snapshot(id=snapshot_id),
                headers=ORIGIN,
            )
            assert response.status_code == 201
        first = client.get("/api/prompt-snapshots").json()
        assert len(first["items"]) == 20 and first["next_offset"] == 20
        second = client.get("/api/prompt-snapshots?offset=20").json()
        assert len(second["items"]) == 3 and second["next_offset"] is None
        ordered = first["items"] + second["items"]
        assert [item["id"] for item in ordered] == list(reversed(ids))
        assert all(set(item) == {"id", "name", "created_at", "entry_count"} for item in ordered)
        assert client.get("/api/prompt-snapshots?offset=9007199254740991").json() == {
            "items": [],
            "next_offset": None,
        }
        assert client.get("/api/prompt-snapshots?limit=1").json()["next_offset"] == 1
        assert len(client.get("/api/prompt-snapshots?limit=100").json()["items"]) == 23
    with client_for(Database(database.path)) as client:
        login(client, database, "restarter")
        # A new owner's library remains empty after application restart.
        assert client.get("/api/prompt-snapshots").json()["items"] == []
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM prompt_snapshots").fetchone()[0] == 23


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "limit=1.5",
        "limit=bad",
        "offset=-1",
        "offset=1.5",
        "offset=9007199254740992",
        "offset=bad",
    ],
)
def test_invalid_pagination_is_safe_validation_error(database, query):
    with client_for(database) as client:
        login(client, database, "alice")
        response = client.get(f"/api/prompt-snapshots?{query}")
        assert response.status_code == 422
        assert response.json() == {
            "code": "validation_error",
            "message": "Invalid request",
            "retryable": False,
        }


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(id="bad"),
        lambda p: p.update(name=""),
        lambda p: p.update(name=" \n "),
        lambda p: p.update(name="x" * 101),
        lambda p: p.update(enabled=True),
        lambda p: p.update(entries=[]),
        lambda p: p.update(entries=p["entries"] * 23),
        lambda p: p.update(entries=[p["entries"][0], p["entries"][0]]),
        lambda p: p.update(entries=[p["entries"][1], p["entries"][1]]),
        lambda p: [entry.update(text=" \n ") for entry in p["entries"]],
        lambda p: p["entries"][0].update(text="x" * 3001),
        lambda p: p["entries"][0].update(character_index=0),
        lambda p: p["entries"][0].update(scope="other"),
        lambda p: p["entries"][0].update(section="character"),
        lambda p: p["entries"][0].update(enabled=False),
        lambda p: p["entries"][1].pop("character_index"),
        lambda p: p["entries"][1].update(character_index=True),
        lambda p: p["entries"][1].update(character_index="0"),
        lambda p: p["entries"][1].update(character_index=0.0),
        lambda p: p["entries"][1].update(character_index=-1),
        lambda p: p["entries"][1].update(character_index=6),
        lambda p: p["entries"][1].update(section="scene"),
        lambda p: p["entries"][1].update(id="draft-id"),
        lambda p: p["entries"][1].update(x=0.5),
        lambda p: p["entries"][1].update(text=None),
    ],
)
def test_snapshot_invalid_shapes_never_create_rows_or_expose_validation_contents(database, change):
    payload = snapshot()
    change(payload)
    with client_for(database) as client:
        login(client, database, "alice")
        response = client.post("/api/prompt-snapshots", json=payload, headers=ORIGIN)
        assert response.status_code == 422
        assert response.json() == {
            "code": "validation_error",
            "message": "Invalid request",
            "retryable": False,
        }
        assert response.headers["Cache-Control"] == "no-store"
        assert client.get("/api/prompt-snapshots").json()["items"] == []


def test_full44_entry_budget_boundary_preserves_empty_sections_and_exact_order(database):
    entries = [
        {"scope": "shared", "section": key, "text": "x" * 3000} for key in ("scene", "other")
    ]
    for index in range(6):
        for key in (
            "character",
            "upper_clothing",
            "lower_clothing",
            "action",
            "tags",
            "special",
            "other",
        ):
            entries.append(
                {"scope": "character", "character_index": index, "section": key, "text": ""}
            )
    payload = {"id": str(uuid4()), "name": "n" * 100, "entries": entries}
    with client_for(database) as client:
        login(client, database, "alice")
        response = client.post("/api/prompt-snapshots", json=payload, headers=ORIGIN)
        assert response.status_code == 201
        assert response.json()["entries"] == entries
        assert client.get("/api/prompt-snapshots").json()["items"][0]["entry_count"] == 44


def test_schema3_upgrade_preserves_all_rows_raw_definitions_auth_and_private_backup(tmp_path):
    path = tmp_path / "schema3.sqlite3"
    with sqlite3.connect(path) as connection:
        for filename in ("0001_auth.sql", "0002_generations.sql", "0003_style_experiments.sql"):
            connection.executescript(
                files("novelai_api").joinpath("migrations", filename).read_text()
            )
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
    database = Database(path)
    _, token = create_token(database, "alice")
    session, user = issue_session(database, token)
    job_id = JobStore(database).create(user["id"], GenerationRequest(**INPUT, seed=77))
    run_id = legacy_run(database, user["id"], run_request(seed=77))
    with database.connect(write=True) as connection:
        # Simulate a frozen legacy definition before optional placement metadata.
        definition = json.loads(
            connection.execute(
                "SELECT definition_json FROM style_experiment_runs",
            ).fetchone()[0]
        )
        definition["parameters"].pop("auto_character_position")
        connection.execute(
            "UPDATE style_experiment_runs SET definition_json = ?",
            (json.dumps(definition, indent=3),),
        )
    tables = (
        "users",
        "access_tokens",
        "browser_sessions",
        "generation_jobs",
        "style_experiment_runs",
    )
    with database.connect() as connection:
        before = {
            table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table}")]
            for table in tables
        }
    assert not database.check_ready()
    path.chmod(0o666)
    database.migrate()
    database.migrate()
    assert database.check_ready()
    assert current_user(database, session) == user
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 9
        for table in tables:
            assert [
                # Later schemas only append columns to the preserved rows.
                tuple(value for key, value in dict(row).items()
                      if key not in ("provider_request_json", "lane"))
                for row in connection.execute(f"SELECT * FROM {table}")
            ] == before[table]
        assert connection.execute("SELECT COUNT(*) FROM prompt_snapshots").fetchone()[0] == 0
    assert JobStore(database).get(user["id"], job_id).parameters.prompt_sections is None
    assert RunStore(database).get(user["id"], run_id).parameters.prompt_sections is None
    saved = PromptSnapshotStore(database).create(user["id"], PromptSnapshotCreate(**snapshot()))
    backup = tmp_path / "schema4-backup.sqlite3"
    database.backup(backup)
    restored = Database(backup)
    assert restored.check_ready()
    assert current_user(restored, session) == user
    assert PromptSnapshotStore(restored).get(user["id"], str(saved.id)) == saved
    with restored.connect() as connection:
        for table in tables:
            assert [
                # Later schemas only append columns to the preserved rows.
                tuple(value for key, value in dict(row).items()
                      if key not in ("provider_request_json", "lane"))
                for row in connection.execute(f"SELECT * FROM {table}")
            ] == before[table]
    if os.name == "posix":
        assert path.stat().st_mode & 0o777 == 0o600
        assert backup.stat().st_mode & 0o777 == 0o600
    # Exact current-version readiness must also probe the new table.
    with restored.connect(write=True) as connection:
        connection.execute("DROP TABLE prompt_snapshots")
    assert not restored.check_ready()


def legacy_run(database: Database, user_id: str, definition) -> str:
    """Insert a run row the way schemas 3-8 stored it (no lane column yet)."""
    definition_json, total = definition.definition()
    with database.connect(write=True) as connection:
        connection.execute(
            "INSERT INTO style_experiment_runs (user_id, id, definition_json, total, seed, "
            "status, created_at, updated_at) VALUES (?, ?, ?, ?, 77, 'running', 1, 1)",
            (user_id, str(definition.id), definition_json, total),
        )
    return str(definition.id)
