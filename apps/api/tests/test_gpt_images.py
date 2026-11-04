"""GPT image character groups: MockTransport and fakes only, never the paid relay."""

import base64
import json
import time
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_character_runs import (  # noqa: F401
    ReferenceProvider,
    database,
    owner,
    png,
    pump,
)
from test_generations import INPUT, ORIGIN, login

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.dataset_plan import DatasetRunCreate
from novelai_api.db import Database
from novelai_api.generations import (
    GenerationManager,
    GenerationRequest,
    ProviderFailure,
    ReferenceImageUse,
    ResultCache,
)
from novelai_api.gpt_images import GptImageProvider, gpt_prompt
from novelai_api.reference_images import ReferenceImageStore
from novelai_api.style_experiments import StyleExperimentService

GPT_INPUT = {
    **INPUT, "model": "gpt-image-2.5-flare", "sampler": "gpt-image", "steps": 1,
    "cfg_scale": 0, "quality": False, "negative_prompt": "", "width": 1024,
    "height": 1536, "sample_count": 1, "positive_prompt": "",
}


def gpt_run(reference_ids, **character):
    return DatasetRunCreate.model_validate({
        "id": str(uuid4()),
        "parameters": {**GPT_INPUT, "style_prompt": "anime coloring", "seed": 3},
        "items": [{"id": "sit", "prompt": "sitting, park"}, {"id": "run", "prompt": "running"}],
        "character": {"traits": "1girl, katana", "mode": "gpt",
                      "reference_ids": [str(value) for value in reference_ids], **character},
    })


def gpt_group(images=1, quality=None):
    return GenerationRequest.model_validate({
        **GPT_INPUT, "style_prompt": "watercolor", "positive_prompt": "1girl, katana, sitting",
        "experiment": {"id": str(uuid4()), "ordinal": "1", "total": "1", "kind": "dataset",
                       "item": {"id": "sit", "prompt": "sitting"}},
        "reference": {"mode": "gpt", "gpt_quality": quality, "images": [
            {"id": str(uuid4()), "sha256": f"{index:064x}"} for index in range(images)
        ]},
    })


def relay(status=200, body=None, *, images=1):
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        payload = body if body is not None else {"data": [
            {"b64_json": base64.b64encode(png()).decode()} for _ in range(images)
        ]}
        return httpx.Response(status, json=payload)

    return httpx.MockTransport(handler), calls


def test_prompt_template_separates_traits_item_and_style() -> None:
    assert gpt_prompt(gpt_group()) == "\n".join([
        "Use the attached reference image(s); they all show the same character.",
        "Draw exactly this character: keep the face, hair, eyes, outfit, accessories and "
        "weapon identical to the references.",
        "Character: 1girl, katana",
        "Scene and pose: sitting",
        "Art style: watercolor",
        "One character only. No text, no watermark, no signature.",
    ])


def test_prompt_drops_novelai_weights_for_gpt() -> None:
    group = gpt_group()
    group.style_prompt = "1.2::watercolor::, -1::monochrome::"
    group.positive_prompt = "1girl, 6::white hair::, {katana}, 1.5::sitting::"
    group.experiment.item.prompt = "1.5::sitting::"
    prompt = gpt_prompt(group)
    assert "Character: 1girl, white hair, katana" in prompt
    assert "Scene and pose: sitting" in prompt
    assert "Art style: watercolor\n" in prompt
    assert "::" not in prompt and "{" not in prompt and "monochrome" not in prompt


def test_edits_request_is_multipart_with_all_references_and_redacted_snapshot() -> None:
    transport, calls = relay()
    provider = GptImageProvider("https://relay.example/v1/", "secret-key", "gpt-image-x",
                                transport=transport)
    recorded = []
    images = provider.generate_with_request(
        gpt_group(images=2, quality="medium"), recorded.append,
        references=[png(), b"\xff\xd8jpeg-bytes"],
    )
    assert len(images) == 1 and images[0].data == png()
    request = calls[0]
    assert str(request.url) == "https://relay.example/v1/images/edits"
    assert request.headers["authorization"] == "Bearer secret-key"
    body = request.content
    assert body.count(b'name="image[]"') == 2
    for field, value in (("model", b"gpt-image-x"), ("size", b"1024x1536"), ("n", b"1"),
                         ("quality", b"medium")):
        assert f'name="{field}"'.encode() in body and value in body
    assert b"Scene and pose: sitting" in body
    snapshot = recorded[0]
    assert snapshot["provider"] == "gpt-image" and snapshot["size"] == "1024x1536"
    assert [image["byte_size"] for image in snapshot["images"]] == [
        len(png()), len(b"\xff\xd8jpeg-bytes"),
    ]
    serialized = json.dumps(snapshot)
    assert "secret-key" not in serialized and base64.b64encode(png()).decode() not in serialized
    provider.generate_with_request(gpt_group(), lambda _arguments: None, references=[png()])
    assert b'name="quality"' not in calls[1].content  # automatic quality sends nothing


@pytest.mark.parametrize(
    ("status", "body", "code"),
    [
        (400, {"error": {"code": "moderation_blocked", "message": "safety system"}},
         "content_policy"),
        (400, {"error": {"message": "invalid size"}}, "invalid_request"),
        (401, {"error": {"message": "bad key"}}, "provider_auth_error"),
        (429, {"error": {"message": "slow down"}}, "provider_rate_limited"),
        (402, {"error": {"message": "quota"}}, "insufficient_balance"),
        (502, {"error": {"message": "upstream"}}, "outcome_unknown"),
        (200, {"data": [{"b64_json": base64.b64encode(b"GIF89a").decode()}]}, "invalid_result"),
        (200, {"data": []}, "invalid_result"),
    ],
)
def test_status_mapping_and_logged_error_text(status, body, code, caplog) -> None:
    transport, _calls = relay(status, body)
    provider = GptImageProvider("https://relay.example/v1", "secret-key", "m", transport=transport)
    caplog.set_level("WARNING", logger="novelai_api.gpt_images")
    with pytest.raises(ProviderFailure) as failure:
        provider.generate_with_request(gpt_group(), lambda _arguments: None, references=[png()])
    assert failure.value.code == code
    assert "secret-key" not in caplog.text


def test_transport_failures_distinguish_unsent_from_uncertain() -> None:
    def refuse(_request):
        raise httpx.ConnectError("refused")

    def hang(_request):
        raise httpx.ReadTimeout("slow")

    for handler, code in ((refuse, "provider_unavailable"), (hang, "outcome_unknown")):
        provider = GptImageProvider("https://relay.example/v1", "k", "m",
                                    transport=httpx.MockTransport(handler))
        with pytest.raises(ProviderFailure) as failure:
            provider.generate_with_request(gpt_group(), lambda _a: None, references=[png()])
        assert failure.value.code == code


@pytest.mark.parametrize(
    "change",
    [{"sampler": "k_euler"}, {"steps": 28}, {"cfg_scale": 5}, {"quality": True},
     {"negative_prompt": "blurry"}, {"width": 832, "height": 1216}],
)
def test_gpt_groups_reject_novelai_settings(change) -> None:
    with pytest.raises(ValidationError, match="GPT"):
        GenerationRequest.model_validate({**gpt_group().model_dump(mode="json"), **change})


@pytest.mark.parametrize(
    "character",
    [{"strength": 0.5}, {"information_extracted": 0.5}, {"reference_strength": 0.5},
     {"gpt_quality": "ultra"}],
)
def test_gpt_character_definitions_reject_other_mode_settings(character) -> None:
    with pytest.raises(ValidationError):
        gpt_run([uuid4()], **character)


class GptFake(ReferenceProvider):
    pass


def test_runs_dispatch_gpt_groups_to_gpt_provider_only(database: Database) -> None:  # noqa: F811
    user = owner(database)
    store = ReferenceImageStore(database)
    images = [store.add(user, png(width=512 + 64 * index), source="upload") for index in range(2)]
    nai, gpt = ReferenceProvider(), GptFake()
    manager = GenerationManager(database, nai, cache=ResultCache(), gpt_provider=gpt)
    service = StyleExperimentService(database, manager)
    run = service.store.create(
        user, gpt_run([image.id for image in images], gpt_quality="high"),
        references=[ReferenceImageUse(id=image.id, sha256=image.sha256) for image in images],
    )
    manager.start()
    try:
        ended = pump(service, user, run.id)
    finally:
        service.stop()
        manager.stop()
    assert ended.succeeded_count == "2" and nai.calls == []
    assert [refs for _call, refs in gpt.calls] == [[png(512), png(576)]] * 2
    assert all(call.reference.gpt_quality == "high" for call, _refs in gpt.calls)
    assert [call.positive_prompt for call, _refs in gpt.calls] == [
        "1girl, katana, sitting, park", "1girl, katana, running",
    ]


def test_api_capabilities_and_unconfigured_gpt_runs(database: Database) -> None:  # noqa: F811
    for configured in (False, True):
        app = create_app(
            Settings(database.path, "https://testserver"), database,
            image_provider=ReferenceProvider(), result_cache=ResultCache(),
            gpt_image_provider=GptFake() if configured else None,
        )
        app.state.experiments._interval = 0.01
        with TestClient(app, base_url="https://testserver") as client:
            assert client.get("/api/capabilities").status_code == 401
            login(client, database, f"user-{configured}")
            capabilities = client.get("/api/capabilities").json()
            assert capabilities["gpt_image"] is configured
            reference = client.post(
                "/api/reference-images", content=png(),
                headers={**ORIGIN, "Content-Type": "image/png"},
            ).json()
            created = client.post(
                "/api/dataset-runs", json=gpt_run([reference["id"]]).model_dump(mode="json"),
                headers=ORIGIN,
            )
            if not configured:
                assert created.status_code == 503
                assert created.json()["code"] == "gpt_image_unavailable"
                continue
            assert created.status_code == 202
            run_id = created.json()["id"]
            deadline = time.monotonic() + 3
            while client.get(f"/api/style-experiment-runs/{run_id}").json()["status"] != (
                "completed"
            ):
                assert time.monotonic() < deadline
                time.sleep(0.01)


def test_settings_default_gpt_endpoint_to_relay_and_hide_key(tmp_path) -> None:
    settings = Settings(tmp_path / "x.sqlite3", "https://o.example",
                        codex_base_url="https://relay.example/v1", gpt_image_api_key="k-secret")
    assert settings.gpt_image_endpoint == "https://relay.example/v1"
    assert settings.gpt_image_model == "gpt-image-2.5-flare"
    assert "k-secret" not in repr(settings)
    with pytest.raises(ValueError):
        Settings(tmp_path / "x.sqlite3", "https://o.example", gpt_image_base_url="http://plain")
