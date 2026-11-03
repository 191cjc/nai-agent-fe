"""Precise Reference (NovelAI director reference) character runs; fakes/MockTransport only."""

import base64
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from test_character_runs import (
    BASE_FIELDS,
    ENCODE_VIBE,
    ReferenceProvider,
    character_run,
    database,  # noqa: F401
    jpeg,
    owner,
    png,
    pump,
    reference_transport,
    schema,
    tool_calls,
)
from test_generations import INPUT

from novelai_api.dataset_plan import DatasetRunCreate
from novelai_api.db import Database
from novelai_api.generations import (
    GenerationManager,
    GenerationRequest,
    ProviderFailure,
    ReferenceImageUse,
    ResultCache,
)
from novelai_api.mcp_images import PRECISE_FIELDS, NovelAiMcpProvider
from novelai_api.reference_images import ReferenceImageStore
from novelai_api.style_experiments import StyleExperimentService


def precise_run(reference_ids, model="nai-diffusion-4-5-full", **character):
    request = character_run(reference_ids, mode="vibe").model_dump(mode="json")
    request["parameters"]["model"] = model
    request["character"] = {
        "traits": "1girl, solo, silver hair", "mode": "precise",
        "reference_ids": [str(value) for value in reference_ids], **character,
    }
    return DatasetRunCreate.model_validate(request)


PRECISE_TOOLS = [
    {"name": "generate_image", "inputSchema": schema(*BASE_FIELDS, "references", *PRECISE_FIELDS)},
    ENCODE_VIBE,
]


def precise_parameters(**changes) -> GenerationRequest:
    reference = {
        "mode": "precise", "images": [{"id": str(uuid4()), "sha256": "a" * 64}],
        "precise_type": "character", "precise_strength": 0.8, "precise_fidelity": 0.75,
        **changes,
    }
    return GenerationRequest.model_validate({
        **INPUT, "model": "nai-diffusion-4-5-full", "sample_count": 1, "seed": 5,
        "reference": reference,
    })


def test_mcp_precise_reference_arguments_and_redacted_snapshot() -> None:
    transport, calls = reference_transport(PRECISE_TOOLS)
    provider = NovelAiMcpProvider("https://mcp.example/x", "token", transport=transport)
    recorded = []
    provider.generate_with_request(precise_parameters(), recorded.append, references=[png()])
    assert tool_calls(calls, "encode_vibe") == []  # no vibe encoding for precise reference
    arguments = tool_calls(calls, "generate_image")[-1]["arguments"]
    assert arguments["director_reference_images"] == [base64.b64encode(png()).decode()]
    assert arguments["director_reference_descriptions"] == [
        {"caption": {"base_caption": "character", "char_captions": []}, "legacy_uc": False},
    ]
    assert arguments["director_reference_information_extracted"] == [1.0]
    assert arguments["director_reference_strength_values"] == [0.8]
    assert arguments["director_reference_secondary_strength_values"] == [0.25]
    assert "references" not in arguments and "character_prompts" not in arguments
    assert recorded[0]["director_reference_images"] == [
        {"sha256": "a" * 64, "byte_size": len(png())},
    ]
    assert base64.b64encode(png()).decode() not in json.dumps(recorded)


def test_mcp_without_director_reference_fields_fails_before_paid_call() -> None:
    tools = [{"name": "generate_image", "inputSchema": schema(*BASE_FIELDS, "references")}]
    transport, calls = reference_transport(tools)
    provider = NovelAiMcpProvider("https://mcp.example/x", "token", transport=transport)
    with pytest.raises(ProviderFailure) as failure:
        provider.generate_with_request(precise_parameters(), lambda _a: None, references=[png()])
    assert failure.value.code == "unsupported_reference_mode"
    assert all(call["method"] != "tools/call" for call in calls)


@pytest.mark.parametrize("changes", [
    {"images": [{"id": str(uuid4()), "sha256": "a" * 64}] * 2},
    {"precise_type": None},
    {"precise_type": "pose"},
    {"precise_strength": 0},
    {"precise_fidelity": 1.5},
    {"strength": 0.5},
    {"reference_strength": 0.5},
])
def test_precise_reference_use_validation(changes) -> None:
    with pytest.raises(ValidationError):
        precise_parameters(**changes)


def test_precise_reference_requires_v45_and_is_exclusive_to_its_mode() -> None:
    with pytest.raises(ValidationError, match="V4.5"):
        GenerationRequest.model_validate({
            **precise_parameters().model_dump(mode="json"), "model": "nai-diffusion-4-full",
        })
    reference_ids = [str(uuid4())]
    assert precise_run(reference_ids).character.mode == "precise"
    with pytest.raises(ValidationError):
        precise_run(reference_ids, mode="vibe", precise_type="style")
    with pytest.raises(ValidationError):
        precise_run(reference_ids, strength=0.5, noise=0)
    with pytest.raises(ValidationError):
        precise_run(reference_ids, reference_strength=0.5)
    with pytest.raises(ValidationError, match="V4.5"):
        precise_run(reference_ids, model="nai-diffusion-5-full")


def test_precise_run_rotates_one_reference_and_freezes_defaults(
    database: Database,  # noqa: F811
) -> None:
    user = owner(database)
    store = ReferenceImageStore(database)
    first = store.add(user, png(), source="upload")
    second = store.add(user, jpeg(), source="upload")
    provider = ReferenceProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        request = precise_run(
            [first.id, second.id], precise_type="character&style", precise_fidelity=0.5,
        )
        run = service.store.create(user, request, references=[
            ReferenceImageUse(id=first.id, sha256=first.sha256),
            ReferenceImageUse(id=second.id, sha256=second.sha256),
        ])
        pump(service, user, run.id)
    finally:
        service.stop()
        manager.stop()
    uses = [call[0].reference for call in provider.calls]
    assert [use.images[0].id for use in uses] == [first.id, second.id, first.id]
    assert {(use.precise_type, use.precise_strength, use.precise_fidelity) for use in uses} == {
        ("character&style", 1.0, 0.5),
    }
    assert [data for _parameters, data in provider.calls] == [[png()], [jpeg()], [png()]]
