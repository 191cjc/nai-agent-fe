"""Stored recipes, the sampling API and recipe items in dataset runs (fakes only)."""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_dataset_runs import dataset
from test_generations import ORIGIN, login
from test_recipe_engine import base_recipe
from test_style_runs import ScriptedProvider, database, owner, pump  # noqa: F401

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.dataset_recipes import MAX_RECIPES
from novelai_api.db import Database
from novelai_api.generations import DatasetItem, GenerationManager, ResultCache
from novelai_api.style_experiments import StyleExperimentService


def client_for(database: Database) -> TestClient:  # noqa: F811
    return TestClient(
        create_app(Settings(database.path, "https://testserver"), database),
        base_url="https://testserver",
    )


def test_crud_owner_isolation_origin_and_optimistic_conflicts(
    database: Database,  # noqa: F811
) -> None:
    with client_for(database) as client:
        login(client, database, "alice")
        recipe_id = str(uuid4())
        url = f"/api/dataset-recipes/{recipe_id}"
        body = {"name": " 我的配方 ", "recipe": base_recipe()}
        assert client.put(url, json=body).status_code == 403  # Origin required
        saved = client.put(url, json=body, headers=ORIGIN)
        assert saved.status_code == 200
        first = saved.json()
        assert first["name"] == "我的配方" and first["recipe"]["draw_order"][0] == "scene"
        assert client.get("/api/dataset-recipes").json() == [
            {"id": recipe_id, "name": "我的配方", "updated_at": first["updated_at"]},
        ]
        stale = {**body, "expected_updated_at": first["updated_at"] - 1}
        conflict = client.put(url, json=stale, headers=ORIGIN)
        assert conflict.status_code == 409 and conflict.json()["code"] == "recipe_conflict"
        fresh = {**body, "name": "改名", "expected_updated_at": first["updated_at"]}
        second = client.put(url, json=fresh, headers=ORIGIN).json()
        assert second["name"] == "改名" and second["updated_at"] > first["updated_at"]
        assert second["created_at"] == first["created_at"]
        missing = {**body, "expected_updated_at": 5}
        assert client.put(f"/api/dataset-recipes/{uuid4()}", json=missing,
                          headers=ORIGIN).json()["code"] == "recipe_conflict"

        alice = dict(client.cookies)
        client.cookies.clear()
        login(client, database, "bob")
        assert client.get(url).status_code == 404
        assert client.get("/api/dataset-recipes").json() == []
        assert client.delete(url, headers=ORIGIN).status_code == 404
        client.cookies.clear()
        client.cookies.update(alice)
        assert client.delete(url, headers=ORIGIN).status_code == 204
        assert client.get(url).status_code == 404
        assert client.get(url).status_code == 404


def test_invalid_recipes_report_their_path(database: Database) -> None:  # noqa: F811
    with client_for(database) as client:
        login(client, database, "alice")
        bad = base_recipe()
        bad["partitions"][6]["options"][0]["when"] = {"chosen": "time.night"}
        response = client.put(f"/api/dataset-recipes/{uuid4()}",
                              json={"name": "x", "recipe": bad}, headers=ORIGIN)
        assert response.status_code == 422
        assert response.json()["code"] == "recipe_invalid"
        assert "expression.options.smile.when.chosen" in response.json()["message"]
        # Other routes keep the generic validation message.
        other = client.post("/api/generations", json={}, headers=ORIGIN)
        assert other.json() == {"code": "validation_error", "message": "Invalid request",
                                "retryable": False}


def test_recipe_limit(database: Database) -> None:  # noqa: F811
    with client_for(database) as client:
        _, user, _ = login(client, database, "alice")
        with database.connect(write=True) as connection:
            for index in range(MAX_RECIPES):
                connection.execute(
                    "INSERT INTO dataset_recipes VALUES (?, ?, 'r', '{}', 1, ?)",
                    (user, str(uuid4()), index),
                )
        response = client.put(f"/api/dataset-recipes/{uuid4()}",
                              json={"name": "x", "recipe": base_recipe()}, headers=ORIGIN)
        assert response.status_code == 409 and response.json()["code"] == "recipe_limit"


def test_sample_and_template_routes_are_offline_and_deterministic(
    database: Database,  # noqa: F811
) -> None:
    with client_for(database) as client:
        login(client, database, "alice")
        template = client.get("/api/dataset-recipes/templates/basic")
        assert template.status_code == 200
        body = {"recipe": template.json(), "n": 30, "seed": 9}
        first = client.post("/api/dataset-recipes/sample", json=body, headers=ORIGIN)
        assert first.status_code == 200
        assert first.json() == client.post("/api/dataset-recipes/sample", json=body,
                                           headers=ORIGIN).json()
        assert len(first.json()["items"]) == 30
        assert client.post("/api/dataset-recipes/sample", json={**body, "n": 401},
                           headers=ORIGIN).status_code == 422
        with database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM dataset_recipes").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM generation_jobs").fetchone()[0] == 0


RECIPE_ITEM = {
    "id": "r9-0001", "prompt": "1girl, solo, smile, blue eyes",
    "draws": [
        {"partition": "expression", "option": "smile", "label": "表情：微笑"},
        {"partition": "outfit", "option": "dress", "label": "套装：红色旗袍",
         "values": {"color": "red"}},
        {"partition": "shoes", "option": "-skip", "label": "鞋：跳过（不可见）",
         "reason": "invisible"},
        {"partition": "-rule", "option": "gentle", "label": "规则：笑容柔和化"},
    ],
    "style_edits": {"add": ["gentle smile"], "remove": ["detailed eyes"]},
    "recipe": {"id": str(uuid4()), "name": "配方"},
}


def test_recipe_items_send_resolved_style_and_keep_captions_content_only(
    database: Database,  # noqa: F811
) -> None:
    user = owner(database)
    provider = ScriptedProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        legacy = {"id": "legacy-2", "prompt": "1boy, full body"}
        request = dataset(items=[RECIPE_ITEM, legacy],
                          style_prompt="artist:fixture, detailed eyes, watercolor")
        run = service.store.create(user, request)
        assert pump(service, user, run.id).status == "completed"
        recipe_call, legacy_call = provider.calls
        assert recipe_call.style_prompt == "artist:fixture, watercolor, gentle smile"
        assert recipe_call.positive_prompt == RECIPE_ITEM["prompt"]
        assert "gentle smile" not in recipe_call.positive_prompt
        assert recipe_call.experiment.item.model_dump(mode="json") == RECIPE_ITEM
        assert legacy_call.style_prompt == "artist:fixture, detailed eyes, watercolor"
        assert legacy_call.experiment.item.model_dump() == legacy
    finally:
        service.stop()
        manager.stop()


def test_style_edits_rotate_with_the_style_pool() -> None:
    from novelai_api.dataset_plan import dataset_parameters

    request = dataset(items=[RECIPE_ITEM], style_prompt="a, detailed eyes")
    item = request.items[0]
    styles = ["a, detailed eyes", "b"]
    resolved = [
        dataset_parameters(request.parameters, item, seed=1, ordinal=ordinal,
                           styles=styles).style_prompt
        for ordinal in (1, 2)
    ]
    assert resolved == ["a, gentle smile", "b, gentle smile"]


@pytest.mark.parametrize("edits", [
    {"add": ["a, b"]}, {"add": ["{x}"]}, {"remove": ["1.2::x"]}, {"add": [" "]},
    {"add": ["x"] * 33}, {"other": []},
])
def test_invalid_style_edits_are_rejected(edits) -> None:
    with pytest.raises(ValidationError):
        dataset(items=[{**RECIPE_ITEM, "style_edits": edits}])


def test_style_edits_that_blank_the_style_are_rejected() -> None:
    item = {**RECIPE_ITEM, "style_edits": {"remove": ["watercolor", "artist:fixture"]}}
    with pytest.raises(ValidationError, match="blank style"):
        dataset(items=[item], style_prompt="artist:fixture, watercolor")


def test_character_runs_reject_style_edits() -> None:
    from test_character_runs import character_run

    with pytest.raises(ValidationError):
        character_run([uuid4()], items=[RECIPE_ITEM])


def test_invalid_draw_records_are_rejected() -> None:
    for draw in (
        {"partition": "Bad", "option": "x", "label": "l"},
        {"partition": "a", "option": "x", "label": ""},
        {"partition": "a", "option": "x", "label": "l", "values": {"c": "Red"}},
        {"partition": "a", "option": "x", "label": "l", "extra": 1},
    ):
        with pytest.raises(ValidationError):
            DatasetItem.model_validate({**RECIPE_ITEM, "draws": [draw]})


def test_old_api_style_tolerance_unknown_item_keys_are_ignored() -> None:
    # Rollback guard: an older reader ignores unknown keys; this build tolerates them too.
    stored = json.loads(json.dumps({**RECIPE_ITEM, "future_field": {"x": 1}}))
    item = DatasetItem.model_validate(stored)
    assert "future_field" not in item.model_dump()


def test_experiment_page_returns_frozen_draws_for_review_filters(
    database: Database,  # noqa: F811
) -> None:
    user = owner(database)
    provider = ScriptedProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        run = service.store.create(user, dataset(items=[RECIPE_ITEM]))
        assert pump(service, user, run.id).status == "completed"
        _summary, rows, _next = manager.store.experiment(user, run.id, limit=10, offset=0)
        item = rows[0].parameters.experiment.item
        assert item.model_dump(mode="json")["draws"] == RECIPE_ITEM["draws"]
        assert item.style_edits.add == ["gentle smile"]
    finally:
        service.stop()
        manager.stop()
