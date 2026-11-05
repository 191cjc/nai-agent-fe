"""WebP previews of owner reference images; synthetic pixels only."""

import io

from fastapi.testclient import TestClient
from PIL import Image
from test_character_runs import ReferenceProvider, database, png  # noqa: F401
from test_generations import ORIGIN, login

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import ResultCache


def encoded(fmt: str, size=(1024, 1536)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, (200, 40, 90)).save(output, format=fmt)
    return output.getvalue()


def test_reference_thumbnail_is_small_owner_only_and_dropped_on_delete(
    database: Database,  # noqa: F811
) -> None:
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=ReferenceProvider(), result_cache=ResultCache(),
    )
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        ids = {}
        for fmt, mime in (("PNG", "image/png"), ("JPEG", "image/jpeg")):
            created = client.post("/api/reference-images", content=encoded(fmt),
                                  headers={"Content-Type": mime, **ORIGIN})
            assert created.status_code == 201
            ids[fmt] = created.json()["id"]
        for reference_id in ids.values():
            assert client.get(f"/api/reference-images/{reference_id}/thumbnail").status_code == 200
        assert len(app.state.thumbnails._entries) == 2
        for reference_id in ids.values():
            preview = client.get(f"/api/reference-images/{reference_id}/thumbnail")
            assert preview.status_code == 200
            assert preview.headers["content-type"] == "image/webp"
            assert preview.headers["cache-control"] == "no-store"
            with Image.open(io.BytesIO(preview.content)) as image:
                assert image.format == "WEBP" and image.size == (256, 384)
            full = client.get(f"/api/reference-images/{reference_id}/image")
            assert len(preview.content) < len(full.content)
        # Header-only bytes cannot be decoded: the preview is simply unavailable.
        broken = client.post("/api/reference-images", content=png(),
                             headers={"Content-Type": "image/png", **ORIGIN})
        assert client.get(
            f"/api/reference-images/{broken.json()['id']}/thumbnail",
        ).status_code == 404

        deleted = client.delete(f"/api/reference-images/{ids['JPEG']}", headers=ORIGIN)
        assert deleted.status_code == 204
        assert client.get(f"/api/reference-images/{ids['JPEG']}/thumbnail").status_code == 404
        assert not any(key[0].startswith(f"reference:{ids['JPEG']}")
                       for key in app.state.thumbnails._entries)

        login(client, database, "bob")
        assert client.get(f"/api/reference-images/{ids['PNG']}/thumbnail").status_code == 404
