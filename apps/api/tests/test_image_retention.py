"""Offline private image persistence, admission and saved experiment regressions."""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_generations import INPUT, ORIGIN, PNG, FakeProvider, login, wait_finished

from novelai_api.app import create_app
from novelai_api.auth import create_token
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import (
    MAX_RESULT_BYTES,
    ExperimentConflict,
    GeneratedImage,
    GenerationManager,
    GenerationRequest,
    JobStore,
    ResultStorageUnavailable,
)
from novelai_api.image_results import (
    DIRECTORY_OVERHEAD_BYTES,
    IMAGE_RETENTION_SECONDS,
    MAX_IMAGE_BYTES,
    DiskResultStore,
)
from novelai_api.security import SESSION_COOKIE

IMAGES = [GeneratedImage(PNG, "image/png")] * 2


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "state" / "retained.sqlite3")
    database.migrate()
    return database


def disk_client(database: Database, provider=None, cache=None) -> TestClient:
    return TestClient(
        create_app(
            Settings(database.path, "https://testserver"), database,
            image_provider=provider, result_cache=cache,
        ),
        base_url="https://testserver",
    )


def context(*, run_id=None, ordinal="1", total="3", weights=None) -> dict:
    return {
        "id": str(run_id or uuid4()), "ordinal": ordinal, "total": total,
        "weights": weights if weights is not None else [
            {"tag_index": 4, "label": "artist:fixture", "weight": "1.0"},
        ],
    }


def test_default_store_survives_app_restart_and_deletion(database: Database) -> None:
    provider = FakeProvider()
    image_root = database.path.parent / "generation-images"
    app = create_app(
        Settings(database.path, "https://testserver"), database, image_provider=provider,
    )
    assert not image_root.exists()
    app.openapi()
    assert not image_root.exists()
    with TestClient(app, base_url="https://testserver") as client:
        _token, user_id, session = login(client, database, "alice")
        job_id = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        job = wait_finished(client, job_id)
        assert job["status"] == "succeeded"
        expiry = job["result_expires_at"]
        assert int(time.time()) + IMAGE_RETENTION_SECONDS - 5 <= expiry
        directory = image_root / job_id
        manifest = json.loads((directory / "manifest.json").read_text())
        assert manifest["user_id"] == user_id
        assert manifest["expires_at"] == expiry
        if os.name == "posix":
            assert image_root.stat().st_mode & 0o777 == 0o700
            assert directory.stat().st_mode & 0o777 == 0o700
            assert all(path.stat().st_mode & 0o777 == 0o600 for path in directory.iterdir())
        assert all(client.get(url).content == PNG for url in job["image_urls"])
        assert provider.calls[0].experiment is None
    with disk_client(database) as restarted:
        restarted.cookies.set(SESSION_COOKIE, session)
        result = restarted.get(f"/api/generations/{job_id}").json()
        assert result["image_urls"] == job["image_urls"]
        assert result["result_expires_at"] == expiry
        assert all(restarted.get(url).content == PNG for url in result["image_urls"])
        restarted.cookies.clear()
        login(restarted, database, "bob")
        assert restarted.get(f"/api/generations/{job_id}").status_code == 404
        assert restarted.get(job["image_urls"][0]).status_code == 404
        assert restarted.delete(f"/api/generations/{job_id}", headers=ORIGIN).status_code == 404
        assert directory.exists()
        restarted.cookies.clear()
        restarted.cookies.set(SESSION_COOKIE, session)
        assert restarted.delete(f"/api/generations/{job_id}", headers=ORIGIN).status_code == 204
        assert not directory.exists()
    assert provider.calls and len(provider.calls) == 1


def test_expiry_uses_saved_wall_time_across_restart_and_keeps_metadata(database: Database) -> None:
    now = [1_000_000.0]
    root = database.path.parent / "generation-images"
    cache = DiskResultStore(root, clock=lambda: now[0])
    run = context()
    with disk_client(database, FakeProvider(), cache) as client:
        _token, _user, session = login(client, database, "alice")
        job_id = client.post(
            "/api/generations", json={**INPUT, "experiment": run}, headers=ORIGIN,
        ).json()["id"]
        saved = wait_finished(client, job_id)
        assert saved["result_expires_at"] == int(now[0]) + IMAGE_RETENTION_SECONDS
    now[0] += IMAGE_RETENTION_SECONDS - 1
    restarted_cache = DiskResultStore(root, clock=lambda: now[0])
    with disk_client(database, cache=restarted_cache) as client:
        client.cookies.set(SESSION_COOKIE, session)
        assert client.get(saved["image_urls"][0]).content == PNG
        now[0] += 1
        assert client.get(saved["image_urls"][0]).status_code == 404
        assert client.get(f"/api/generations/{job_id}").json()["image_urls"] == []
        restarted_cache.sweep()
        assert not (root / job_id).exists()
        detail = client.get(f"/api/style-experiments/{run['id']}").json()
        assert detail["summary"]["group_count"] == 1
        assert detail["summary"]["completed_count"] == 1
        assert detail["summary"]["image_count"] == 2
        assert detail["items"][0]["parameters"]["experiment"] == run
        assert detail["items"][0]["image_urls"] == []


def test_periodic_and_startup_sweep_remove_expired_and_abandoned_files(tmp_path: Path) -> None:
    root = tmp_path / "images"
    now = [time.time()]
    cache = DiskResultStore(root, clock=lambda: now[0], sweep_interval=0.01)
    job_id, owner = str(uuid4()), str(uuid4())
    assert not root.exists()
    assert cache.put(job_id, owner, IMAGES)
    abandoned = root / f".tmp-{uuid4()}"
    abandoned.mkdir(mode=0o700)
    (abandoned / "partial.png").write_bytes(PNG)
    reserve = root / f".reserve-{uuid4()}"
    reserve.write_bytes(b"partial")
    cache.start()
    try:
        assert not abandoned.exists() and not reserve.exists()
        assert (root / job_id).exists()
        now[0] += IMAGE_RETENTION_SECONDS
        deadline = time.monotonic() + 2
        while (root / job_id).exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not (root / job_id).exists()
    finally:
        cache.stop()


@pytest.mark.parametrize("damage", ["missing", "symlink", "contents", "manifest", "oversized"])
def test_corrupt_files_fail_safely_without_owner_or_path_escape(
    tmp_path: Path, damage: str,
) -> None:
    cache = DiskResultStore(tmp_path / "images")
    job_id, owner, stranger = str(uuid4()), str(uuid4()), str(uuid4())
    assert cache.put(job_id, owner, IMAGES)
    assert cache.describe(job_id, stranger) is None
    assert cache.image(job_id, stranger, 0) is None
    assert cache.describe("../outside", owner) is None
    assert cache.image(job_id, owner, -1) is None
    outside = tmp_path / "outside.png"
    outside.write_bytes(PNG)
    target = cache.path / job_id / "0.png"
    if damage == "missing":
        target.unlink()
    elif damage == "symlink":
        target.unlink()
        target.symlink_to(outside)
    elif damage == "contents":
        target.write_bytes(b"x" * len(PNG))
    elif damage == "manifest":
        (target.parent / "manifest.json").write_bytes(b"{" * 9000)
    else:
        with target.open("wb") as output:
            output.truncate(MAX_IMAGE_BYTES + 1)
    assert cache.image(job_id, owner, 0) is None
    assert cache.get(job_id, owner) is None
    cache.discard(job_id)
    assert outside.read_bytes() == PNG
    assert not target.parent.exists()


def test_root_and_result_symlinks_are_never_followed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "images"
    root.symlink_to(outside, target_is_directory=True)
    cache = DiskResultStore(root)
    cache.start()
    try:
        with pytest.raises(ResultStorageUnavailable):
            cache.reserve(1)
        with pytest.raises(ResultStorageUnavailable):
            cache.put(str(uuid4()), str(uuid4()), IMAGES)
        assert list(outside.iterdir()) == []
    finally:
        cache.stop()
    root.unlink()
    root.mkdir()
    job_id = str(uuid4())
    (root / job_id).symlink_to(outside, target_is_directory=True)
    cache.discard(job_id)
    assert (root / job_id).is_symlink()
    assert list(outside.iterdir()) == []


def test_cleanup_preserves_unknown_old_entries_and_refuses_unbudgetable_trees(
    tmp_path: Path,
) -> None:
    cache = DiskResultStore(tmp_path / "images")
    cache.path.mkdir()
    unknown = cache.path / "operator-sentinel"
    unknown.mkdir()
    sentinel = unknown / "keep.txt"
    sentinel.write_bytes(b"keep")
    os.utime(unknown, (0, 0))
    cache.start()
    try:
        cache.sweep()
        assert sentinel.read_bytes() == b"keep"
        (unknown / "nested").mkdir()
        with pytest.raises(ResultStorageUnavailable):
            cache.reserve(1)
        assert sentinel.read_bytes() == b"keep"
    finally:
        cache.stop()


@pytest.mark.parametrize("images", [[], IMAGES * 5, [GeneratedImage(b"bad", "image/png")],
                                   [GeneratedImage(PNG, "text/html")]])
def test_invalid_result_sets_never_create_partial_files(tmp_path: Path, images) -> None:
    cache = DiskResultStore(tmp_path / "images")
    assert cache.put(str(uuid4()), str(uuid4()), images) is False
    assert not cache.path.exists()


def test_capacity_reserves_all_pending_work_and_never_evicts_unexpired(tmp_path: Path) -> None:
    now = [1000.0]
    amount = MAX_IMAGE_BYTES + DIRECTORY_OVERHEAD_BYTES
    cache = DiskResultStore(
        tmp_path / "images", budget_bytes=amount * 2,
        free_reserve_bytes=0, disk_free=lambda _path: 10**12, clock=lambda: now[0],
    )
    first = cache.reserve(1)
    second = cache.reserve(1)
    with pytest.raises(ResultStorageUnavailable):
        cache.reserve(1)
    cache.release(first)
    cache.release(first)
    third = cache.reserve(1)
    cache.release(second)
    cache.release(third)
    job_id, owner = str(uuid4()), str(uuid4())
    assert cache.put(job_id, owner, IMAGES)
    cache._budget = amount
    with pytest.raises(ResultStorageUnavailable):
        cache.reserve(1)
    assert cache.image(job_id, owner, 0).data == PNG
    now[0] += IMAGE_RETENTION_SECONDS
    reservation = cache.reserve(1)
    cache.release(reservation)
    assert not (cache.path / job_id).exists()


def test_default_store_has_no_fixed_budget_and_keeps_three_gib_free(tmp_path: Path) -> None:
    gib = 1024 * 1024 * 1024
    amount = MAX_RESULT_BYTES + DIRECTORY_OVERHEAD_BYTES
    free = [100 * gib]
    cache = DiskResultStore(tmp_path / "images", disk_free=lambda _path: free[0])
    # Far more pending work than the old 2 GiB budget is admitted while disk is free.
    reservations = [cache.reserve(4) for _ in range(100)]
    assert sum(cache._reservations.values()) > 2 * gib
    for reservation in reservations:
        cache.release(reservation)
    free[0] = 3 * gib + amount
    cache.release(cache.reserve(4))
    free[0] = 3 * gib + amount - 1
    with pytest.raises(ResultStorageUnavailable):
        cache.reserve(4)


@pytest.mark.parametrize("failure", ["low-disk", "write"])
def test_storage_refusal_is_before_seed_history_or_provider(
    database: Database, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    cache = DiskResultStore(database.path.parent / "images", disk_free=lambda _path: 0)
    if failure == "write":
        cache._disk_free = lambda _path: 10**12
        monkeypatch.setattr(cache, "_write", Mock(side_effect=OSError("secret-disk-error")))
    provider = FakeProvider()
    seed = Mock(return_value=10)
    monkeypatch.setattr("novelai_api.generations.secrets.randbelow", seed)
    with disk_client(database, provider, cache) as client:
        login(client, database, "alice")
        response = client.post("/api/generations", json=INPUT, headers=ORIGIN)
        assert response.status_code == 503
        assert response.json() == {
            "code": "result_storage_unavailable", "message": "Image storage is unavailable",
            "retryable": False,
        }
        assert client.get("/api/generations").json()["items"] == []
        assert provider.calls == []
        assert cache._reservations == {}
        seed.assert_not_called()
        assert client.app.state.generations._capacity.acquire(blocking=False)
        client.app.state.generations._capacity.release()


def test_storage_failure_after_paid_work_is_terminal_without_retry(
    database: Database, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = DiskResultStore(database.path.parent / "images")
    monkeypatch.setattr(cache, "put", Mock(side_effect=ResultStorageUnavailable("private-path")))
    provider = FakeProvider()
    with disk_client(database, provider, cache) as client:
        login(client, database, "alice")
        response = client.post("/api/generations", json=INPUT, headers=ORIGIN)
        assert response.status_code == 202
        result = wait_finished(client, response.json()["id"])
        assert result["status"] == "failed"
        assert result["error_code"] == "result_storage_error"
        assert result["image_urls"] == []
        assert len(provider.calls) == 1
        assert cache._reservations == {}


def test_enqueue_failure_releases_reservation_and_late_queued_work_cannot_start(
    database: Database, monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeProvider()
    app = create_app(
        Settings(database.path, "https://testserver"), database, image_provider=provider,
    )
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as client:
        login(client, database, "alice")
        manager = app.state.generations
        enqueued = []

        def failed_submit(*args):
            enqueued.append(args)
            raise RuntimeError("fixture queued before thread startup error")

        monkeypatch.setattr(manager._executor, "submit", failed_submit)
        response = client.post("/api/generations", json=INPUT, headers=ORIGIN)
        assert response.status_code == 500
        assert manager.cache._reservations == {}
        assert len(enqueued) == 1
        work, *arguments = enqueued[0]
        work(*arguments)
        assert provider.calls == []
        assert len(client.get("/api/generations").json()["items"]) == 1


def test_shutdown_cancels_queued_jobs_and_releases_each_admission(database: Database) -> None:
    token_id, _token = create_token(database, "alice")
    with database.connect() as connection:
        owner = connection.execute(
            "SELECT user_id FROM access_tokens WHERE id = ?", (token_id,),
        ).fetchone()[0]
    gate = threading.Event()
    provider = FakeProvider(gate=gate)
    manager = GenerationManager(database, provider)
    manager.start()
    stopping = None
    try:
        parameters = GenerationRequest(**INPUT)
        first = manager.submit(owner, parameters)
        assert provider.started.wait(timeout=2)
        others = [manager.submit(owner, parameters) for _ in range(2)]
        assert len(manager.cache._reservations) == 3
        stopping = threading.Thread(target=manager.stop)
        stopping.start()
        deadline = time.monotonic() + 2
        while len(manager.cache._reservations) > 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(manager.cache._reservations) == 1
        gate.set()
        stopping.join(timeout=2)
        assert not stopping.is_alive()
        assert manager.cache._reservations == {}
        assert len(provider.calls) == 1
        assert manager.store.get(owner, first).status == "succeeded"
        assert all(manager.store.get(owner, job_id).status == "queued" for job_id in others)
        assert all(manager._capacity.acquire(blocking=False) for _ in range(3))
        assert manager._capacity.acquire(blocking=False) is False
        for _ in range(3):
            manager._capacity.release()
    finally:
        gate.set()
        if stopping is not None:
            stopping.join(timeout=3)
        manager.stop()


@pytest.mark.parametrize(
    "override",
    [
        {"id": "not-a-uuid"}, {"ordinal": "0"}, {"ordinal": "01"}, {"ordinal": 1},
        {"total": "1e10"}, {"total": "9" * 1001}, {"ordinal": "4"},
        {"weights": []}, {"weights": [{"tag_index": 0, "label": " ", "weight": "1.0"}]},
        {"weights": [{"tag_index": True, "label": "x", "weight": "1.0"}]},
        {"weights": [{"tag_index": 3000, "label": "x", "weight": "1.0"}]},
        {"weights": [{"tag_index": 0, "label": "x", "weight": "01.0"}]},
        {"weights": [{"tag_index": 0, "label": "x", "weight": "+1.0"}]},
        {"weights": [{"tag_index": 0, "label": "x", "weight": "1e0"}]},
        {"weights": [{"tag_index": 0, "label": "x", "weight": "1" * 101}]},
        {"weights": [{"tag_index": 0, "label": "x", "weight": 1.0}]},
        {"weights": [{"tag_index": 0, "label": "x", "weight": "1.0"}] * 2},
        {"weights": [{"tag_index": index, "label": "x" * 1501, "weight": "1.0"}
                     for index in range(2)]},
    ],
)
def test_invalid_metadata_is_rejected_before_any_submission(
    database: Database, override: dict,
) -> None:
    provider = FakeProvider()
    with disk_client(database, provider) as client:
        login(client, database, "alice")
        response = client.post(
            "/api/generations", json={**INPUT, "experiment": {**context(), **override}},
            headers=ORIGIN,
        )
        assert response.status_code == 422
        assert client.get("/api/generations").json()["items"] == []
        assert client.get("/api/style-experiments").json()["items"] == []
        assert provider.calls == []


def test_duplicate_and_changed_total_refuse_without_paid_retry_and_keep_exact_metadata(
    database: Database,
) -> None:
    provider = FakeProvider()
    run = context(weights=[
        {"tag_index": 0, "label": "artist:fixture", "weight": "1.0"},
        {"tag_index": 3, "label": "other", "weight": "-0.1"},
        {"tag_index": 4, "label": "zero", "weight": "0.0"},
    ])
    with disk_client(database, provider) as client:
        login(client, database, "alice")
        payload = {**INPUT, "experiment": run}
        response = client.post("/api/generations", json=payload, headers=ORIGIN)
        job_id = response.json()["id"]
        assert wait_finished(client, job_id)["parameters"]["experiment"] == run
        for candidate in (run, {**run, "ordinal": "2", "total": "4"}):
            refused = client.post(
                "/api/generations", json={**INPUT, "experiment": candidate}, headers=ORIGIN,
            )
            assert refused.status_code == 409
            assert refused.json()["code"] == "experiment_conflict"
        assert len(provider.calls) == 1
        assert client.app.state.generations.cache._reservations == {}
        saved = client.get(f"/api/style-experiments/{run['id']}").json()
        assert saved["items"][0]["parameters"]["experiment"] == run
        login(client, database, "bob")
        assert client.get("/api/style-experiments").json()["items"] == []
        assert client.get(f"/api/style-experiments/{run['id']}").status_code == 404
        # Run identity and duplicate ordinal are scoped to the authenticated owner.
        second = client.post("/api/generations", json=payload, headers=ORIGIN)
        assert second.status_code == 202
        wait_finished(client, second.json()["id"])
        assert len(provider.calls) == 2


def test_duplicate_group_transaction_serializes_concurrent_writers(database: Database) -> None:
    token_id, _token = create_token(database, "alice")
    with database.connect() as connection:
        owner = connection.execute(
            "SELECT user_id FROM access_tokens WHERE id = ?", (token_id,),
        ).fetchone()[0]
    store = JobStore(database)
    parameters = GenerationRequest(**INPUT, seed=77, experiment=context())
    barrier = threading.Barrier(2)

    def create():
        barrier.wait(timeout=2)
        try:
            return store.create(owner, parameters)
        except ExperimentConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create(), range(2)))
    assert results.count("conflict") == 1
    assert len(store.list(owner, limit=20, offset=0).items) == 1


def test_sqlite_backup_keeps_group_metadata_without_copying_private_images(
    database: Database,
) -> None:
    run = context()
    with disk_client(database, FakeProvider()) as client:
        _token, _owner, session = login(client, database, "alice")
        job_id = client.post(
            "/api/generations", json={**INPUT, "experiment": run}, headers=ORIGIN,
        ).json()["id"]
        assert wait_finished(client, job_id)["image_urls"]
        backup_dir = database.path.parent / "restore"
        backup_dir.mkdir(mode=0o700)
        snapshot = backup_dir / "snapshot.sqlite3"
        database.backup(snapshot)
    assert PNG not in snapshot.read_bytes()
    with disk_client(Database(snapshot)) as restored:
        restored.cookies.set(SESSION_COOKIE, session)
        saved = restored.get(f"/api/style-experiments/{run['id']}").json()
        assert saved["items"][0]["parameters"]["experiment"] == run
        assert saved["items"][0]["image_urls"] == []
        assert saved["summary"]["image_count"] == 2


def test_huge_ordinals_page_in_numeric_order_and_groups_survive_restart(database: Database) -> None:
    run_id, another_id = str(uuid4()), str(uuid4())
    total = "9" * 1000
    ordinals = ["9" * 999, "10", "2", "1" + "0" * 999, "1"]
    with disk_client(database) as client:
        _token, owner, session = login(client, database, "alice")
        store = JobStore(database)
        ids = {}
        for index, ordinal in enumerate(ordinals):
            parameters = GenerationRequest(**INPUT, seed=77, experiment=context(
                run_id=run_id, ordinal=ordinal, total=total,
            ))
            job_id = store.create(owner, parameters)
            store.mark_running(job_id)
            store.finish(
                job_id, image_count=2, error_code="fixture_failure" if index == 0 else None,
            )
            ids[ordinal] = job_id
        other = store.create(owner, GenerationRequest(
            **INPUT, seed=77, experiment=context(run_id=another_id),
        ))
        with database.connect(write=True) as connection:
            connection.execute("UPDATE generation_jobs SET created_at = 100, updated_at = 200")
        expected_order = sorted(ordinals, key=lambda value: (len(value), value))
        for offset, ordinal in enumerate(expected_order):
            response = client.get(f"/api/style-experiments/{run_id}", params={"offset": offset})
            assert response.status_code == 200
            page = response.json()
            assert page["items"][0]["id"] == ids[ordinal]
            assert page["items"][0]["parameters"]["experiment"]["ordinal"] == ordinal
            assert page["items"][0]["image_urls"] == []
            assert page["next_offset"] == (offset + 1 if offset + 1 < len(ordinals) else None)
            assert page["summary"] == {
                "id": run_id, "kind": "style", "total": total, "group_count": 5,
                "completed_count": 5, "image_count": 10, "created_at": 100, "updated_at": 200,
                "name": None, "dataset_type": None,
            }
        ordered_runs = sorted([run_id, another_id], reverse=True)
        first = client.get("/api/style-experiments?limit=1").json()
        last = client.get("/api/style-experiments?limit=1&offset=1").json()
        assert [first["items"][0]["id"], last["items"][0]["id"]] == ordered_runs
        assert first["next_offset"] == 1 and last["next_offset"] is None
        # Deletion removes only this saved group, retaining the other ordinals.
        assert client.delete(f"/api/generations/{ids['2']}", headers=ORIGIN).status_code == 204
        assert client.get(f"/api/style-experiments/{run_id}").json()["summary"]["group_count"] == 4
        assert client.get(f"/api/generations/{other}").status_code == 200
    with disk_client(database) as client:
        client.cookies.set(SESSION_COOKIE, session)
        saved = client.get(f"/api/style-experiments/{run_id}?limit=100").json()
        assert saved["summary"]["group_count"] == 4
        assert [item["parameters"]["experiment"]["ordinal"] for item in saved["items"]] == [
            ordinal for ordinal in expected_order if ordinal != "2"
        ]
        assert client.get(f"/api/style-experiments/{run_id}?offset=9007199254740991").json()[
            "items"
        ] == []


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "offset=9007199254740992"])
def test_saved_experiment_pagination_bounds(database: Database, query: str) -> None:
    with disk_client(database) as client:
        login(client, database, "alice")
        assert client.get(f"/api/style-experiments?{query}").status_code == 422
        assert client.get(f"/api/style-experiments/{uuid4()}?{query}").status_code == 422


def test_malformed_legacy_json_is_not_an_experiment(database: Database) -> None:
    with disk_client(database) as client:
        login(client, database, "alice")
        _token, owner, _session = login(client, database, "bob")
        store = JobStore(database)
        for settings in ("not-json", '{"experiment": {"id": "bad"}}', "[]"):
            job_id = store.create(owner, GenerationRequest(**INPUT, seed=77))
            with database.connect(write=True) as connection:
                connection.execute(
                    "UPDATE generation_jobs SET settings_json = ? WHERE id = ?", (settings, job_id),
                )
        assert client.get("/api/style-experiments").json() == {"items": [], "next_offset": None}
