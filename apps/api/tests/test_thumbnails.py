"""Grid-review previews of retained results; fakes and disposable SQLite only."""

import io
import threading

import pytest
from PIL import Image, PngImagePlugin
from test_generations import (
    INPUT,
    ORIGIN,
    FakeProvider,
    client_for,
    database,  # noqa: F401
    login,
    wait_finished,
)

from novelai_api import thumbnails as thumbnail_module
from novelai_api.db import Database
from novelai_api.generations import GeneratedImage
from novelai_api.thumbnails import ThumbnailBusy, ThumbnailCache, render_thumbnail


def png(width: int, height: int, *, text: str = "", alpha: bool = False) -> bytes:
    image = Image.new("RGBA" if alpha else "RGB", (width, height), (200, 40, 90))
    info = PngImagePlugin.PngInfo()
    if text:
        info.add_text("Comment", text)
    output = io.BytesIO()
    image.save(output, format="PNG", pnginfo=info)
    return output.getvalue()


def test_thumbnails_are_small_webp_without_source_metadata() -> None:
    data = render_thumbnail(png(1024, 1536, text="secret prompt fixture"))
    with Image.open(io.BytesIO(data)) as preview:
        assert preview.format == "WEBP"
        assert preview.size == (256, 384)
        assert not preview.info.get("exif") and not preview.info.get("icc_profile")
    assert b"secret prompt fixture" not in data
    with Image.open(io.BytesIO(render_thumbnail(png(200, 100, alpha=True)))) as small:
        assert small.size == (200, 100)  # never upscaled


@pytest.mark.parametrize("source", [png(2049, 2048), b"\x89PNG\r\n\x1a\nbroken"])
def test_oversized_or_invalid_sources_are_refused(source: bytes) -> None:
    with pytest.raises((ValueError, OSError)):
        render_thumbnail(source)


def test_cache_is_owner_bound_byte_bounded_and_discardable() -> None:
    cache = ThumbnailCache(max_bytes=1)
    source = png(64, 64)
    cache.render("job", "alice", 0, source)
    assert cache.get("job", "alice", 0) is None  # larger than the whole budget
    cache = ThumbnailCache()
    first = cache.render("job", "alice", 0, source)
    assert cache.get("job", "alice", 0) == first
    assert cache.get("job", "bob", 0) is None
    single = len(first)
    cache = ThumbnailCache(max_bytes=single * 2)
    for index in range(3):
        cache.render("job", "alice", index, source)
    assert cache.get("job", "alice", 0) is None
    assert cache.get("job", "alice", 2) is not None
    cache.discard("job")
    assert cache.get("job", "alice", 2) is None


def test_busy_render_slots_refuse_instead_of_queueing_without_bound() -> None:
    cache = ThumbnailCache(concurrency=1, wait=0.01)
    held = threading.Event()
    release = threading.Event()
    original = thumbnail_module.render_thumbnail

    def slow(data: bytes) -> bytes:
        held.set()
        assert release.wait(timeout=3)
        return original(data)

    thumbnail_module.render_thumbnail = slow
    try:
        worker = threading.Thread(target=cache.render, args=("job", "alice", 0, png(8, 8)))
        worker.start()
        assert held.wait(timeout=3)
        with pytest.raises(ThumbnailBusy):
            cache.render("job", "alice", 1, png(8, 8))
        release.set()
        worker.join(timeout=3)
    finally:
        thumbnail_module.render_thumbnail = original


def test_api_serves_owner_previews_with_original_retention_rules(
    database: Database, monkeypatch: pytest.MonkeyPatch,  # noqa: F811
) -> None:
    renders = []
    original = thumbnail_module.render_thumbnail
    monkeypatch.setattr(
        thumbnail_module, "render_thumbnail", lambda data: renders.append(1) or original(data),
    )
    images = [GeneratedImage(png(1024, 1024, text="hidden"), "image/png")] * 2
    with client_for(database, FakeProvider(images)) as client:
        _token, _user, alice = login(client, database, "alice")
        job = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        wait_finished(client, job)
        url = f"/api/generation-results/{job}/images/1/thumbnail"
        response = client.get(url)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert b"hidden" not in response.content
        assert client.get(url).content == response.content
        assert len(renders) == 1  # second read is a cache hit
        assert client.get(f"/api/generation-results/{job}/images/2/thumbnail").status_code == 404
        login(client, database, "bob")
        assert client.get(url).status_code == 404
        client.cookies.set("__Host-nai_session", alice)
        assert client.delete(f"/api/generations/{job}", headers=ORIGIN).status_code == 204
        assert client.get(url).status_code == 404
        client.cookies.clear()
        assert client.get(url).status_code == 401


def test_failed_jobs_have_no_preview(database: Database) -> None:  # noqa: F811
    with client_for(database, FakeProvider(failure="boom")) as client:
        login(client, database, "alice")
        job = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        assert wait_finished(client, job)["status"] == "failed"
        assert client.get(f"/api/generation-results/{job}/images/0/thumbnail").status_code == 404
