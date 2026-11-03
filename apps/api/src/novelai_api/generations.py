"""Owner-scoped generation history, experiment metadata and bounded image results."""

from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Protocol, Self, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator

from .db import Database
from .prompt_comments import compile_prompt_comments
from .prompt_sections import PromptSections

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_TRAILER = b"\x00\x00\x00\x00IEND\xaeB`\x82"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_RESULT_BYTES = 32 * 1024 * 1024
MAX_CACHED_BYTES = 64 * 1024 * 1024
RESULT_TTL_SECONDS = 10 * 60
NATIVE_CHARACTER_MODELS = frozenset(
    {
        "nai-diffusion-4-full",
        "nai-diffusion-4-curated-preview",
        "nai-diffusion-4-5-full",
        "nai-diffusion-4-5-curated",
        "nai-diffusion-5-full",
        "nai-diffusion-5-curated",
    }
)


class CharacterPrompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=3000)
    x: float = Field(default=0.5, ge=0.1, le=0.9, allow_inf_nan=False, strict=True)
    y: float = Field(default=0.5, ge=0.1, le=0.9, allow_inf_nan=False, strict=True)

    @field_validator("prompt")
    @classmethod
    def nonblank_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Character prompt cannot be blank")
        return value


VIBE_MODELS = NATIVE_CHARACTER_MODELS - {"nai-diffusion-5-full", "nai-diffusion-5-curated"}
# GPT image groups are independent of NovelAI: these neutral values fill the NAI-only fields.
GPT_IMAGE_SIZES = frozenset({(1024, 1024), (1024, 1536), (1536, 1024)})
GPT_SAMPLER = "gpt-image"


class ReferenceImageUse(BaseModel):
    id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReferenceUse(BaseModel):
    """Frozen reference images for one dataset group; bytes stay in the private store."""

    mode: Literal["vibe", "img2img", "gpt"]
    images: list[ReferenceImageUse] = Field(min_length=1, max_length=4)
    strength: float | None = Field(default=None, ge=0.01, le=0.99, allow_inf_nan=False)
    noise: float | None = Field(default=None, ge=0, le=0.99, allow_inf_nan=False)
    # Vibe only: encode_vibe information_extracted; absent means the upstream default 1.0.
    information_extracted: float | None = Field(
        default=None, ge=0.01, le=1.0, allow_inf_nan=False,
        exclude_if=lambda value: value is None,
    )
    # Vibe only: generation-time influence (generate_image.reference_strengths), default 1.0.
    reference_strength: float | None = Field(
        default=None, ge=0.01, le=1.0, allow_inf_nan=False,
        exclude_if=lambda value: value is None,
    )
    # GPT only: relay image quality; absent means the model's automatic choice.
    gpt_quality: Literal["low", "medium", "high"] | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def valid_mode(self) -> Self:
        nai_tuning = (self.strength, self.noise, self.information_extracted,
                      self.reference_strength)
        if self.mode == "gpt" and any(value is not None for value in nai_tuning):
            raise ValueError("GPT image mode has no NovelAI reference settings")
        if self.mode != "gpt" and self.gpt_quality is not None:
            raise ValueError("Only GPT image mode has gpt_quality")
        if self.mode == "img2img" and (len(self.images) != 1 or self.strength is None
                                       or self.noise is None
                                       or self.information_extracted is not None
                                       or self.reference_strength is not None):
            raise ValueError("Image-to-image uses one image with strength and noise")
        if self.mode == "vibe" and (self.strength is not None or self.noise is not None):
            raise ValueError("Vibe transfer has no strength or noise")
        return self

    @property
    def vibe_information(self) -> float:
        return 1.0 if self.information_extracted is None else self.information_extracted


PositiveDecimal = Annotated[str, Field(min_length=1, max_length=1000, pattern=r"^[1-9][0-9]*$")]


class ExperimentWeight(BaseModel):
    tag_index: int = Field(ge=0, le=2999, strict=True)
    label: str = Field(min_length=1, max_length=3000)
    weight: str = Field(
        min_length=1, max_length=100, pattern=r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$",
    )

    @field_validator("label")
    @classmethod
    def nonblank_label(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Weight label cannot be blank")
        return value


class DatasetItem(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    prompt: str = Field(min_length=1, max_length=1000)
    # Multi-person items: one native character prompt per person (scene stays in `prompt`),
    # so each person's hair and clothing colours stay bound to that person. Absent on
    # single-person items and on every stored legacy item.
    characters: list[CharacterPrompt] = Field(
        default_factory=list, max_length=6, exclude_if=lambda value: not value,
    )

    @field_validator("prompt")
    @classmethod
    def nonblank_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Dataset prompt cannot be blank")
        return value

    @field_validator("characters")
    @classmethod
    def bounded_characters(cls, value: list[CharacterPrompt]) -> list[CharacterPrompt]:
        if any(len(character.prompt) > 1000 for character in value):
            raise ValueError("Dataset character prompt exceeds 1000 characters")
        return value


class ExperimentContext(BaseModel):
    id: UUID
    ordinal: PositiveDecimal
    total: PositiveDecimal
    # Absent kind is a style weight group; stored style rows never carry these fields.
    kind: Literal["dataset"] | None = Field(default=None, exclude_if=lambda value: value is None)
    item: DatasetItem | None = Field(default=None, exclude_if=lambda value: value is None)
    weights: list[ExperimentWeight] = Field(default_factory=list, max_length=1500)

    @model_validator(mode="after")
    def valid_context(self) -> Self:
        if (len(self.ordinal), self.ordinal) > (len(self.total), self.total):
            raise ValueError("Experiment ordinal exceeds total")
        if self.kind is None and (self.item is not None or not self.weights):
            raise ValueError("Style experiment groups require weights only")
        if self.kind == "dataset" and (self.item is None or self.weights):
            raise ValueError("Dataset groups require one item and no weights")
        if len({weight.tag_index for weight in self.weights}) != len(self.weights):
            raise ValueError("Duplicate experiment tag index")
        if sum(len(weight.label) for weight in self.weights) > 3000:
            raise ValueError("Experiment labels exceed budget")
        return self


class GenerationRequest(BaseModel):
    positive_prompt: str = Field(max_length=3000)
    style_prompt: str = Field(default="", max_length=3000)
    character_prompts: list[CharacterPrompt] = Field(default_factory=list, max_length=6)
    auto_character_position: bool = Field(default=False, strict=True)
    prompt_comments: bool = Field(default=False, strict=True, exclude_if=lambda value: not value)
    prompt_sections: PromptSections | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
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
    experiment: ExperimentContext | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    reference: ReferenceUse | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )

    @field_validator("model", "sampler")
    @classmethod
    def nonempty_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Required generation text cannot be blank")
        return value

    @property
    def effective_style_prompt(self) -> str:
        return (
            compile_prompt_comments(self.style_prompt)
            if self.prompt_comments else self.style_prompt
        )

    @property
    def effective_positive_prompt(self) -> str:
        # Section fields already contain the independently compiled projection.
        if self.prompt_comments and self.prompt_sections is None:
            return compile_prompt_comments(self.positive_prompt)
        return self.positive_prompt

    @property
    def effective_negative_prompt(self) -> str:
        return (
            compile_prompt_comments(self.negative_prompt)
            if self.prompt_comments else self.negative_prompt
        )

    @property
    def effective_character_prompts(self) -> list[CharacterPrompt]:
        if not self.prompt_comments or self.prompt_sections is not None:
            return self.character_prompts
        return [
            character.model_copy(update={"prompt": prompt})
            for character in self.character_prompts
            if (prompt := compile_prompt_comments(character.prompt)).strip()
        ]

    @property
    def base_prompt(self) -> str:
        style, positive = self.effective_style_prompt, self.effective_positive_prompt
        if not style.strip():
            return positive
        return ", ".join(
            part.strip() for part in (style, positive) if part.strip()
        )

    @model_validator(mode="after")
    def valid_prompt_structure(self) -> Self:
        if self.prompt_sections is not None:
            if self.positive_prompt != self.prompt_sections.shared.compose(
                prompt_comments=self.prompt_comments,
            ):
                raise ValueError("Shared prompt differs from section metadata")
            if [character.model_dump() for character in self.character_prompts] != (
                self.prompt_sections.effective_characters(prompt_comments=self.prompt_comments)
            ):
                raise ValueError("Character prompts differ from section metadata")
        base = self.base_prompt
        if not base.strip() or len(base) > 3000:
            raise ValueError("Combined style and shared prompt must contain 1 to 3000 characters")
        if self.effective_character_prompts and self.model not in NATIVE_CHARACTER_MODELS:
            raise ValueError("Model does not support native character prompts")
        if self.reference is not None:
            if self.effective_character_prompts:
                raise ValueError("Reference generation does not use native character prompts")
            if self.reference.mode == "gpt" and (
                (self.width, self.height) not in GPT_IMAGE_SIZES or self.sampler != GPT_SAMPLER
                or self.steps != 1 or self.cfg_scale != 0 or self.quality
                or self.negative_prompt
            ):
                raise ValueError("GPT image groups use only GPT sizes and no NovelAI settings")
            if self.reference.mode == "vibe" and self.model not in VIBE_MODELS:
                raise ValueError("Vibe transfer requires a V4 or V4.5 model")
        return self


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    mime_type: str


class ImageProvider(Protocol):
    def generate(self, parameters: GenerationRequest) -> Sequence[GeneratedImage]: ...


class VibeTokens(Protocol):
    """Owner-bound cache of encoded vibe tokens keyed by image digest and encode settings."""

    def get(self, sha256: str, model: str, information: float) -> str | None: ...

    def put(self, sha256: str, model: str, information: float, token: str) -> None: ...


@runtime_checkable
class RequestRecordingImageProvider(ImageProvider, Protocol):
    def generate_with_request(
        self, parameters: GenerationRequest, record_request: Callable[[dict[str, Any]], None],
        *, references: Sequence[bytes] = (), vibe_tokens: VibeTokens | None = None,
    ) -> Sequence[GeneratedImage]: ...


class ProviderFailure(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


_NOT_LOADED = object()


class HistoryItem(BaseModel):
    id: str
    parameters: GenerationRequest
    status: Literal["queued", "running", "succeeded", "failed"]
    created_at: int
    updated_at: int
    effective_seed: int
    error_code: str | None
    image_count: int
    # Raw provider snapshot from the same row read; not part of the list contract.
    _provider_request_json: str | None | object = PrivateAttr(default=_NOT_LOADED)


class GenerationView(HistoryItem):
    image_urls: list[str]
    result_expires_at: int | None
    provider_request: dict[str, Any] | None = None
    # Owner review marks: exports skip these image indexes; files are kept.
    discarded_images: list[int] = Field(default_factory=list)


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    next_offset: int | None


class ExperimentSummary(BaseModel):
    id: str
    kind: Literal["style", "dataset"] = "style"
    total: str
    group_count: int
    completed_count: int
    image_count: int
    created_at: int
    updated_at: int


class ExperimentPage(BaseModel):
    items: list[ExperimentSummary]
    next_offset: int | None


class ExperimentDetail(BaseModel):
    summary: ExperimentSummary
    items: list[GenerationView]
    next_offset: int | None


class ExperimentConflict(Exception):
    """The transaction refused duplicate or inconsistent run metadata."""


# Metadata is validated before write, and checked again when reading old/private DBs.
# Decimal strings stay strings: SQLite INTEGER/REAL cannot order arbitrary ordinals.
EXPERIMENT_ROWS = """
WITH experiment_rows AS (
    SELECT *, json_extract(settings_json, '$.experiment.id') AS experiment_id,
        json_extract(settings_json, '$.experiment.ordinal') AS ordinal,
        json_extract(settings_json, '$.experiment.total') AS total
    FROM generation_jobs
    WHERE user_id = ? AND json_valid(settings_json)
        AND json_type(settings_json, '$.experiment') = 'object'
        AND valid_experiment(settings_json) = 1
)
"""
EXPERIMENT_SUMMARY = """
SELECT experiment_id AS id,
    COALESCE(MAX(json_extract(settings_json, '$.experiment.kind')), 'style') AS kind,
    total, COUNT(*) AS group_count,
    SUM(CASE WHEN status IN ('succeeded', 'failed') THEN 1 ELSE 0 END) AS completed_count,
    SUM(image_count) AS image_count, MIN(created_at) AS created_at,
    MAX(updated_at) AS updated_at
FROM experiment_rows
"""


def _valid_experiment(settings_json: str) -> int:
    try:
        data = json.loads(settings_json)
        ExperimentContext.model_validate(data.get("experiment"))
    except (ValueError, TypeError, AttributeError):
        return 0
    return 1


def _experiment_connection(connection: sqlite3.Connection) -> None:
    connection.create_function("valid_experiment", 1, _valid_experiment, deterministic=True)


class JobStore:
    def __init__(self, database: Database):
        self.database = database

    def create(self, user_id: str, parameters: GenerationRequest) -> str:
        with self.database.connect(write=True) as connection:
            return self.create_in_transaction(connection, user_id, parameters)

    @staticmethod
    def create_in_transaction(
        connection: sqlite3.Connection, user_id: str, parameters: GenerationRequest,
        *, run_claim: bool = False,
    ) -> str:
        job_id = str(uuid4())
        now = int(time.time())
        if parameters.experiment is not None:
            _experiment_connection(connection)
            context = parameters.experiment
            server_run = connection.execute(
                "SELECT 1 FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, str(context.id)),
            ).fetchone()
            conflict = connection.execute(
                EXPERIMENT_ROWS + "SELECT 1 FROM experiment_rows WHERE experiment_id = ? "
                "AND (ordinal = ? OR total != ?) LIMIT 1",
                (user_id, str(context.id), context.ordinal, context.total),
            ).fetchone()
            # Dataset groups exist only as claims of a durable server-owned run.
            dataset = context.kind == "dataset" and not run_claim
            if conflict or dataset or (server_run and not run_claim):
                raise ExperimentConflict("Conflicting experiment group")
        connection.execute(
            "INSERT INTO generation_jobs "
            "(id, user_id, positive_prompt, negative_prompt, settings_json, effective_seed, "
            "status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?)",
            (
                job_id, user_id, parameters.positive_prompt, parameters.negative_prompt,
                parameters.model_dump_json(), parameters.seed, now, now,
            )
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

    def record_provider_request(
        self, user_id: str, job_id: str, arguments: dict[str, Any],
    ) -> bool:
        with self.database.connect(write=True) as connection:
            updated = connection.execute(
                "UPDATE generation_jobs SET provider_request_json = ? "
                "WHERE id = ? AND user_id = ? AND status = 'running' "
                "AND provider_request_json IS NULL",
                (json.dumps(arguments, ensure_ascii=False, allow_nan=False), job_id, user_id),
            )
        return bool(updated.rowcount)

    def set_discarded(self, user_id: str, job_id: str, index: int, discarded: bool) -> None:
        with self.database.connect(write=True) as connection:
            if discarded:
                connection.execute(
                    "INSERT OR IGNORE INTO discarded_images (user_id, job_id, image_index, "
                    "created_at) VALUES (?, ?, ?, ?)", (user_id, job_id, index, int(time.time())),
                )
            else:
                connection.execute(
                    "DELETE FROM discarded_images WHERE user_id = ? AND job_id = ? "
                    "AND image_index = ?", (user_id, job_id, index),
                )

    def discarded(self, user_id: str, job_ids: Sequence[str]) -> dict[str, list[int]]:
        marks: dict[str, list[int]] = {job_id: [] for job_id in job_ids}
        if not job_ids:
            return marks
        with self.database.connect() as connection:
            for start in range(0, len(job_ids), 500):
                chunk = list(job_ids[start:start + 500])
                rows = connection.execute(
                    "SELECT job_id, image_index FROM discarded_images WHERE user_id = ? "
                    f"AND job_id IN ({','.join('?' * len(chunk))}) ORDER BY image_index",
                    (user_id, *chunk),
                ).fetchall()
                for row in rows:
                    marks[row["job_id"]].append(row["image_index"])
        return marks

    def provider_request(self, user_id: str, job_id: str) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT provider_request_json FROM generation_jobs WHERE id = ? AND user_id = ?",
                (job_id, user_id),
            ).fetchone()
        if row is None or row["provider_request_json"] is None:
            return None
        return json.loads(row["provider_request_json"])

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

    def list(
        self, user_id: str, *, limit: int, offset: int, manual_only: bool = False,
    ) -> HistoryPage:
        # Manual jobs are ordinary submissions: no style-experiment or dataset metadata.
        manual = (
            " AND json_extract(settings_json, '$.experiment') IS NULL" if manual_only else ""
        )
        with self.database.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM generation_jobs WHERE user_id = ?{manual} "
                "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                (user_id, limit + 1, offset),
            ).fetchall()
        return HistoryPage(
            items=[self._item(row) for row in rows[:limit]],
            next_offset=offset + limit if len(rows) > limit else None,
        )

    def experiments(self, user_id: str, *, limit: int, offset: int) -> ExperimentPage:
        with self.database.connect() as connection:
            _experiment_connection(connection)
            rows = connection.execute(
                EXPERIMENT_ROWS + EXPERIMENT_SUMMARY +
                " GROUP BY experiment_id, total ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                (user_id, limit + 1, offset),
            ).fetchall()
        return ExperimentPage(
            items=[ExperimentSummary(**dict(row)) for row in rows[:limit]],
            next_offset=offset + limit if len(rows) > limit else None,
        )

    def experiment(
        self, user_id: str, experiment_id: str, *, limit: int, offset: int,
    ) -> tuple[ExperimentSummary, list[HistoryItem], int | None] | None:
        with self.database.connect() as connection:
            _experiment_connection(connection)
            summary = connection.execute(
                EXPERIMENT_ROWS + EXPERIMENT_SUMMARY +
                " WHERE experiment_id = ? GROUP BY experiment_id, total",
                (user_id, experiment_id),
            ).fetchone()
            if summary is None:
                return None
            rows = connection.execute(
                EXPERIMENT_ROWS + "SELECT * FROM experiment_rows WHERE experiment_id = ? "
                "ORDER BY length(ordinal), ordinal, id LIMIT ? OFFSET ?",
                (user_id, experiment_id, limit + 1, offset),
            ).fetchall()
        return (
            ExperimentSummary(**dict(summary)), [self._item(row) for row in rows[:limit]],
            offset + limit if len(rows) > limit else None,
        )

    def delete(self, user_id: str, job_id: str) -> str | None:
        with self.database.connect(write=True) as connection:
            row = connection.execute(
                "SELECT status, settings_json FROM generation_jobs WHERE id = ? AND user_id = ?",
                (job_id, user_id),
            ).fetchone()
            if row is None:
                return None
            if row["status"] in ("queued", "running"):
                return "active"
            if _valid_experiment(row["settings_json"]):
                context_id = json.loads(row["settings_json"])["experiment"]["id"]
                active = connection.execute(
                    "SELECT 1 FROM style_experiment_runs WHERE user_id = ? AND id = ? "
                    "AND status IN ('running', 'stopping')", (user_id, context_id),
                ).fetchone()
                if active:
                    return "experiment_active"
            connection.execute(
                "DELETE FROM generation_jobs WHERE id = ? AND user_id = ?", (job_id, user_id)
            )
        return "deleted"

    @staticmethod
    def _item(row: sqlite3.Row) -> HistoryItem:
        item = HistoryItem(
            id=row["id"],
            parameters=GenerationRequest.model_validate(json.loads(row["settings_json"])),
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            effective_seed=row["effective_seed"],
            error_code=row["error_code"],
            image_count=row["image_count"],
        )
        if "provider_request_json" in row.keys():
            item._provider_request_json = row["provider_request_json"]
        return item


@dataclass
class CachedResult:
    user_id: str
    images: tuple[GeneratedImage, ...]
    expires_at: int
    deadline: float
    size: int


@dataclass(frozen=True)
class ResultInfo:
    image_count: int
    expires_at: int


def valid_images(images: Sequence[GeneratedImage]) -> bool:
    return (
        1 <= len(images) <= 8
        and all(
            isinstance(image, GeneratedImage)
            and image.mime_type == "image/png"
            and isinstance(image.data, bytes)
            and image.data.startswith(PNG_SIGNATURE)
            and 45 <= len(image.data) <= MAX_IMAGE_BYTES
            and image.data[12:16] == b"IHDR"
            and image.data.endswith(PNG_TRAILER)
            for image in images
        )
        and sum(len(image.data) for image in images) <= MAX_RESULT_BYTES
    )


class ResultStorageUnavailable(Exception):
    """Storage refused admission before seed/history/provider work."""


class ResultStore(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def reserve(self, sample_count: int) -> str: ...
    def release(self, reservation: str) -> None: ...
    def put(self, job_id: str, user_id: str, images: Sequence[GeneratedImage]) -> bool: ...
    def describe(self, job_id: str, user_id: str) -> ResultInfo | None: ...
    def image(self, job_id: str, user_id: str, index: int) -> GeneratedImage | None: ...
    def discard(self, job_id: str) -> None: ...


class ResultCache:
    def __init__(self, *, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._results: dict[str, CachedResult] = {}
        self._size = 0
        self._lock = threading.Lock()

    def put(self, job_id: str, user_id: str, images: Sequence[GeneratedImage]) -> bool:
        if not valid_images(images):
            return False
        size = sum(len(image.data) for image in images)
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

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def reserve(self, sample_count: int) -> str:
        return str(uuid4())

    def release(self, reservation: str) -> None:
        pass

    def describe(self, job_id: str, user_id: str) -> ResultInfo | None:
        result = self.get(job_id, user_id)
        return ResultInfo(len(result.images), result.expires_at) if result else None

    def image(self, job_id: str, user_id: str, index: int) -> GeneratedImage | None:
        result = self.get(job_id, user_id)
        return result.images[index] if result and 0 <= index < len(result.images) else None

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


class GenerationNotConfigured(RuntimeError):
    """No executor exists, so submission has performed no work."""


class _Admission:
    """One idempotent release for worker, cancelled future and enqueue failure."""

    def __init__(self, release: Callable[[], None]):
        self._release = release
        self._lock = threading.Lock()
        self._started = False
        self._released = False

    def begin(self) -> bool:
        with self._lock:
            if self._released:
                return False
            self._started = True
            return True

    @property
    def live(self) -> bool:
        with self._lock:
            return not self._released

    def finish(self, *, only_if_pending: bool = False) -> None:
        with self._lock:
            if self._released or (only_if_pending and self._started):
                return
            self._released = True
            self._release()


class GenerationManager:
    def __init__(
        self,
        database: Database,
        provider: ImageProvider | None,
        *,
        cache: ResultStore | None = None,
        references: Callable[[str, str, str], bytes | None] | None = None,
        vibe_tokens: Callable[[str], VibeTokens] | None = None,
        gpt_provider: ImageProvider | None = None,
    ):
        from .image_results import DiskResultStore
        from .reference_images import ReferenceImageStore

        self.store = JobStore(database)
        self.provider = provider
        # GPT image groups never touch the NovelAI provider.
        self.gpt_provider = gpt_provider
        store = ReferenceImageStore(database)
        # Encoded vibes are paid once per image/model/information and reused across groups.
        self.vibe_tokens = vibe_tokens or store.vibe_tokens
        if references is None:
            def references(user_id: str, image_id: str, sha256: str) -> bytes | None:
                found = store.read(user_id, image_id)
                return found[1] if found is not None and found[0].sha256 == sha256 else None
        # Returns bytes only when the owner's stored image still matches the frozen digest.
        self.references = references
        self.cache = cache if cache is not None else DiskResultStore(
            database.path.parent / "generation-images",
        )
        self._capacity = threading.BoundedSemaphore(3)
        self._executor: ThreadPoolExecutor | None = None
        self._work_lock = threading.Lock()
        self._working: dict[str, _Admission] = {}

    def start(self) -> None:
        self.store.mark_interrupted()
        self.cache.start()
        if self.provider is not None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nai-gen")

    def stop(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
        self.cache.stop()

    def views(self, jobs: Sequence[HistoryItem], user_id: str) -> list[GenerationView]:
        """Batch the discard lookup for pages instead of one query per job."""
        marks = self.store.discarded(user_id, [job.id for job in jobs])
        return [self.view(job, user_id, discarded=marks[job.id]) for job in jobs]

    def view(
        self, job: HistoryItem, user_id: str, *, discarded: list[int] | None = None,
    ) -> GenerationView:
        result = self.cache.describe(job.id, user_id) if job.status == "succeeded" else None
        raw_request = job._provider_request_json
        if raw_request is _NOT_LOADED:
            provider_request = self.store.provider_request(user_id, job.id)
        else:
            provider_request = json.loads(raw_request) if raw_request is not None else None
        return GenerationView(
            **job.model_dump(),
            image_urls=[f"/api/generation-results/{job.id}/images/{index}"
                        for index in range(result.image_count)] if result else [],
            result_expires_at=result.expires_at if result else None,
            provider_request=provider_request,
            discarded_images=(
                discarded if discarded is not None
                else self.store.discarded(user_id, [job.id])[job.id]
            ),
        )

    def is_inflight(self, job_id: str) -> bool:
        with self._work_lock:
            admission = self._working.get(job_id)
        return admission is not None and admission.live

    def _forget(self, job_id: str) -> None:
        with self._work_lock:
            self._working.pop(job_id, None)

    def submit(
        self, user_id: str, request: GenerationRequest,
        *, create: Callable[[str, GenerationRequest], str | None] | None = None,
    ) -> str | None:
        if self._executor is None:
            raise GenerationNotConfigured("Generation provider not configured")
        if not self._capacity.acquire(blocking=False):
            return None
        try:
            reservation = self.cache.reserve(request.sample_count)
        except BaseException:
            self._capacity.release()
            raise

        def release() -> None:
            self.cache.release(reservation)
            self._capacity.release()

        admission = _Admission(release)
        job_id = None
        try:
            seed = request.seed if request.seed is not None else secrets.randbelow(4294967295) + 1
            parameters = request.model_copy(update={"seed": seed})
            with self._work_lock:
                job_id = (create or self.store.create)(user_id, parameters)
                if job_id is not None:
                    self._working[job_id] = admission
            if job_id is None:
                admission.finish()
                return None
            future = self._executor.submit(self._run, job_id, user_id, parameters, admission)

            def cancelled(finished) -> None:
                if finished.cancelled():
                    admission.finish(only_if_pending=True)
                    self._forget(job_id)

            future.add_done_callback(cancelled)
            return job_id
        except BaseException:
            admission.finish(only_if_pending=True)
            if job_id is not None and not admission.live:
                self._forget(job_id)
            raise

    def _run(
        self, job_id: str, user_id: str, parameters: GenerationRequest, admission: _Admission,
    ) -> None:
        if not admission.begin():
            self._forget(job_id)
            return
        try:
            if not self.store.mark_running(job_id):
                return
            try:
                def record_request(arguments: dict[str, Any]) -> None:
                    if not self.store.record_provider_request(user_id, job_id, arguments):
                        raise RuntimeError("Provider request could not be recorded")

                if parameters.reference is not None:
                    references = [
                        self.references(user_id, image.id, image.sha256)
                        for image in parameters.reference.images
                    ]
                    if any(data is None for data in references):
                        self.store.finish(job_id, error_code="reference_unavailable")
                        return
                    provider = (
                        self.gpt_provider if parameters.reference.mode == "gpt" else self.provider
                    )
                    if provider is None and parameters.reference.mode == "gpt":
                        self.store.finish(job_id, error_code="gpt_image_unavailable")
                        return
                    if not isinstance(provider, RequestRecordingImageProvider):
                        self.store.finish(job_id, error_code="unsupported_reference_mode")
                        return
                    images = provider.generate_with_request(
                        parameters, record_request, references=references,
                        vibe_tokens=self.vibe_tokens(user_id),
                    )
                elif isinstance(self.provider, RequestRecordingImageProvider):
                    images = self.provider.generate_with_request(parameters, record_request)
                else:
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
            except ResultStorageUnavailable:
                self.cache.discard(job_id)
                self.store.finish(job_id, error_code="result_storage_error")
            except Exception:
                self.cache.discard(job_id)
                self.store.finish(job_id, error_code="upstream_error")
        finally:
            admission.finish()
            self._forget(job_id)
