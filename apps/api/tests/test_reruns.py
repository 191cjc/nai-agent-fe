"""Owner-requested re-runs of training-set images; disposable SQLite and fakes only."""

import sqlite3
import time

from fastapi.testclient import TestClient
from test_character_runs import ReferenceProvider, database  # noqa: F401
from test_generations import INPUT, login

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import ResultCache

ORIGIN = {"Origin": "https://testserver"}


def wait(client: TestClient, url: str, done) -> dict:
    deadline = time.monotonic() + 3
    while not done(body := client.get(url).json()):
        assert time.monotonic() < deadline
        time.sleep(0.01)
    return body


def finished_run(client: TestClient, **changes) -> dict:
    from test_dataset_runs import dataset

    run = client.post("/api/dataset-runs", json=dataset(**changes).model_dump(mode="json"),
                      headers=ORIGIN).json()
    wait(client, f"/api/style-experiment-runs/{run['id']}", lambda r: r["status"] == "completed")
    return run


def test_rerun_keeps_prompt_draws_new_seed_and_joins_its_ordinal(
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
        run = finished_run(client, seed=77, sample_count=2)
        page = client.get(f"/api/style-experiments/{run['id']}", params={"limit": 10}).json()
        source = page["items"][1]
        url = f"/api/generations/{source['id']}/rerun"
        assert client.post(url, json={}).status_code == 403  # Origin required
        assert client.post(url, json={"discard_index": 2}, headers=ORIGIN).status_code == 404
        accepted = client.post(url, json={"discard_index": 1}, headers=ORIGIN)
        assert accepted.status_code == 202
        rerun = wait(client, f"/api/generations/{accepted.json()['id']}",
                     lambda job: job["status"] == "succeeded")

        parameters, original = rerun["parameters"], source["parameters"]
        assert parameters["experiment"] == {**original["experiment"], "rerun_of": source["id"]}
        assert parameters["sample_count"] == 1 and parameters["seed"] == rerun["effective_seed"]
        assert rerun["effective_seed"] != source["effective_seed"]
        assert {key: value for key, value in parameters.items()
                if key not in ("seed", "sample_count", "experiment")} == {
            key: value for key, value in original.items()
            if key not in ("seed", "sample_count", "experiment")}
        assert provider.calls[-1][0].base_prompt == provider.calls[1][0].base_prompt
        assert client.get(f"/api/generations/{source['id']}").json()["discarded_images"] == [1]

        # The re-run sits right after its ordinal; summaries still count run groups only.
        page = client.get(f"/api/style-experiments/{run['id']}", params={"limit": 10}).json()
        assert [item["id"] for item in page["items"]][1:3] == [source["id"], rerun["id"]]
        assert page["summary"]["group_count"] == 3 and page["summary"]["completed_count"] == 3
        assert page["summary"]["image_count"] == 7
        state = client.get(f"/api/style-experiment-runs/{run['id']}").json()
        assert state["processed_count"] == "3"

        # A re-run of a re-run stays on the same ordinal without a discard.
        again = client.post(f"/api/generations/{rerun['id']}/rerun", json={}, headers=ORIGIN)
        assert again.status_code == 202
        wait(client, f"/api/generations/{again.json()['id']}",
             lambda job: job["status"] == "succeeded")
        assert client.get(f"/api/generations/{rerun['id']}").json()["discarded_images"] == []

        login(client, database, "bob")
        assert client.post(url, json={}, headers=ORIGIN).status_code == 404


def test_rerun_refuses_ordinary_and_forged_groups(database: Database) -> None:  # noqa: F811
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=ReferenceProvider(), result_cache=ResultCache(),
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        ordinary = client.post("/api/generations", json=INPUT, headers=ORIGIN).json()["id"]
        wait(client, f"/api/generations/{ordinary}", lambda job: job["status"] == "succeeded")
        refused = client.post(f"/api/generations/{ordinary}/rerun", json={}, headers=ORIGIN)
        assert refused.status_code == 422 and refused.json()["code"] == "rerun_unsupported"

        run = finished_run(client)
        source = client.get(f"/api/style-experiments/{run['id']}").json()["items"][0]
        forged = {**source["parameters"], "experiment": {
            **source["parameters"]["experiment"], "rerun_of": source["id"]}}
        # Ordinary submissions can never carry re-run identity.
        assert client.post("/api/generations", json=forged, headers=ORIGIN).status_code == 409

        with sqlite3.connect(database.path) as connection:
            connection.execute("UPDATE generation_jobs SET status = 'running' WHERE id = ?",
                               (source["id"],))
        busy = client.post(f"/api/generations/{source['id']}/rerun", json={}, headers=ORIGIN)
        assert busy.status_code == 409 and busy.json()["code"] == "job_active"


def test_rerun_can_edit_prompt_and_style_and_the_caption_follows(
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
        run = finished_run(client, seed=5)
        page = client.get(f"/api/style-experiments/{run['id']}", params={"limit": 10}).json()
        source = page["items"][0]
        url = f"/api/generations/{source['id']}/rerun"
        for bad in ({"style_prompt": ""}, {"prompt": ""}, {"prompt": "x" * 1001}):
            assert client.post(url, json=bad, headers=ORIGIN).status_code == 422
        accepted = client.post(url, json={"prompt": "1girl, parted bangs", "style_prompt": "ink"},
                               headers=ORIGIN)
        assert accepted.status_code == 202
        rerun = wait(client, f"/api/generations/{accepted.json()['id']}",
                     lambda job: job["status"] == "succeeded")
        parameters = rerun["parameters"]
        assert parameters["positive_prompt"] == "1girl, parted bangs"
        assert parameters["style_prompt"] == "ink"
        assert parameters["experiment"]["item"] == {
            **source["parameters"]["experiment"]["item"], "prompt": "1girl, parted bangs"}
        assert parameters["experiment"]["rerun_of"] == source["id"]
        # The source group keeps its frozen prompt and style.
        kept = client.get(f"/api/generations/{source['id']}").json()["parameters"]
        assert kept == source["parameters"]



def test_rerun_prompt_edit_keeps_character_traits(database: Database) -> None:  # noqa: F811
    from test_character_runs import character_run, png

    provider = ReferenceProvider()
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=provider, result_cache=ResultCache(),
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        image = client.post("/api/reference-images", content=png(),
                            headers={"Content-Type": "image/png", **ORIGIN}).json()
        run = client.post("/api/dataset-runs", headers=ORIGIN, json=character_run(
            [image["id"]]).model_dump(mode="json")).json()
        wait(client, f"/api/style-experiment-runs/{run['id']}",
             lambda state: state["status"] == "completed")
        page = client.get(f"/api/style-experiments/{run['id']}", params={"limit": 10}).json()
        source = page["items"][0]
        accepted = client.post(f"/api/generations/{source['id']}/rerun",
                               json={"prompt": "full body, floating"}, headers=ORIGIN)
        assert accepted.status_code == 202
        rerun = client.get(f"/api/generations/{accepted.json()['id']}").json()
        assert rerun["parameters"]["positive_prompt"] == (
            "1girl, solo, silver hair, red eyes, full body, floating")
        assert rerun["parameters"]["experiment"]["item"]["prompt"] == "full body, floating"
        assert rerun["parameters"]["reference"] == source["parameters"]["reference"]
