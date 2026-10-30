"""Opt-in hidden source never reaches paid arguments; frozen old syntax stays exact."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from test_generations import INPUT, ORIGIN, FakeProvider, client_for, login, wait_finished
from test_mcp_images import CHARACTER_SCHEMA, POSITION_SCHEMA, SCHEMA, mock_mcp, provider_for
from test_prompt_sections import sections_request
from test_style_plan import axis
from test_style_runs import ScriptedProvider, owner, pump

from novelai_api.db import Database
from novelai_api.generations import GenerationManager, GenerationRequest, JobStore, ResultCache
from novelai_api.prompt_comments import compile_prompt_comments
from novelai_api.prompt_snapshots import PromptSnapshotCreate, PromptSnapshotStore
from novelai_api.style_experiments import (
    RunConflict,
    RunCreate,
    RunStore,
    StyleExperimentService,
    group_parameters,
)
from novelai_api.style_plan import ExperimentRange, create_style_plan, parse_prompt_tags


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "private" / "comments.sqlite3")
    database.migrate()
    return database


def modern(**changes) -> GenerationRequest:
    return GenerationRequest.model_validate({**INPUT, "prompt_comments": True, **changes})


def modern_sections() -> dict:
    payload = sections_request()
    payload.update(prompt_comments=True, style_prompt="artist:a\n// PRIVATE style",
                   negative_prompt="blurry\r\n\t// PRIVATE negative")
    metadata = payload["prompt_sections"]
    metadata["shared"]["scene"]["text"] = "garden\n// PRIVATE scene"
    metadata["shared"]["other"] = {"text": "sky\n// PRIVATE other", "enabled": True}
    metadata["characters"][0]["sections"]["character"] = {
        "text": "// PRIVATE first", "enabled": True,
    }
    metadata["characters"][1]["sections"]["character"]["text"] = (
        "blue hair\n// PRIVATE clothing"
    )
    metadata["characters"][1]["sections"]["action"]["text"] = "standing"
    metadata["characters"][2]["sections"]["character"]["text"] = "// PRIVATE third"
    payload["positive_prompt"] = "garden, sky"
    payload["character_prompts"] = [{"prompt": "blue hair, standing", "x": 0.7, "y": 0.3}]
    return payload


@pytest.mark.parametrize(("source", "effective"), [
    ("// hidden", ""), (" \t// hidden\r\n", ""),
    ("a\r\n// b\r\nc\r// d\re\n// f\n", "a\r\nc\re\n"),
    ("a\n// b\nc", "a\nc"), ("// a,b\nc", "c"),
    ("a, // literal\nhttps://example.test\n\\// literal",
     "a, // literal\nhttps://example.test\n\\// literal"),
    ("\u00a0// literal\n\t// hidden\n", "\u00a0// literal\n"),
    ("1.2::a,\n// hidden group line\nb::", "1.2::a,\nb::"),
    ("\n\r\n\r", "\n\r\n\r"),
])
def test_physical_line_compiler_preserves_active_bytes(source, effective):
    assert compile_prompt_comments(source) == effective
    assert compile_prompt_comments(effective) == effective


@pytest.mark.parametrize("bad", [None, 0, 1, "true", "false", [], {}])
def test_comment_mode_requires_boolean(bad):
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate({**INPUT, "prompt_comments": bad})


def test_omitted_and_false_serialization_are_legacy_identical():
    raw = {**INPUT, "positive_prompt": "// literal", "negative_prompt": "// literal negative"}
    legacy = GenerationRequest.model_validate(raw)
    explicit = GenerationRequest.model_validate({**raw, "prompt_comments": False})
    assert legacy.model_dump() == explicit.model_dump()
    assert legacy.model_dump_json() == explicit.model_dump_json()
    assert "prompt_comments" not in legacy.model_dump()
    assert "prompt_comments" not in json.loads(explicit.model_dump_json())
    assert legacy.base_prompt == "// literal"
    assert legacy.effective_negative_prompt == "// literal negative"
    assert modern().model_dump()["prompt_comments"] is True


def test_sections_compile_independently_preserving_source_and_character_order():
    payload = modern_sections()
    parameters = GenerationRequest.model_validate(payload)
    assert parameters.base_prompt == "artist:a, garden, sky"
    assert parameters.effective_negative_prompt == "blurry\r\n"
    assert [person.model_dump() for person in parameters.effective_character_prompts] == [
        {"prompt": "blue hair, standing", "x": 0.7, "y": 0.3},
    ]
    assert parameters.prompt_sections.model_dump() == payload["prompt_sections"]
    assert len(parameters.prompt_sections.characters) == 3
    assert parameters.prompt_sections.shared.scene.text.endswith("// PRIVATE scene")
    for field, changed in (("positive_prompt", "garden"), ("character_prompts", []),
                           ("prompt_comments", False)):
        with pytest.raises(ValidationError):
            GenerationRequest.model_validate({**payload, field: changed})


def test_flat_effective_people_filter_before_model_gating_without_losing_coordinates():
    parameters = modern(
        character_prompts=[{"prompt": "// hidden", "x": 0.1, "y": 0.9}],
    )
    assert parameters.effective_character_prompts == []
    assert parameters.character_prompts[0].prompt == "// hidden"
    with pytest.raises(ValidationError):
        modern(character_prompts=[{"prompt": "// hidden\nvisible"}])
    parameters = modern(model="nai-diffusion-5-full", character_prompts=[
        {"prompt": "// first", "x": 0.1, "y": 0.9},
        {"prompt": "blue hair\n// skirt", "x": 0.7, "y": 0.3},
        {"prompt": "// third", "x": 0.4, "y": 0.6},
    ])
    assert [person.model_dump() for person in parameters.effective_character_prompts] == [
        {"prompt": "blue hair\n", "x": 0.7, "y": 0.3},
    ]


def test_effective_section_projection_is_not_compiled_a_second_time():
    payload = modern_sections()
    payload["prompt_sections"]["shared"] = {
        "scene": {"text": "\u00a0// literal"}, "other": {"text": "dog"},
    }
    # NBSP is active source; section composition trims its outer whitespace.
    payload["positive_prompt"] = "// literal, dog"
    parameters = GenerationRequest.model_validate(payload)
    assert parameters.effective_positive_prompt == "// literal, dog"
    assert parameters.base_prompt == "artist:a, // literal, dog"


@pytest.mark.parametrize("change", [
    {"positive_prompt": "// shared", "style_prompt": "// style"},
    {"positive_prompt": "\t// only"},
    {"style_prompt": "//" + "x" * 2999},
    {"style_prompt": "a" * 1500, "positive_prompt": "b" * 1500},
])
def test_invalid_effective_or_raw_bounds_fail_before_seed_history_provider(database, monkeypatch,
                                                                         change):
    provider = FakeProvider()
    with client_for(database, provider) as client:
        login(client, database, "alice")
        monkeypatch.setattr("novelai_api.generations.secrets.randbelow",
                            lambda _: pytest.fail("No seed before valid effective prompts"))
        response = client.post("/api/generations", headers=ORIGIN,
                               json={**INPUT, "prompt_comments": True, **change})
        assert response.status_code == 422
        assert client.get("/api/generations").json()["items"] == []
        assert provider.calls == []


@pytest.mark.parametrize("metadata", [False, True])
@pytest.mark.parametrize("automatic", [False, True])
@pytest.mark.parametrize("all_hidden_people", [False, True])
def test_actual_mcp_arguments_exclude_hidden_source_flag_and_metadata(
    metadata, automatic, all_hidden_people,
):
    payload = modern_sections() if metadata else {
        **INPUT, "seed": 77, "prompt_comments": True, "model": "nai-diffusion-5-full",
        "style_prompt": "artist:a\n// PRIVATE style",
        "positive_prompt": "garden\n// PRIVATE shared",
        "negative_prompt": "blurry\r\n\t// PRIVATE negative",
        "character_prompts": [
            {"prompt": "// PRIVATE first", "x": 0.1, "y": 0.9},
            {"prompt": "blue hair\n// PRIVATE clothing", "x": 0.7, "y": 0.3},
        ],
    }
    payload["auto_character_position"] = automatic
    if all_hidden_people:
        if metadata:
            payload["character_prompts"] = []
            payload["prompt_sections"]["characters"][1]["sections"]["character"]["enabled"] = False
            payload["prompt_sections"]["characters"][1]["sections"]["action"]["enabled"] = False
        else:
            payload["character_prompts"][1]["prompt"] = "// PRIVATE all hidden"
    parameters = GenerationRequest.model_validate(payload)
    properties = {**SCHEMA["properties"], "character_prompts": CHARACTER_SCHEMA,
                  "auto_character_position": POSITION_SCHEMA}
    transport, calls = mock_mcp(schema=SCHEMA if all_hidden_people else {
        **SCHEMA, "properties": properties,
    })
    provider_for(transport).generate(parameters)
    paid = [call for call in calls if call["method"] == "tools/call"]
    assert len(paid) == 1
    arguments = paid[0]["params"]["arguments"]
    expected = {
        "prompt": "artist:a, garden, sky" if metadata else "artist:a, garden",
        "negative_prompt": "blurry ", "model": "nai-diffusion-5-full",
        "width": 512, "height": 512, "steps": 28, "scale": 5.0, "sampler": "fixture-sampler",
        "seed": 77, "n_samples": 2, "quality": True,
    }
    if not all_hidden_people:
        expected.update(auto_character_position=automatic, character_prompts=[{
            "prompt": "blue hair, standing" if metadata else "blue hair ",
            "negative_prompt": "", "enabled": True,
            **({} if automatic else {"x": 0.7, "y": 0.3}),
        }])
    assert arguments == expected
    assert "PRIVATE" not in json.dumps(arguments)
    assert "prompt_comments" not in arguments and "prompt_sections" not in arguments


@pytest.mark.parametrize("comments", [None, False])
@pytest.mark.parametrize("automatic", [False, True])
def test_legacy_submission_preserves_physical_newlines_and_literal_escapes(comments, automatic):
    payload = {
        **INPUT, "seed": 77, "model": "nai-diffusion-5-full",
        "positive_prompt": "garden,\r\n// literal\nhttps://example.test/a\\n",
        "negative_prompt": "bad\rworse,\nworst\\n",
        "character_prompts": [{"prompt": "blue\r\neyes,\n// literal\rsmile\\n"}],
        "auto_character_position": automatic,
    }
    if comments is not None:
        payload["prompt_comments"] = comments
    parameters = GenerationRequest.model_validate(payload)
    before = parameters.model_dump(mode="json")
    transport, calls = mock_mcp(schema={
        **SCHEMA, "properties": {
            **SCHEMA["properties"], "character_prompts": CHARACTER_SCHEMA,
            "auto_character_position": POSITION_SCHEMA,
        },
    })
    captured = []
    provider_for(transport).generate_with_request(parameters, captured.append)
    submitted = [call for call in calls if call["method"] == "tools/call"]
    assert len(submitted) == 1
    arguments = submitted[0]["params"]["arguments"]
    assert captured == [arguments]
    assert arguments["prompt"] == payload["positive_prompt"]
    assert arguments["negative_prompt"] == payload["negative_prompt"]
    assert arguments["character_prompts"][0]["prompt"] == payload["character_prompts"][0]["prompt"]
    assert parameters.model_dump(mode="json") == before


def test_comment_source_round_trips_history_snapshots_restart_and_backup(database):
    payload = modern_sections()
    with client_for(database, FakeProvider()) as client:
        _, user, _ = login(client, database, "alice")
        response = client.post("/api/generations", json=payload, headers=ORIGIN)
        assert response.status_code == 202
        job_id = response.json()["id"]
        finished = wait_finished(client, job_id)
        expected = GenerationRequest.model_validate(payload).model_dump(mode="json")
        assert finished["parameters"] == expected
        assert client.get("/api/generations").json()["items"][0]["parameters"] == expected
        snapshot = PromptSnapshotCreate(id=uuid4(), name="Hidden clothing", entries=[{
            "scope": "character", "character_index": 1, "section": "lower_clothing",
            "text": "// 1.2::red skirt::\r\nboots\r// stockings",
        }])
        saved = PromptSnapshotStore(database).create(user, snapshot)
    target = database.path.parent / "backup.sqlite3"
    database.backup(target)
    for source in (Database(database.path), Database(target)):
        assert JobStore(source).get(user, job_id).parameters.model_dump(mode="json") == expected
        assert PromptSnapshotStore(source).get(user, str(saved.id)) == saved
        with source.connect() as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 7


@pytest.mark.parametrize(("source", "expected"), [
    ("a,\n// b, c\nd", [("a", False, "1.0"), ("b", True, "1.0"),
                          ("c", True, "1.0"), ("d", False, "1.0")]),
    ("😀,\r\n\t// 1.20::blue,red::\r\\// active\nhttps://x", [
        ("😀", False, "1.0"), ("blue,red", True, "1.2"),
        ("\\// active", False, "1.0"), ("https://x", False, "1.0"),
    ]),
    ("// 1.2::blue,\n// red::\ntail", [("blue,\nred", True, None), ("tail", False, "1.0")]),
    ("1.2::blue,\nred::,tail", [("blue,\nred", False, None), ("tail", False, "1.0")]),
    ("1.2::blue,\n// red\ntail::", [("1.2::blue,\n// red\ntail::", False, None)]),
    ("a, // inline\n// // nested", [("a, // inline\n// // nested", False, None)]),
    ("// // nested\na", [("// nested", True, None), ("a", False, "1.0")]),
    ("1.2:: // literal::,a", [("1.2:: // literal::,a", False, None)]),
])
def test_comment_aware_occurrence_index_golden_vectors(source, expected):
    tags = parse_prompt_tags(source, prompt_comments=True)
    assert [(tag.text, tag.hidden, tag.weight) for tag in tags] == expected
    assert all(source[tag.start:tag.end] == tag.source for tag in tags)
    assert all(tag.weight is None for tag in tags if tag.manual_only)


@pytest.mark.parametrize(("source", "index"), [
    ("// hidden\na", 0), ("a, // inline", 0), ("(a,\nb),tail", 0),
    ("a, // literal, b", 0), ("1.2::// literal::,a", 0),
    ("1.2::a\n// b\nc::", 0),
])
def test_hidden_and_manual_only_experiment_candidates_are_rejected(source, index):
    parameters = modern(style_prompt=source)
    with pytest.raises(ValueError, match="unsupported style tag"):
        create_style_plan(parameters, [ExperimentRange(**axis(index))])


@pytest.mark.parametrize(("source", "removed", "expected"), [
    ("a\n// hidden\nb", [0], "// hidden\nb"),
    ("a\n// hidden\nb", [2], "a\n// hidden\n"),
    ("a\n// hidden\nb", [0, 2], "// hidden\n"),
    ("// hidden first\r\na,b\r// hidden last", [1, 2], "// hidden first\r\n// hidden last"),
    ("a,b\n// hidden\nc,d", [1, 3], "a\n// hidden\nd"),
    ("a\n// hidden", [0], "// hidden"),
])
def test_modern_zero_removal_preserves_all_hidden_source_and_occurrence_identity(
    source, removed, expected,
):
    parameters = modern(style_prompt=source)
    plan = create_style_plan(parameters, [ExperimentRange(**axis(index, "0", "0", "1"))
                                          for index in removed])
    rendered, weights = plan.combination(0)
    assert rendered == expected
    assert plan.max_style_length == len(expected)
    assert [weight.tag_index for weight in weights] == removed
    assert "hidden" not in compile_prompt_comments(rendered)


@pytest.mark.parametrize("shared", ["", "// hidden shared"])
def test_hidden_only_survivors_cannot_rescue_zero_plan(shared):
    parameters = modern(style_prompt="a\n// hidden", positive_prompt=shared)
    with pytest.raises(ValueError, match="remove all style tags"):
        create_style_plan(parameters, [ExperimentRange(**axis(0, "0", "1", "1"))])


def test_experiment_raw_and_effective_budgets_are_both_enforced():
    parameters = modern(style_prompt="a\n//" + "h" * 2490, positive_prompt="s" * 2490)
    plan = create_style_plan(parameters, [ExperimentRange(**axis(0, "1", "2", "1"))])
    assert plan.total == 2
    too_long = modern(style_prompt="a\n//" + "h" * 2990, positive_prompt="scene")
    with pytest.raises(ValueError, match="prompt exceeds limit"):
        create_style_plan(too_long, [ExperimentRange(**axis(0, "1000", "1000", "1"))])


@pytest.mark.parametrize("version", [None, 1, 2])
def test_old_literal_slash_run_identity_restart_and_no_ordinal_replay(database, version):
    user = owner(database)
    parameters = {**INPUT, "seed": 77, "style_prompt": "artist:a,\n// literal"}
    original = RunCreate.model_validate({"id": str(uuid4()), "parameters": parameters,
                                        "ranges": [axis(1, "0.8", "1", "0.1")]})
    store = RunStore(database)
    run = store.create(user, original)
    with database.connect(write=True) as connection:
        definition = json.loads(connection.execute(
            "SELECT definition_json FROM style_experiment_runs",
        ).fetchone()[0])
        assert "prompt_comments" not in definition["parameters"]
        definition["parameters"].pop("auto_character_position")
        if version is None:
            definition.pop("plan_version")
        else:
            definition["plan_version"] = version
        frozen = json.dumps(definition, indent=2)
        connection.execute("UPDATE style_experiment_runs SET definition_json = ?", (frozen,))
    assert store.create(user, original).parameters.prompt_comments is False
    # A new request must conflict rather than reinterpret the stored literal occurrence.
    changed = original.model_copy(deep=True)
    changed.parameters.prompt_comments = True
    changed.ranges[0].tag_index = 0
    with pytest.raises(RunConflict):
        store.create(user, changed)
    accepted = store.claim(user, run.id, "1", group_parameters(store.get(user, run.id)))
    assert JobStore(database).mark_running(accepted)
    provider = ScriptedProvider()
    manager = GenerationManager(Database(database.path), provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        ended = pump(service, user, run.id)
        assert ended.processed_count == "3" and ended.failed_count == "1"
        assert [call.experiment.ordinal for call in provider.calls] == ["2", "3"]
        assert [call.style_prompt for call in provider.calls] == [
            "artist:a,\n0.9::// literal::", "artist:a,\n// literal",
        ]
        assert all(not call.prompt_comments and call.seed == 77 for call in provider.calls)
        with database.connect() as connection:
            assert connection.execute(
                "SELECT definition_json FROM style_experiment_runs",
            ).fetchone()[0] == frozen
    finally:
        manager.stop()


def test_new_hidden_run_freezes_source_seed_and_continues_after_failure(database):
    user = owner(database)
    original = RunCreate.model_validate({
        "id": str(uuid4()),
        "parameters": modern(style_prompt="artist:a\n// hidden", seed=77).model_dump(),
        "ranges": [axis(0, "0", "1", "1")],
    })
    store = RunStore(database)
    run = store.create(user, original)
    changed = original.model_copy(deep=True)
    changed.parameters.style_prompt = "artist:a\n// changed hidden"
    with pytest.raises(RunConflict):
        store.create(user, changed)
    changed = original.model_copy(deep=True)
    changed.parameters.prompt_comments = False
    with pytest.raises(RunConflict):
        store.create(user, changed)
    provider = ScriptedProvider(["outcome_unknown", None])
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        ended = pump(service, user, run.id)
        assert ended.processed_count == "2" and ended.failed_count == "1"
        assert [call.style_prompt for call in provider.calls] == [
            "// hidden", "artist:a\n// hidden",
        ]
        assert [call.experiment.ordinal for call in provider.calls] == ["1", "2"]
        assert all(call.seed == 77 and call.prompt_comments for call in provider.calls)
        assert [call.base_prompt for call in provider.calls] == ["blue hair", "artist:a, blue hair"]
        assert store.create(user, original).status == "completed"
    finally:
        manager.stop()
