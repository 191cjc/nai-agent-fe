"""Continuing a stopped dataset run; synthetic fixtures only."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_character_runs import ReferenceProvider, character_run, database, owner, png  # noqa: F401
from test_generations import ORIGIN, login

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.generations import ReferenceImageUse, ResultCache
from novelai_api.reference_images import ReferenceImageStore
from novelai_api.style_experiments import ContinuationRefused, RunStore, group_parameters

ITEMS = [{"id": f"i{index}", "prompt": f"pose {index}"} for index in range(7)]


def stopped(database: Database, user: str, run_id: str, next_ordinal: int) -> None:  # noqa: F811
    with database.connect(write=True) as connection:
        connection.execute(
            "UPDATE style_experiment_runs SET status = 'stopped', next_ordinal = ?, "
            "processed_count = ? WHERE user_id = ? AND id = ?",
            (str(next_ordinal), str(next_ordinal - 1), user, run_id),
        )


def digest_of(images: ReferenceImageStore):
    def digest(user_id: str, reference_id: str) -> str | None:
        item = images.get(user_id, reference_id)
        return item.sha256 if item is not None else None
    return digest


def rendered(run, ordinal: int):
    state = run.model_copy(update={"next_ordinal": str(ordinal)})
    request = group_parameters(state)
    return (request.positive_prompt, request.style_prompt, request.seed,
            [image.id for image in request.reference.images])


@pytest.mark.parametrize("mode", ["img2img", "vibe"])
def test_continuation_renders_remaining_items_exactly_like_the_original(
    database: Database, mode: str,  # noqa: F811
) -> None:
    user = owner(database)
    images = ReferenceImageStore(database)
    refs = [images.add(user, png(width=512 + 64 * index), source="upload") for index in range(3)]
    store = RunStore(database)
    original = store.create(
        user, character_run([ref.id for ref in refs], mode=mode, items=ITEMS,
                            styles=["style a", "style b"], seed=4294967290),
        references=[ReferenceImageUse(id=ref.id, sha256=ref.sha256) for ref in refs],
    )
    stopped(database, user, original.id, 4)
    original = store.get(user, original.id)
    new_id = uuid4()
    follow = store.continue_run(user, original.id, new_id, digest_of(images))
    assert follow.total == "4" and follow.status == "running"
    for ordinal in range(1, 5):
        assert rendered(follow, ordinal) == rendered(original, ordinal + 3)
    # Retrying with the same new id is idempotent.
    assert store.continue_run(user, original.id, new_id, digest_of(images)).id == follow.id


def test_continuation_refusals_and_api(database: Database) -> None:  # noqa: F811
    app = create_app(
        Settings(database.path, "https://testserver"), database,
        image_provider=ReferenceProvider(), result_cache=ResultCache(),
    )
    app.state.experiments._interval = 3600
    with TestClient(app, base_url="https://testserver") as client:
        login(client, database, "alice")
        uploaded = client.post("/api/reference-images", content=png(),
                               headers={"Content-Type": "image/png", **ORIGIN}).json()
        body = character_run([uploaded["id"]], items=ITEMS).model_dump(mode="json")
        run = client.post("/api/dataset-runs", json={**body, "name": "测试集"}, headers=ORIGIN)
        run_id = run.json()["id"]
        path = f"/api/style-experiment-runs/{run_id}/continue"
        assert client.post(path, json={"id": str(uuid4())}).status_code == 403
        active = client.post(path, json={"id": str(uuid4())}, headers=ORIGIN)
        assert active.status_code == 409 and active.json()["code"] == "experiment_run_active"
        with database.connect() as connection:
            user = connection.execute(
                "SELECT user_id FROM style_experiment_runs WHERE id = ?", (run_id,),
            ).fetchone()[0]
        stopped(database, user, run_id, 3)
        created = client.post(path, json={"id": str(uuid4())}, headers=ORIGIN)
        assert created.status_code == 202 and created.json()["total"] == "5"
        queue = client.get("/api/style-experiment-runs/queue").json()["runs"]
        assert [item["name"] for item in queue] == ["测试集（续）"]
        login(client, database, "bob")
        assert client.post(path, json={"id": str(uuid4())}, headers=ORIGIN).status_code == 404

    store = RunStore(database)
    stopped(database, user, run_id, 8)
    with pytest.raises(ContinuationRefused, match="nothing_to_continue"):
        store.continue_run(user, run_id, uuid4(), lambda *_: None)
    stopped(database, user, run_id, 2)
    with pytest.raises(ContinuationRefused, match="reference_not_found"):
        store.continue_run(user, run_id, uuid4(), lambda *_: None)


def test_gpt_continuation_keeps_concurrency_and_records_current_model(
    database: Database,  # noqa: F811
) -> None:
    from test_gpt_parallel import gpt_items

    from novelai_api.dataset_plan import DatasetRunCreate

    user = owner(database)
    images = ReferenceImageStore(database)
    ref = images.add(user, png(), source="upload")
    store = RunStore(database)
    request = DatasetRunCreate.model_validate({
        **gpt_items(str(ref.id), 5).model_dump(mode="json"), "gpt_concurrency": 3,
    })
    original = store.create(
        user, request, references=[ReferenceImageUse(id=ref.id, sha256=ref.sha256)],
    )
    stopped(database, user, original.id, 3)
    follow = store.continue_run(user, original.id, uuid4(), digest_of(images),
                                gpt_model="gpt-image-2.5-flare")
    assert (follow.lane, follow.total, follow.parallelism) == ("gpt", "3", 3)
    assert follow.parameters.model == "gpt-image-2.5-flare"
