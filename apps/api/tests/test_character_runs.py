"""Character dataset runs, reference images and trait advice; fakes and MockTransport only."""

import base64
import hashlib
import json
import os
import stat
import struct
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_generations import INPUT, ORIGIN, login

from novelai_api.app import create_app
from novelai_api.config import Settings
from novelai_api.dataset_plan import DatasetRunCreate
from novelai_api.db import Database
from novelai_api.generations import (
    GeneratedImage,
    GenerationManager,
    GenerationRequest,
    ReferenceImageUse,
    ResultCache,
)
from novelai_api.mcp_images import NovelAiMcpProvider
from novelai_api.reference_images import (
    MAX_REFERENCES_PER_OWNER,
    ReferenceFailure,
    ReferenceImageStore,
    inspect_image,
)
from novelai_api.style_experiments import RunConflict, StyleExperimentService

PNG_TRAILER = b"\x00\x00\x00\x00IEND\xaeB`\x82"


def png(width=512, height=768, payload=b"") -> bytes:
    """Header-valid PNG; the store validates headers only and never decodes pixels."""
    header = struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00"
    return (
        b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + header + b"\x00" * 4 + payload
        + PNG_TRAILER
    )


def jpeg(width=640, height=480) -> bytes:
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = b"\xff\xc0\x00\x11\x08" + struct.pack(">HH", height, width) + b"\x03" + b"\x00" * 9
    return b"\xff\xd8" + app0 + sof + b"\xff\xda\x00\x02" + b"\x00" * 8 + b"\xff\xd9"


class ReferenceProvider:
    """Records exactly what a reference-capable provider receives."""

    def __init__(self):
        self.calls = []

    def generate(self, parameters):
        raise AssertionError("reference groups must use generate_with_request")

    def generate_with_request(self, parameters, record_request, *, references=(), vibe_tokens=None):
        self.calls.append((parameters, list(references)))
        record_request({"prompt": parameters.base_prompt, "references": len(references)})
        return [GeneratedImage(png(), "image/png")] * parameters.sample_count


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "state" / "character.sqlite3")
    database.migrate()
    return database


def owner(database: Database, label="alice") -> str:
    from novelai_api.auth import create_token

    token_id, _token = create_token(database, label)
    with database.connect() as connection:
        return connection.execute(
            "SELECT user_id FROM access_tokens WHERE id = ?", (token_id,),
        ).fetchone()[0]


def character_run(reference_ids, *, mode="vibe", items=None, styles=None, seed=10, **changes):
    parameters = {
        **INPUT, "model": "nai-diffusion-4-5-full", "positive_prompt": "",
        "style_prompt": (styles or ["watercolor"])[0], "seed": seed, "sample_count": 1, **changes,
    }
    character = {"traits": "1girl, solo, silver hair, red eyes", "mode": mode,
                 "reference_ids": [str(value) for value in reference_ids]}
    if mode == "img2img":
        character.update(strength=0.55, noise=0.1)
    return DatasetRunCreate.model_validate({
        "id": str(uuid4()), "parameters": parameters, "styles": styles,
        "items": items or [
            {"id": "smile", "prompt": "portrait, smile"},
            {"id": "run", "prompt": "full body, running"},
            {"id": "sit", "prompt": "sitting, cafe"},
        ],
        "character": character,
    })


def pump(service, user, run_id):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        service.tick()
        state = service.store.get(user, run_id)
        if state.status in ("completed", "stopped"):
            return state
        time.sleep(0.005)
    pytest.fail("character run did not finish")


def test_header_validation_accepts_png_and_jpeg_and_rejects_others() -> None:
    assert inspect_image(png(512, 768)) == ("image/png", 512, 768)
    assert inspect_image(jpeg(640, 480)) == ("image/jpeg", 640, 480)
    for data in (b"GIF89a" + b"\x00" * 64, png(32, 512), png(512, 4096), b""):
        with pytest.raises(ReferenceFailure):
            inspect_image(data)
    with pytest.raises(ReferenceFailure) as large:
        inspect_image(png(payload=b"\x00" * (8 * 1024 * 1024)))
    assert large.value.code == "reference_too_large"


def test_store_keeps_private_files_quota_owner_isolation_and_in_use_guard(
    database: Database,
) -> None:
    alice, bob = owner(database), owner(database, "bob")
    store = ReferenceImageStore(database)
    image = store.add(alice, png(), source="upload")
    assert image.sha256 == hashlib.sha256(png()).hexdigest()
    path = store.path / alice / image.id
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE((store.path / alice).stat().st_mode) == 0o700
    with database.connect() as connection:
        assert png() not in b"".join(
            bytes(str(tuple(row)), "utf-8") for row in connection.execute(
                "SELECT * FROM reference_images",
            )
        )
    assert store.read(alice, image.id)[1] == png()
    assert store.read(bob, image.id) is None and store.list(bob) == []
    assert store.delete(bob, image.id) is False
    for _index in range(MAX_REFERENCES_PER_OWNER - 1):
        store.add(alice, png(), source="upload")
    with pytest.raises(ReferenceFailure) as quota:
        store.add(alice, png(), source="upload")
    assert quota.value.code == "reference_quota_exceeded"
    assert len(list((store.path / alice).iterdir())) == MAX_REFERENCES_PER_OWNER
    path.write_bytes(png(width=600))
    assert store.read(alice, image.id) is None  # changed bytes never match the digest

    service = StyleExperimentService(
        database, GenerationManager(database, ReferenceProvider(), cache=ResultCache()),
    )
    other = store.list(alice)[1]
    run = service.store.create(
        alice, character_run([other.id]),
        references=[ReferenceImageUse(id=other.id, sha256=other.sha256)],
    )
    with pytest.raises(ReferenceFailure) as in_use:
        store.delete(alice, other.id)
    assert in_use.value.code == "reference_in_use"
    service.store.stop(alice, run.id)
    assert store.delete(alice, other.id) is True
    assert not (store.path / alice / other.id).exists()


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"model": "nai-diffusion-5-full"}, "V4 or V4.5"),
        ({"mode": "img2img", "strength": None}, "strength"),
        ({"mode": "vibe", "strength": 0.4}, "strength"),
        ({"traits": "   "}, "traits"),
        ({"traits": "// hidden"}, "traits"),
        ({"reference_ids": []}, "reference_ids"),
        ({"duplicate": True}, "Duplicate"),
        ({"styles": ["other", "x"]}, "first pooled style"),
    ],
)
def test_character_definition_validation(change, fragment) -> None:
    reference = uuid4()
    payload = character_run([reference]).model_dump(mode="json")
    if "model" in change:
        payload["parameters"]["model"] = change["model"]
    if "styles" in change:
        payload["styles"] = change["styles"]
    if change.get("duplicate"):
        payload["character"]["reference_ids"] = [str(reference), str(reference)]
    for key in ("mode", "strength", "traits", "reference_ids"):
        if key in change:
            payload["character"][key] = change[key]
    if change.get("mode") == "img2img":
        payload["character"]["noise"] = 0
    with pytest.raises(ValidationError, match=fragment):
        DatasetRunCreate.model_validate(payload)


def test_vibe_run_sends_all_references_rotates_styles_and_composes_traits(
    database: Database,
) -> None:
    user = owner(database)
    store = ReferenceImageStore(database)
    images = [store.add(user, png(width=512 + 64 * index), source="upload") for index in range(2)]
    provider = ReferenceProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        request = character_run([image.id for image in images], styles=["watercolor", "sketch"])
        run = service.store.create(user, request, references=[
            ReferenceImageUse(id=image.id, sha256=image.sha256) for image in images
        ])
        assert run.character.references[0].sha256 == images[0].sha256
        ended = pump(service, user, run.id)
    finally:
        service.stop()
        manager.stop()
    assert ended.status == "completed" and ended.succeeded_count == "3"
    assert [call.style_prompt for call, _refs in provider.calls] == [
        "watercolor", "sketch", "watercolor",
    ]
    assert [call.positive_prompt for call, _refs in provider.calls] == [
        "1girl, solo, silver hair, red eyes, portrait, smile",
        "1girl, solo, silver hair, red eyes, full body, running",
        "1girl, solo, silver hair, red eyes, sitting, cafe",
    ]
    assert [call.seed for call, _refs in provider.calls] == [10, 11, 12]
    assert all(call.reference.mode == "vibe" for call, _refs in provider.calls)
    assert all(refs == [png(512), png(576)] for _call, refs in provider.calls)
    assert all(call.experiment.item.prompt in call.positive_prompt for call, _ in provider.calls)
    with database.connect() as connection:
        stored = " ".join(row[0] for row in connection.execute(
            "SELECT settings_json || COALESCE(provider_request_json, '') FROM generation_jobs",
        ))
    assert base64.b64encode(png()).decode() not in stored


def test_img2img_rotates_one_reference_and_changed_bytes_fail_only_that_group(
    database: Database,
) -> None:
    user = owner(database)
    store = ReferenceImageStore(database)
    images = [store.add(user, png(width=512 + 64 * index), source="upload") for index in range(2)]
    provider = ReferenceProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    run = service.store.create(
        user, character_run([image.id for image in images], mode="img2img"),
        references=[ReferenceImageUse(id=image.id, sha256=image.sha256) for image in images],
    )
    # Replace the second file after creation: its frozen digest no longer matches.
    (store.path / user / images[1].id).write_bytes(png(width=1024))
    manager.start()
    try:
        ended = pump(service, user, run.id)
    finally:
        service.stop()
        manager.stop()
    assert (ended.succeeded_count, ended.failed_count) == ("2", "1")
    assert [refs for _call, refs in provider.calls] == [[png(512)], [png(512)]]
    assert all(
        call.reference.strength == 0.55 and call.reference.noise == 0.1
        for call, _refs in provider.calls
    )
    jobs = manager.store.list(user, limit=10, offset=0).items
    assert sorted(job.error_code or "" for job in jobs) == ["", "", "reference_unavailable"]


def schema(*names):
    return {"type": "object", "required": ["prompt"], "properties": {name: {} for name in names}}


BASE_FIELDS = (
    "prompt", "negative_prompt", "model", "width", "height", "steps", "scale", "sampler",
    "seed", "n_samples", "quality",
)


ENCODE_VIBE = {"name": "encode_vibe", "inputSchema": schema(
    "reference", "information_extracted", "model",
)}


def reference_transport(tools, *, encode_error=None):
    calls = []

    def handler(request: httpx.Request):
        payload = json.loads(request.content)
        calls.append(payload)
        method = payload["method"]
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "initialize":
            result = {"protocolVersion": "2025-06-18"}
        elif method == "tools/list":
            result = {"tools": tools}
        elif payload["params"]["name"] == "encode_vibe":
            encodes = sum(
                1 for call in calls
                if call["method"] == "tools/call" and call["params"]["name"] == "encode_vibe"
            )
            result = (
                {"isError": True, "content": [{"type": "text", "text": encode_error}]}
                if encode_error else
                {"content": [{"type": "text", "text": f"VIBETOKEN{encodes - 1:08d}abcdef=="}]}
            )
        else:
            image = base64.b64encode(png()).decode()
            result = {"content": [{"type": "image", "mimeType": "image/png", "data": image}]}
        return httpx.Response(
            200, headers={"Mcp-Session-Id": "s"},
            json={"jsonrpc": "2.0", "id": payload["id"], "result": result},
        )

    return httpx.MockTransport(handler), calls


def reference_parameters(mode, information=None):
    reference = {"mode": mode, "images": [
        {"id": str(uuid4()), "sha256": "a" * 64}, {"id": str(uuid4()), "sha256": "b" * 64},
    ]}
    if information is not None:
        reference["information_extracted"] = information
    if mode == "img2img":
        reference.update(images=reference["images"][:1], strength=0.5, noise=0.2)
    return GenerationRequest.model_validate({
        **INPUT, "model": "nai-diffusion-4-5-full", "sample_count": 1, "seed": 5,
        "reference": reference,
    })


class MemoryVibes:
    def __init__(self):
        self.tokens = {}

    def get(self, sha256, model, information):
        return self.tokens.get((sha256, model, information))

    def put(self, sha256, model, information, token):
        self.tokens[(sha256, model, information)] = token


def tool_calls(calls, name):
    return [call["params"] for call in calls
            if call["method"] == "tools/call" and call["params"]["name"] == name]


TOOLS = [
    {"name": "generate_image", "inputSchema": schema(*BASE_FIELDS, "references")},
    {"name": "image_to_image", "inputSchema": schema(
        *BASE_FIELDS, "image", "strength", "noise", "extra_noise_seed",
    )},
    ENCODE_VIBE,
]


def test_mcp_vibe_encodes_references_once_and_img2img_arguments_are_redacted() -> None:
    transport, calls = reference_transport(TOOLS)
    provider = NovelAiMcpProvider("https://mcp.example/x", "token", transport=transport)
    recorded = []
    vibes = MemoryVibes()
    parameters = reference_parameters("vibe", information=0.7)
    provider.generate_with_request(
        parameters, recorded.append, references=[png(), jpeg()], vibe_tokens=vibes,
    )
    encodes = tool_calls(calls, "encode_vibe")
    assert [call["arguments"] for call in encodes] == [
        {"reference": base64.b64encode(png()).decode(), "information_extracted": 0.7,
         "model": "nai-diffusion-4-5-full"},
        {"reference": base64.b64encode(jpeg()).decode(), "information_extracted": 0.7,
         "model": "nai-diffusion-4-5-full"},
    ]
    generate = tool_calls(calls, "generate_image")[-1]
    # NovelAI V4/V4.5 receives encoded vibe tokens, never raw image bytes.
    assert generate["arguments"]["references"] == [
        "VIBETOKEN00000000abcdef==", "VIBETOKEN00000001abcdef==",
    ]
    assert recorded[0]["references"] == [
        {"sha256": "a" * 64, "byte_size": len(png()), "information_extracted": 0.7},
        {"sha256": "b" * 64, "byte_size": len(jpeg()), "information_extracted": 0.7},
    ]
    assert "VIBETOKEN" not in json.dumps(recorded)
    provider.generate_with_request(
        parameters, recorded.append, references=[png(), jpeg()], vibe_tokens=vibes,
    )
    assert len(tool_calls(calls, "encode_vibe")) == 2  # cached tokens: no second paid encode
    assert tool_calls(calls, "generate_image")[-1]["arguments"]["references"] == (
        generate["arguments"]["references"]
    )
    provider.generate_with_request(
        reference_parameters("img2img"), recorded.append, references=[png()],
    )
    tool_call = calls[-1]["params"]
    assert tool_call["name"] == "image_to_image"
    arguments = tool_call["arguments"]
    assert arguments["image"] == base64.b64encode(png()).decode()
    assert (arguments["strength"], arguments["noise"], arguments["extra_noise_seed"]) == (
        0.5, 0.2, 5,
    )
    assert "character_prompts" not in arguments and "references" not in arguments
    assert recorded[-1]["image"] == {"sha256": "a" * 64, "byte_size": len(png())}
    assert base64.b64encode(png()).decode() not in json.dumps(recorded)


@pytest.mark.parametrize(
    ("mode", "tools"),
    [
        ("vibe", [{"name": "generate_image", "inputSchema": schema(*BASE_FIELDS)}]),
        # References without encode_vibe would send raw images, which NovelAI rejects.
        ("vibe", [{"name": "generate_image", "inputSchema": schema(*BASE_FIELDS, "references")}]),
        ("img2img", [{"name": "generate_image", "inputSchema": schema(*BASE_FIELDS)}]),
    ],
)
def test_mcp_missing_reference_support_fails_before_paid_call(mode, tools) -> None:
    transport, calls = reference_transport(tools)
    provider = NovelAiMcpProvider("https://mcp.example/x", "token", transport=transport)
    references = [png(), jpeg()] if mode == "vibe" else [png()]
    from novelai_api.generations import ProviderFailure

    with pytest.raises(ProviderFailure) as failure:
        provider.generate_with_request(
            reference_parameters(mode), lambda _arguments: None, references=references,
        )
    assert failure.value.code == "unsupported_reference_mode"
    assert all(call["method"] != "tools/call" for call in calls)


class ImageRunner:
    def __init__(self):
        self.calls = []

    async def run(self, text, *, images=()):
        self.calls.append((text, list(images)))
        return {"suggestion": "1girl, solo, silver hair, red eyes"}


def test_reference_api_upload_pick_list_bytes_delete_trait_advice_and_isolation(
    database: Database,
) -> None:
    runner = ImageRunner()
    provider = ReferenceProvider()
    app = create_app(
        Settings(database.path, "https://testserver"), database, image_provider=provider,
        result_cache=ResultCache(), advice_runner=runner,
    )
    app.state.experiments._interval = 0.01
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/api/reference-images").status_code == 401
        login(client, database, "alice")
        upload = {"Content-Type": "image/png", **ORIGIN}
        assert client.post("/api/reference-images", content=png()).status_code == 403
        assert client.post(
            "/api/reference-images", content=b"GIF89a",
            headers={**ORIGIN, "Content-Type": "image/gif"},
        ).status_code == 415
        assert client.post(
            "/api/reference-images", content=png(16, 16), headers=upload,
        ).status_code == 422
        created = client.post("/api/reference-images", content=png(), headers=upload)
        assert created.status_code == 201
        first = created.json()
        assert first["source"] == "upload" and (first["width"], first["height"]) == (512, 768)
        image = client.get(f"/api/reference-images/{first['id']}/image")
        assert image.content == png() and image.headers["cache-control"] == "no-store"

        job = client.post("/api/generations", json={**INPUT, "sample_count": 1}, headers=ORIGIN)
        job_id = job.json()["id"]
        deadline = time.monotonic() + 3
        while client.get(f"/api/generations/{job_id}").json()["status"] != "succeeded":
            assert time.monotonic() < deadline
            time.sleep(0.01)
        picked = client.post(
            "/api/reference-images/from-result",
            json={"job_id": job_id, "image_index": 0}, headers=ORIGIN,
        )
        assert picked.status_code == 201 and picked.json()["source"] == "result"
        assert client.post(
            "/api/reference-images/from-result",
            json={"job_id": job_id, "image_index": 5}, headers=ORIGIN,
        ).status_code == 404
        assert len(client.get("/api/reference-images").json()["items"]) == 2

        advice = client.post("/api/reference-images/trait-advice", json={
            "reference_ids": [first["id"], picked.json()["id"]], "traits": "1girl, blue hair",
        }, headers=ORIGIN)
        assert advice.status_code == 200
        assert advice.json() == {"suggestion": "1girl, solo, silver hair, red eyes"}
        text, images = runner.calls[0]
        assert "1girl, blue hair" in text and images == [png(), png()]

        injected = {**INPUT, "reference": {"mode": "vibe", "images": [
            {"id": first["id"], "sha256": first["sha256"]},
        ]}, "model": "nai-diffusion-4-5-full"}
        assert client.post("/api/generations", json=injected, headers=ORIGIN).status_code == 422

        run = client.post(
            "/api/dataset-runs", json=character_run([first["id"]]).model_dump(mode="json"),
            headers=ORIGIN,
        )
        assert run.status_code == 202
        assert run.json()["character"]["references"] == [
            {"id": first["id"], "sha256": first["sha256"]},
        ]
        deadline = time.monotonic() + 3
        while client.get(f"/api/style-experiment-runs/{run.json()['id']}").json()["status"] != (
            "completed"
        ):
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert client.delete(
            f"/api/reference-images/{first['id']}", headers=ORIGIN,
        ).status_code == 204

        login(client, database, "bob")
        assert client.get("/api/reference-images").json() == {"items": []}
        foreign = picked.json()["id"]
        assert client.get(f"/api/reference-images/{foreign}/image").status_code == 404
        assert client.delete(f"/api/reference-images/{foreign}", headers=ORIGIN).status_code == 404
        assert client.post("/api/reference-images/trait-advice", json={
            "reference_ids": [foreign],
        }, headers=ORIGIN).json()["code"] == "reference_not_found"
        bob_run = client.post(
            "/api/dataset-runs", json=character_run([foreign]).model_dump(mode="json"),
            headers=ORIGIN,
        )
        assert bob_run.status_code == 422 and bob_run.json()["code"] == "reference_not_found"


def test_legacy_dataset_definition_is_unchanged_and_conflicts_with_character_same_id(
    database: Database,
) -> None:
    user = owner(database)
    store = ReferenceImageStore(database)
    image = store.add(user, png(), source="upload")
    service = StyleExperimentService(
        database, GenerationManager(database, ReferenceProvider(), cache=ResultCache()),
    )
    request = character_run([image.id])
    plain = DatasetRunCreate.model_validate({
        **request.model_dump(mode="json", exclude={"character", "styles"}),
    })
    definition, _total = plain.definition()
    assert set(json.loads(definition)) == {"kind", "parameters", "items"}
    service.store.create(user, plain)
    with pytest.raises(RunConflict):
        service.store.create(user, DatasetRunCreate.model_validate({
            **request.model_dump(mode="json"), "id": str(plain.id),
        }), references=[ReferenceImageUse(id=image.id, sha256=image.sha256)])


def test_style_experiment_runs_reject_reference_parameters() -> None:
    from novelai_api.style_experiments import RunCreate

    reference = {"mode": "vibe", "images": [{"id": str(uuid4()), "sha256": "a" * 64}]}
    with pytest.raises(ValidationError, match="reference identity"):
        RunCreate.model_validate({
            "id": str(uuid4()),
            "parameters": {**INPUT, "model": "nai-diffusion-4-5-full", "style_prompt": "a",
                           "reference": reference},
            "ranges": [{"tag_index": 0, "min": "0.5", "max": "1", "step": "0.5"}],
        })


def test_run_creation_rechecks_references_inside_the_insert_transaction(
    database: Database,
) -> None:
    from novelai_api.style_experiments import ReferenceMissing

    user = owner(database)
    store = ReferenceImageStore(database)
    image = store.add(user, png(), source="upload")
    pinned = [ReferenceImageUse(id=image.id, sha256=image.sha256)]
    store.delete(user, image.id)  # deleted after the route resolved it
    service = StyleExperimentService(
        database, GenerationManager(database, ReferenceProvider(), cache=ResultCache()),
    )
    with pytest.raises(ReferenceMissing):
        service.store.create(user, character_run([image.id]), references=pinned)
    assert service.store.active(user) is None


def test_mcp_encode_failure_logs_upstream_text_and_skips_generation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from novelai_api.generations import ProviderFailure

    transport, calls = reference_transport(
        TOOLS, encode_error="NovelAI stream error: Internal Server Error",
    )
    provider = NovelAiMcpProvider("https://mcp.example/x", "token", transport=transport)
    vibes = MemoryVibes()
    caplog.set_level("WARNING", logger="novelai_api.mcp_images")
    with pytest.raises(ProviderFailure) as failure:
        provider.generate_with_request(
            reference_parameters("vibe"), lambda _arguments: None,
            references=[png(), jpeg()], vibe_tokens=vibes,
        )
    assert failure.value.code == "provider_error"
    assert "encode_vibe failed: NovelAI stream error: Internal Server Error" in caplog.text
    assert "token" not in caplog.text.lower().replace("vibe token", "")
    assert tool_calls(calls, "generate_image") == [] and vibes.tokens == {}


def test_owner_vibe_cache_is_private_keyed_and_dropped_with_last_image_copy(
    database: Database,
) -> None:
    user = owner(database)
    store = ReferenceImageStore(database)
    first = store.add(user, png(), source="upload")
    second = store.add(user, png(), source="result")
    cache = store.vibe_tokens(user)
    cache.put(first.sha256, "nai-diffusion-4-5-full", 1.0, "VIBETOKEN00000000abcdef==")
    assert cache.get(first.sha256, "nai-diffusion-4-5-full", 1.0) == "VIBETOKEN00000000abcdef=="
    assert cache.get(first.sha256, "nai-diffusion-4-5-full", 0.5) is None
    assert cache.get(first.sha256, "nai-diffusion-4-full", 1.0) is None
    assert store.vibe_tokens(owner(database, "bob")).get(
        first.sha256, "nai-diffusion-4-5-full", 1.0,
    ) is None
    files = list((store.path / user / "vibes").iterdir())
    if os.name == "posix":
        assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in files)
    store.delete(user, first.id)
    assert cache.get(first.sha256, "nai-diffusion-4-5-full", 1.0) is not None  # copy remains
    store.delete(user, second.id)
    assert cache.get(first.sha256, "nai-diffusion-4-5-full", 1.0) is None


def test_vibe_information_extracted_is_frozen_into_every_group(database: Database) -> None:
    user = owner(database)
    store = ReferenceImageStore(database)
    image = store.add(user, png(), source="upload")
    provider = ReferenceProvider()
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    payload = character_run([image.id]).model_dump(mode="json")
    payload["character"]["information_extracted"] = 0.6
    run = service.store.create(
        user, DatasetRunCreate.model_validate(payload),
        references=[ReferenceImageUse(id=image.id, sha256=image.sha256)],
    )
    assert run.character.information_extracted == 0.6
    manager.start()
    try:
        pump(service, user, run.id)
    finally:
        service.stop()
        manager.stop()
    assert [call.reference.vibe_information for call, _refs in provider.calls] == [0.6] * 3
    for invalid in ({"information_extracted": 0}, {"information_extracted": 1.5},
                    {"mode": "img2img", "strength": 0.5, "noise": 0, "information_extracted": 0.5}):
        bad = character_run([image.id]).model_dump(mode="json")
        bad["character"].update(invalid)
        with pytest.raises(ValidationError):
            DatasetRunCreate.model_validate(bad)


def test_image_to_image_call_gets_the_longer_deadline() -> None:
    seen = {}
    transport, calls = reference_transport(TOOLS)

    def handler(request: httpx.Request):
        payload = json.loads(request.content)
        if payload.get("method") == "tools/call":
            seen[payload["params"]["name"]] = request.extensions["timeout"]["read"]
        return transport.handle_request(request)

    provider = NovelAiMcpProvider(
        "https://mcp.example/x", "token", transport=httpx.MockTransport(handler), timeout=30,
    )
    provider.generate_with_request(
        reference_parameters("img2img"), lambda _arguments: None, references=[png()],
    )
    provider.generate_with_request(
        GenerationRequest.model_validate({**INPUT, "sample_count": 1, "seed": 5}),
        lambda _arguments: None,
    )
    assert seen == {"image_to_image": 600.0, "generate_image": 30}


def test_vibe_reference_strength_is_sent_per_reference_and_required_upstream() -> None:
    from novelai_api.generations import ProviderFailure

    tools = [
        {"name": "generate_image", "inputSchema": schema(
            *BASE_FIELDS, "references", "reference_strengths",
        )},
        ENCODE_VIBE,
    ]
    transport, calls = reference_transport(tools)
    provider = NovelAiMcpProvider("https://mcp.example/x", "token", transport=transport)
    parameters = reference_parameters("vibe")
    parameters = parameters.model_copy(update={
        "reference": parameters.reference.model_copy(update={"reference_strength": 0.6}),
    })
    recorded = []
    provider.generate_with_request(
        parameters, recorded.append, references=[png(), jpeg()], vibe_tokens=MemoryVibes(),
    )
    assert tool_calls(calls, "generate_image")[-1]["arguments"]["reference_strengths"] == [0.6, 0.6]
    assert recorded[0]["reference_strengths"] == [0.6, 0.6]
    # Default strength sends nothing, preserving the upstream default 1.0.
    provider.generate_with_request(
        reference_parameters("vibe"), lambda _arguments: None,
        references=[png(), jpeg()], vibe_tokens=MemoryVibes(),
    )
    assert "reference_strengths" not in tool_calls(calls, "generate_image")[-1]["arguments"]

    old_transport, old_calls = reference_transport(TOOLS)  # service without the field
    with pytest.raises(ProviderFailure) as failure:
        NovelAiMcpProvider("https://mcp.example/x", "token", transport=old_transport) \
            .generate_with_request(parameters, lambda _arguments: None,
                                   references=[png(), jpeg()], vibe_tokens=MemoryVibes())
    assert failure.value.code == "unsupported_reference_mode"
    assert tool_calls(old_calls, "encode_vibe") == []  # nothing paid


def test_vibe_reference_strength_is_frozen_and_rejected_for_img2img() -> None:
    payload = character_run([uuid4()]).model_dump(mode="json")
    payload["character"]["reference_strength"] = 0.7
    request = DatasetRunCreate.model_validate(payload)
    definition = json.loads(request.definition([
        ReferenceImageUse(id=str(request.character.reference_ids[0]), sha256="c" * 64),
    ])[0])
    assert definition["character"]["reference_strength"] == 0.7
    for invalid in ({"reference_strength": 0}, {"reference_strength": 1.2},
                    {"mode": "img2img", "strength": 0.5, "noise": 0, "reference_strength": 0.5}):
        bad = character_run([uuid4()]).model_dump(mode="json")
        bad["character"].update(invalid)
        with pytest.raises(ValidationError):
            DatasetRunCreate.model_validate(bad)
