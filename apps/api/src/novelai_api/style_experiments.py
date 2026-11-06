"""Durable owner-scoped style runs, queued per owner and lane, on the paid generation manager."""

import json
import secrets
import sqlite3
import threading
import time
from collections.abc import Callable
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, PrivateAttr, model_validator

from .dataset_plan import (
    CharacterPlan,
    DatasetRunCreate,
    dataset_parameters,
    item_seed,
)
from .db import Database
from .generations import (
    EXPERIMENT_ROWS,
    DatasetItem,
    ExperimentConflict,
    ExperimentContext,
    GenerationManager,
    GenerationNotConfigured,
    GenerationRequest,
    JobStore,
    ReferenceImageUse,
    ResultStorageUnavailable,
    _experiment_connection,
)
from .reruns import RerunBatchCreate, RerunBatchItem, RerunRefused, rerun_parameters
from .style_plan import ExperimentRange, create_style_plan


class RunCreate(BaseModel):
    id: UUID
    parameters: GenerationRequest
    ranges: list[ExperimentRange] = Field(min_length=1, max_length=1500)

    @model_validator(mode="after")
    def valid_plan(self) -> Self:
        if self.parameters.experiment is not None or self.parameters.reference is not None:
            # Reference images belong only to character dataset runs.
            raise ValueError("Run parameters must not inherit experiment or reference identity")
        create_style_plan(self.parameters, self.ranges)
        return self

    def definition(self) -> tuple[str, str]:
        plan = create_style_plan(self.parameters, self.ranges)
        definition = {
            "plan_version": 2,
            "parameters": self.parameters.model_dump(mode="json"),
            "ranges": [dimension.range.model_dump() for dimension in plan.dimensions],
        }
        return json.dumps(definition, sort_keys=True, separators=(",", ":")), str(plan.total)


Lane = Literal["novelai", "gpt"]
ACTIVE_STATUSES = "('running', 'stopping')"
# Unfinished (running, stopping or queued) runs one owner may hold at once.
MAX_ACTIVE_RUNS = 10
_INFLIGHT_COUNT = (
    "(SELECT COUNT(*) FROM style_experiment_inflight AS i "
    "WHERE i.user_id = style_experiment_runs.user_id "
    "AND i.run_id = style_experiment_runs.id) AS in_flight_count"
)
_ROW = f"SELECT rowid AS seq, *, {_INFLIGHT_COUNT} FROM style_experiment_runs "
_INFLIGHT_ORDER = "ORDER BY length(ordinal), ordinal"


def run_lane(request: "RunCreate | DatasetRunCreate") -> Lane:
    """GPT image character runs use the relay; everything else uses NovelAI."""
    character = getattr(request, "character", None)
    return "gpt" if character is not None and character.mode == "gpt" else "novelai"


class RunState(BaseModel):
    _plan_version: Literal[1, 2] = PrivateAttr(default=2)
    id: str
    # "rerun": a durable batch of paid re-runs of one training set's finished groups.
    kind: Literal["style", "dataset", "rerun"] = "style"
    lane: Lane = "novelai"
    # Unfinished runs only: 0 is the run its lane is executing, N waits behind N others.
    queue_position: int | None = None
    name: str | None = None
    status: Literal["running", "stopping", "stopped", "completed"]
    total: str
    next_ordinal: str
    processed_count: str
    succeeded_count: str
    failed_count: str
    # Lowest in-flight ordinal and its job (a run on the GPT lane may hold several).
    current_ordinal: str | None
    current_job_id: str | None
    # Accepted groups of this run not yet counted (0..lane parallelism).
    in_flight_count: int = 0
    # Running runs only: epoch seconds until which the lane's provider is paused after an
    # outage (no new groups are claimed meanwhile); None when claims may proceed.
    provider_paused_until: int | None = None
    # GPT runs: owner-chosen concurrency (None = server maximum); always None on NovelAI.
    parallelism: int | None = None
    seed: int
    sample_count: int
    parameters: GenerationRequest
    ranges: list[ExperimentRange]
    items: list[DatasetItem] = Field(default_factory=list)
    styles: list[str] | None = None
    character: CharacterPlan | None = None
    # Re-run batches: the training set they belong to and one source per ordinal.
    rerun_experiment_id: str | None = None
    rerun_items: list[RerunBatchItem] | None = None
    created_at: int
    updated_at: int
    error_code: str | None


class ActiveRun(BaseModel):
    run: RunState | None


class ActiveRuns(BaseModel):
    runs: list[RunState]


class RunConflict(Exception):
    def __init__(self, code: Literal["experiment_run_conflict", "experiment_run_queue_full"]):
        self.code = code
        super().__init__(code)


class ReferenceMissing(Exception):
    """A pinned reference image disappeared before the run could be created."""


class ContinuationRefused(Exception):
    def __init__(self, code: Literal[
        "experiment_run_active", "continuation_unsupported", "nothing_to_continue",
        "reference_not_found",
    ]):
        self.code = code
        super().__init__(code)


CONTINUATION_SUFFIX = "（续）"


def continuation_request(
    run: RunState, new_id: UUID, *, name: str | None, gpt_model: str | None = None,
) -> tuple[DatasetRunCreate, list[ReferenceImageUse] | None]:
    """A new dataset run for the stopped run's never-claimed items, rendered exactly as the
    original would have: same seed per item, same style rotation and reference rotation."""
    if run.kind != "dataset":
        raise ContinuationRefused("continuation_unsupported")
    if run.status in ("running", "stopping"):
        raise ContinuationRefused("experiment_run_active")
    offset = int(run.next_ordinal) - 1
    if offset >= len(run.items):
        raise ContinuationRefused("nothing_to_continue")
    styles = None
    if run.styles:
        shift = offset % len(run.styles)
        styles = run.styles[shift:] + run.styles[:shift]
    parameters = run.parameters.model_copy(update={
        "seed": item_seed(run.seed, offset + 1),
        **({"style_prompt": styles[0]} if styles else {}),
        # GPT groups render with the server's current model; record that, not the old one.
        **({"model": gpt_model} if gpt_model and run.lane == "gpt" else {}),
    })
    character = None
    pinned = None
    if run.character is not None:
        plan = run.character
        pinned = list(plan.references)
        if plan.mode in ("img2img", "precise"):
            # These modes use one reference per item in turn; keep each item's image.
            shift = offset % len(pinned)
            pinned = pinned[shift:] + pinned[:shift]
        character = {
            **plan.model_dump(mode="json", exclude_none=True, exclude={"references"}),
            "reference_ids": [reference.id for reference in pinned],
        }
    label = (name or "").strip()
    if label:
        label = label[:80 - len(CONTINUATION_SUFFIX)].rstrip() + CONTINUATION_SUFFIX
    request = DatasetRunCreate.model_validate({
        "id": str(new_id),
        "parameters": parameters.model_dump(mode="json"),
        "items": [item.model_dump(mode="json") for item in run.items[offset:]],
        **({"styles": styles} if styles else {}),
        **({"character": character} if character else {}),
        **({"name": label} if label else {}),
        **({"gpt_concurrency": run.parallelism} if run.parallelism else {}),
    })
    return request, pinned


class RunStore:
    def __init__(
        self, database: Database,
        *, paused_until: Callable[[str], float | None] | None = None,
    ):
        self.database = database
        self._paused_until = paused_until

    def _mark_paused(self, state: RunState) -> RunState:
        if self._paused_until is not None and state.status == "running":
            until = self._paused_until(state.lane)
            state.provider_paused_until = int(until) if until is not None else None
        return state

    @staticmethod
    def _position(connection: sqlite3.Connection, row: sqlite3.Row) -> int | None:
        if row["status"] not in ("running", "stopping"):
            return None
        return connection.execute(
            "SELECT COUNT(*) FROM style_experiment_runs WHERE user_id = ? AND lane = ? "
            f"AND status IN {ACTIVE_STATUSES} AND (created_at, rowid) < (?, ?)",
            (row["user_id"], row["lane"], row["created_at"], row["seq"]),
        ).fetchone()[0]

    def _located(self, connection: sqlite3.Connection, row: sqlite3.Row) -> RunState:
        state = self._state(row)
        state.queue_position = self._position(connection, row)
        return self._mark_paused(state)

    @staticmethod
    def _state(row: sqlite3.Row) -> RunState:
        definition = json.loads(row["definition_json"])
        kind = definition.get("kind", "style")
        version = definition.get("plan_version", 1)
        if kind not in ("style", "dataset", "rerun") or version not in (1, 2):
            raise ValueError("Unsupported stored style plan version")
        rerun = kind == "rerun"
        state = RunState(
            kind=kind, items=[] if rerun else definition.get("items", []),
            styles=definition.get("styles"), character=definition.get("character"),
            rerun_experiment_id=definition.get("experiment_id") if rerun else None,
            rerun_items=definition.get("sources") if rerun else None,
            **{key: row[key] for key in (
                "id", "lane", "status", "total", "next_ordinal", "processed_count",
                "succeeded_count", "failed_count", "current_ordinal", "current_job_id", "seed",
                "created_at", "updated_at", "error_code", "in_flight_count", "parallelism",
            )},
            parameters=definition["parameters"], ranges=definition.get("ranges", []),
            sample_count=definition["parameters"]["sample_count"],
        )
        state._plan_version = version
        return state

    def create(
        self, user_id: str, request: RunCreate | DatasetRunCreate | RerunBatchCreate,
        *, references: list[ReferenceImageUse] | None = None,
        rerun_base: "tuple[GenerationRequest, Lane] | None" = None,
    ) -> RunState:
        if isinstance(request, RerunBatchCreate):
            if rerun_base is None:
                raise ValueError("A re-run batch needs its training set's parameters and lane")
            definition, total = rerun_definition(request, rerun_base[0])
            lane, request_seed = rerun_base[1], None
        else:
            definition, total = (
                request.definition(references) if isinstance(request, DatasetRunCreate)
                else request.definition()
            )
            lane, request_seed = run_lane(request), request.parameters.seed
        run_id = str(request.id)
        with self.database.connect(write=True) as connection:
            existing = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            if existing:
                saved = json.loads(existing["definition_json"])
                requested = json.loads(definition)
                # A retry of a frozen v1 definition must retain its original renderer.
                if saved.get("plan_version", 1) not in (1, 2):
                    raise RunConflict("experiment_run_conflict")
                saved.pop("plan_version", None)
                requested.pop("plan_version", None)
                # Older snapshots omitted the mode and always used manual coordinates.
                # Normalize only the comparison copy; never rewrite their definition.
                saved["parameters"].setdefault("auto_character_position", False)
                if saved != requested:
                    raise RunConflict("experiment_run_conflict")
                return self._located(connection, existing)
            active = connection.execute(
                "SELECT COUNT(*) FROM style_experiment_runs WHERE user_id = ? "
                f"AND status IN {ACTIVE_STATUSES}", (user_id,),
            ).fetchone()[0]
            if active >= MAX_ACTIVE_RUNS:
                raise RunConflict("experiment_run_queue_full")
            _experiment_connection(connection)
            used = connection.execute(
                EXPERIMENT_ROWS + "SELECT 1 FROM experiment_rows WHERE experiment_id = ? LIMIT 1",
                (user_id, run_id),
            ).fetchone()
            if used:
                raise RunConflict("experiment_run_conflict")
            # Re-check pinned references in this write transaction so a concurrent delete
            # cannot leave a new run pointing at missing bytes.
            for reference in references or ():
                if connection.execute(
                    "SELECT 1 FROM reference_images WHERE user_id = ? AND id = ? AND sha256 = ?",
                    (user_id, reference.id, reference.sha256),
                ).fetchone() is None:
                    raise ReferenceMissing("reference_not_found")
            seed = request_seed
            if seed is None:
                seed = secrets.randbelow(4294967295) + 1
            now = int(time.time())
            connection.execute(
                "INSERT INTO style_experiment_runs (user_id, id, definition_json, total, "
                "seed, lane, status, created_at, updated_at, parallelism) "
                "VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?, ?)",
                (user_id, run_id, definition, total, seed, lane, now, now,
                 getattr(request, "gpt_concurrency", None)),
            )
            name = getattr(request, "name", None)
            if name is not None:
                connection.execute(
                    "INSERT INTO experiment_names (user_id, run_id, name, named_at) "
                    "VALUES (?, ?, ?, ?)", (user_id, run_id, name, now),
                )
            row = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            state = self._located(connection, row)
        state.name = name
        return state

    def get(self, user_id: str, run_id: str) -> RunState | None:
        with self.database.connect() as connection:
            row = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            return self._located(connection, row) if row else None

    def queue(self, user_id: str) -> list[RunState]:
        """The owner's unfinished runs, oldest first, with lane positions and names."""
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT r.rowid AS seq, r.*, n.name AS display_name, "
                "(SELECT COUNT(*) FROM style_experiment_inflight AS i "
                "WHERE i.user_id = r.user_id AND i.run_id = r.id) AS in_flight_count "
                "FROM style_experiment_runs r LEFT JOIN experiment_names n "
                "ON n.user_id = r.user_id AND n.run_id = r.id "
                f"WHERE r.user_id = ? AND r.status IN {ACTIVE_STATUSES} "
                "ORDER BY r.created_at, r.rowid", (user_id,),
            ).fetchall()
        lanes: dict[str, int] = {}
        runs = []
        for row in rows:
            state = self._state(row)
            state.queue_position = lanes.get(row["lane"], 0)
            lanes[row["lane"]] = state.queue_position + 1
            state.name = row["display_name"]
            runs.append(self._mark_paused(state))
        return runs

    def active(self, user_id: str) -> RunState | None:
        """Oldest unfinished run (kept for clients that observe only one run)."""
        runs = self.queue(user_id)
        return runs[0] if runs else None

    def is_lane_head(self, user_id: str, run_id: str) -> bool:
        with self.database.connect() as connection:
            row = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            return row is not None and self._position(connection, row) == 0

    def active_keys(self, *, after: tuple[str, str] | None) -> list[tuple[str, str]]:
        with self.database.connect() as connection:
            query = (
                "SELECT user_id, id FROM style_experiment_runs "
                "WHERE status IN ('running', 'stopping') "
            )
            if after is None:
                rows = connection.execute(query + "ORDER BY user_id, id LIMIT 128").fetchall()
            else:
                rows = connection.execute(
                    query + "AND (user_id, id) > (?, ?) ORDER BY user_id, id LIMIT 128", after,
                ).fetchall()
                if len(rows) < 128:
                    rows.extend(connection.execute(
                        query + "AND (user_id, id) <= (?, ?) ORDER BY user_id, id LIMIT ?",
                        (*after, 128 - len(rows)),
                    ).fetchall())
        return [(row["user_id"], row["id"]) for row in rows]

    def name(self, user_id: str, run_id: str) -> str | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT name FROM experiment_names WHERE user_id = ? AND run_id = ?",
                (user_id, run_id),
            ).fetchone()
        return row["name"] if row else None

    def continue_run(
        self, user_id: str, run_id: str, new_id: UUID,
        reference_digest: Callable[[str, str], str | None], *, gpt_model: str | None = None,
    ) -> RunState | None:
        """Create (idempotently, by new_id) the continuation of a stopped dataset run."""
        run = self.get(user_id, run_id)
        if run is None:
            return None
        if run.kind == "rerun":
            return self.create(
                user_id, rerun_continuation(run, new_id, name=self.name(user_id, run_id)),
                rerun_base=(run.parameters, run.lane),
            )
        request, pinned = continuation_request(
            run, new_id, name=self.name(user_id, run_id), gpt_model=gpt_model,
        )
        if pinned is not None and any(
            reference_digest(user_id, reference.id) != reference.sha256 for reference in pinned
        ):
            # The owner deleted or replaced a reference; never render with different bytes.
            raise ContinuationRefused("reference_not_found")
        return self.create(user_id, request, references=pinned)

    def set_parallelism(
        self, user_id: str, run_id: str, parallelism: int,
    ) -> RunState | Literal["not_gpt", "finished"] | None:
        """Change an unfinished GPT run's concurrency; in-flight groups are never cancelled."""
        with self.database.connect(write=True) as connection:
            row = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            if row is None:
                return None
            if row["lane"] != "gpt":
                return "not_gpt"
            if row["status"] not in ("running", "stopping"):
                return "finished"
            connection.execute(
                "UPDATE style_experiment_runs SET parallelism = ?, updated_at = ? "
                "WHERE user_id = ? AND id = ?",
                (parallelism, int(time.time()), user_id, run_id),
            )
            row = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            return self._located(connection, row)

    def stop(self, user_id: str, run_id: str) -> RunState | None:
        with self.database.connect(write=True) as connection:
            connection.execute(
                "UPDATE style_experiment_runs SET status = CASE WHEN EXISTS ("
                "SELECT 1 FROM style_experiment_inflight WHERE user_id = ? AND run_id = ?) "
                "THEN 'stopping' ELSE 'stopped' END, updated_at = ? "
                "WHERE user_id = ? AND id = ? AND status = 'running'",
                (user_id, run_id, int(time.time()), user_id, run_id),
            )
            row = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            return self._located(connection, row) if row else None

    @staticmethod
    def _sync_current(connection: sqlite3.Connection, user_id: str, run_id: str) -> None:
        """Mirror the lowest in-flight group into the run's legacy current_* columns."""
        lowest = connection.execute(
            "SELECT job_id, ordinal FROM style_experiment_inflight "
            f"WHERE user_id = ? AND run_id = ? {_INFLIGHT_ORDER} LIMIT 1", (user_id, run_id),
        ).fetchone()
        connection.execute(
            "UPDATE style_experiment_runs SET current_job_id = ?, current_ordinal = ? "
            "WHERE user_id = ? AND id = ?",
            (lowest["job_id"] if lowest else None, lowest["ordinal"] if lowest else None,
             user_id, run_id),
        )

    def in_flight_jobs(self, user_id: str, run_id: str) -> list[str]:
        with self.database.connect() as connection:
            return [row["job_id"] for row in connection.execute(
                "SELECT job_id FROM style_experiment_inflight "
                f"WHERE user_id = ? AND run_id = ? {_INFLIGHT_ORDER}", (user_id, run_id),
            ).fetchall()]

    def claim(
        self, user_id: str, run_id: str, ordinal: str, parameters: GenerationRequest,
        *, refusal: str | None = None, limit: int = 1,
    ) -> str | None:
        """Persist job and cursor together before any executor can invoke the provider."""
        with self.database.connect(write=True) as connection:
            row = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            if (
                row is None or row["status"] != "running" or row["in_flight_count"] >= limit
                or row["next_ordinal"] != ordinal or int(ordinal) > int(row["total"])
            ):
                return None
            _experiment_connection(connection)
            existing = connection.execute(
                EXPERIMENT_ROWS + "SELECT id FROM experiment_rows "
                "WHERE experiment_id = ? AND ordinal = ? AND rerun_of IS NULL LIMIT 1",
                (user_id, run_id, ordinal),
            ).fetchone()
            job_id = existing["id"] if existing else JobStore.create_in_transaction(
                connection, user_id, parameters, run_claim=True,
            )
            now = int(time.time())
            if refusal is not None and not existing:
                connection.execute(
                    "UPDATE generation_jobs SET status = 'failed', error_code = ?, updated_at = ? "
                    "WHERE id = ? AND status = 'queued'", (refusal, now, job_id),
                )
            connection.execute(
                "INSERT OR IGNORE INTO style_experiment_inflight "
                "(user_id, run_id, job_id, ordinal) VALUES (?, ?, ?, ?)",
                (user_id, run_id, job_id, ordinal),
            )
            connection.execute(
                "UPDATE style_experiment_runs SET next_ordinal = ?, updated_at = ? "
                "WHERE user_id = ? AND id = ?",
                (str(int(ordinal) + 1), now, user_id, run_id),
            )
            self._sync_current(connection, user_id, run_id)
        return job_id if existing is None and refusal is None else None

    def claim_rerun(
        self, user_id: str, run_id: str, ordinal: str, parameters: GenerationRequest,
        discard_index: int | None, *, limit: int = 1,
    ) -> str | None:
        """Persist one batch re-run job, its in-flight row, the cursor and the optional
        discard mark of the replaced image together, before any paid call."""
        with self.database.connect(write=True) as connection:
            row = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            if (
                row is None or row["status"] != "running" or row["in_flight_count"] >= limit
                or row["next_ordinal"] != ordinal or int(ordinal) > int(row["total"])
            ):
                return None
            # Raises ExperimentConflict (rolling everything back) when the source is gone.
            job_id = JobStore.create_in_transaction(connection, user_id, parameters, rerun=True)
            now = int(time.time())
            connection.execute(
                "INSERT INTO style_experiment_inflight (user_id, run_id, job_id, ordinal) "
                "VALUES (?, ?, ?, ?)", (user_id, run_id, job_id, ordinal),
            )
            connection.execute(
                "UPDATE style_experiment_runs SET next_ordinal = ?, updated_at = ? "
                "WHERE user_id = ? AND id = ?", (str(int(ordinal) + 1), now, user_id, run_id),
            )
            source = parameters.experiment.rerun_of if parameters.experiment else None
            if discard_index is not None and source is not None:
                connection.execute(
                    "INSERT OR IGNORE INTO discarded_images (user_id, job_id, image_index, "
                    "created_at) VALUES (?, ?, ?, ?)", (user_id, source, discard_index, now),
                )
            self._sync_current(connection, user_id, run_id)
        return job_id

    def skip_rerun(self, user_id: str, run_id: str, ordinal: str, error_code: str) -> None:
        """Count one batch item that can no longer be re-run as failed, without a job."""
        with self.database.connect(write=True) as connection:
            row = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            if row is None or row["status"] != "running" or row["next_ordinal"] != ordinal:
                return
            processed = int(row["processed_count"]) + 1
            done = processed >= int(row["total"]) and row["in_flight_count"] == 0
            connection.execute(
                "UPDATE style_experiment_runs SET next_ordinal = ?, processed_count = ?, "
                "failed_count = ?, error_code = ?, status = ?, updated_at = ? "
                "WHERE user_id = ? AND id = ?",
                (str(int(ordinal) + 1), str(processed), str(int(row["failed_count"]) + 1),
                 error_code, "completed" if done else "running", int(time.time()),
                 user_id, run_id),
            )

    def fail_unowned(self, user_id: str, run_id: str, job_ids: list[str]) -> None:
        # Call only after the manager's admission for these jobs is no longer live. A worker
        # that lost terminal persistence must not strand the run or repeat paid work.
        if not job_ids:
            return
        with self.database.connect(write=True) as connection:
            for job_id in job_ids:
                connection.execute(
                    "UPDATE generation_jobs SET status = 'failed', "
                    "error_code = 'outcome_unknown', updated_at = ? "
                    "WHERE status IN ('queued', 'running') AND user_id = ? AND id = ? "
                    "AND EXISTS (SELECT 1 FROM style_experiment_inflight "
                    "WHERE user_id = ? AND run_id = ? AND job_id = ?)",
                    (int(time.time()), user_id, job_id, user_id, run_id, job_id),
                )

    def reconcile(self, user_id: str, run_id: str) -> RunState | None:
        with self.database.connect(write=True) as connection:
            row = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            if row is None:
                return None
            if row["in_flight_count"] == 0:
                return self._located(connection, row)
            pending = connection.execute(
                "SELECT f.job_id, j.status, j.error_code FROM style_experiment_inflight AS f "
                "LEFT JOIN generation_jobs AS j ON j.user_id = f.user_id AND j.id = f.job_id "
                "WHERE f.user_id = ? AND f.run_id = ? ORDER BY length(f.ordinal), f.ordinal",
                (user_id, run_id),
            ).fetchall()
            settled = [job for job in pending if job["status"] not in ("queued", "running")]
            if not settled:
                return self._located(connection, row)
            processed = int(row["processed_count"])
            succeeded_count = int(row["succeeded_count"])
            failed_count = int(row["failed_count"])
            error_code = row["error_code"]
            for job in settled:
                # Missing private state is never grounds to repeat a possibly paid group.
                succeeded = job["status"] == "succeeded"
                processed += 1
                succeeded_count += int(succeeded)
                failed_count += int(not succeeded)
                error_code = (
                    None if succeeded else job["error_code"] if job["status"] is not None
                    else "outcome_unknown"
                )
                connection.execute(
                    "DELETE FROM style_experiment_inflight "
                    "WHERE user_id = ? AND run_id = ? AND job_id = ?",
                    (user_id, run_id, job["job_id"]),
                )
            remaining = len(pending) - len(settled)
            status = (
                ("stopping" if remaining else "stopped") if row["status"] == "stopping" else
                "completed" if processed >= int(row["total"]) and not remaining else "running"
            )
            connection.execute(
                "UPDATE style_experiment_runs SET processed_count = ?, succeeded_count = ?, "
                "failed_count = ?, status = ?, error_code = ?, updated_at = ? "
                "WHERE user_id = ? AND id = ?",
                (
                    str(processed), str(succeeded_count), str(failed_count), status,
                    error_code, int(time.time()), user_id, run_id,
                ),
            )
            self._sync_current(connection, user_id, run_id)
            row = connection.execute(
                _ROW + "WHERE user_id = ? AND id = ?", (user_id, run_id),
            ).fetchone()
            return self._located(connection, row)


def rerun_definition(request: RerunBatchCreate, base: GenerationRequest) -> tuple[str, str]:
    """Frozen batch: the training set's run parameters (for display) and each source."""
    definition = {
        "kind": "rerun",
        "plan_version": 2,
        "parameters": base.model_copy(update={"sample_count": 1}).model_dump(mode="json"),
        "experiment_id": str(request.experiment_id),
        "sources": [
            item.model_dump(mode="json", exclude_none=True) for item in request.items
        ],
    }
    return json.dumps(definition, sort_keys=True, separators=(",", ":")), str(len(request.items))


def rerun_continuation(run: RunState, new_id: UUID, *, name: str | None) -> RerunBatchCreate:
    """A new batch for a stopped batch's never-claimed sources."""
    if run.status in ("running", "stopping"):
        raise ContinuationRefused("experiment_run_active")
    offset = int(run.next_ordinal) - 1
    items = run.rerun_items or []
    if offset >= len(items):
        raise ContinuationRefused("nothing_to_continue")
    label = (name or "").strip()
    if label and not label.endswith(CONTINUATION_SUFFIX):
        label = label[:80 - len(CONTINUATION_SUFFIX)].rstrip() + CONTINUATION_SUFFIX
    return RerunBatchCreate(
        id=new_id, experiment_id=UUID(run.rerun_experiment_id or ""), items=items[offset:],
        name=label or None,
    )


def group_parameters(run: RunState) -> GenerationRequest:
    if run.kind == "dataset":
        ordinal = int(run.next_ordinal)
        item = run.items[ordinal - 1]
        return dataset_parameters(
            run.parameters, item, seed=item_seed(run.seed, ordinal),
            context=ExperimentContext(
                id=run.id, ordinal=run.next_ordinal, total=run.total, kind="dataset", item=item,
            ),
            ordinal=ordinal, styles=run.styles, character=run.character,
        )
    plan = create_style_plan(run.parameters, run.ranges, plan_version=run._plan_version)
    source, weights = plan.combination(int(run.next_ordinal) - 1)
    return GenerationRequest.model_validate({
        **run.parameters.model_dump(mode="json"), "style_prompt": source, "seed": run.seed,
        "experiment": ExperimentContext(
            id=run.id, ordinal=run.next_ordinal, total=run.total, weights=weights,
        ),
    })


class StyleExperimentService:
    def __init__(self, database: Database, manager: GenerationManager, *, interval: float = 1):
        self.store = RunStore(database, paused_until=manager.lane_paused_until)
        self.manager = manager
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._cursor: tuple[str, str] | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="nai-style-runs", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                # A transient DB/storage fault detaches work until the next bounded tick.
                # Persisted current identity prevents retries or loss of paid ownership.
                pass
            self._stop.wait(self._interval)

    def tick(self) -> None:
        keys = self.store.active_keys(after=self._cursor)
        # Rotate the first owner every tick, even below the bounded page size.
        # Otherwise fast earlier runs can reclaim all shared queue slots forever.
        self._cursor = keys[0] if keys else None
        for user_id, run_id in keys:
            if self._stop.is_set():
                return
            try:
                self._advance(user_id, run_id)
            except Exception:
                # Keep one owner's damaged/transient state from starving other owners.
                continue

    def _release_orphans(self, user_id: str, run_id: str) -> None:
        dead = [
            job_id for job_id in self.store.in_flight_jobs(user_id, run_id)
            if not self.manager.is_inflight(job_id)
        ]
        self.store.fail_unowned(user_id, run_id, dead)

    def _advance(self, user_id: str, run_id: str) -> None:
        previous = self.store.get(user_id, run_id)
        if previous is not None and previous.in_flight_count:
            self._release_orphans(user_id, run_id)
        run = self.store.reconcile(user_id, run_id)
        if run is None or run.status != "running":
            return
        if run.queue_position != 0:
            # Queued behind an earlier run of this owner's lane; waits without a claim.
            return
        if not self.manager.lane_ready(run.lane):
            # Provider outage pause: wait without consuming an ordinal (see lane_health).
            return
        # NovelAI runs keep one group in flight; GPT runs fill up to the owner's chosen
        # concurrency, never beyond the lane's configured parallelism.
        limit = self.manager.parallelism(run.lane)
        if run.parallelism is not None:
            limit = max(1, min(limit, run.parallelism))
        while (
            run is not None and run.status == "running" and run.in_flight_count < limit
            and int(run.next_ordinal) <= int(run.total) and not self._stop.is_set()
        ):
            if not self._submit_next(user_id, run, limit):
                return
            run = self.store.get(user_id, run_id)

    def _submit_rerun(self, user_id: str, run: RunState, limit: int) -> bool:
        """Claim and submit a re-run batch's next source; False when nothing more can start."""
        ordinal = run.next_ordinal
        source = (run.rerun_items or [])[int(ordinal) - 1]
        job = self.manager.store.get(user_id, source.job_id)
        context = job.parameters.experiment if job is not None else None
        if job is None or context is None or str(context.id) != run.rerun_experiment_id:
            # The owner deleted the source group or its training set meanwhile.
            self.store.skip_rerun(user_id, run.id, ordinal, "rerun_source_missing")
            return True
        try:
            parameters = rerun_parameters(job, source)
        except RerunRefused as refused:
            self.store.skip_rerun(user_id, run.id, ordinal, refused.code)
            return True

        def create(owner: str, request: GenerationRequest) -> str | None:
            return self.store.claim_rerun(
                owner, run.id, ordinal, request, source.discard_index, limit=limit,
            )

        try:
            return self.manager.submit(user_id, parameters, create=create) is not None
        except ExperimentConflict:
            self.store.skip_rerun(user_id, run.id, ordinal, "rerun_source_missing")
        except (GenerationNotConfigured, ResultStorageUnavailable) as exception:
            self.store.skip_rerun(user_id, run.id, ordinal, (
                "provider_unavailable" if isinstance(exception, GenerationNotConfigured)
                else "result_storage_unavailable"
            ))
        except Exception:
            self._release_orphans(user_id, run.id)
            self.store.reconcile(user_id, run.id)
        return False

    def _submit_next(self, user_id: str, run: RunState, limit: int) -> bool:
        """Claim and submit the run's next ordinal; False when nothing more can start now."""
        if run.kind == "rerun":
            return self._submit_rerun(user_id, run, limit)
        parameters = group_parameters(run)
        ordinal = run.next_ordinal

        def create(owner: str, request: GenerationRequest) -> str | None:
            return self.store.claim(owner, run.id, ordinal, request, limit=limit)

        try:
            return self.manager.submit(user_id, parameters, create=create) is not None
        except (GenerationNotConfigured, ResultStorageUnavailable) as exception:
            refusal = (
                "provider_unavailable" if isinstance(exception, GenerationNotConfigured)
                else "result_storage_unavailable"
            )
            self.store.claim(user_id, run.id, ordinal, parameters, refusal=refusal, limit=limit)
            self.store.reconcile(user_id, run.id)
        except Exception:
            self._release_orphans(user_id, run.id)
            self.store.reconcile(user_id, run.id)
        # Refusal-only progression keeps the bounded per-tick cadence.
        return False
