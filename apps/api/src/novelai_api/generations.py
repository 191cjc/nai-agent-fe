"""Owner-scoped generation history and bounded in-process image results."""

import json
import secrets
import sqlite3
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from .db import Database


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_TRAILER = b"\x00\x00\x00\x00IEND\xaeB`\x82"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_RESULT_BYTES = 32 * 1024 * 1024
MAX_CACHED_BYTES = 64 * 1024 * 1024
RESULT_TTL_SECONDS = 10 * 60


class GenerationRequest(BaseModel):
    positive_prompt: str = Field(min_length=1, max_length=3000)
    negative_prompt: str = Field(default="", max_length=3000)
    model: str = Field(min_length=1, max_length=80)
    width: int = Field(ge=64, le=2048, multiple_of=64)
    height: int = Field(ge=64, le=2048, multiple_of=64)
    steps: int = Field(ge=1, le=50)
    cfg_scale: float = Field(ge=0, le=20)
    sampler: str = Field(min_length=1, max_length=80)
    seed: int | None = Field(default=None, ge=1, le=4294967295)
    sample_count: int = Field(ge=1, le=8)
    quality: bool

    @field_validator("positive_prompt", "model", "sampler")
    @classmethod
    def nonempty_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Required generation text cannot be blank")
        return value


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    mime_type: str


class ImageProvider(Protocol):
    def generate(self, parameters: GenerationRequest) -> Sequence[GeneratedImage]: ...


class ProviderFailure(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class HistoryItem(BaseModel):
    id: str
    parameters: GenerationRequest
    status: Literal["queued", "running", "succeeded", "failed"]
    created_at: int
    updated_at: int
    effective_seed: int
    error_code: str | None
    image_count: int


class GenerationView(HistoryItem):
    image_urls: list[str]
    result_expires_at: int | None


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    next_offset: int | None


class JobStore:
    def __init__(self, database: Database):
        self.database = database

    def create(self, user_id: str, parameters: GenerationRequest) -> str:
        job_id = str(uuid4())
        now = int(time.time())
        with self.database.connect(write=True) as connection:
            connection.execute(
                "INSERT INTO generation_jobs "
                "(id, user_id, positive_prompt, negative_prompt, settings_json, effective_seed, "
                "status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?)",
                (
                    job_id,
                    user_id,
                    parameters.positive_prompt,
                    parameters.negative_prompt,
                    parameters.model_dump_json(),
                    parameters.seed,
                    now,
                    now,
                ),
            )
        return job_id

    def mark_interrupted(self) -> None:
        with self.database.connect(write=True) as connection:
            connection.execute(
                "UPDATE generation_jobs SET status = 'failed', error_code = 'outcome_unknown', "
                "updated_at = ? WHERE status IN ('queued', 'running')",
                (int(time.time()),),
            )

    def mark_running(self, job_id: str) -> bool:
        with self.database.connect(write=True) as connection:
            updated = connection.execute(
                "UPDATE generation_jobs SET status = 'running', updated_at = ? "
                "WHERE id = ? AND status = 'queued'",
                (int(time.time()), job_id),
            )
        return bool(updated.rowcount)

    def finish(self, job_id: str, *, image_count: int = 0, error_code: str | None = None) -> bool:
        status = "failed" if error_code is not None else "succeeded"
        with self.database.connect(write=True) as connection:
            updated = connection.execute(
                "UPDATE generation_jobs SET status = ?, error_code = ?, image_count = ?, "
                "updated_at = ? WHERE id = ? AND status = 'running'",
                (status, error_code, image_count, int(time.time()), job_id),
            )
        return bool(updated.rowcount)

    def get(self, user_id: str, job_id: str) -> HistoryItem | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM generation_jobs WHERE id = ? AND user_id = ?",
                (job_id, user_id),
            ).fetchone()
        return self._item(row) if row else None

    def list(self, user_id: str, *, limit: int, offset: int) -> HistoryPage:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM generation_jobs WHERE user_id = ? "
                "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                (user_id, limit + 1, offset),
            ).fetchall()
        return HistoryPage(
            items=[self._item(row) for row in rows[:limit]],
            next_offset=offset + limit if len(rows) > limit else None,
        )

    def delete(self, user_id: str, job_id: str) -> str | None:
        with self.database.connect(write=True) as connection:
            row = connection.execute(
                "SELECT status FROM generation_jobs WHERE id = ? AND user_id = ?",
                (job_id, user_id),
            ).fetchone()
            if row is None:
                return None
            if row["status"] in ("queued", "running"):
                return "active"
            connection.execute(
                "DELETE FROM generation_jobs WHERE id = ? AND user_id = ?", (job_id, user_id)
            )
        return "deleted"

    @staticmethod
    def _item(row: sqlite3.Row) -> HistoryItem:
        return HistoryItem(
            id=row["id"],
            parameters=GenerationRequest.model_validate(json.loads(row["settings_json"])),
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            effective_seed=row["effective_seed"],
            error_code=row["error_code"],
            image_count=row["image_count"],
        )


@dataclass
class CachedResult:
    user_id: str
    images: tuple[GeneratedImage, ...]
    expires_at: int
    deadline: float
    size: int


class ResultCache:
    def __init__(self, *, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._results: dict[str, CachedResult] = {}
        self._size = 0
        self._lock = threading.Lock()

    def put(self, job_id: str, user_id: str, images: Sequence[GeneratedImage]) -> bool:
        if len(images) == 0 or len(images) > 8:
            return False
        if any(
            not isinstance(image, GeneratedImage)
            or image.mime_type != "image/png"
            or not isinstance(image.data, bytes)
            or not image.data.startswith(PNG_SIGNATURE)
            or len(image.data) < 45
            or image.data[12:16] != b"IHDR"
            or not image.data.endswith(PNG_TRAILER)
            or len(image.data) > MAX_IMAGE_BYTES
            for image in images
        ):
            return False
        size = sum(len(image.data) for image in images)
        if size > MAX_RESULT_BYTES:
            return False
        with self._lock:
            self._prune()
            self._remove(job_id)
            while self._size + size > MAX_CACHED_BYTES and self._results:
                oldest = min(self._results, key=lambda key: self._results[key].deadline)
                self._remove(oldest)
            self._results[job_id] = CachedResult(
                user_id=user_id,
                images=tuple(images),
                expires_at=int(time.time()) + RESULT_TTL_SECONDS,
                deadline=self._clock() + RESULT_TTL_SECONDS,
                size=size,
            )
            self._size += size
        return True

    def get(self, job_id: str, user_id: str) -> CachedResult | None:
        with self._lock:
            self._prune()
            result = self._results.get(job_id)
            return result if result and result.user_id == user_id else None

    def discard(self, job_id: str) -> None:
        with self._lock:
            self._remove(job_id)

    def _remove(self, job_id: str) -> None:
        result = self._results.pop(job_id, None)
        if result:
            self._size -= result.size

    def _prune(self) -> None:
        for job_id, result in list(self._results.items()):
            if self._clock() >= result.deadline:
                self._remove(job_id)


class GenerationManager:
    def __init__(
        self,
        database: Database,
        provider: ImageProvider | None,
        *,
        cache: ResultCache | None = None,
    ):
        self.store = JobStore(database)
        self.provider = provider
        self.cache = cache or ResultCache()
        self._capacity = threading.BoundedSemaphore(3)
        self._executor: ThreadPoolExecutor | None = None

    def start(self) -> None:
        self.store.mark_interrupted()
        if self.provider is not None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nai-gen")

    def stop(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None

    def submit(self, user_id: str, request: GenerationRequest) -> str | None:
        if self._executor is None:
            raise RuntimeError("Generation provider not configured")
        if not self._capacity.acquire(blocking=False):
            return None
        try:
            seed = request.seed if request.seed is not None else secrets.randbelow(4294967295) + 1
            parameters = request.model_copy(update={"seed": seed})
            job_id = self.store.create(user_id, parameters)
            self._executor.submit(self._run, job_id, user_id, parameters)
            return job_id
        except BaseException:
            self._capacity.release()
            raise

    def _run(self, job_id: str, user_id: str, parameters: GenerationRequest) -> None:
        try:
            if not self.store.mark_running(job_id):
                return
            try:
                images = self.provider.generate(parameters) if self.provider else ()
                if len(images) != parameters.sample_count:
                    self.store.finish(job_id, error_code="invalid_result")
                    return
                if not self.cache.put(job_id, user_id, images):
                    self.store.finish(job_id, error_code="invalid_result")
                    return
                if not self.store.finish(job_id, image_count=len(images)):
                    self.cache.discard(job_id)
            except ProviderFailure as exception:
                self.cache.discard(job_id)
                self.store.finish(job_id, error_code=exception.code)
            except Exception:
                self.cache.discard(job_id)
                self.store.finish(job_id, error_code="upstream_error")
        finally:
            self._capacity.release()
