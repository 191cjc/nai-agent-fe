"""Fixed-style dataset runs share the durable scheduler; tests use only fakes."""

import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_generations import INPUT, ORIGIN, login
from test_style_runs import ScriptedProvider, database, owner, pump, request  # noqa: F401

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.dataset_plan import DatasetRunCreate, item_seed
from novelai_api.db import Database
from novelai_api.generations import GenerationManager, ResultCache
from novelai_api.style_experiments import MAX_ACTIVE_RUNS, RunConflict, StyleExperimentService

ITEMS = [
    {"id": "portrait-1", "prompt": "1girl, portrait, smile"},
    {"id": "full-body-2", "prompt": "1boy, full body, standing, street"},
    {"id": "scenery-3", "prompt": "no humans, scenery, mountain, sunset"},
]


def dataset(*, run_id=None, seed=None, items=ITEMS, **changes) -> DatasetRunCreate:
    parameters = {
        **INPUT, "positive_prompt": "", "style_prompt": "artist:fixture, watercolor",
        "seed": seed, **changes,
    }
    return DatasetRunCreate.model_validate({
        "id": str(run_id or uuid4()), "parameters": parameters, "items": items,
    })


def test_item_seeds_vary_and_wrap_within_provider_range() -> None:
    assert [item_seed(10, ordinal) for ordinal in (1, 2, 3)] == [10, 11, 12]
    assert item_seed(4294967295, 1) == 4294967295
    assert item_seed(4294967295, 2) == 1
    assert item_seed(4294967294, 4) == 2


@pytest.mark.parametrize(
    ("changes", "items"),
    [
        ({"positive_prompt": "shared"}, ITEMS),
        ({"style_prompt": "   "}, ITEMS),
        ({"style_prompt": "// hidden style", "prompt_comments": True}, ITEMS),
        ({"prompt_comments": True}, [{"id": "a", "prompt": "1girl\n// hidden"}]),
        ({}, [{"id": "a", "prompt": " "}]),
        ({}, [{"id": "a", "prompt": "x"}, {"id": "a", "prompt": "y"}]),
        ({}, [{"id": "Bad Id", "prompt": "x"}]),
        ({}, []),
        ({}, [{"id": f"i{index}", "prompt": "x"} for index in range(301)]),
        ({"style_prompt": "s" * 2500}, [{"id": "a", "prompt": "x" * 600}]),
        ({"model": "fixture-model", "character_prompts": [{"prompt": "c"}]}, ITEMS),
    ],
)
def test_invalid_definitions_are_rejected_before_any_state(changes, items) -> None:
    with pytest.raises(ValidationError):
        dataset(items=items, **changes)


def test_items_run_with_frozen_style_distinct_seeds_and_continue_after_failure(
    database: Database,  # noqa: F811
) -> None:
    user = owner(database)
    provider = ScriptedProvider(["outcome_unknown", None, None])
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        original = dataset(seed=4294967294)
        run = service.store.create(user, original)
        assert run.kind == "dataset" and run.total == "3" and run.ranges == []
        assert [item.id for item in run.items] == ["portrait-1", "full-body-2", "scenery-3"]
        original.parameters.style_prompt = "edited"
        ended = pump(service, user, run.id)
        assert ended.status == "completed"
        assert (ended.processed_count, ended.succeeded_count, ended.failed_count) == ("3", "2", "1")
        assert [call.positive_prompt for call in provider.calls] == [
            item["prompt"] for item in ITEMS
        ]
        assert {call.style_prompt for call in provider.calls} == {"artist:fixture, watercolor"}
        assert [call.seed for call in provider.calls] == [4294967294, 4294967295, 1]
        assert [call.experiment.item.id for call in provider.calls] == [
            item["id"] for item in ITEMS
        ]
        assert all(
            call.experiment.kind == "dataset" and call.experiment.weights == []
            for call in provider.calls
        )
        page = manager.store.experiments(user, limit=10, offset=0)
        assert [(item.id, item.kind, item.group_count) for item in page.items] == [
            (run.id, "dataset", 3),
        ]
        service.tick()
        assert len(provider.calls) == 3
    finally:
        service.stop()
        manager.stop()


def test_stop_and_restart_never_repeat_a_dataset_item(database: Database) -> None:  # noqa: F811
    user = owner(database)
    provider = ScriptedProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        run = service.store.create(user, dataset(seed=5))
        pump(service, user, run.id, terminal=False)
        assert service.store.stop(user, run.id).status == "stopping"
        ended = pump(service, user, run.id)
        assert ended.status == "stopped" and ended.processed_count == "1"
    finally:
        service.stop()
        manager.stop()
    restarted = GenerationManager(database, provider, cache=ResultCache())
    again = StyleExperimentService(database, restarted)
    try:
        again.tick()
        assert len(provider.calls) == 1
    finally:
        again.stop()
        restarted.stop()


def test_idempotency_conflicts_and_queued_runs_across_kinds(
    database: Database,  # noqa: F811
) -> None:
    user = owner(database)
    store = StyleExperimentService(
        database, GenerationManager(database, ScriptedProvider(), cache=ResultCache()),
    ).store
    run_id = uuid4()
    first = store.create(user, dataset(run_id=run_id, seed=9))
    assert store.create(user, dataset(run_id=run_id, seed=9)).id == first.id
    with pytest.raises(RunConflict) as changed:
        store.create(user, dataset(run_id=run_id, seed=9, items=ITEMS[:1]))
    assert changed.value.code == "experiment_run_conflict"
    with pytest.raises(RunConflict) as style_same_id:
        store.create(user, request(run_id=run_id))
    assert style_same_id.value.code == "experiment_run_conflict"
    # A second run of either kind queues behind the first in the NovelAI lane.
    style = store.create(user, request())
    assert (style.lane, style.queue_position) == ("novelai", 1)
    assert [run.id for run in store.queue(user)] == [first.id, style.id]
    assert store.active(user).id == first.id
    store.stop(user, first.id)
    assert store.get(user, style.id).queue_position == 0
    assert store.get(user, first.id).queue_position is None
    for _ in range(MAX_ACTIVE_RUNS - 1):
        store.create(user, dataset())
    with pytest.raises(RunConflict) as full:
        store.create(user, request())
    assert full.value.code == "experiment_run_queue_full"
    assert [run.queue_position for run in store.queue(user)] == list(range(MAX_ACTIVE_RUNS))


def test_api_create_reattach_owner_origin_and_no_ordinary_injection(
    database: Database,  # noqa: F811
) -> None:
    provider = ScriptedProvider()
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=provider, result_cache=ResultCache(),
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        payload = dataset().model_dump(mode="json")
        assert client.post("/api/dataset-runs", json=payload, headers=ORIGIN).status_code == 401
        _token, alice, _session = login(client, database, "alice")
        assert client.post("/api/dataset-runs", json=payload).status_code == 403
        invalid = {**payload, "items": []}
        assert client.post("/api/dataset-runs", json=invalid, headers=ORIGIN).status_code == 422
        created = client.post("/api/dataset-runs", json=payload, headers=ORIGIN)
        assert created.status_code == 202
        body = created.json()
        assert body["kind"] == "dataset" and body["items"] == ITEMS and body["ranges"] == []
        assert client.get("/api/style-experiment-runs/active").json()["run"]["id"] == body["id"]
        injected = {**INPUT, "experiment": {
            "id": str(uuid4()), "ordinal": "1", "total": "1", "kind": "dataset", "item": ITEMS[0],
        }}
        refused = client.post("/api/generations", json=injected, headers=ORIGIN)
        assert refused.status_code == 409 and refused.json()["code"] == "experiment_conflict"
        deadline = time.monotonic() + 3
        while app.state.experiments.store.get(alice, body["id"]).status != "completed":
            assert time.monotonic() < deadline
            time.sleep(0.01)
        saved = client.get(f"/api/style-experiments/{body['id']}", params={"limit": 3}).json()
        assert saved["summary"]["kind"] == "dataset"
        assert [item["parameters"]["experiment"]["item"] for item in saved["items"]] == ITEMS
        assert all(
            "weights" not in item["parameters"]["experiment"] or
            item["parameters"]["experiment"]["weights"] == []
            for item in saved["items"]
        )
        login(client, database, "bob")
        assert client.get(f"/api/style-experiment-runs/{body['id']}").status_code == 404


MULTI_ITEM = {
    "id": "multi-1", "prompt": "2girls, upper body, friends, classroom",
    "characters": [
        {"prompt": "girl, long hair, black hair, navy blue blazer", "x": 0.3, "y": 0.5},
        {"prompt": "girl, short hair, blonde hair, white cardigan", "x": 0.7, "y": 0.5},
    ],
}


def test_multi_person_items_send_native_characters_and_keep_legacy_items_unchanged(
    database: Database,  # noqa: F811
) -> None:
    user = owner(database)
    provider = ScriptedProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        run = service.store.create(
            user, dataset(items=[ITEMS[0], MULTI_ITEM], model="nai-diffusion-4-5-full"),
        )
        assert pump(service, user, run.id).status == "completed"
        single, multi = provider.calls
        assert single.character_prompts == [] and "characters" not in (
            single.experiment.item.model_dump()
        )
        assert multi.positive_prompt == MULTI_ITEM["prompt"]
        assert multi.auto_character_position is False
        assert [c.model_dump() for c in multi.character_prompts] == MULTI_ITEM["characters"]
        assert multi.experiment.item.model_dump() == MULTI_ITEM
    finally:
        service.stop()
        manager.stop()


@pytest.mark.parametrize(
    ("changes", "item"),
    [
        ({}, MULTI_ITEM),  # fixture-model has no native character prompts
        ({"model": "nai-diffusion-4-5-full", "prompt_comments": True},
         {**MULTI_ITEM, "characters": [{"prompt": "girl\n// hidden"}]}),
        ({"model": "nai-diffusion-4-5-full"},
         {**MULTI_ITEM, "characters": [{"prompt": "x" * 1001}]}),
        ({"model": "nai-diffusion-4-5-full"},
         {**MULTI_ITEM, "characters": [{"prompt": "girl"}] * 7}),
        ({"model": "nai-diffusion-4-5-full"}, {**MULTI_ITEM, "characters": [{"prompt": " "}]}),
    ],
)
def test_invalid_multi_person_items_are_rejected(changes, item) -> None:
    with pytest.raises(ValidationError):
        dataset(items=[item], **changes)


def test_character_runs_reject_multi_person_items() -> None:
    from test_character_runs import character_run

    with pytest.raises(ValidationError):
        character_run([uuid4()], items=[MULTI_ITEM])
