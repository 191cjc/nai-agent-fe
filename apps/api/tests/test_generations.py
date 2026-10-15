"""In-process fake provider exercises generation without paid service calls."""

import base64
import json
import sqlite3
import threading
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from novelai_api.app import create_app
from novelai_api.auth import create_token, revoke_token
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import (
    GeneratedImage,
    GenerationManager,
    GenerationNotConfigured,
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
NATIVE_INPUT = {
    **INPUT,
    "model": "nai-diffusion-5-full",
    "style_prompt": " watercolor ",
    "positive_prompt": " garden, 2girls ",
    "character_prompts": [
        {"prompt": " blue hair ", "x": 0.1, "y": 0.9},
        {"prompt": "red hair, glasses", "x": 0.73, "y": 0.27},
    ],
    "seed": 77,
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


@pytest.mark.parametrize(
    ("style", "shared", "expected"),
    [
        ("", "  blue hair, garden  ", "  blue hair, garden  "),
        (" \t", "  blue hair, garden  ", "  blue hair, garden  "),
        (" watercolor ", " garden ", "watercolor, garden"),
        (" watercolor ", "", "watercolor"),
        (" watercolor ", " \t ", "watercolor"),
        ("x" * 1499, "y" * 1499, "x" * 1499 + ", " + "y" * 1499),
        ("x" * 3000, "", "x" * 3000),
        ("", "y" * 3000, "y" * 3000),
    ],
)
def test_base_prompt_preserves_legacy_text_and_composes_only_style_and_shared(
    style: str, shared: str, expected: str,
) -> None:
    parameters = GenerationRequest.model_validate(
        {**NATIVE_INPUT, "style_prompt": style, "positive_prompt": shared}
    )
    assert parameters.base_prompt == expected
    assert parameters.style_prompt == style
    assert parameters.positive_prompt == shared
    assert [character.prompt for character in parameters.character_prompts] == [
        " blue hair ", "red hair, glasses"
    ]


@pytest.mark.parametrize(
    "model",
    [
        "nai-diffusion-4-full", "nai-diffusion-4-curated-preview",
        "nai-diffusion-4-5-full", "nai-diffusion-4-5-curated",
        "nai-diffusion-5-full", "nai-diffusion-5-curated",
    ],
)
def test_native_models_accept_workspace_character_limits(model: str) -> None:
    characters = [{"prompt": "x" * 3000} for _ in range(6)]
    parameters = GenerationRequest.model_validate(
        {**NATIVE_INPUT, "model": model, "character_prompts": characters}
    )
    assert parameters.model_dump()["character_prompts"] == [
        {**character, "x": 0.5, "y": 0.5} for character in characters
    ]


@pytest.mark.parametrize(
    ("coordinates", "expected"),
    [
        ({}, {"x": 0.5, "y": 0.5}),
        ({"x": 0.1}, {"x": 0.1, "y": 0.5}),
        ({"y": 0.9}, {"x": 0.5, "y": 0.9}),
        ({"x": 0.9, "y": 0.1}, {"x": 0.9, "y": 0.1}),
        ({"x": 0.234, "y": 0.876}, {"x": 0.234, "y": 0.876}),
    ],
)
def test_character_coordinates_default_independently_and_preserve_valid_numbers(
    coordinates: dict, expected: dict,
) -> None:
    parameters = GenerationRequest.model_validate({
        **NATIVE_INPUT, "character_prompts": [{"prompt": "person", **coordinates}],
    })
    assert parameters.model_dump()["character_prompts"] == [{"prompt": "person", **expected}]


@pytest.mark.parametrize("axis", ["x", "y"])
@pytest.mark.parametrize(
    "coordinate",
    [
        None, True, False, "0.5", "NaN", [], {}, 0, 1, 0.099, 0.901,
        float("nan"), float("inf"), float("-inf"),
    ],
)
def test_invalid_character_coordinates_rejected_without_job_or_provider_work(
    database: Database, axis: str, coordinate,
) -> None:
    provider = FakeProvider()
    with client_for(database, provider) as client:
        login(client, database, "alice")
        parameters = {
            **NATIVE_INPUT, "character_prompts": [{"prompt": "person", axis: coordinate}],
        }
        # Raw content also exercises nonstandard JSON NaN/Infinity if the parser accepts it.
        response = client.post(
            "/api/generations", content=json.dumps(parameters),
            headers={**ORIGIN, "Content-Type": "application/json"},
        )
        assert response.status_code == 422
        assert response.json() == {
            "code": "validation_error", "message": "Invalid request", "retryable": False,
        }
        assert client.get("/api/generations").json()["items"] == []
        assert provider.calls == []


@pytest.mark.parametrize(
    "override",
    [
        {"positive_prompt": "", "style_prompt": ""},
        {"positive_prompt": " \t", "style_prompt": " \t"},
        {"positive_prompt": "x" * 3001},
        {"style_prompt": "x" * 3001},
        {"style_prompt": "x" * 1500, "positive_prompt": "y" * 1499},
        {"character_prompts": [{"prompt": "person"}] * 7},
        {"character_prompts": [{"prompt": ""}]},
        {"character_prompts": [{"prompt": " \t "}]},
        {"character_prompts": [{"prompt": "x" * 3001}]},
        {"character_prompts": [{}]},
        {"character_prompts": ["person"]},
        {"character_prompts": None},
        {"model": "nai-diffusion-3"},
        {"model": "nai-diffusion-4-full-inpainting"},
        {"model": "nai-diffusion-5-full-inpainting"},
        {"model": "unknown-future-model"},
    ],
)
def test_invalid_native_prompts_rejected_before_submission(
    database: Database, override: dict,
) -> None:
    provider = FakeProvider()
    with client_for(database, provider) as client:
        login(client, database, "alice")
        response = client.post(
            "/api/generations", json={**NATIVE_INPUT, **override}, headers=ORIGIN,
        )
        assert response.status_code == 422
        assert response.json() == {
            "code": "validation_error", "message": "Invalid request", "retryable": False,
        }
        assert client.get("/api/generations").json()["items"] == []
        assert provider.calls == []


def test_structured_and_legacy_history_survive_restart_backup_and_reuse(
    database: Database,
) -> None:
    provider = FakeProvider()
    legacy = {**INPUT, "positive_prompt": "  original flat prompt  ", "seed": 77}
    old_native = {
        **NATIVE_INPUT,
        "character_prompts": [{"prompt": " blue hair "}, {"prompt": "red hair, glasses"}],
    }
    with client_for(database, provider) as client:
        _token, alice_id, session = login(client, database, "alice")
        native_id = client.post(
            "/api/generations", json=NATIVE_INPUT, headers=ORIGIN,
        ).json()["id"]
        assert wait_finished(client, native_id)["parameters"] == NATIVE_INPUT
        assert provider.calls[0].model_dump() == NATIVE_INPUT
        old_native_id = JobStore(database).create(alice_id, GenerationRequest(**old_native))
        legacy_id = JobStore(database).create(alice_id, GenerationRequest(**legacy))
        with database.connect(write=True) as connection:
            persisted = connection.execute(
                "SELECT settings_json FROM generation_jobs WHERE id = ?", (native_id,),
            ).fetchone()
            assert json.loads(persisted["settings_json"]) == NATIVE_INPUT
            # Simulate saved JSON from before positions and before native characters.
            connection.executemany(
                "UPDATE generation_jobs SET settings_json = ?, status = 'succeeded' WHERE id = ?",
                [(json.dumps(old_native), old_native_id), (json.dumps(legacy), legacy_id)],
            )
        login(client, database, "bob")
        assert client.get("/api/generations").json()["items"] == []
        assert client.get(f"/api/generations/{native_id}").status_code == 404
        assert client.get(f"/api/generations/{old_native_id}").status_code == 404
        assert client.get(f"/api/generations/{legacy_id}").status_code == 404
        client.cookies.set(SESSION_COOKIE, session)
        target = database.path.parent / "structured-snapshot.sqlite3"
        database.backup(target)

    expected = {
        native_id: NATIVE_INPUT,
        old_native_id: {
            **old_native,
            "character_prompts": [
                {**character, "x": 0.5, "y": 0.5} for character in old_native["character_prompts"]
            ],
        },
        legacy_id: {**legacy, "style_prompt": "", "character_prompts": []},
    }
    for stored_database in (database, Database(target)):
        reusable_provider = FakeProvider()
        with client_for(stored_database, reusable_provider) as restored:
            restored.cookies.set(SESSION_COOKIE, session)
            history = restored.get("/api/generations").json()["items"]
            assert {item["id"]: item["parameters"] for item in history} == expected
            for job_id, parameters in expected.items():
                saved = restored.get(f"/api/generations/{job_id}").json()
                assert saved["parameters"] == parameters
                assert saved["image_urls"] == []
                response = restored.post("/api/generations", json=parameters, headers=ORIGIN)
                assert response.status_code == 202
                reused = wait_finished(restored, response.json()["id"])
                assert reused["parameters"] == parameters
            assert [parameters.model_dump() for parameters in reusable_provider.calls] == list(
                expected.values()
            )
    assert target.stat().st_mode & 0o777 == 0o600
    assert PNG not in target.read_bytes()


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


def test_history_paginates_past_ten_thousand_records(database: Database) -> None:
    with client_for(database) as client:
        _alice_token, alice_id, alice_session = login(client, database, "alice")
        _bob_token, bob_id, _bob_session = login(client, database, "bob")
        client.cookies.set(SESSION_COOKIE, alice_session)
        parameters = GenerationRequest(**INPUT, seed=77)
        total = 10_105
        with database.connect(write=True) as connection:
            connection.executemany(
                "INSERT INTO generation_jobs "
                "(id, user_id, positive_prompt, negative_prompt, settings_json, effective_seed, "
                "status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'failed', ?, ?)",
                (
                    (
                        f"history-{index:05d}", alice_id, parameters.positive_prompt,
                        parameters.negative_prompt, parameters.model_dump_json(), 77, index, index,
                    )
                    for index in range(total)
                ),
            )
        JobStore(database).create(bob_id, parameters)

        default_response = client.get("/api/generations")
        assert default_response.status_code == 200
        default_page = default_response.json()
        assert [item["id"] for item in default_page["items"]] == [
            f"history-{index:05d}" for index in range(total - 1, total - 21, -1)
        ]
        assert default_page["next_offset"] == 20

        for offset in (0, 10_000, 10_100):
            response = client.get("/api/generations", params={"limit": 100, "offset": offset})
            assert response.status_code == 200
            page = response.json()
            expected_size = min(100, total - offset)
            assert [item["id"] for item in page["items"]] == [
                f"history-{index:05d}"
                for index in range(total - offset - 1, total - offset - expected_size - 1, -1)
            ]
            assert page["next_offset"] == (offset + 100 if offset + 100 < total else None)
            assert all(item["parameters"] == parameters.model_dump() for item in page["items"])

        end = client.get("/api/generations", params={"offset": total})
        assert end.status_code == 200
        assert end.json() == {"items": [], "next_offset": None}
        for offset in (9_007_199_254_740_990, 9_007_199_254_740_991):
            response = client.get("/api/generations", params={"offset": offset})
            assert response.status_code == 200
            assert response.json() == {"items": [], "next_offset": None}


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "offset=9007199254740992"])
def test_history_rejects_out_of_range_pagination(database: Database, query: str) -> None:
    with client_for(database) as client:
        login(client, database, "alice")
        response = client.get(f"/api/generations?{query}")
        assert response.status_code == 422
        assert response.json() == {
            "code": "validation_error",
            "message": "Invalid request",
            "retryable": False,
        }


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
        ([GeneratedImage(PNG, "image/png"), GeneratedImage(b"invalid", "image/png")], None),
        ([GeneratedImage(PNG, "text/html")] * 2, None),
        (None, "secret upstream traceback"),
    ],
)
def test_bad_results_and_upstream_errors_fail_closed(database: Database, images, failure) -> None:
    provider = FakeProvider(images, failure=failure)
    cache = ResultCache()
    with client_for(database, provider, cache) as client:
        _token_id, user_id, _session = login(client, database, "alice")
        job_id = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        job = wait_finished(client, job_id)
        assert job["status"] == "failed"
        assert job["image_count"] == 0
        assert job["image_urls"] == []
        assert cache.get(job_id, user_id) is None
        if failure is not None:
            assert failure not in str(job)
        assert len(provider.calls) == 1


@pytest.mark.parametrize(
    ("limit_name", "limit"),
    [("MAX_IMAGE_BYTES", len(PNG) - 1), ("MAX_RESULT_BYTES", 2 * len(PNG) - 1)],
)
def test_image_byte_limits_fail_without_retaining_partial_results(
    database: Database, monkeypatch: pytest.MonkeyPatch, limit_name: str, limit: int
) -> None:
    monkeypatch.setattr(f"novelai_api.generations.{limit_name}", limit)
    provider = FakeProvider()
    cache = ResultCache()
    with client_for(database, provider, cache) as client:
        _token_id, user_id, _session = login(client, database, "alice")
        response = client.post("/api/generations", json=INPUT, headers=ORIGIN)
        assert response.status_code == 202
        job_id = response.json()["id"]
        job = wait_finished(client, job_id)
        assert job["status"] == "failed"
        assert job["error_code"] == "invalid_result"
        assert job["image_count"] == 0
        assert job["image_urls"] == []
        assert cache.get(job_id, user_id) is None
        assert client.get(f"/api/generation-results/{job_id}/images/0").status_code == 404
        assert len(provider.calls) == 1


def test_cache_byte_limit_discards_old_images_and_preserves_history(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("novelai_api.generations.MAX_CACHED_BYTES", 2 * len(PNG))
    with client_for(database, FakeProvider()) as client:
        login(client, database, "alice")
        first = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        first_job = wait_finished(client, first)
        assert len(first_job["image_urls"]) == 2
        second = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        second_job = wait_finished(client, second)
        assert len(second_job["image_urls"]) == 2
        assert all(client.get(url).content == PNG for url in second_job["image_urls"])
        evicted = client.get(f"/api/generations/{first}").json()
        assert evicted["status"] == "succeeded"
        assert evicted["image_count"] == 2
        assert evicted["image_urls"] == []
        assert evicted["result_expires_at"] is None
        assert all(client.get(url).status_code == 404 for url in first_job["image_urls"])
        assert {item["id"] for item in client.get("/api/generations").json()["items"]} == {
            first, second
        }


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


def test_missing_executor_refuses_before_submission_side_effects(
    database: Database, monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeProvider()
    manager = GenerationManager(database, provider)
    request = GenerationRequest(**INPUT)
    capacity = Mock(wraps=manager._capacity)
    create = Mock(wraps=manager.store.create)
    random_seed = Mock(return_value=76)
    run = Mock(wraps=manager._run)
    monkeypatch.setattr(manager, "_capacity", capacity)
    monkeypatch.setattr(manager.store, "create", create)
    monkeypatch.setattr(manager, "_run", run)
    monkeypatch.setattr("novelai_api.generations.secrets.randbelow", random_seed)

    with pytest.raises(GenerationNotConfigured):
        manager.submit("not-used", request)

    capacity.acquire.assert_not_called()
    random_seed.assert_not_called()
    create.assert_not_called()
    run.assert_not_called()
    assert request.seed is None
    assert manager.store.list("not-used", limit=20, offset=0).items == []
    assert provider.calls == []


@pytest.mark.parametrize("persist_first", [False, True])
def test_history_runtime_error_is_not_a_provider_configuration_refusal(
    database: Database, monkeypatch: pytest.MonkeyPatch, persist_first: bool,
) -> None:
    provider = FakeProvider()
    app = create_app(
        Settings(database.path, "https://testserver"), database, image_provider=provider,
    )
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as client:
        login(client, database, "alice")
        manager = app.state.generations
        create = manager.store.create
        enqueue = Mock(wraps=manager._executor.submit)

        def failing_create(user_id: str, parameters: GenerationRequest) -> str:
            if persist_first:
                create(user_id, parameters)
            raise RuntimeError("Fixture history failure")

        monkeypatch.setattr(manager.store, "create", failing_create)
        monkeypatch.setattr(manager._executor, "submit", enqueue)
        response = client.post("/api/generations", json={**INPUT, "seed": 77}, headers=ORIGIN)

        assert response.status_code == 500
        assert response.text == "Internal Server Error"
        history = client.get("/api/generations").json()["items"]
        assert len(history) == int(persist_first)
        if persist_first:
            assert history[0]["effective_seed"] == 77
            assert history[0]["status"] == "queued"
        enqueue.assert_not_called()
        assert provider.calls == []


def test_executor_runtime_error_after_enqueue_keeps_history_and_unknown_outcome(
    database: Database, monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeProvider()
    app = create_app(
        Settings(database.path, "https://testserver"), database, image_provider=provider,
    )
    queued = []
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as client:
        login(client, database, "alice")
        manager = app.state.generations

        def failing_submit(work, job_id: str, user_id: str, parameters: GenerationRequest):
            # An executor can queue work before raising (for example on thread startup).
            queued.append((work, job_id, user_id, parameters))
            raise RuntimeError("Fixture executor failure after enqueue")

        monkeypatch.setattr(manager._executor, "submit", failing_submit)
        response = client.post("/api/generations", json={**INPUT, "seed": 77}, headers=ORIGIN)

        assert response.status_code == 500
        assert response.text == "Internal Server Error"
        assert len(queued) == 1
        history = client.get("/api/generations").json()["items"]
        assert len(history) == 1
        assert history[0]["id"] == queued[0][1]
        assert history[0]["effective_seed"] == 77
        assert history[0]["parameters"] == queued[0][3].model_dump()
        assert history[0]["status"] == "queued"
        assert provider.calls == []


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
