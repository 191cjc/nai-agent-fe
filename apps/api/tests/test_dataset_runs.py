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
        ({}, [{"id": f"i{index}", "prompt": "x"} for index in range(401)]),
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
        # Style training sets give each item its own random seed (the draft seed is ignored).
        seeds = [call.seed for call in provider.calls]
        assert all(1 <= seed <= 4294967295 for seed in seeds)
        assert len(set(seeds)) == 3 and seeds != [4294967294, 4294967295, 1]
        assert seeds == service.store.get(user, run.id).item_seeds
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


def test_item_sizes_override_the_run_canvas_and_legacy_items_keep_it(
    database: Database,  # noqa: F811
) -> None:
    user = owner(database)
    provider = ScriptedProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        tall = {"id": "tall", "prompt": "full body, standing", "width": 832, "height": 1216}
        run = service.store.create(user, dataset(items=[ITEMS[0], tall]))
        assert pump(service, user, run.id).status == "completed"
        plain, sized = provider.calls
        assert (plain.width, plain.height) == (512, 512)
        assert "width" not in plain.experiment.item.model_dump()
        assert (sized.width, sized.height) == (832, 1216)
        assert sized.experiment.item.model_dump() == tall
    finally:
        service.stop()
        manager.stop()


@pytest.mark.parametrize("item", [
    {"id": "a", "prompt": "x", "width": 832},
    {"id": "a", "prompt": "x", "width": 830, "height": 1216},
    {"id": "a", "prompt": "x", "width": 4096, "height": 1024},
])
def test_invalid_item_sizes_are_rejected(item) -> None:
    with pytest.raises(ValidationError):
        dataset(items=[item])


def test_item_sizes_follow_run_rules_for_gpt_and_img2img() -> None:
    from test_character_runs import character_run

    sized = [{"id": "a", "prompt": "full body", "width": 832, "height": 1216}]
    with pytest.raises(ValidationError):
        character_run([uuid4()], mode="img2img", items=sized)
    gpt = {"width": 1024, "height": 1024, "sampler": "gpt-image", "steps": 1, "cfg_scale": 0,
           "quality": False, "negative_prompt": ""}
    with pytest.raises(ValidationError):  # not a GPT size
        character_run([uuid4()], mode="gpt", items=sized, **gpt)
    character_run([uuid4()], mode="gpt", **gpt,
                  items=[{"id": "a", "prompt": "full body", "width": 1024, "height": 1536}])


def test_style_runs_store_random_item_seeds_and_continuations_keep_them(
    database: Database,  # noqa: F811
) -> None:
    from novelai_api.style_experiments import continuation_request

    user = owner(database)
    manager = GenerationManager(database, ScriptedProvider(), cache=ResultCache())
    service = StyleExperimentService(database, manager)
    items = [{"id": f"i-{n}", "prompt": f"1girl, item {n}"} for n in range(6)]
    first = service.store.create(user, dataset(items=items, seed=7))
    second = service.store.create(user, dataset(items=items, seed=7))
    assert first.item_seeds and second.item_seeds and first.item_seeds != second.item_seeds
    assert first.item_seeds != [7, 8, 9, 10, 11, 12]
    # Browser JSON never carries the stored seeds.
    assert "item_seeds" not in first.model_dump(mode="json")
    # An idempotent retry of the same request returns the stored run unchanged.
    retry = dataset(run_id=first.id, items=items, seed=7)
    assert service.store.create(user, retry).item_seeds == first.item_seeds
    # A continuation after item 2 keeps the original seeds of items 3..6.
    with database.connect(write=True) as connection:
        connection.execute(
            "UPDATE style_experiment_runs SET status = 'stopped', next_ordinal = '3' "
            "WHERE user_id = ? AND id = ?", (user, first.id),
        )
    stopped = service.store.get(user, first.id)
    request, _ = continuation_request(stopped, uuid4(), name=None)
    assert request.item_seeds == first.item_seeds[2:]
    assert service.store.create(user, request).item_seeds == first.item_seeds[2:]


def test_legacy_runs_without_item_seeds_keep_base_plus_n(
    database: Database,  # noqa: F811
) -> None:
    import json

    from novelai_api.style_experiments import group_parameters

    user = owner(database)
    manager = GenerationManager(database, ScriptedProvider(), cache=ResultCache())
    service = StyleExperimentService(database, manager)
    run = service.store.create(user, dataset(seed=100))
    with database.connect(write=True) as connection:
        row = connection.execute(
            "SELECT definition_json FROM style_experiment_runs WHERE id = ?", (run.id,),
        ).fetchone()
        definition = json.loads(row["definition_json"])
        definition.pop("seeds")
        connection.execute(
            "UPDATE style_experiment_runs SET definition_json = ?, next_ordinal = '2' "
            "WHERE id = ?", (json.dumps(definition), run.id),
        )
    legacy = service.store.get(user, run.id)
    assert legacy.item_seeds is None
    assert group_parameters(legacy).seed == 101
