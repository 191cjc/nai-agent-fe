"""Offline regression guard for the browser-visible API contract."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from novelai_api.app import create_app
from novelai_api.auth import create_token
from novelai_api.config import Settings
from novelai_api.db import Database


SNAPSHOT = Path(__file__).resolve().parents[1] / "contracts" / "openapi.json"


def test_openapi_contract_matches_snapshot_without_database_or_provider_calls(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "absent.sqlite3"
    settings = Settings(
        sqlite_path=sqlite_path,
        public_origin="https://contract.example",
        tag_search_url="https://tags.example/api",
        tag_search_key="contract-tag-key-sentinel",
        novelai_mcp_url="https://mcp.example/api",
        novelai_mcp_token="contract-mcp-token-sentinel",
    )
    schema = create_app(settings).openapi()
    serialized = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    assert not sqlite_path.exists()
    assert SNAPSHOT.read_text(encoding="utf-8") == serialized
    assert "contract.example" not in serialized
    assert "mcp.example" not in serialized
    assert "tags.example" not in serialized
    assert "contract-tag-key-sentinel" not in serialized
    assert "contract-mcp-token-sentinel" not in serialized
    assert "NAI_" not in serialized
    assert all(not path.startswith("/api/admin") for path in schema["paths"])

    expected_errors = {
        ("/api/health/ready", "get"): {503},
        ("/api/auth/session", "post"): {401, 403, 422, 429, 503},
        ("/api/auth/session", "get"): {401, 422, 503},
        ("/api/auth/session", "delete"): {401, 403, 422, 503},
        ("/api/generations", "post"): {401, 403, 422, 429, 503},
        ("/api/generations", "get"): {401, 422, 503},
        ("/api/generations/{job_id}", "get"): {401, 404, 422, 503},
        ("/api/generations/{job_id}", "delete"): {401, 403, 404, 409, 422, 503},
        ("/api/generation-results/{job_id}/images/{image_id}", "get"): {401, 404, 422, 503},
        ("/api/tags/search", "post"): {401, 403, 422, 429, 502, 503, 504},
        ("/api/advice", "post"): {401, 403, 422, 429, 502, 503, 504},
    }
    documented_errors = {
        (path, method): {
            int(status): response
            for status, response in operation["responses"].items()
            if int(status) >= 400
        }
        for path, methods in schema["paths"].items()
        for method, operation in methods.items()
        if method in {"get", "post", "delete"}
    }
    assert set(documented_errors) == set(expected_errors) | {("/api/health/live", "get")}
    for route, codes in expected_errors.items():
        assert set(documented_errors[route]) == codes
        for response in documented_errors[route].values():
            assert response["content"]["application/json"]["schema"] == {
                "$ref": "#/components/schemas/ApiError"
            }
    assert documented_errors[("/api/health/live", "get")] == {}

    retry_after = documented_errors[("/api/tags/search", "post")][429]["headers"]
    assert retry_after == {
        "Retry-After": {
            "description": "Optional on upstream rate limits; delta-seconds or HTTP-date.",
            "schema": {"type": "string"},
        }
    }
    for route, responses in documented_errors.items():
        if route != ("/api/tags/search", "post"):
            assert all(
                "Retry-After" not in response.get("headers", {}) for response in responses.values()
            )

    image_responses = schema["paths"][
        "/api/generation-results/{job_id}/images/{image_id}"
    ]["get"]["responses"]
    assert set(image_responses["200"]["content"]) == {"image/png"}
    generation_fields = schema["components"]["schemas"]["GenerationRequest"]["properties"]
    assert "enum" not in generation_fields["model"]
    assert "enum" not in generation_fields["sampler"]


def test_documented_errors_match_offline_validation_origin_and_ownership(tmp_path: Path) -> None:
    database = Database(tmp_path / "contract.sqlite3")
    database.migrate()
    settings = Settings(database.path, "https://contract.example")
    with TestClient(create_app(settings, database), base_url=settings.public_origin) as client:
        unauthenticated = client.get("/api/generations/absent")
        forbidden = client.post("/api/auth/session", json={"token": "invalid"})
        _token_id, token = create_token(database, "contract-user")
        login = client.post(
            "/api/auth/session",
            json={"token": token},
            headers={"Origin": settings.public_origin},
        )
        assert login.status_code == 200
        invalid_query = client.get("/api/generations?limit=0")
        invalid_path = client.get("/api/generation-results/absent/images/not-an-int")
        not_owned = client.get("/api/generations/absent")
        forbidden_delete = client.delete("/api/generations/absent")

    for response, status, code, message in (
        (unauthenticated, 401, "unauthenticated", "Authentication required"),
        (forbidden, 403, "forbidden_origin", "Invalid request origin"),
        (invalid_query, 422, "validation_error", "Invalid request"),
        (invalid_path, 422, "validation_error", "Invalid request"),
        (not_owned, 404, "not_found", "Generation not found"),
        (forbidden_delete, 403, "forbidden_origin", "Invalid request origin"),
    ):
        assert response.status_code == status
        assert response.json() == {
            "code": code,
            "message": message,
            "retryable": False,
        }
