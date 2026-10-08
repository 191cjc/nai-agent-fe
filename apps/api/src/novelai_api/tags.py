"""Backend-only adapter for the public DanbooruSearch REST search endpoint."""

import json
import math
import re
import threading
import zlib
from collections.abc import Iterator
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from time import monotonic

import httpx
from pydantic import BaseModel, Field, field_validator


SOURCE_URL = "https://huggingface.co/spaces/SAkizuki/DanbooruSearch"
MAX_RESPONSE_BYTES = 1024 * 1024
SEARCH_DEADLINE_SECONDS = 30.0
RESPONSE_CHUNK_BYTES = 8192
MAX_RETRY_AFTER_BYTES = 128
_DELTA_SECONDS = re.compile(r"[0-9]+")
_IMF_DATE = re.compile(
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), [0-9]{2} "
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT"
)
_RFC850_DATE = re.compile(
    r"(?P<weekday>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
    r"(?P<day>[0-9]{2})-(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-"
    r"(?P<year>[0-9]{2}) (?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2}) GMT"
)
_ASCTIME_DATE = re.compile(
    r"(?P<weekday>Mon|Tue|Wed|Thu|Fri|Sat|Sun) "
    r"(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"(?P<day>[0-9]{2}| [1-9]) (?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2}) "
    r"(?P<year>[0-9]{4})"
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=10, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def nonempty_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Search query cannot be blank")
        return value


class TagCandidate(BaseModel):
    tag: str
    cn_name: str | None = None
    category: str | None = None
    is_nsfw: bool | None = None
    count: int | None = None
    score: float | None = None
    summary: str | None = None


class SearchResults(BaseModel):
    results: list[TagCandidate]
    source_url: str = SOURCE_URL


class SearchFailure(Exception):
    def __init__(
        self, status: int, code: str, message: str, *,
        retryable: bool = False, retry_after: str | None = None,
    ):
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        self.retry_after = retry_after
        super().__init__(message)


def _safe_retry_after(value: str | None) -> str | None:
    if value is None or len(value) > MAX_RETRY_AFTER_BYTES or not value.isascii():
        return None
    value = value.strip(" \t")
    if _DELTA_SECONDS.fullmatch(value):
        return str(int(value))
    imf_date = value
    rfc850 = _RFC850_DATE.fullmatch(value)
    asctime = _ASCTIME_DATE.fullmatch(value)
    if rfc850:
        year = datetime.now(timezone.utc).year
        century_year = year // 100 * 100 + int(rfc850["year"])
        if century_year > year + 50:
            century_year -= 100
        elif century_year + 100 <= year + 50:
            century_year += 100
        imf_date = (
            f"{rfc850['weekday'][:3]}, {rfc850['day']} {rfc850['month']} "
            f"{century_year:04d} {rfc850['time']} GMT"
        )
    elif asctime:
        imf_date = (
            f"{asctime['weekday']}, {int(asctime['day']):02d} {asctime['month']} "
            f"{asctime['year']} {asctime['time']} GMT"
        )
    elif not _IMF_DATE.fullmatch(value):
        return None
    try:
        parsed = parsedate_to_datetime(imf_date)
        canonical = format_datetime(parsed, usegmt=True)
    except (ValueError, TypeError):
        return None
    return canonical if canonical == imf_date else None


def _bounded_raw_chunks(response: httpx.Response) -> Iterator[bytes]:
    for raw_chunk in response.iter_raw():
        for start in range(0, len(raw_chunk), RESPONSE_CHUNK_BYTES):
            yield raw_chunk[start : start + RESPONSE_CHUNK_BYTES]


def _optional_text(value) -> str | None:
    return value if isinstance(value, str) else None


def _optional_nsfw(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value == "1":
        return True
    if value == "0":
        return False
    return None


def _optional_score(value: object) -> float | None:
    if not isinstance(value, (float, int)) or isinstance(value, bool):
        return None
    try:
        score = float(value)
    except OverflowError:
        return None
    return score if math.isfinite(score) else None


def _candidate(raw: object) -> TagCandidate | None:
    if not isinstance(raw, dict):
        return None
    tag = raw.get("tag")
    if not isinstance(tag, str) or not tag.strip():
        return None
    count = raw.get("count", raw.get("post_count"))
    is_nsfw = _optional_nsfw(raw.get("nsfw"))
    score = _optional_score(raw.get("final_score"))
    return TagCandidate(
        tag=tag,
        cn_name=_optional_text(raw.get("cn_name")),
        category=_optional_text(raw.get("category")),
        is_nsfw=is_nsfw if is_nsfw is not None else _optional_nsfw(raw.get("is_nsfw")),
        count=(
            count if isinstance(count, int) and not isinstance(count, bool) and count >= 0
            else None
        ),
        score=score if score is not None else _optional_score(raw.get("score")),
        summary=_optional_text(raw.get("wiki", raw.get("summary"))),
    )


class TagSearch:
    def __init__(
        self,
        base_url: str,
        public_origin: str,
        api_key: str | None,
        *,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.public_origin = public_origin
        self.api_key = api_key
        self.transport = transport
        self._capacity = threading.BoundedSemaphore(1)

    def search(self, request: SearchRequest) -> SearchResults:
        if not self._capacity.acquire(blocking=False):
            raise SearchFailure(429, "search_busy", "Search is busy", retryable=True)
        try:
            return self._search(request)
        finally:
            self._capacity.release()

    def _search(self, request: SearchRequest) -> SearchResults:
        headers = {
            "X-DanbooruSearch-Client": "novelai-workspace",
            "X-DanbooruSearch-Site": self.public_origin,
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        headers["Accept-Encoding"] = "gzip, deflate"
        deadline = monotonic() + SEARCH_DEADLINE_SECONDS
        try:
            with httpx.Client(
                transport=self.transport,
                timeout=httpx.Timeout(SEARCH_DEADLINE_SECONDS, connect=5.0),
                follow_redirects=False,
            ) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}/search",
                    json={
                        "query": request.query.strip(),
                        "limit": request.limit,
                        "show_nsfw": True,
                    },
                    headers=headers,
                ) as response:
                    if monotonic() >= deadline:
                        raise SearchFailure(
                            504, "search_timeout", "Tag search timed out", retryable=True
                        )
                    if response.status_code == 429:
                        raise SearchFailure(
                            429, "search_rate_limited", "Tag search rate limited", retryable=True,
                            retry_after=_safe_retry_after(response.headers.get("Retry-After")),
                        )
                    if response.status_code in (401, 403):
                        raise SearchFailure(
                            502, "search_auth_error", "Tag search configuration error"
                        )
                    if response.status_code == 422:
                        raise SearchFailure(502, "search_rejected", "Tag search request rejected")
                    if response.status_code >= 500:
                        raise SearchFailure(
                            503, "search_unavailable", "Tag search unavailable", retryable=True
                        )
                    if response.status_code != 200:
                        raise SearchFailure(502, "search_error", "Tag search failed")
                    encoding = response.headers.get("Content-Encoding", "identity").strip().lower()
                    if encoding not in ("identity", "gzip", "deflate"):
                        raise SearchFailure(
                            502, "search_bad_response", "Invalid tag search response"
                        )
                    chunks: list[bytes] = []
                    size = 0
                    decoder = None
                    if response.is_stream_consumed:
                        body_chunks = response.iter_bytes(chunk_size=RESPONSE_CHUNK_BYTES)
                    elif encoding == "identity":
                        body_chunks = response.iter_raw()
                    else:
                        decoder = zlib.decompressobj(
                            zlib.MAX_WBITS | 16 if encoding == "gzip" else zlib.MAX_WBITS
                        )
                        body_chunks = _bounded_raw_chunks(response)
                    first_compressed_chunk = True
                    for chunk in body_chunks:
                        if monotonic() >= deadline:
                            raise SearchFailure(
                                504, "search_timeout", "Tag search timed out", retryable=True
                            )
                        if decoder is not None:
                            try:
                                decoded = decoder.decompress(chunk, MAX_RESPONSE_BYTES - size + 1)
                            except zlib.error as exception:
                                if encoding != "deflate" or not first_compressed_chunk:
                                    raise SearchFailure(
                                        502, "search_bad_response", "Invalid tag search response"
                                    ) from exception
                                decoder = zlib.decompressobj(-zlib.MAX_WBITS)
                                try:
                                    decoded = decoder.decompress(
                                        chunk, MAX_RESPONSE_BYTES - size + 1
                                    )
                                except zlib.error as raw_exception:
                                    raise SearchFailure(
                                        502, "search_bad_response", "Invalid tag search response"
                                    ) from raw_exception
                            first_compressed_chunk = False
                            if decoder.unused_data:
                                raise SearchFailure(
                                    502, "search_bad_response", "Invalid tag search response"
                                )
                            chunk = decoded
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise SearchFailure(
                                502, "search_bad_response", "Invalid tag search response"
                            )
                        chunks.append(chunk)
                    if decoder is not None:
                        if monotonic() >= deadline:
                            raise SearchFailure(
                                504, "search_timeout", "Tag search timed out", retryable=True
                            )
                        try:
                            tail = decoder.flush(MAX_RESPONSE_BYTES - size + 1)
                        except zlib.error as exception:
                            raise SearchFailure(
                                502, "search_bad_response", "Invalid tag search response"
                            ) from exception
                        size += len(tail)
                        if size > MAX_RESPONSE_BYTES or not decoder.eof or decoder.unused_data:
                            raise SearchFailure(
                                502, "search_bad_response", "Invalid tag search response"
                            )
                        chunks.append(tail)
                    if monotonic() >= deadline:
                        raise SearchFailure(
                            504, "search_timeout", "Tag search timed out", retryable=True
                        )
                    try:
                        payload = json.loads(b"".join(chunks))
                    except (UnicodeError, ValueError) as exception:
                        raise SearchFailure(
                            502, "search_bad_response", "Invalid tag search response"
                        ) from exception
                    if monotonic() >= deadline:
                        raise SearchFailure(
                            504, "search_timeout", "Tag search timed out", retryable=True
                        )
        except httpx.TimeoutException as exception:
            raise SearchFailure(
                504, "search_timeout", "Tag search timed out", retryable=True
            ) from exception
        except httpx.RequestError as exception:
            raise SearchFailure(
                503, "search_unavailable", "Tag search unavailable", retryable=True
            ) from exception
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise SearchFailure(502, "search_bad_response", "Invalid tag search response")
        candidates = (_candidate(raw) for raw in payload["results"][: request.limit])
        return SearchResults(
            results=[candidate for candidate in candidates if candidate is not None]
        )
