"""Captured provider arguments use disposable databases and offline MCP transports."""

import json
import sqlite3
from importlib.resources import files
from uuid import uuid4

import httpx
import pytest
from test_generations import INPUT, ORIGIN, FakeProvider, client_for, login, wait_finished
from test_mcp_images import CHARACTER_SCHEMA, POSITION_SCHEMA, SCHEMA, mock_mcp, provider_for
from test_prompt_comments import modern_sections
from test_prompt_snapshots import snapshot
from test_style_runs import pump
from test_style_runs import request as run_request

from novelai_api.auth import create_token, current_user, issue_session
from novelai_api.db import Database
from novelai_api.generations import GenerationRequest, JobStore
from novelai_api.prompt_snapshots import PromptSnapshotCreate, PromptSnapshotStore
from novelai_api.security import SESSION_COOKIE
from novelai_api.style_experiments import RunStore


@pytest.fixture
def database(tmp_path):
    instance = Database(tmp_path / "private" / "provider-requests.sqlite3")
    instance.migrate()
    return instance


def native_schema(*, position_mode=True):
    properties = {**SCHEMA["properties"], "character_prompts": CHARACTER_SCHEMA}
    if position_mode:
        properties["auto_character_position"] = POSITION_SCHEMA
    return {**SCHEMA, "properties": properties}


def private_parameters(*, automatic=False, all_hidden=False):
    payload = modern_sections()
    payload["auto_character_position"] = automatic
    first = payload["prompt_sections"]["characters"][0]
    first["enabled"] = False
    first["sections"]["character"]["text"] = "PRIVATE whole hidden person"
    if all_hidden:
        payload["prompt_sections"]["characters"][1]["enabled"] = False
        payload["character_prompts"] = []
    return payload


@pytest.mark.parametrize("mode", ["flat", "manual", "automatic", "all_hidden", "old_schema"])
def test_actual_arguments_are_committed_before_call_and_survive_history_backup_restart(
    database, mode,
):
    payload = (
        {**INPUT, "seed": None} if mode == "flat"
        else private_parameters(automatic=mode == "automatic", all_hidden=mode == "all_hidden")
    )
    schema = SCHEMA if mode == "flat" else native_schema(position_mode=mode != "old_schema")
    base, calls = mock_mcp(schema=schema)
    observed = []

    def handler(request):
        rpc = json.loads(request.content)
        if rpc["method"] == "tools/call":
            with database.connect() as connection:
                row = connection.execute(
                    "SELECT provider_request_json FROM generation_jobs WHERE status = 'running'",
                ).fetchone()
            recorded = json.loads(row["provider_request_json"])
            assert recorded == rpc["params"]["arguments"]
            observed.append(recorded)
        return base.handle_request(request)

    with client_for(database, provider_for(httpx.MockTransport(handler))) as client:
        _, user_id, session = login(client, database, "alice")
        accepted = client.post("/api/generations", json=payload, headers=ORIGIN)
        assert accepted.status_code == 202
        job_id = accepted.json()["id"]
        job = wait_finished(client, job_id)
        assert job["status"] == "succeeded"
        exact = calls[-1]["params"]["arguments"]
        assert observed == [exact]
        assert job["provider_request"] == exact
        assert exact["seed"] == job["effective_seed"]
        assert "PRIVATE" not in json.dumps(exact)
        assert "fake-mcp-token" not in json.dumps(job)
        assert "provider_request" not in client.get("/api/generations").json()["items"][0]
        if mode != "flat":
            assert job["parameters"]["prompt_sections"] == payload["prompt_sections"]
            assert "PRIVATE" in json.dumps(job["parameters"])
        if mode in ("flat", "all_hidden"):
            assert "character_prompts" not in exact
            assert "auto_character_position" not in exact
        else:
            child = exact["character_prompts"][0]
            assert child["prompt"] == "blue hair, standing"
            assert ("x" not in child) is (mode == "automatic")
            if mode != "automatic":
                assert (child["x"], child["y"]) == (0.7, 0.3)
            assert ("auto_character_position" not in exact) is (mode == "old_schema")
        store = JobStore(database)
        assert not store.record_provider_request(user_id, job_id, {"prompt": "later edit"})
        assert store.provider_request(user_id, job_id) == exact
        assert store.provider_request("another-owner", job_id) is None
        backup = database.path.parent / "backup.sqlite3"
        database.backup(backup)
        login(client, database, "bob")
        assert client.get(f"/api/generations/{job_id}").status_code == 404
    for source in (database.path, backup):
        with client_for(Database(source)) as restarted:
            restarted.cookies.set(SESSION_COOKIE, session)
            restored = restarted.get(f"/api/generations/{job_id}")
            assert restored.status_code == 200
            assert restored.headers["Cache-Control"] == "no-store"
            assert restored.json()["provider_request"] == exact
            assert restored.json()["parameters"] == job["parameters"]


@pytest.mark.parametrize("mode", ["flat", "manual", "automatic", "sections"])
def test_modern_submission_removes_physical_newlines_without_changing_raw_source(database, mode):
    style = "1.25::画风,\r\n柔光::\n// PRIVATE style"
    shared = "garden,\n\nforest\rsky\t https://example.test/a\\n,\r\n// PRIVATE scene\n\\// literal"
    character = "blue\r\neyes,\n// PRIVATE character\n1.10::smile,\rlook::"
    negative = "bad\r\n// PRIVATE negative\r\nworse,\rworst\n\nend\t\\n"
    payload = {
        **INPUT, "seed": 77, "prompt_comments": True, "model": "nai-diffusion-5-full",
        "style_prompt": style, "positive_prompt": shared, "negative_prompt": negative,
        "auto_character_position": mode == "automatic",
    }
    if mode in ("manual", "automatic"):
        payload["character_prompts"] = [
            {"prompt": "// PRIVATE hidden person", "x": 0.1, "y": 0.9},
            {"prompt": character, "x": 0.7, "y": 0.3},
        ]
    elif mode == "sections":
        payload = modern_sections()
        payload.update(style_prompt=style, negative_prompt=negative)
        payload["prompt_sections"]["shared"]["scene"]["text"] = shared
        payload["prompt_sections"]["characters"][1]["sections"]["character"]["text"] = (
            character
        )
        payload["positive_prompt"] = (
            "garden,\n\nforest\rsky\t https://example.test/a\\n,\r\n\\// literal, sky"
        )
        payload["character_prompts"] = [{
            "prompt": "blue\r\neyes,\n1.10::smile,\rlook::, standing", "x": 0.7, "y": 0.3,
        }]
    raw = GenerationRequest.model_validate(payload).model_dump(mode="json")
    transport, calls = mock_mcp(schema=native_schema())
    with client_for(database, provider_for(transport)) as client:
        login(client, database, "alice")
        accepted = client.post("/api/generations", json=payload, headers=ORIGIN)
        assert accepted.status_code == 202
        job = wait_finished(client, accepted.json()["id"])
        assert job["status"] == "succeeded"
        submitted = [call for call in calls if call["method"] == "tools/call"]
        assert len(submitted) == 1
        arguments = submitted[0]["params"]["arguments"]
        assert job["provider_request"] == arguments
        assert job["parameters"] == raw
        assert arguments["prompt"] == (
            "1.25::画风, 柔光::, garden, forest sky\t https://example.test/a\\n, \\// literal"
            + (", sky" if mode == "sections" else "")
        )
        assert arguments["negative_prompt"] == "bad worse, worst end\t\\n"
        if mode != "flat":
            assert arguments["character_prompts"] == [{
                "prompt": "blue eyes, 1.10::smile, look::"
                + (", standing" if mode == "sections" else ""),
                "negative_prompt": "", "enabled": True,
                **({} if mode == "automatic" else {"x": 0.7, "y": 0.3}),
            }]
        for fields in (arguments, *arguments.get("character_prompts", [])):
            for field in ("prompt", "negative_prompt"):
                assert "\r" not in fields[field] and "\n" not in fields[field]
                assert "PRIVATE" not in fields[field]


def test_uncertain_paid_timeout_retains_exact_attempt_once(database):
    base, _calls = mock_mcp()
    attempted = []

    def handler(request):
        rpc = json.loads(request.content)
        if rpc["method"] == "tools/call":
            attempted.append(rpc["params"]["arguments"])
            raise httpx.ReadTimeout("private upstream timeout", request=request)
        return base.handle_request(request)

    with client_for(database, provider_for(httpx.MockTransport(handler))) as client:
        login(client, database, "alice")
        response = client.post("/api/generations", json=INPUT, headers=ORIGIN)
        job = wait_finished(client, response.json()["id"])
        assert job["status"] == "failed"
        assert job["error_code"] == "outcome_unknown"
        assert attempted == [job["provider_request"]]
        assert "private upstream timeout" not in json.dumps(job)


@pytest.mark.parametrize("record_failure", ["refused", "database_error", "discovery"])
def test_pre_call_failure_never_sends_paid_request_or_invents_snapshot(
    database, monkeypatch, record_failure,
):
    transport, calls = mock_mcp()
    with client_for(database, provider_for(transport)) as client:
        login(client, database, "alice")
        if record_failure != "discovery":
            def reject_record(*_args):
                if record_failure == "database_error":
                    raise sqlite3.OperationalError("private recording failure")
                return False

            monkeypatch.setattr(
                client.app.state.generations.store, "record_provider_request", reject_record,
            )
        payload = private_parameters() if record_failure == "discovery" else INPUT
        response = client.post("/api/generations", json=payload, headers=ORIGIN)
        job = wait_finished(client, response.json()["id"])
        assert job["status"] == "failed"
        assert job["provider_request"] is None
        assert not any(call["method"] == "tools/call" for call in calls)
        assert "private recording failure" not in json.dumps(job)


def test_experiment_details_keep_each_groups_actual_arguments(database, monkeypatch):
    transport, calls = mock_mcp(schema=native_schema())
    with client_for(database, provider_for(transport)) as client:
        _, user_id, _session = login(client, database, "alice")
        run_id = str(uuid4())
        response = client.post("/api/style-experiment-runs", json={
            "id": run_id, "parameters": private_parameters(),
            "ranges": [{"tag_index": 0, "min": "0.8", "max": "1", "step": "0.1"}],
        }, headers=ORIGIN)
        assert response.status_code == 202
        completed = pump(client.app.state.experiments, user_id, run_id)
        assert completed.succeeded_count == "3"
        # Detail items reuse the row they were read from; no per-item snapshot query.
        monkeypatch.setattr(
            JobStore, "provider_request", lambda *_args: pytest.fail("per-item snapshot query"),
        )
        detail = client.get(f"/api/style-experiments/{run_id}?limit=100").json()
        submitted = [
            call["params"]["arguments"] for call in calls if call["method"] == "tools/call"
        ]
        assert len(detail["items"]) == len(submitted) == 3
        assert [job["provider_request"] for job in detail["items"]] == submitted
        assert len({item["prompt"] for item in submitted}) == 3
        assert all("PRIVATE" not in json.dumps(item) for item in submitted)
        login(client, database, "bob")
        assert client.get(f"/api/style-experiments/{run_id}").status_code == 404


def test_schema4_upgrade_preserves_private_rows_and_marks_legacy_snapshot_unavailable(tmp_path):
    path = tmp_path / "schema4.sqlite3"
    with sqlite3.connect(path) as connection:
        for filename in (
            "0001_auth.sql", "0002_generations.sql", "0003_style_experiments.sql",
            "0004_prompt_snapshots.sql",
        ):
            connection.executescript(
                files("novelai_api").joinpath("migrations", filename).read_text()
            )
    database = Database(path)
    _, token = create_token(database, "alice")
    session, user = issue_session(database, token)
    job_id = JobStore(database).create(user["id"], GenerationRequest(**INPUT, seed=77))
    run = RunStore(database).create(user["id"], run_request(seed=77))
    saved = PromptSnapshotStore(database).create(user["id"], PromptSnapshotCreate(**snapshot()))
    with database.connect() as connection:
        before = dict(connection.execute("SELECT * FROM generation_jobs").fetchone())
    assert not database.check_ready()
    database.migrate()
    database.migrate()
    assert database.check_ready()
    assert current_user(database, session) == user
    assert PromptSnapshotStore(database).get(user["id"], str(saved.id)) == saved
    assert RunStore(database).get(user["id"], run.id).model_dump() == run.model_dump()
    with database.connect() as connection:
        after = dict(connection.execute("SELECT * FROM generation_jobs").fetchone())
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
    assert after.pop("provider_request_json") is None
    assert after == before
    # Existing test providers and old rows have no captured request; never infer one.
    with client_for(database, FakeProvider()) as client:
        client.cookies.set(SESSION_COOKIE, session)
        assert client.get(f"/api/generations/{job_id}").json()["provider_request"] is None
