"""Fake HTTP transports prove tag-search policy without live API requests."""

import json
import threading
import zlib
from gzip import compress as gzip_compress
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import novelai_api.tags as tags
from novelai_api.app import create_app
from novelai_api.auth import create_token
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.tags import SearchFailure, SearchRequest, TagSearch


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.sqlite3")
    database.migrate()
    return database


def app_client(database: Database, transport: httpx.MockTransport) -> TestClient:
    settings = Settings(database.path, "https://testserver", tag_search_key="test-key")
    return TestClient(
        create_app(
            settings,
            database,
            tag_search=TagSearch(
                "https://search.example/api", settings.public_origin, settings.tag_search_key,
                transport=transport,
            ),
        ),
        base_url="https://testserver",
    )


def login(client: TestClient, database: Database) -> None:
    _token_id, token = create_token(database, "alice")
    assert client.post(
        "/api/auth/session", json={"token": token}, headers={"Origin": "https://testserver"}
    ).status_code == 200


def search(client: TestClient, query: str = "水手服", limit: int = 10):
    return client.post(
        "/api/tags/search",
        json={"query": query, "limit": limit},
        headers={"Origin": "https://testserver"},
    )


class TrackingStream(httpx.SyncByteStream):
    def __init__(self, chunks: list[bytes], *, on_chunk=None):
        self.chunks = chunks
        self.on_chunk = on_chunk
        self.read_count = 0
        self.closed = False

    def __iter__(self):
        for chunk in self.chunks:
            self.read_count += 1
            if self.on_chunk is not None:
                self.on_chunk()
            yield chunk

    def close(self):
        self.closed = True


def test_streamed_response_has_bounded_bytes_and_releases_capacity(database: Database) -> None:
    oversized = TrackingStream([b" " * (512 * 1024), b" " * (512 * 1024), b"x", b"secret"])
    valid = TrackingStream(
        [b'{"results":[{"tag":"safe","nsfw":"0",', b'"final_score":0.85}]}']
    )
    streams = iter((oversized, valid))
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, stream=next(streams)))

    with app_client(database, transport) as client:
        login(client, database)
        failure = search(client)
        assert failure.status_code == 502
        assert failure.json()["code"] == "search_bad_response"
        assert oversized.read_count == 3
        assert oversized.closed
        response = search(client)
        assert response.status_code == 200
        assert response.json()["results"] == [
            {
                "tag": "safe", "cn_name": None, "category": None,
                "is_nsfw": False, "count": None, "score": 0.85, "summary": None,
            }
        ]
        assert valid.read_count == 2
        assert valid.closed


@pytest.mark.parametrize(
    ("encoding", "compress"),
    [
        ("gzip", gzip_compress),
        ("deflate", zlib.compress),
        ("deflate", lambda body: zlib.compress(body)[2:-4]),
    ],
)
def test_compressed_response_is_decoded_with_bounded_chunks(
    database: Database, encoding: str, compress,
) -> None:
    body = b'{"results":[{"tag":"safe","nsfw":"0"}]}'
    compressed = compress(body)
    upstream = TrackingStream([compressed[:5], compressed[5:]])

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["accept-encoding"] == "gzip, deflate"
        return httpx.Response(200, stream=upstream, headers={"Content-Encoding": encoding})

    with app_client(database, httpx.MockTransport(handler)) as client:
        login(client, database)
        response = search(client)
        assert response.status_code == 200
        assert response.json()["results"][0]["tag"] == "safe"
        assert response.json()["results"][0]["is_nsfw"] is False
        assert upstream.read_count == 2
        assert upstream.closed


def test_compressed_bomb_stops_at_decoded_cap_and_releases_capacity(database: Database) -> None:
    bomb = TrackingStream([gzip_compress(b" " * (20 * 1024 * 1024)), b"secret"])
    valid = TrackingStream([gzip_compress(b'{"results":[]}')])
    streams = iter((bomb, valid))
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, stream=next(streams), headers={"Content-Encoding": "gzip"}
        )
    )
    with app_client(database, transport) as client:
        login(client, database)
        failure = search(client)
        assert failure.status_code == 502
        assert failure.json()["code"] == "search_bad_response"
        assert bomb.read_count == 1
        assert bomb.closed
        assert search(client).json()["results"] == []
        assert valid.closed


@pytest.mark.parametrize("body", [b"private-key-value", gzip_compress(b'{"results":[]}')[:-4]])
def test_invalid_compressed_stream_is_secret_free(database: Database, body: bytes) -> None:
    stream = TrackingStream([body])
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, stream=stream, headers={"Content-Encoding": "gzip"}
        )
    )
    with app_client(database, transport) as client:
        login(client, database)
        response = search(client)
        assert response.status_code == 502
        assert response.json()["code"] == "search_bad_response"
        assert body.decode("utf-8", "replace") not in response.text
        assert stream.closed


def test_streamed_chunks_exceed_overall_deadline_without_sleep(
    database: Database, monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [0.0]
    monkeypatch.setattr(tags, "monotonic", lambda: clock[0])

    def advance_clock() -> None:
        clock[0] += 11.0

    slow = TrackingStream([b" "] * 4, on_chunk=advance_clock)
    streams = iter((slow, TrackingStream([b'{"results":[]}'])))
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, stream=next(streams)))
    with app_client(database, transport) as client:
        login(client, database)
        response = search(client)
        assert response.status_code == 504
        assert response.json()["code"] == "search_timeout"
        assert slow.read_count == 3
        assert slow.closed
        assert search(client).json()["results"] == []


def test_compressed_chunks_exceed_overall_deadline_without_sleep(
    database: Database, monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [0.0]
    monkeypatch.setattr(tags, "monotonic", lambda: clock[0])

    def advance_clock() -> None:
        clock[0] += 11.0

    compressed = gzip_compress(b'{"results":[]}')
    slow = TrackingStream(
        [compressed[:1], compressed[1:2], compressed[2:3], compressed[3:]],
        on_chunk=advance_clock,
    )
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, stream=slow, headers={"Content-Encoding": "gzip"}
        )
    )
    with app_client(database, transport) as client:
        login(client, database)
        response = search(client)
        assert response.status_code == 504
        assert response.json()["code"] == "search_timeout"
        assert slow.read_count == 3
        assert slow.closed


@pytest.mark.parametrize(
    ("retry_after", "expected"),
    [
        ("0", "0"),
        (" 00042 ", "42"),
        ("Wed, 21 Oct 2015 07:28:00 GMT", "Wed, 21 Oct 2015 07:28:00 GMT"),
        ("Sunday, 06-Nov-94 08:49:37 GMT", "Sun, 06 Nov 1994 08:49:37 GMT"),
        ("Sun Nov  6 08:49:37 1994", "Sun, 06 Nov 1994 08:49:37 GMT"),
    ],
)
def test_rate_limited_stream_is_not_consumed(
    database: Database, retry_after: str, expected: str,
) -> None:
    body = TrackingStream([b"upstream secret" * 100000])
    responses = iter((
        httpx.Response(
            429, stream=body,
            headers={"Content-Encoding": "gzip", "Retry-After": retry_after},
        ),
        httpx.Response(200, json={"results": []}),
    ))
    transport = httpx.MockTransport(lambda _request: next(responses))
    with app_client(database, transport) as client:
        login(client, database)
        response = search(client)
        assert response.status_code == 429
        assert response.json() == {
            "code": "search_rate_limited", "message": "Tag search rate limited", "retryable": True,
        }
        assert response.headers["Retry-After"] == expected
        assert "upstream secret" not in response.text
        assert body.read_count == 0
        assert body.closed
        assert search(client).json()["results"] == []


@pytest.mark.parametrize(
    "retry_after",
    [
        "-1", "+2", "2.5", "1, secret", "12\r\nX-API-Key: test-key", "1\x00secret",
        "9" * 129, "Thu, 21 Oct 2015 07:28:00 GMT", "Wed, 32 Oct 2015 07:28:00 GMT",
        "Wed, 21 Oct 2015 07:28:00 PST", "Sun Nov  6 25:49:37 1994", "秘密",
    ],
)
def test_untrusted_retry_after_is_not_exposed(database: Database, retry_after: str) -> None:
    body = TrackingStream([b"upstream secret"])
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            429, stream=body, headers=[(b"Retry-After", retry_after.encode("utf-8"))]
        )
    )
    with app_client(database, transport) as client:
        login(client, database)
        response = search(client)
        assert response.status_code == 429
        assert response.json()["code"] == "search_rate_limited"
        assert "Retry-After" not in response.headers
        assert "secret" not in response.text
        assert body.read_count == 0
        assert body.closed


def test_busy_search_has_no_retry_after(database: Database) -> None:
    adapter = TagSearch(
        "https://search.example/api", "https://testserver", None,
        transport=httpx.MockTransport(lambda _request: pytest.fail("Busy search called upstream")),
    )
    settings = Settings(database.path, "https://testserver")
    with TestClient(
        create_app(settings, database, tag_search=adapter), base_url=settings.public_origin
    ) as client:
        login(client, database)
        assert adapter._capacity.acquire(blocking=False)
        try:
            response = search(client)
        finally:
            adapter._capacity.release()
        assert response.status_code == 429
        assert response.json() == {
            "code": "search_busy", "message": "Search is busy", "retryable": True,
        }
        assert "Retry-After" not in response.headers


def test_search_includes_nsfw_without_exposing_credentials(database: Database) -> None:
    requests = []

    def handler(request: httpx.Request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "tag": "serafuku",
                        "cn_name": "水手服",
                        "category": "general",
                        "is_nsfw": False,
                        "count": 1200,
                        "score": 0.9,
                        "wiki": "school outfit",
                    },
                    {"tag": "explicit_tag", "is_nsfw": True},
                ]
            },
        )

    with app_client(database, httpx.MockTransport(handler)) as client:
        assert search(client).status_code == 401
        assert requests == []
        login(client, database)
        response = search(client)
        assert response.status_code == 200
        assert response.json()["results"][0] == {
            "tag": "serafuku",
            "cn_name": "水手服",
            "category": "general",
            "is_nsfw": False,
            "count": 1200,
            "score": 0.9,
            "summary": "school outfit",
        }
        assert response.json()["results"][1]["is_nsfw"] is True
        assert response.json()["source_url"].startswith("https://")
        assert "test-key" not in response.text
        assert len(requests) == 1
        assert requests[0].url.path == "/api/search"
        assert json.loads(requests[0].content) == {
            "query": "水手服", "limit": 10, "show_nsfw": True
        }
        assert requests[0].headers["x-danboorusearch-client"] == "novelai-workspace"
        assert requests[0].headers["x-danboorusearch-site"] == "https://testserver"
        assert requests[0].headers["x-api-key"] == "test-key"
        assert search(client, "school uniform", 1).json()["results"][0]["tag"] == "serafuku"


def test_upstream_search_results_normalize_nsfw_and_final_score(database: Database) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            json={
                "results": [
                    {
                        "tag": "upstream_explicit",
                        "cn_name": "示例",
                        "category": "general",
                        "nsfw": "1",
                        "count": 42,
                        "final_score": 0.85,
                        "wiki": "upstream description",
                    },
                    {"tag": "upstream_safe", "nsfw": "0", "final_score": 0},
                    {"tag": "unknown", "nsfw": "unknown", "final_score": "bad"},
                    {"tag": "legacy", "is_nsfw": True, "score": 0.5},
                    {
                        "tag": "upstream_precedence",
                        "nsfw": "1",
                        "is_nsfw": False,
                        "final_score": 0,
                        "score": 0.9,
                    },
                    {
                        "tag": "legacy_fallback",
                        "nsfw": "unknown",
                        "is_nsfw": False,
                        "final_score": "bad",
                        "score": 0.75,
                    },
                ]
            },
        )
    )
    with app_client(database, transport) as client:
        login(client, database)
        response = search(client)
        assert response.status_code == 200
        assert response.json()["results"] == [
            {
                "tag": "upstream_explicit",
                "cn_name": "示例",
                "category": "general",
                "is_nsfw": True,
                "count": 42,
                "score": 0.85,
                "summary": "upstream description",
            },
            {
                "tag": "upstream_safe",
                "cn_name": None,
                "category": None,
                "is_nsfw": False,
                "count": None,
                "score": 0.0,
                "summary": None,
            },
            {
                "tag": "unknown",
                "cn_name": None,
                "category": None,
                "is_nsfw": None,
                "count": None,
                "score": None,
                "summary": None,
            },
            {
                "tag": "legacy",
                "cn_name": None,
                "category": None,
                "is_nsfw": True,
                "count": None,
                "score": 0.5,
                "summary": None,
            },
            {
                "tag": "upstream_precedence",
                "cn_name": None,
                "category": None,
                "is_nsfw": True,
                "count": None,
                "score": 0.0,
                "summary": None,
            },
            {
                "tag": "legacy_fallback",
                "cn_name": None,
                "category": None,
                "is_nsfw": False,
                "count": None,
                "score": 0.75,
                "summary": None,
            },
        ]


@pytest.mark.parametrize(
    ("nsfw", "score"),
    [("true", "0.8"), (2, True), (None, None), ("", 10**400)],
)
def test_unrecognized_upstream_values_are_null(database: Database, nsfw: object, score: object):
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, json={"results": [{"tag": "unknown", "nsfw": nsfw, "final_score": score}]}
        )
    )
    with app_client(database, transport) as client:
        login(client, database)
        response = search(client)
        assert response.status_code == 200
        assert response.json()["results"][0]["is_nsfw"] is None
        assert response.json()["results"][0]["score"] is None


def test_non_finite_upstream_score_is_null(database: Database) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, text='{"results":[{"tag":"nonfinite","nsfw":"0","final_score":1e999}]}'
        )
    )
    with app_client(database, transport) as client:
        login(client, database)
        response = search(client)
        assert response.status_code == 200
        assert response.json()["results"][0]["is_nsfw"] is False
        assert response.json()["results"][0]["score"] is None


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (429, "search_rate_limited"),
        (503, "search_unavailable"),
        (422, "search_rejected"),
        (401, "search_auth_error"),
    ],
)
def test_provider_errors_are_normalized(database: Database, status: int, code: str) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(status, text="upstream secret response")
    )
    with app_client(database, transport) as client:
        login(client, database)
        response = search(client)
        assert response.json()["code"] == code
        assert "upstream secret response" not in response.text
        assert "Retry-After" not in response.headers


def test_other_provider_errors_do_not_forward_retry_after(database: Database) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(503, headers={"Retry-After": "40"}, text="secret")
    )
    with app_client(database, transport) as client:
        login(client, database)
        response = search(client)
        assert response.status_code == 503
        assert response.json()["code"] == "search_unavailable"
        assert "Retry-After" not in response.headers


def test_timeout_invalid_json_and_blank_query(database: Database) -> None:
    def timeout_handler(request: httpx.Request):
        raise httpx.ReadTimeout("secret URL", request=request)

    with app_client(database, httpx.MockTransport(timeout_handler)) as client:
        login(client, database)
        assert search(client).json()["code"] == "search_timeout"
        assert search(client, "   ").status_code == 422
        assert search(client, "query", 0).status_code == 422

    bad_json = httpx.MockTransport(lambda _request: httpx.Response(200, text="bad"))
    with app_client(database, bad_json) as client:
        login(client, database)
        assert search(client).json()["code"] == "search_bad_response"


def test_only_one_concurrent_search() -> None:
    entered = threading.Event()
    release = threading.Event()

    def handler(_request: httpx.Request):
        entered.set()
        assert release.wait(timeout=3)
        return httpx.Response(200, json={"results": []})

    adapter = TagSearch(
        "https://search.example/api",
        "https://testserver",
        None,
        transport=httpx.MockTransport(handler),
    )
    worker = threading.Thread(target=adapter.search, args=(SearchRequest(query="one"),))
    worker.start()
    assert entered.wait(timeout=2)
    try:
        with pytest.raises(SearchFailure) as exception:
            adapter.search(SearchRequest(query="two"))
        assert exception.value.code == "search_busy"
    finally:
        release.set()
        worker.join(timeout=3)
    assert not worker.is_alive()
