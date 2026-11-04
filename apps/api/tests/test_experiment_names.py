"""Training-set display names and style/character type; fakes only, no paid calls."""

import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_character_runs import ReferenceProvider, character_run, png
from test_character_runs import pump as pump_character
from test_dataset_runs import dataset
from test_generations import ORIGIN, login
from test_style_runs import ScriptedProvider, database, owner, pump  # noqa: F401

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.dataset_plan import DatasetRunCreate
from novelai_api.db import Database
from novelai_api.generations import (
    ExperimentRename,
    GenerationManager,
    JobStore,
    ReferenceImageUse,
    ResultCache,
)
from novelai_api.reference_images import ReferenceImageStore
from novelai_api.style_experiments import StyleExperimentService


def summaries(db: Database, user: str) -> dict[str, dict]:
    page = JobStore(db).experiments(user, limit=100, offset=0)
    return {item.id: item.model_dump() for item in page.items}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, None), ("", None), ("   ", None), ("  风格\t A \n", "风格 A"), ("x" * 80, "x" * 80)],
)
def test_name_normalization(raw, expected) -> None:
    assert ExperimentRename(name=raw).name == expected


@pytest.mark.parametrize("raw", ["x" * 81, "bad\x00name", "zero​width"])
def test_invalid_names_are_rejected(raw) -> None:
    with pytest.raises(ValidationError):
        ExperimentRename(name=raw)
    with pytest.raises(ValidationError):
        DatasetRunCreate.model_validate({**dataset().model_dump(mode="json"), "name": raw})


def test_named_style_and_character_sets_report_type_and_rename(
    database: Database,  # noqa: F811
) -> None:
    user = owner(database)
    references = ReferenceImageStore(database)
    image = references.add(user, png(), source="upload")
    manager = GenerationManager(database, ReferenceProvider(), cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        style_payload = {**dataset().model_dump(mode="json"), "name": "  水彩  画风 "}
        style_run = service.store.create(user, DatasetRunCreate.model_validate(style_payload))
        pump(service, user, style_run.id)
        character = character_run([image.id])
        character_run_state = service.store.create(user, character, references=[
            ReferenceImageUse(id=image.id, sha256=image.sha256),
        ])
        pump_character(service, user, character_run_state.id)
    finally:
        service.stop()
        manager.stop()
    saved = summaries(database, user)
    assert saved[style_run.id]["name"] == "水彩 画风"
    assert saved[style_run.id]["dataset_type"] == "style"
    assert saved[character_run_state.id]["name"] is None
    assert saved[character_run_state.id]["dataset_type"] == "character"
    # A retry of the same definition keeps the original name and identity.
    assert service.store.create(
        user, DatasetRunCreate.model_validate({**style_payload, "name": "other"}),
    ).id == style_run.id
    assert summaries(database, user)[style_run.id]["name"] == "水彩 画风"

    store = JobStore(database)
    assert store.rename_experiment(user, character_run_state.id, "角色 A")
    assert store.rename_experiment(user, style_run.id, None)
    saved = summaries(database, user)
    assert saved[character_run_state.id]["name"] == "角色 A"
    assert saved[style_run.id]["name"] is None
    assert not store.rename_experiment(user, str(uuid4()), "missing")
    assert not store.rename_experiment(owner(database, "bob"), style_run.id, "stolen")


def test_rename_api_owner_origin_and_validation(database: Database) -> None:  # noqa: F811
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=ScriptedProvider(), result_cache=ResultCache(),
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        _token, alice, _session = login(client, database, "alice")
        payload = {**dataset().model_dump(mode="json"), "name": "第一组"}
        run_id = client.post("/api/dataset-runs", json=payload, headers=ORIGIN).json()["id"]
        deadline = time.monotonic() + 3
        while app.state.experiments.store.get(alice, run_id).status != "completed":
            assert time.monotonic() < deadline
            time.sleep(0.01)
        listed = client.get("/api/style-experiments").json()["items"][0]
        assert (listed["name"], listed["dataset_type"]) == ("第一组", "style")
        url = f"/api/style-experiments/{run_id}/name"
        assert client.put(url, json={"name": "新名字"}).status_code == 403
        assert client.put(url, json={"name": "x" * 81}, headers=ORIGIN).status_code == 422
        assert client.put(url, json={"name": "新名字"}, headers=ORIGIN).status_code == 204
        detail = client.get(f"/api/style-experiments/{run_id}").json()["summary"]
        assert detail["name"] == "新名字"
        missing = f"/api/style-experiments/{uuid4()}/name"
        assert client.put(missing, json={"name": "x"}, headers=ORIGIN).status_code == 404
        login(client, database, "bob")
        assert client.put(url, json={"name": "bob"}, headers=ORIGIN).status_code == 404
