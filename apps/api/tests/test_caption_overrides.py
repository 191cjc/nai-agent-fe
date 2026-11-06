"""Owner-edited training captions of training-set groups; disposable SQLite and fakes only."""

import sqlite3

from fastapi.testclient import TestClient
from test_character_runs import ReferenceProvider, database  # noqa: F401
from test_generations import INPUT, login
from test_reruns import ORIGIN, finished_run, wait

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import ResultCache


def test_caption_overrides_are_training_only_and_owner_scoped(
    database: Database,  # noqa: F811
) -> None:
    provider = ReferenceProvider()
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=provider, result_cache=ResultCache(),
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        run = finished_run(client, seed=4)
        other = finished_run(client, seed=5)
        page = client.get(f"/api/style-experiments/{run['id']}", params={"limit": 10}).json()
        first, second = page["items"][0], page["items"][1]
        assert first["caption_override"] is None
        url = f"/api/style-experiments/{run['id']}/captions"
        edits = {"items": [
            {"job_id": first["id"], "caption": "  1girl, smile  "},
            {"job_id": second["id"], "caption": "1boy"},
        ]}
        assert client.put(url, json=edits).status_code == 403  # Origin
        saved = client.put(url, json=edits, headers=ORIGIN)
        assert saved.status_code == 200 and saved.json() == {"updated": 2}
        view = client.get(f"/api/generations/{first['id']}").json()
        assert view["caption_override"] == "1girl, smile"
        assert view["parameters"] == first["parameters"]  # Generation stays frozen.
        page = client.get(f"/api/style-experiments/{run['id']}", params={"limit": 10}).json()
        assert [item["caption_override"] for item in page["items"][:2]] == ["1girl, smile", "1boy"]

        # Clearing restores the derived caption; blank text is refused.
        cleared = client.put(url, json={"items": [{"job_id": second["id"], "caption": None}]},
                             headers=ORIGIN)
        assert cleared.status_code == 200
        assert client.get(f"/api/generations/{second['id']}").json()["caption_override"] is None
        blank = client.put(url, json={"items": [{"job_id": first["id"], "caption": "  "}]},
                           headers=ORIGIN)
        assert (blank.status_code, blank.json()["code"]) == (422, "caption_blank")

        # A group of another set, or an ordinary job, rolls back the whole batch.
        foreign = client.get(f"/api/style-experiments/{other['id']}").json()["items"][0]
        ordinary = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        wait(client, f"/api/generations/{ordinary}", lambda job: job["status"] == "succeeded")
        for stranger in (foreign["id"], ordinary, "missing"):
            refused = client.put(url, headers=ORIGIN, json={"items": [
                {"job_id": second["id"], "caption": "changed"},
                {"job_id": stranger, "caption": "x"}]})
            assert refused.status_code == 404
        assert client.get(f"/api/generations/{second['id']}").json()["caption_override"] is None

        # Deleting the set removes its overrides with the groups.
        assert client.delete(f"/api/style-experiments/{run['id']}",
                             headers=ORIGIN).status_code == 200
        with sqlite3.connect(database.path) as connection:
            assert connection.execute("SELECT COUNT(*) FROM caption_overrides").fetchone() == (0,)

        login(client, database, "bob")
        assert client.put(url, json=edits, headers=ORIGIN).status_code == 404
