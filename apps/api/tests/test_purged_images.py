"""Irreversible review cleanup; synthetic images and disposable SQLite only."""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_dataset_runs import dataset
from test_generations import INPUT, ORIGIN, login, wait_finished
from test_thumbnails import png

from novelai_api import thumbnails as thumbnail_module
from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import GeneratedImage, GenerationRequest, JobStore, ResultCache
from novelai_api.image_results import DiskResultStore, ResultStorageUnavailable
from novelai_api.security import SESSION_COOKIE


class SyntheticProvider:
    def __init__(self):
        self.calls = []

    def generate(self, parameters):
        self.calls.append(parameters)
        return [GeneratedImage(png(64, 64, text=f"fixture-{index}"), "image/png")
                for index in range(parameters.sample_count)]


@pytest.fixture
def database(tmp_path: Path) -> Database:
    value = Database(tmp_path / "state" / "purge.sqlite3")
    value.migrate()
    return value


def finished_dataset(client: TestClient, *, items=2, samples=2) -> tuple[str, list[dict]]:
    request = dataset(
        items=[{"id": f"synthetic-{index}", "prompt": f"synthetic scene {index}"}
               for index in range(items)], sample_count=samples,
    ).model_dump(mode="json")
    request["name"] = "Synthetic review fixture"
    response = client.post("/api/dataset-runs", json=request, headers=ORIGIN)
    assert response.status_code == 202
    run_id = response.json()["id"]
    deadline = time.monotonic() + 5
    while client.get(f"/api/style-experiment-runs/{run_id}").json()["status"] != "completed":
        assert time.monotonic() < deadline
        time.sleep(0.01)
    page = client.get(f"/api/style-experiments/{run_id}", params={"limit": 100}).json()
    return run_id, page["items"]


@pytest.mark.parametrize("disk", [False, True])
def test_member_cleanup_keeps_original_indexes_expiry_and_sibling_bytes(tmp_path, disk) -> None:
    store = DiskResultStore(tmp_path / "images") if disk else ResultCache()
    images = [GeneratedImage(png(64, 64, text=f"synthetic-{index}"), "image/png")
              for index in range(3)]
    job, user = str(uuid4()), str(uuid4())
    store.start()
    try:
        assert store.put(job, user, images)
        original = store.describe(job, user)
        assert store.purge_image(job, user, 1)
        assert store.describe(job, user) == original
        assert store.image(job, user, 1) is None
        assert store.image(job, user, 0) == images[0]
        assert store.image(job, user, 2) == images[2]
        assert not store.purge_image(job, user, 1)
        if disk:
            assert not (store.path / job / "1.png").exists()
            assert len(list((store.path / job).glob("*.png"))) == 2
            restarted = DiskResultStore(store.path)
            assert restarted.image(job, user, 2) == images[2]
            assert restarted.image(job, user, 1) is None
        else:
            assert store._size == len(images[0].data) + len(images[2].data)
    finally:
        store.stop()


@pytest.mark.parametrize("failure", ["manifest_write", "unlink"])
def test_failed_physical_cleanup_has_safe_retry_and_no_temporary_leak(
    tmp_path, monkeypatch, failure,
) -> None:
    store = DiskResultStore(tmp_path / "images")
    job, user = str(uuid4()), str(uuid4())
    images = [GeneratedImage(png(64, 64), "image/png")] * 2
    assert store.put(job, user, images)
    with monkeypatch.context() as patch:
        if failure == "manifest_write":
            def refuse_write(_descriptor, _data):
                raise OSError("synthetic write refusal")
            patch.setattr(store, "_write", refuse_write)
        else:
            original = os.unlink

            def refuse_unlink(name, *args, **kwargs):
                if name == "0.png":
                    raise OSError("synthetic unlink refusal")
                return original(name, *args, **kwargs)
            patch.setattr(os, "unlink", refuse_unlink)
        with pytest.raises(ResultStorageUnavailable):
            store.purge_image(job, user, 0)
        assert (store.path / job / "0.png").exists()
        assert store.image(job, user, 1) == images[1]
        assert not list((store.path / job).glob(".manifest-*"))
    assert store.purge_image(job, user, 0)
    assert not (store.path / job / "0.png").exists()
    assert store.image(job, user, 1) == images[1]


def test_missing_member_is_marked_without_breaking_retained_siblings(tmp_path) -> None:
    store = DiskResultStore(tmp_path / "images")
    job, user = str(uuid4()), str(uuid4())
    images = [GeneratedImage(png(64, 64), "image/png")] * 2
    assert store.put(job, user, images)
    (store.path / job / "0.png").unlink()
    assert not store.purge_image(job, user, 0)
    assert store.image(job, user, 1) == images[1]
    (store.path / job / "manifest.json").unlink()
    with pytest.raises(ResultStorageUnavailable):
        store.purge_image(job, user, 1)
    assert (store.path / job / "1.png").exists()


def test_cleanup_is_current_set_only_preserves_history_and_survives_restart(database) -> None:
    provider = SyntheticProvider()
    settings = Settings(database.path, "https://testserver")
    app = create_app(settings, database, image_provider=provider)
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        _token, alice, session = login(client, database, "alice")
        run_id, groups = finished_dataset(client)
        other_run, other_groups = finished_dataset(client, items=1)
        first, second = groups
        retained = client.get(first["image_urls"][1]).content
        expiry = first["result_expires_at"]
        reference = client.post(
            "/api/reference-images/from-result",
            json={"job_id": first["id"], "image_index": 0}, headers=ORIGIN,
        ).json()
        assert "id" in reference
        caption = "synthetic caption override"
        assert client.put(
            f"/api/style-experiments/{run_id}/captions",
            json={"items": [{"job_id": first["id"], "caption": caption}]}, headers=ORIGIN,
        ).status_code == 200
        rerun_response = client.post(
            f"/api/generations/{first['id']}/rerun", json={}, headers=ORIGIN,
        )
        assert rerun_response.status_code == 202
        rerun = wait_finished(client, rerun_response.json()["id"])
        manual = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        wait_finished(client, manual)
        targets = [(first["id"], 0), (second["id"], 1), (rerun["id"], 0)]
        for job_id, index in [*targets, (other_groups[0]["id"], 0), (manual, 0)]:
            assert client.put(f"/api/generations/{job_id}/images/{index}/discard",
                              headers=ORIGIN).status_code == 204
        preview = f"/api/generation-results/{first['id']}/images/0/thumbnail"
        assert client.get(preview).status_code == 200  # prime the in-memory preview
        url = f"/api/style-experiments/{run_id}/discarded-images"
        assert client.delete(url).status_code == 403
        client.cookies.clear()
        assert client.delete(url, headers=ORIGIN).status_code == 401
        login(client, database, "bob")
        assert client.delete(url, headers=ORIGIN).status_code == 404
        client.cookies.clear()
        client.cookies.set(SESSION_COOKIE, session)
        calls = len(provider.calls)
        result = client.delete(url, headers=ORIGIN)
        assert result.status_code == 200 and result.json() == {
            "deleted_images": 3, "missing_images": 0, "failed_images": 0,
        }
        assert len(provider.calls) == calls  # cleanup cannot generate
        for job_id, index in targets:
            assert not (app.state.generations.cache.path / job_id / f"{index}.png").exists()
            image_url = f"/api/generation-results/{job_id}/images/{index}"
            assert client.get(image_url).status_code == 404
            assert client.get(image_url + "/thumbnail").status_code == 404
            restored = client.delete(
                f"/api/generations/{job_id}/images/{index}/discard", headers=ORIGIN,
            )
            assert restored.status_code == 409 and restored.json()["code"] == "image_purged"
        saved = client.get(f"/api/generations/{first['id']}").json()
        assert saved["parameters"] == first["parameters"]
        assert saved["caption_override"] == caption
        assert saved["image_urls"] == first["image_urls"]
        assert saved["result_expires_at"] == expiry
        assert saved["purged_images"] == [0] and saved["purge_pending_images"] == []
        assert client.get(saved["image_urls"][1]).content == retained
        assert client.get(other_groups[0]["image_urls"][0]).status_code == 200
        assert client.get(f"/api/generation-results/{manual}/images/0").status_code == 200
        assert client.get(f"/api/reference-images/{reference['id']}/image").status_code == 200
        assert client.get(f"/api/style-experiments/{other_run}").status_code == 200
        repeated = client.delete(url, headers=ORIGIN)
        assert repeated.json() == {"deleted_images": 0, "missing_images": 0, "failed_images": 0}
        # A non-dataset experiment cannot be turned into a cleanup scope.
        from test_style_runs import request as style_request
        style_run = app.state.experiments.store.create(alice, style_request())
        unsupported = client.delete(
            f"/api/style-experiments/{style_run.id}/discarded-images", headers=ORIGIN,
        )
        assert unsupported.status_code == 422
        assert app.state.generations.store.is_purged(alice, first["id"], 0)
    restarted = create_app(settings, database, image_provider=SyntheticProvider())
    with TestClient(restarted, base_url="https://testserver") as client:
        client.cookies.set(SESSION_COOKIE, session)
        assert client.get(preview).status_code == 404
        assert client.get(first["image_urls"][0]).status_code == 404
        assert client.get(first["image_urls"][1]).content == retained
        saved = client.get(f"/api/generations/{first['id']}").json()
        assert saved["purged_images"] == [0]


def test_partial_failure_denies_cached_content_and_explicit_retry_removes_bytes(
    database, monkeypatch,
) -> None:
    app = create_app(Settings(database.path, "https://testserver"), database,
                     image_provider=SyntheticProvider())
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        run_id, [group] = finished_dataset(client, items=1)
        for index in range(2):
            assert client.put(f"/api/generations/{group['id']}/images/{index}/discard",
                              headers=ORIGIN).status_code == 204
        preview = group["image_urls"][0] + "/thumbnail"
        assert client.get(preview).status_code == 200
        original = os.unlink

        def refuse_unlink(name, *args, **kwargs):
            if name == "0.png":
                raise OSError("synthetic unlink refusal")
            return original(name, *args, **kwargs)

        url = f"/api/style-experiments/{run_id}/discarded-images"
        with monkeypatch.context() as patch:
            patch.setattr(os, "unlink", refuse_unlink)
            response = client.delete(url, headers=ORIGIN)
            assert response.json() == {"deleted_images": 1, "missing_images": 0, "failed_images": 1}
            view = client.get(f"/api/generations/{group['id']}").json()
            assert view["purged_images"] == [0, 1] and view["purge_pending_images"] == [0]
            assert (app.state.generations.cache.path / group["id"] / "0.png").exists()
            assert client.get(group["image_urls"][0]).status_code == 404
            assert client.get(preview).status_code == 404
            assert client.post("/api/reference-images/from-result", json={
                "job_id": group["id"], "image_index": 0,
            }, headers=ORIGIN).status_code == 404
        response = client.delete(url, headers=ORIGIN)
        assert response.json() == {"deleted_images": 1, "missing_images": 0, "failed_images": 0}
        assert not list((app.state.generations.cache.path / group["id"]).glob("*.png"))
        assert client.get(f"/api/generations/{group['id']}").json()["purge_pending_images"] == []


def test_render_finishing_after_purge_cannot_reintroduce_a_preview(database, monkeypatch) -> None:
    app = create_app(Settings(database.path, "https://testserver"), database,
                     image_provider=SyntheticProvider())
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        _token, alice, _session = login(client, database, "alice")
        run_id, [group] = finished_dataset(client, items=1)
        client.put(f"/api/generations/{group['id']}/images/0/discard", headers=ORIGIN)
        render = thumbnail_module.render_thumbnail

        def finish_after_cleanup(data):
            store = app.state.generations.store
            _, targets = store.begin_discarded_cleanup(alice, run_id)
            for job_id, index in targets:
                app.state.generations.cache.purge_image(job_id, alice, index)
                store.complete_image_purge(alice, job_id, index)
            return render(data)

        monkeypatch.setattr(thumbnail_module, "render_thumbnail", finish_after_cleanup)
        response = client.get(group["image_urls"][0] + "/thumbnail")
        assert response.status_code == 404
        assert app.state.thumbnails.get(group["id"], alice, 0) is None


def test_cleanup_counts_missing_files_without_losing_surviving_members(database) -> None:
    app = create_app(Settings(database.path, "https://testserver"), database,
                     image_provider=SyntheticProvider())
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        run_id, [group] = finished_dataset(client, items=1)
        client.put(f"/api/generations/{group['id']}/images/0/discard", headers=ORIGIN)
        (app.state.generations.cache.path / group["id"] / "0.png").unlink()
        result = client.delete(f"/api/style-experiments/{run_id}/discarded-images", headers=ORIGIN)
        assert result.json() == {"deleted_images": 0, "missing_images": 1, "failed_images": 0}
        assert client.get(group["image_urls"][1]).status_code == 200


def test_restore_racing_purge_is_serialized_and_migration_preserves_marks(database) -> None:
    from novelai_api.auth import create_token

    create_token(database, "alice")
    with database.connect() as connection:
        user = connection.execute("SELECT id FROM users").fetchone()[0]
    store = JobStore(database)
    run_id = str(uuid4())
    parameters = GenerationRequest(**INPUT, experiment={
        "kind": "dataset", "id": run_id, "ordinal": "1", "total": "1", "weights": [],
        "item": {"id": "synthetic-1", "prompt": "synthetic scene"},
    }, seed=5)
    # Direct synthetic fixture bypasses only the run-claim admission check.
    job = store.create(user, GenerationRequest(**INPUT, seed=5))
    with database.connect(write=True) as connection:
        connection.execute("UPDATE generation_jobs SET settings_json = ?, status = 'succeeded', "
                           "image_count = 2 WHERE id = ?", (parameters.model_dump_json(), job))
        connection.execute("DROP TABLE dataset_recipes")
        connection.execute("DROP TABLE purged_images")
        connection.execute("PRAGMA user_version = 12")
    assert not database.check_ready()
    store.set_discarded(user, job, 0, True)
    database.migrate()
    database.migrate()
    assert database.check_ready() and store.discarded(user, [job]) == {job: [0]}
    barrier = threading.Barrier(2)

    def cleanup():
        barrier.wait(timeout=3)
        return store.begin_discarded_cleanup(user, run_id)

    def restore():
        barrier.wait(timeout=3)
        return store.set_discarded(user, job, 0, False)

    with ThreadPoolExecutor(max_workers=2) as pool:
        purge_future, restore_future = pool.submit(cleanup), pool.submit(restore)
        _status, targets = purge_future.result(timeout=5)
        restored = restore_future.result(timeout=5)
    assert bool(targets) != restored
    assert store.is_purged(user, job, 0) == bool(targets)
    if targets:
        with database.connect(write=True) as connection:
            connection.execute("DELETE FROM generation_jobs WHERE id = ?", (job,))
        assert not store.is_purged(user, job, 0)  # job deletion cascades metadata
