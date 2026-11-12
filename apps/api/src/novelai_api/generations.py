"""Owner-scoped generation history, experiment metadata and bounded image results."""

from __future__ import annotations

import json
import logging
import re
import secrets
import sqlite3
import threading
import time
import unicodedata
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Protocol, Self, runtime_checkable
from uuid import UUID, uuid4

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from .db import Database
from .lane_health import LaneHealth
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


logger = logging.getLogger(__name__)


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
# NovelAI documents Precise Reference (director reference) for V4.5 only.
PRECISE_MODELS = frozenset({"nai-diffusion-4-5-full", "nai-diffusion-4-5-curated"})
# GPT image groups are independent of NovelAI: these neutral values fill the NAI-only fields.
GPT_IMAGE_SIZES = frozenset({(1024, 1024), (1024, 1536), (1536, 1024)})
GPT_SAMPLER = "gpt-image"
# Upper bound for concurrent GPT image calls (15 concurrent calls verified on the relay).
MAX_GPT_PARALLELISM = 16


class ReferenceImageUse(BaseModel):
    id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReferenceUse(BaseModel):
    """Frozen reference images for one dataset group; bytes stay in the private store."""

    mode: Literal["vibe", "img2img", "gpt", "precise"]
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
    # Precise Reference only (NovelAI director reference, V4.5): what to copy from the
    # one image, how strongly, and fidelity (sent upstream as 1 - fidelity).
    precise_type: Literal["character", "style", "character&style"] | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    precise_strength: float | None = Field(
        default=None, ge=0.01, le=1.0, allow_inf_nan=False,
        exclude_if=lambda value: value is None,
    )
    precise_fidelity: float | None = Field(
        default=None, ge=0, le=1.0, allow_inf_nan=False,
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def valid_mode(self) -> Self:
        precise = (self.precise_type, self.precise_strength, self.precise_fidelity)
        if self.mode != "precise" and any(value is not None for value in precise):
            raise ValueError("Only Precise Reference has precise settings")
        if self.mode == "precise" and (
            len(self.images) != 1 or self.precise_type is None
            or self.precise_strength is None or self.precise_fidelity is None
            or self.strength is not None or self.noise is not None
            or self.information_extracted is not None or self.reference_strength is not None
            or self.gpt_quality is not None
        ):
            raise ValueError("Precise Reference uses one image with type, strength and fidelity")
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


_DRAW_ID = r"^-?[a-z0-9][a-z0-9-]*$"

class DatasetDraw(BaseModel):
    """One frozen recipe draw: ids for filtering plus a label snapshot for display."""

    model_config = ConfigDict(extra="forbid")

    partition: str = Field(min_length=1, max_length=64, pattern=_DRAW_ID)
    option: str = Field(min_length=1, max_length=64, pattern=_DRAW_ID)
    label: str = Field(min_length=1, max_length=100)
    values: dict[str, str] | None = Field(default=None, exclude_if=lambda value: value is None)
    reason: str | None = Field(
        default=None, max_length=100, exclude_if=lambda value: value is None,
    )

    @field_validator("values")
    @classmethod
    def valid_values(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is not None and (len(value) > 20 or any(
            not re.fullmatch(r"[a-z0-9][a-z0-9-]*", key)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", item)
            or len(key) > 64 or len(item) > 64
            for key, item in value.items()
        )):
            raise ValueError("Draw slot values must be ids")
        return value

StyleTag = Annotated[str, Field(min_length=1, max_length=100)]

class StyleEdits(BaseModel):
    """Plain tags removed from / appended to this item's style before it is sent."""

    model_config = ConfigDict(extra="forbid")

    add: list[StyleTag] = Field(default_factory=list, max_length=32)
    remove: list[StyleTag] = Field(default_factory=list, max_length=128)

    @field_validator("add", "remove")
    @classmethod
    def plain_tags(cls, value: list[str]) -> list[str]:
        for tag in value:
            if not tag.strip() or re.search(r"[,\n{}\[\]]|::|//", tag):
                raise ValueError("Style edits must be plain single tags")
        return value

class RecipeRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # A string (not UUID) because run definitions are serialized with python-mode dumps.
    id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    name: str = Field(min_length=1, max_length=100)

class DatasetItem(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    prompt: str = Field(min_length=1, max_length=1000)
    # Multi-person items: one native character prompt per person (scene stays in `prompt`),
    # so each person's hair and clothing colours stay bound to that person. Absent on
    # single-person items and on every stored legacy item.
    characters: list[CharacterPrompt] = Field(
        default_factory=list, max_length=6, exclude_if=lambda value: not value,
    )
    # Optional per-item canvas (both or neither), e.g. portrait for full-body items and
    # landscape for wide scenery. Absent keeps the run's size, so stored items are unchanged.
    width: int | None = Field(
        default=None, ge=64, le=2048, multiple_of=64, exclude_if=lambda value: value is None,
    )
    height: int | None = Field(
        default=None, ge=64, le=2048, multiple_of=64, exclude_if=lambda value: value is None,
    )

    # Random-recipe items only (all optional, excluded when empty so stored legacy items
    # stay byte-identical): what the recipe drew (review filtering), per-item style tag
    # edits applied on top of the run's style (never captioned) and the source recipe.
    draws: list[DatasetDraw] = Field(
        default_factory=list, max_length=128, exclude_if=lambda value: not value,
    )
    style_edits: StyleEdits | None = Field(default=None, exclude_if=lambda value: value is None)
    recipe: RecipeRef | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def paired_size(self) -> Self:
        if (self.width is None) != (self.height is None):
            raise ValueError("Dataset item width and height go together")
        if self.style_edits is not None and self.characters:
            raise ValueError("Style edits are only for single-person recipe items")
        return self

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
    # Dataset only: an owner-requested re-generation of this ordinal with a new random
    # seed. Names the job it replaces; the run's own group for the ordinal stays intact.
    rerun_of: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def valid_context(self) -> Self:
        if (len(self.ordinal), self.ordinal) > (len(self.total), self.total):
            raise ValueError("Experiment ordinal exceeds total")
        if self.rerun_of is not None and self.kind != "dataset":
            raise ValueError("Only dataset groups can be re-run")
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
            if self.reference.mode == "precise" and self.model not in PRECISE_MODELS:
                raise ValueError("Precise Reference requires a V4.5 model")
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


class _ForeignCaption(Exception):
    """A caption edit named a job outside the owner's training set (rolls back the batch)."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(job_id)


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
    # Original indexes remain stable after irreversible cleanup, including pending unlinks.
    purged_images: list[int] = Field(default_factory=list)
    purge_pending_images: list[int] = Field(default_factory=list)
    # Owner-edited training caption (content tags) of a training-set group; None = derived.
    caption_override: str | None = None


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    next_offset: int | None


MAX_EXPERIMENT_NAME = 80


def _clean_experiment_name(value: str | None) -> str | None:
    """Collapse whitespace; blank means unnamed. Control/format characters are refused."""
    if value is None:
        return None
    text = " ".join(value.split())
    if any(unicodedata.category(char) in ("Cc", "Cf", "Cs", "Co", "Cn") for char in text):
        raise ValueError("Name contains control characters")
    if len(text) > MAX_EXPERIMENT_NAME:
        raise ValueError(f"Name is longer than {MAX_EXPERIMENT_NAME} characters")
    return text or None


ExperimentName = Annotated[str | None, AfterValidator(_clean_experiment_name)]


class ExperimentDeleted(BaseModel):
    deleted_groups: int
    deleted_images: int


class DiscardedImagesDeleted(BaseModel):
    deleted_images: int = 0
    missing_images: int = 0
    failed_images: int = 0


class ExperimentRename(BaseModel):
    name: ExperimentName = Field(max_length=400)


class ExperimentSummary(BaseModel):
    id: str
    kind: Literal["style", "dataset"] = "style"
    total: str
    group_count: int
    completed_count: int
    image_count: int
    created_at: int
    updated_at: int
    # Owner display name; absent for unnamed (older) sets.
    name: str | None = None
    # Training sets only: character sets carry reference images, style sets do not.
    dataset_type: Literal["style", "character"] | None = None
    # Cover: the lowest-ordinal succeeded group whose first image is not discarded (its
    # image may since have expired; clients hide a missing thumbnail).
    cover_job_id: str | None = None


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
    SELECT *, rowid AS row_order, json_extract(settings_json, '$.experiment.id') AS experiment_id,
        json_extract(settings_json, '$.experiment.ordinal') AS ordinal,
        json_extract(settings_json, '$.experiment.total') AS total,
        json_extract(settings_json, '$.experiment.rerun_of') AS rerun_of
    FROM generation_jobs
    WHERE user_id = ? AND json_valid(settings_json)
        AND json_type(settings_json, '$.experiment') = 'object'
        AND valid_experiment(settings_json) = 1
)
"""
EXPERIMENT_SUMMARY = """
SELECT experiment_id AS id,
    COALESCE(MAX(json_extract(settings_json, '$.experiment.kind')), 'style') AS kind,
    total, SUM(CASE WHEN rerun_of IS NULL THEN 1 ELSE 0 END) AS group_count,
    SUM(CASE WHEN rerun_of IS NULL AND status IN ('succeeded', 'failed') THEN 1 ELSE 0 END)
        AS completed_count,
    SUM(image_count) AS image_count, MIN(created_at) AS created_at,
    MAX(updated_at) AS updated_at, MAX(names.name) AS name,
    CASE WHEN MAX(json_extract(settings_json, '$.experiment.kind')) IS NOT 'dataset' THEN NULL
        WHEN MAX(CASE WHEN json_type(settings_json, '$.reference') = 'object' THEN 1 ELSE 0 END) = 1
        THEN 'character' ELSE 'style' END AS dataset_type,
    -- One pass: the minimum sortable key of eligible rows carries the cover job id.
    -- Ordinals are exact decimal strings of any length: order by (length, text) like
    -- the group pages, then creation order; the fixed-length UUID job id ends the key.
    substr(MIN(CASE WHEN status = 'succeeded' AND image_count > 0 AND NOT EXISTS (
        SELECT 1 FROM discarded_images AS d WHERE d.user_id = experiment_rows.user_id
            AND d.job_id = experiment_rows.id AND d.image_index = 0
    ) AND NOT EXISTS (
        SELECT 1 FROM purged_images AS p WHERE p.user_id = experiment_rows.user_id
            AND p.job_id = experiment_rows.id AND p.image_index = 0
    ) THEN printf('%06d', length(ordinal)) || ordinal || printf('%012d', row_order) || id
    END), -36) AS cover_job_id
FROM experiment_rows LEFT JOIN experiment_names AS names
    ON names.user_id = experiment_rows.user_id AND names.run_id = experiment_rows.experiment_id
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

    def create_rerun(self, user_id: str, parameters: GenerationRequest) -> str:
        with self.database.connect(write=True) as connection:
            return self.create_in_transaction(connection, user_id, parameters, rerun=True)

    @staticmethod
    def create_in_transaction(
        connection: sqlite3.Connection, user_id: str, parameters: GenerationRequest,
        *, run_claim: bool = False, rerun: bool = False,
    ) -> str:
        job_id = str(uuid4())
        now = int(time.time())
        if parameters.experiment is not None and parameters.experiment.rerun_of is not None:
            _experiment_connection(connection)
            context = parameters.experiment
            # A re-run joins an existing ordinal of the owner's server-owned dataset run.
            source = connection.execute(
                EXPERIMENT_ROWS + "SELECT 1 FROM experiment_rows WHERE id = ? "
                "AND experiment_id = ? AND ordinal = ? AND total = ? "
                "AND status IN ('succeeded', 'failed') AND EXISTS (SELECT 1 FROM "
                "style_experiment_runs WHERE user_id = experiment_rows.user_id AND id = ?)",
                (user_id, context.rerun_of, str(context.id), context.ordinal, context.total,
                 str(context.id)),
            ).fetchone()
            if not rerun or source is None:
                raise ExperimentConflict("Re-run source group not found")
        elif parameters.experiment is not None:
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

    def delete_experiment(
        self, user_id: str, run_id: str,
    ) -> tuple[str, list[str], int] | None:
        """Delete one owner experiment/training set atomically.

        Returns None when unknown, else (outcome, deleted job ids, deleted image count).
        Outcomes: "deleted", "experiment_active" (its run is running/stopping) or
        "active" (a group or re-run is still queued/running). Reference images,
        snapshots and ordinary history are never touched; callers remove image files
        after this commits.
        """
        with self.database.connect(write=True) as connection:
            _experiment_connection(connection)
            run = connection.execute(
                "SELECT status FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, run_id),
            ).fetchone()
            rows = connection.execute(
                EXPERIMENT_ROWS
                + "SELECT id, status, image_count FROM experiment_rows WHERE experiment_id = ?",
                (user_id, run_id),
            ).fetchall()
            if run is None and not rows:
                return None
            if run is not None and run["status"] in ("running", "stopping"):
                return "experiment_active", [], 0
            if any(row["status"] in ("queued", "running") for row in rows):
                return "active", [], 0
            job_ids = [row["id"] for row in rows]
            for start in range(0, len(job_ids), 500):
                chunk = job_ids[start:start + 500]
                connection.execute(
                    f"DELETE FROM generation_jobs WHERE user_id = ? "
                    f"AND id IN ({','.join('?' * len(chunk))})", (user_id, *chunk),
                )
            connection.execute(
                "DELETE FROM experiment_names WHERE user_id = ? AND run_id = ?",
                (user_id, run_id),
            )
            connection.execute(
                "DELETE FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, run_id),
            )
        return "deleted", job_ids, sum(row["image_count"] or 0 for row in rows)

    def rename_experiment(self, user_id: str, run_id: str, name: str | None) -> bool:
        """Set or clear an owner's display name; False when the experiment is unknown."""
        with self.database.connect(write=True) as connection:
            known = connection.execute(
                "SELECT 1 FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, run_id),
            ).fetchone()
            if known is None:
                _experiment_connection(connection)
                known = connection.execute(
                    EXPERIMENT_ROWS
                    + "SELECT 1 FROM experiment_rows WHERE experiment_id = ? LIMIT 1",
                    (user_id, run_id),
                ).fetchone()
            if known is None:
                return False
            if name is None:
                connection.execute(
                    "DELETE FROM experiment_names WHERE user_id = ? AND run_id = ?",
                    (user_id, run_id),
                )
            else:
                connection.execute(
                    "INSERT INTO experiment_names (user_id, run_id, name, named_at) "
                    "VALUES (?, ?, ?, ?) ON CONFLICT(user_id, run_id) DO UPDATE SET "
                    "name = excluded.name, named_at = excluded.named_at",
                    (user_id, run_id, name, int(time.time())),
                )
            return True

    def set_discarded(self, user_id: str, job_id: str, index: int, discarded: bool) -> bool:
        with self.database.connect(write=True) as connection:
            if not discarded and connection.execute(
                "SELECT 1 FROM purged_images WHERE user_id = ? AND job_id = ? "
                "AND image_index = ?", (user_id, job_id, index),
            ).fetchone() is not None:
                return False
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
        return True

    def begin_discarded_cleanup(
        self, user_id: str, experiment_id: str,
    ) -> tuple[str, list[tuple[str, int]]] | None:
        """Snapshot one owner's discarded dataset identities and durably deny restore.

        Read only identity/status metadata, never materialize stored prompts. The
        immediate transaction serializes discard restoration against purge intent.
        Previously completed purges are omitted; incomplete file removal is retried.
        """
        with self.database.connect(write=True) as connection:
            run = connection.execute(
                "SELECT json_extract(definition_json, '$.kind') AS kind "
                "FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, experiment_id),
            ).fetchone()
            groups = connection.execute(
                "SELECT DISTINCT json_extract(settings_json, '$.experiment.kind') AS kind "
                "FROM generation_jobs WHERE user_id = ? AND json_valid(settings_json) "
                "AND json_extract(settings_json, '$.experiment.id') = ?",
                (user_id, experiment_id),
            ).fetchall()
            if run is None and not groups:
                return None
            if (run is not None and run["kind"] != "dataset") or any(
                group["kind"] != "dataset" for group in groups
            ):
                return "unsupported", []
            rows = connection.execute(
                "SELECT d.job_id, d.image_index FROM discarded_images AS d "
                "JOIN generation_jobs AS j ON j.id = d.job_id AND j.user_id = d.user_id "
                "LEFT JOIN purged_images AS p ON p.user_id = d.user_id "
                "AND p.job_id = d.job_id AND p.image_index = d.image_index "
                "WHERE d.user_id = ? AND j.status = 'succeeded' "
                "AND d.image_index < j.image_count AND json_valid(j.settings_json) "
                "AND json_extract(j.settings_json, '$.experiment.id') = ? "
                "AND p.completed_at IS NULL ORDER BY d.job_id, d.image_index",
                (user_id, experiment_id),
            ).fetchall()
            targets = [(row["job_id"], row["image_index"]) for row in rows]
            connection.executemany(
                "INSERT OR IGNORE INTO purged_images "
                "(user_id, job_id, image_index, created_at) VALUES (?, ?, ?, ?)",
                [(user_id, job_id, index, int(time.time())) for job_id, index in targets],
            )
        return "ready", targets

    def complete_image_purge(self, user_id: str, job_id: str, index: int) -> None:
        with self.database.connect(write=True) as connection:
            connection.execute(
                "UPDATE purged_images SET completed_at = COALESCE(completed_at, ?) "
                "WHERE user_id = ? AND job_id = ? AND image_index = ?",
                (int(time.time()), user_id, job_id, index),
            )

    def is_purged(self, user_id: str, job_id: str, index: int) -> bool:
        with self.database.connect() as connection:
            return connection.execute(
                "SELECT 1 FROM purged_images WHERE user_id = ? AND job_id = ? "
                "AND image_index = ?", (user_id, job_id, index),
            ).fetchone() is not None

    def purged(
        self, user_id: str, job_ids: Sequence[str],
    ) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
        marks: dict[str, list[int]] = {job_id: [] for job_id in job_ids}
        pending: dict[str, list[int]] = {job_id: [] for job_id in job_ids}
        if not job_ids:
            return marks, pending
        with self.database.connect() as connection:
            for start in range(0, len(job_ids), 500):
                chunk = list(job_ids[start:start + 500])
                rows = connection.execute(
                    "SELECT job_id, image_index, completed_at FROM purged_images "
                    f"WHERE user_id = ? AND job_id IN ({','.join('?' * len(chunk))}) "
                    "ORDER BY image_index", (user_id, *chunk),
                ).fetchall()
                for row in rows:
                    marks[row["job_id"]].append(row["image_index"])
                    if row["completed_at"] is None:
                        pending[row["job_id"]].append(row["image_index"])
        return marks, pending

    def caption_overrides(self, user_id: str, job_ids: Sequence[str]) -> dict[str, str]:
        captions: dict[str, str] = {}
        if not job_ids:
            return captions
        with self.database.connect() as connection:
            for start in range(0, len(job_ids), 500):
                chunk = list(job_ids[start:start + 500])
                captions.update((row["job_id"], row["caption"]) for row in connection.execute(
                    "SELECT job_id, caption FROM caption_overrides WHERE user_id = ? "
                    f"AND job_id IN ({','.join('?' * len(chunk))})", (user_id, *chunk),
                ).fetchall())
        return captions

    def set_captions(
        self, user_id: str, experiment_id: str, entries: Sequence[tuple[str, str | None]],
    ) -> str | None:
        """Set (or clear with None) caption overrides of one training set's groups in one
        transaction. Returns the first job id that is not a group of that set, else None."""
        try:
            self._set_captions(user_id, experiment_id, entries)
        except _ForeignCaption as foreign:
            return foreign.job_id  # Raised inside the transaction: nothing was written.
        return None

    def _set_captions(
        self, user_id: str, experiment_id: str, entries: Sequence[tuple[str, str | None]],
    ) -> None:
        with self.database.connect(write=True) as connection:
            now = int(time.time())
            for job_id, caption in entries:
                row = connection.execute(
                    "SELECT settings_json FROM generation_jobs WHERE id = ? AND user_id = ?",
                    (job_id, user_id),
                ).fetchone()
                context = (
                    json.loads(row["settings_json"]).get("experiment")
                    if row is not None and _valid_experiment(row["settings_json"]) else None
                )
                if not context or context.get("kind") != "dataset" or (
                    str(context.get("id")) != experiment_id
                ):
                    raise _ForeignCaption(job_id)
                if caption is None:
                    connection.execute(
                        "DELETE FROM caption_overrides WHERE user_id = ? AND job_id = ?",
                        (user_id, job_id),
                    )
                else:
                    connection.execute(
                        "INSERT INTO caption_overrides (user_id, job_id, caption, updated_at) "
                        "VALUES (?, ?, ?, ?) ON CONFLICT(user_id, job_id) DO UPDATE SET "
                        "caption = excluded.caption, updated_at = excluded.updated_at",
                        (user_id, job_id, caption, now),
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
                # Re-runs follow their ordinal's run group in creation order.
                "ORDER BY length(ordinal), ordinal, row_order LIMIT ? OFFSET ?",
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
    images: tuple[GeneratedImage | None, ...]
    expires_at: int | None
    deadline: float
    size: int


@dataclass(frozen=True)
class ResultInfo:
    image_count: int
    expires_at: int | None


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
    def purge_image(self, job_id: str, user_id: str, index: int) -> bool: ...
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

    def purge_image(self, job_id: str, user_id: str, index: int) -> bool:
        """Release one member's bytes without changing any sibling's original index."""
        with self._lock:
            self._prune()
            result = self._results.get(job_id)
            if result is None or result.user_id != user_id or not 0 <= index < len(result.images):
                return False
            image = result.images[index]
            if image is None:
                return False
            images = list(result.images)
            images[index] = None
            result.images = tuple(images)
            result.size -= len(image.data)
            self._size -= len(image.data)
            return True

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
        gpt_parallelism: int = 1,
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
        # Separate provider lanes: GPT image groups never wait behind NovelAI groups (or
        # the reverse). NovelAI sees one call at a time; the GPT relay accepts several
        # concurrent calls, so its lane runs `gpt_parallelism` workers. Each lane keeps
        # two admission slots beyond its workers for ordinary submissions and re-runs.
        if not 1 <= gpt_parallelism <= MAX_GPT_PARALLELISM:
            raise ValueError(f"gpt_parallelism must be 1..{MAX_GPT_PARALLELISM}")
        self._workers = {"novelai": 1, "gpt": gpt_parallelism}
        self._capacity = {
            lane: threading.BoundedSemaphore(workers + 2)
            for lane, workers in self._workers.items()
        }
        # Pre-payment provider outages pause new run claims per lane (see lane_health).
        probe = getattr(provider, "probe", None)
        self.health = {
            "novelai": LaneHealth("novelai", probe if callable(probe) else None),
            "gpt": LaneHealth("gpt"),
        }
        self._executors: dict[str, ThreadPoolExecutor] = {}
        self._work_lock = threading.Lock()
        self._working: dict[str, _Admission] = {}

    def start(self) -> None:
        self.store.mark_interrupted()
        self.cache.start()
        if self.provider is not None:
            self._executors["novelai"] = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="nai-gen",
            )
        if self.provider is not None or self.gpt_provider is not None:
            # Without a GPT provider its groups still finish as gpt_image_unavailable.
            self._executors["gpt"] = ThreadPoolExecutor(
                max_workers=self._workers["gpt"], thread_name_prefix="gpt-gen",
            )

    def stop(self) -> None:
        executors, self._executors = self._executors, {}
        for executor in executors.values():
            executor.shutdown(wait=True, cancel_futures=True)
        self.cache.stop()

    def parallelism(self, lane: str) -> int:
        """Groups of one run that may be in flight at once on this lane."""
        return self._workers[lane]

    def lane_ready(self, lane: str) -> bool:
        """False while the lane's provider is in an outage pause; run claims must wait."""
        return self.health[lane].ready()

    def lane_paused_until(self, lane: str) -> float | None:
        return self.health[lane].paused_until()

    @staticmethod
    def lane(request: GenerationRequest) -> str:
        reference = request.reference
        return "gpt" if reference is not None and reference.mode == "gpt" else "novelai"

    def views(self, jobs: Sequence[HistoryItem], user_id: str) -> list[GenerationView]:
        """Batch the discard and caption lookups for pages instead of one query per job."""
        ids = [job.id for job in jobs]
        marks = self.store.discarded(user_id, ids)
        captions = self.store.caption_overrides(user_id, ids)
        purged, pending = self.store.purged(user_id, ids)
        return [
            self.view(
                job, user_id, discarded=marks[job.id], caption=captions.get(job.id, ""),
                purged=purged[job.id], purge_pending=pending[job.id],
            )
            for job in jobs
        ]

    def view(
        self, job: HistoryItem, user_id: str, *, discarded: list[int] | None = None,
        caption: str | None = None,
        purged: list[int] | None = None, purge_pending: list[int] | None = None,
    ) -> GenerationView:
        # caption: "" = looked up, none set; None = not looked up yet.
        if caption is None:
            caption = self.store.caption_overrides(user_id, [job.id]).get(job.id, "")
        if purged is None or purge_pending is None:
            marks, pending = self.store.purged(user_id, [job.id])
            purged, purge_pending = marks[job.id], pending[job.id]
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
            caption_override=caption or None,
            purged_images=purged,
            purge_pending_images=purge_pending,
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
        lane = self.lane(request)
        executor = self._executors.get(lane)
        if executor is None:
            raise GenerationNotConfigured("Generation provider not configured")
        capacity = self._capacity[lane]
        if not capacity.acquire(blocking=False):
            return None
        try:
            reservation = self.cache.reserve(request.sample_count)
        except BaseException:
            capacity.release()
            raise

        def release() -> None:
            self.cache.release(reservation)
            capacity.release()

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
            future = executor.submit(self._run, job_id, user_id, parameters, admission)

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
                self.health[self.lane(parameters)].report(None)
            except ProviderFailure as exception:
                self.cache.discard(job_id)
                self.store.finish(job_id, error_code=exception.code)
                lane = self.lane(parameters)
                cause = exception.__cause__
                # Codes and exception class only; never prompts, tokens or upstream bodies.
                logger.warning(
                    "Generation group failed on lane %s: %s%s", lane, exception.code,
                    f" ({type(cause).__name__})" if cause is not None else "",
                )
                self.health[lane].report(exception.code)
            except ResultStorageUnavailable:
                self.cache.discard(job_id)
                self.store.finish(job_id, error_code="result_storage_error")
            except Exception:
                self.cache.discard(job_id)
                self.store.finish(job_id, error_code="upstream_error")
        finally:
            admission.finish()
            self._forget(job_id)
