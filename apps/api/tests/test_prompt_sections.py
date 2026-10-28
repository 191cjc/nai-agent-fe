"""Section metadata stays private while effective provider inputs remain exact."""

import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from test_generations import INPUT, ORIGIN, FakeProvider, client_for, login, wait_finished
from test_style_runs import ScriptedProvider, owner, pump

from novelai_api.db import Database
from novelai_api.generations import GenerationManager, GenerationRequest, JobStore, ResultCache
from novelai_api.prompt_sections import CharacterSections, PromptSections
from novelai_api.style_experiments import (
    RunConflict,
    RunCreate,
    RunStore,
    StyleExperimentService,
    group_parameters,
)


def sections_request(*, all_hidden=False, automatic=False, hide_whole_characters=False) -> dict:
    def character(text: str, *, hidden=False, x=0.5, y=0.5):
        sections = {key: {"text": "", "enabled": True} for key in CharacterSections.model_fields}
        sections["character"] = {"text": text, "enabled": not hidden}
        sections["special"] = {"text": "PRIVATE hidden special", "enabled": False}
        return {"sections": sections, "x": x, "y": y}

    metadata = {
        "version": 1,
        "shared": {
            "scene": {"text": "  garden  ", "enabled": True},
            "other": {"text": "PRIVATE hidden shared", "enabled": False},
        },
        "characters": [
            character("PRIVATE hidden first", hidden=True, x=0.1, y=0.9),
            character("  blue hair  ", hidden=all_hidden, x=0.7, y=0.3),
            character("", x=0.4, y=0.6),
        ],
    }
    if hide_whole_characters:
        metadata["characters"][0]["enabled"] = False
        metadata["characters"][0]["sections"]["character"]["enabled"] = True
        if all_hidden:
            metadata["characters"][1]["enabled"] = False
            metadata["characters"][1]["sections"]["character"]["enabled"] = True
    return {
        **INPUT,
        "seed": 77,
        "style_prompt": "artist:fixture",
        "positive_prompt": "  garden  ",
        "model": "nai-diffusion-5-full",
        "auto_character_position": automatic,
        "prompt_sections": metadata,
        "character_prompts": []
        if all_hidden
        else [
            {"prompt": "  blue hair  ", "x": 0.7, "y": 0.3},
        ],
    }


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "private" / "sections.sqlite3")
    database.migrate()
    return database


def test_absent_metadata_preserves_legacy_dump_and_both_none_serializers():
    legacy = GenerationRequest(**INPUT)
    explicit = GenerationRequest(**INPUT, prompt_sections=None)
    assert "prompt_sections" not in legacy.model_dump(mode="json")
    assert "prompt_sections" not in json.loads(explicit.model_dump_json())
    assert explicit.model_dump_json() == legacy.model_dump_json()
    assert legacy.positive_prompt == INPUT["positive_prompt"]
    with pytest.raises(ValidationError):
        GenerationRequest(**{**INPUT, "character_prompts": [{"prompt": " "}]})


def test_fixed_order_one_part_raw_and_hidden_character_positions_are_lossless():
    payload = sections_request()
    request = GenerationRequest.model_validate(payload)
    assert request.model_dump(mode="json")["prompt_sections"] == payload["prompt_sections"]
    metadata = payload["prompt_sections"]
    metadata["shared"]["other"] = {"text": "  sunset ", "enabled": True}
    sections = metadata["characters"][1]["sections"]
    for key, text in zip(
        CharacterSections.model_fields,
        (
            " person ",
            " shirt ",
            " skirt ",
            " sitting ",
            " smile ",
            " glowing ",
            " rest ",
        ),
        strict=True,
    ):
        sections[key] = {"text": text, "enabled": True}
    payload["positive_prompt"] = "garden, sunset"
    payload["character_prompts"][0]["prompt"] = (
        "person, shirt, skirt, sitting, smile, glowing, rest"
    )
    assert GenerationRequest.model_validate(payload).prompt_sections.shared.compose() == (
        "garden, sunset"
    )


def test_character_visibility_preserves_sections_coordinates_and_legacy_serialization():
    payload = sections_request()
    original = copy.deepcopy(payload)
    payload["prompt_sections"]["characters"][1]["enabled"] = False
    payload["character_prompts"] = []
    hidden = GenerationRequest.model_validate(payload)
    assert hidden.character_prompts == []
    assert hidden.model_dump(mode="json")["prompt_sections"] == payload["prompt_sections"]
    assert json.loads(hidden.model_dump_json())["prompt_sections"] == payload["prompt_sections"]
    # Re-enable the person without changing the independent section switches or axes.
    restored_payload = hidden.model_dump(mode="json")
    restored_payload["prompt_sections"]["characters"][1]["enabled"] = True
    restored_payload["character_prompts"] = original["character_prompts"]
    restored = GenerationRequest.model_validate(restored_payload)
    assert restored.prompt_sections.characters[1].enabled is True
    original_request = GenerationRequest.model_validate(original)
    assert restored.model_dump(mode="json") == original_request.model_dump(mode="json")
    assert all(
        "enabled" not in person for person in restored.prompt_sections.model_dump()["characters"]
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(positive_prompt="garden"),
        lambda p: p.update(character_prompts=[]),
        lambda p: p["character_prompts"][0].update(prompt="blue hair"),
        lambda p: p["character_prompts"][0].update(x=0.5),
        lambda p: p["prompt_sections"]["characters"][1].update(enabled=False),
        lambda p: p["prompt_sections"]["characters"][0]["sections"]["character"].update(
            enabled=True
        ),
        lambda p: p["prompt_sections"]["shared"]["scene"].update(enabled=False),
        lambda p: p["prompt_sections"]["characters"].reverse(),
    ],
)
def test_metadata_projection_mismatch_is_rejected(change):
    payload = sections_request()
    # A second visible person makes reversing the metadata order a real mismatch.
    payload["prompt_sections"]["characters"][2]["sections"]["tags"]["text"] = "second"
    payload["character_prompts"].append({"prompt": "second", "x": 0.4, "y": 0.6})
    change(payload)
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(payload)


@pytest.mark.parametrize("bad", [None, 0, 1, "true", [], {}])
@pytest.mark.parametrize("scope", ["section", "character"])
def test_enabled_is_a_strict_boolean_even_when_hidden(bad, scope):
    payload = sections_request()
    target = (
        payload["prompt_sections"]["shared"]["other"]
        if scope == "section" else payload["prompt_sections"]["characters"][0]
    )
    target["enabled"] = bad
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(payload)


@pytest.mark.parametrize("bad", [None, True, "0.5", float("inf"), float("nan"), 0.09, 0.91])
@pytest.mark.parametrize("axis", ["x", "y"])
def test_hidden_coordinates_remain_strict_finite_and_bounded(axis, bad):
    payload = sections_request()
    payload["prompt_sections"]["characters"][0][axis] = bad
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(payload)


@pytest.mark.parametrize(
    "change",
    [
        lambda m: m.update(version=2),
        lambda m: m.update(version=True),
        lambda m: m.update(version=1.0),
        lambda m: m.update(version="1"),
        lambda m: m.update(id="draft-id"),
        lambda m: m["shared"].update(extra={"text": ""}),
        lambda m: m["shared"]["scene"].update(id="draft-id"),
        lambda m: m["shared"].pop("scene"),
        lambda m: m["characters"][0].update(id="draft-id"),
        lambda m: m["characters"][0]["sections"].update(extra={"text": ""}),
        lambda m: m["shared"]["other"].update(text="x" * 3001),
        lambda m: m["characters"][0]["sections"]["other"].update(text="x" * 3001),
        lambda m: m.update(characters=m["characters"] * 3),
    ],
)
def test_metadata_schema_rejects_unknown_fields_missing_sections_and_hidden_overflow(change):
    payload = sections_request()
    change(payload["prompt_sections"])
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(payload)


def test_effective_limits_and_native_model_rules_remain_authoritative():
    payload = sections_request(all_hidden=True)
    payload["model"] = "fixture-model"
    assert GenerationRequest.model_validate(payload).character_prompts == []
    payload = sections_request()
    payload["model"] = "fixture-model"
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(payload)
    payload = sections_request()
    payload["prompt_sections"]["shared"] = {
        "scene": {"text": "x" * 2000},
        "other": {"text": "y" * 2000},
    }
    payload["positive_prompt"] = "x" * 2000 + ", " + "y" * 2000
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(payload)
    payload = sections_request()
    payload["prompt_sections"]["characters"][1]["sections"]["character"]["text"] = "x" * 3000
    payload["prompt_sections"]["characters"][1]["sections"]["other"]["text"] = "extra"
    payload["character_prompts"][0]["prompt"] = "x" * 3000 + ", extra"
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(payload)


def test_defaults_and_empty_projection_do_not_discard_draft_metadata():
    metadata = sections_request(all_hidden=True)["prompt_sections"]
    metadata["shared"]["scene"] = {"text": " "}
    metadata["characters"][0].pop("x")
    metadata["characters"][0].pop("y")
    result = PromptSections.model_validate(metadata)
    assert result.shared.scene.enabled is True
    assert result.shared.compose() == ""
    assert result.effective_characters() == []
    assert result.characters[0].x == result.characters[0].y == 0.5
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(
            {
                **sections_request(),
                "positive_prompt": "",
                "style_prompt": "",
                "character_prompts": [],
                "prompt_sections": result.model_dump(),
            }
        )


def test_api_rejects_mismatch_before_seed_history_and_provider(database, monkeypatch):
    provider = FakeProvider()
    with client_for(database, provider) as client:
        login(client, database, "alice")
        monkeypatch.setattr(
            "novelai_api.generations.secrets.randbelow",
            lambda _: pytest.fail("Invalid metadata must not assign a seed"),
        )
        payload = sections_request()
        payload.update(positive_prompt="changed", seed=None)
        response = client.post("/api/generations", json=payload, headers=ORIGIN)
        assert response.status_code == 422
        assert response.json() == {
            "code": "validation_error",
            "message": "Invalid request",
            "retryable": False,
        }
        assert client.get("/api/generations").json()["items"] == []
        assert provider.calls == []


def test_hidden_shared_text_cannot_rescue_an_all_zero_style_plan(database, monkeypatch):
    provider = FakeProvider()
    with client_for(database, provider) as client:
        login(client, database, "alice")
        monkeypatch.setattr(
            "novelai_api.style_experiments.secrets.randbelow",
            lambda _: pytest.fail("Invalid plan must not assign a seed"),
        )
        payload = sections_request(all_hidden=True)
        payload.update(positive_prompt="", seed=None)
        payload["prompt_sections"]["shared"]["scene"]["enabled"] = False
        response = client.post(
            "/api/style-experiment-runs",
            json={
                "id": str(uuid4()),
                "parameters": payload,
                "ranges": [{"tag_index": 0, "min": "0", "max": "1", "step": "1"}],
            },
            headers=ORIGIN,
        )
        assert response.status_code == 422
        assert client.get("/api/style-experiment-runs/active").json() == {"run": None}
        assert client.get("/api/generations").json()["items"] == []
        assert provider.calls == []


@pytest.mark.parametrize("all_hidden", [False, True])
@pytest.mark.parametrize("automatic", [False, True])
@pytest.mark.parametrize("hide_whole_characters", [False, True])
def test_full_metadata_history_restart_and_online_backup(
    database, all_hidden, automatic, hide_whole_characters,
):
    payload = sections_request(
        all_hidden=all_hidden, automatic=automatic, hide_whole_characters=hide_whole_characters,
    )
    expected = copy.deepcopy(payload["prompt_sections"])
    with client_for(database, FakeProvider()) as client:
        _, user, _ = login(client, database, "alice")
        accepted = client.post("/api/generations", json=payload, headers=ORIGIN)
        assert accepted.status_code == 202
        job_id = accepted.json()["id"]
        finished = wait_finished(client, job_id)
        assert finished["parameters"]["prompt_sections"] == expected
        assert (
            client.get("/api/generations").json()["items"][0]["parameters"]["prompt_sections"]
            == expected
        )
    target = database.path.parent / "backup.sqlite3"
    database.backup(target)
    for source in (Database(database.path), Database(target)):
        saved = JobStore(source).get(user, job_id)
        assert saved.parameters.prompt_sections.model_dump() == expected
        assert saved.parameters.auto_character_position is automatic
        assert len(saved.parameters.character_prompts) == (0 if all_hidden else 1)
        with source.connect() as connection:
            raw = connection.execute(
                "SELECT settings_json FROM generation_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()[0]
            assert json.loads(raw)["prompt_sections"] == expected


@pytest.mark.parametrize("automatic", [False, True])
@pytest.mark.parametrize("seed", [None, 77])
@pytest.mark.parametrize("hide_whole_characters", [False, True])
def test_frozen_run_metadata_idempotency_group_history_restart_and_backup(
    database, automatic, seed, hide_whole_characters,
):
    user = owner(database)
    definition = RunCreate.model_validate(
        {
            "id": str(uuid4()),
            "parameters": {
                **sections_request(
                    automatic=automatic, hide_whole_characters=hide_whole_characters,
                ),
                "seed": seed,
            },
            "ranges": [{"tag_index": 0, "min": "0.9", "max": "1.1", "step": "0.1"}],
        }
    )
    expected = definition.parameters.prompt_sections.model_dump()
    retry = definition.model_copy(deep=True)
    store = RunStore(database)
    run = store.create(user, definition)
    first = group_parameters(run)
    assert first.prompt_sections.model_dump() == expected
    assert first.auto_character_position is automatic
    assert first.seed == run.seed and (seed is None or first.seed == seed)
    definition.parameters.prompt_sections.characters[0].sections.character.text = "later draft edit"
    assert store.get(user, run.id).parameters.prompt_sections.model_dump() == expected
    assert store.create(user, retry).id == run.id
    with pytest.raises(RunConflict, match="experiment_run_conflict"):
        store.create(user, definition)
    # The empty third card still changes frozen identity when hidden as a whole.
    changed_visibility = retry.model_copy(deep=True)
    changed_visibility.parameters.prompt_sections.characters[2].enabled = False
    with pytest.raises(RunConflict, match="experiment_run_conflict"):
        store.create(user, changed_visibility)
    for section, field, value in (
        ("tags", "enabled", False),
        ("special", "text", "private later text"),
    ):
        changed = retry.model_copy(deep=True)
        setattr(getattr(changed.parameters.prompt_sections.characters[0].sections, section),
                field, value)
        # These changes leave every effective provider field unchanged.
        changed.parameters = GenerationRequest.model_validate(changed.parameters.model_dump())
        with pytest.raises(RunConflict, match="experiment_run_conflict"):
            store.create(user, changed)
    with database.connect() as connection:
        raw = connection.execute("SELECT definition_json FROM style_experiment_runs").fetchone()[0]
    # Persist an accepted first group, then recover it as unknown after process restart.
    job_id = store.claim(user, run.id, "1", first)
    provider = ScriptedProvider()
    manager = GenerationManager(Database(database.path), provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        ended = pump(service, user, run.id)
        assert ended.processed_count == "3"
        assert [call.experiment.ordinal for call in provider.calls] == ["2", "3"]
        assert all(call.prompt_sections.model_dump() == expected for call in provider.calls)
        assert all(call.auto_character_position is automatic for call in provider.calls)
        assert all(call.seed == run.seed for call in provider.calls)
        jobs = JobStore(database).list(user, limit=20, offset=0).items
        assert len(jobs) == 3 and job_id in {job.id for job in jobs}
        assert all(job.parameters.prompt_sections.model_dump() == expected for job in jobs)
        assert all(job.effective_seed == run.seed for job in jobs)
        assert store.create(user, retry).model_dump() == ended.model_dump()
        with database.connect() as connection:
            assert (
                connection.execute(
                    "SELECT definition_json FROM style_experiment_runs",
                ).fetchone()[0]
                == raw
            )
    finally:
        manager.stop()
    target = database.path.parent / "run-backup.sqlite3"
    database.backup(target)
    restored = RunStore(Database(target)).get(user, run.id)
    assert restored.parameters.prompt_sections.model_dump() == expected
    assert restored.parameters.auto_character_position is automatic
    assert restored.seed == run.seed
