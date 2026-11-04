"""Durable owner-scoped style runs using the sole paid generation manager."""

import json
import secrets
import sqlite3
import threading
import time
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, PrivateAttr, model_validator

from .dataset_plan import CharacterPlan, DatasetRunCreate, dataset_parameters, item_seed
from .db import Database
from .generations import (
    EXPERIMENT_ROWS,
    DatasetItem,
    ExperimentContext,
    GenerationManager,
    GenerationNotConfigured,
    GenerationRequest,
    JobStore,
    ReferenceImageUse,
    ResultStorageUnavailable,
    _experiment_connection,
)
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


class RunState(BaseModel):
    _plan_version: Literal[1, 2] = PrivateAttr(default=2)
    id: str
    kind: Literal["style", "dataset"] = "style"
    status: Literal["running", "stopping", "stopped", "completed"]
    total: str
    next_ordinal: str
    processed_count: str
    succeeded_count: str
    failed_count: str
    current_ordinal: str | None
    current_job_id: str | None
    seed: int
    sample_count: int
    parameters: GenerationRequest
    ranges: list[ExperimentRange]
    items: list[DatasetItem] = Field(default_factory=list)
    styles: list[str] | None = None
    character: CharacterPlan | None = None
    created_at: int
    updated_at: int
    error_code: str | None


class ActiveRun(BaseModel):
    run: RunState | None


class RunConflict(Exception):
    def __init__(self, code: Literal["experiment_run_conflict", "experiment_run_active"]):
        self.code = code
        super().__init__(code)


class ReferenceMissing(Exception):
    """A pinned reference image disappeared before the run could be created."""


class RunStore:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _state(row: sqlite3.Row) -> RunState:
        definition = json.loads(row["definition_json"])
        kind = definition.get("kind", "style")
        version = definition.get("plan_version", 1)
        if kind not in ("style", "dataset") or version not in (1, 2):
            raise ValueError("Unsupported stored style plan version")
        state = RunState(
            kind=kind, items=definition.get("items", []), styles=definition.get("styles"),
            character=definition.get("character"),
            **{key: row[key] for key in (
                "id", "status", "total", "next_ordinal", "processed_count", "succeeded_count",
                "failed_count", "current_ordinal", "current_job_id", "seed", "created_at",
                "updated_at", "error_code",
            )},
            parameters=definition["parameters"], ranges=definition.get("ranges", []),
            sample_count=definition["parameters"]["sample_count"],
        )
        state._plan_version = version
        return state

    def create(
        self, user_id: str, request: RunCreate | DatasetRunCreate,
        *, references: list[ReferenceImageUse] | None = None,
    ) -> RunState:
        definition, total = (
            request.definition(references) if isinstance(request, DatasetRunCreate)
            else request.definition()
        )
        run_id = str(request.id)
        with self.database.connect(write=True) as connection:
            existing = connection.execute(
                "SELECT * FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, run_id),
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
                return self._state(existing)
            active = connection.execute(
                "SELECT 1 FROM style_experiment_runs WHERE user_id = ? "
                "AND status IN ('running', 'stopping')", (user_id,),
            ).fetchone()
            if active:
                raise RunConflict("experiment_run_active")
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
            seed = request.parameters.seed
            if seed is None:
                seed = secrets.randbelow(4294967295) + 1
            now = int(time.time())
            connection.execute(
                "INSERT INTO style_experiment_runs "
                "(user_id, id, definition_json, total, seed, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'running', ?, ?)",
                (user_id, run_id, definition, total, seed, now, now),
            )
            name = request.name if isinstance(request, DatasetRunCreate) else None
            if name is not None:
                connection.execute(
                    "INSERT INTO experiment_names (user_id, run_id, name, named_at) "
                    "VALUES (?, ?, ?, ?)", (user_id, run_id, name, now),
                )
            row = connection.execute(
                "SELECT * FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, run_id),
            ).fetchone()
        return self._state(row)

    def get(self, user_id: str, run_id: str) -> RunState | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, run_id),
            ).fetchone()
        return self._state(row) if row else None

    def active(self, user_id: str) -> RunState | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM style_experiment_runs WHERE user_id = ? "
                "AND status IN ('running', 'stopping')", (user_id,),
            ).fetchone()
        return self._state(row) if row else None

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

    def stop(self, user_id: str, run_id: str) -> RunState | None:
        with self.database.connect(write=True) as connection:
            connection.execute(
                "UPDATE style_experiment_runs SET status = CASE "
                "WHEN current_job_id IS NULL THEN 'stopped' ELSE 'stopping' END, updated_at = ? "
                "WHERE user_id = ? AND id = ? AND status = 'running'",
                (int(time.time()), user_id, run_id),
            )
            row = connection.execute(
                "SELECT * FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, run_id),
            ).fetchone()
        return self._state(row) if row else None

    def claim(
        self, user_id: str, run_id: str, ordinal: str, parameters: GenerationRequest,
        *, refusal: str | None = None,
    ) -> str | None:
        """Persist job and cursor together before any executor can invoke the provider."""
        with self.database.connect(write=True) as connection:
            row = connection.execute(
                "SELECT * FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, run_id),
            ).fetchone()
            if (
                row is None or row["status"] != "running" or row["current_job_id"] is not None
                or row["next_ordinal"] != ordinal or int(ordinal) > int(row["total"])
            ):
                return None
            _experiment_connection(connection)
            existing = connection.execute(
                EXPERIMENT_ROWS + "SELECT id FROM experiment_rows "
                "WHERE experiment_id = ? AND ordinal = ? LIMIT 1",
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
                "UPDATE style_experiment_runs SET current_job_id = ?, current_ordinal = ?, "
                "next_ordinal = ?, updated_at = ? WHERE user_id = ? AND id = ?",
                (job_id, ordinal, str(int(ordinal) + 1), now, user_id, run_id),
            )
        return job_id if existing is None and refusal is None else None

    def fail_unowned_current(self, user_id: str, run_id: str) -> None:
        # Call only after the manager's admission is no longer live. A worker that
        # lost terminal persistence must not strand the run or repeat paid work.
        with self.database.connect(write=True) as connection:
            connection.execute(
                "UPDATE generation_jobs SET status = 'failed', error_code = 'outcome_unknown', "
                "updated_at = ? WHERE status IN ('queued', 'running') AND user_id = ? AND id = "
                "(SELECT current_job_id FROM style_experiment_runs WHERE user_id = ? AND id = ?)",
                (int(time.time()), user_id, user_id, run_id),
            )

    def reconcile(self, user_id: str, run_id: str) -> RunState | None:
        with self.database.connect(write=True) as connection:
            row = connection.execute(
                "SELECT * FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, run_id),
            ).fetchone()
            if row is None:
                return None
            if row["current_job_id"] is None:
                return self._state(row)
            job = connection.execute(
                "SELECT status, error_code FROM generation_jobs WHERE user_id = ? AND id = ?",
                (user_id, row["current_job_id"]),
            ).fetchone()
            if job is not None and job["status"] in ("queued", "running"):
                return self._state(row)
            # Missing private state is never grounds to repeat a possibly paid group.
            succeeded = job is not None and job["status"] == "succeeded"
            processed = int(row["processed_count"]) + 1
            status = (
                "stopped" if row["status"] == "stopping" else
                "completed" if processed >= int(row["total"]) else "running"
            )
            connection.execute(
                "UPDATE style_experiment_runs SET processed_count = ?, succeeded_count = ?, "
                "failed_count = ?, current_job_id = NULL, current_ordinal = NULL, status = ?, "
                "error_code = ?, updated_at = ? WHERE user_id = ? AND id = ?",
                (
                    str(processed), str(int(row["succeeded_count"]) + int(succeeded)),
                    str(int(row["failed_count"]) + int(not succeeded)), status,
                    (None if succeeded else
                     job["error_code"] if job is not None else "outcome_unknown"),
                    int(time.time()), user_id, run_id,
                ),
            )
            row = connection.execute(
                "SELECT * FROM style_experiment_runs WHERE user_id = ? AND id = ?",
                (user_id, run_id),
            ).fetchone()
        return self._state(row)


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
        self.store = RunStore(database)
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

    def _advance(self, user_id: str, run_id: str) -> None:
        previous = self.store.get(user_id, run_id)
        if (
            previous is not None and previous.current_job_id is not None
            and not self.manager.is_inflight(previous.current_job_id)
        ):
            self.store.fail_unowned_current(user_id, run_id)
        run = self.store.reconcile(user_id, run_id)
        if run is None or run.status != "running" or run.current_job_id is not None:
            return
        parameters = group_parameters(run)

        def create(owner: str, request: GenerationRequest) -> str | None:
            return self.store.claim(owner, run_id, run.next_ordinal, request)

        try:
            self.manager.submit(user_id, parameters, create=create)
        except (GenerationNotConfigured, ResultStorageUnavailable) as exception:
            refusal = (
                "provider_unavailable" if isinstance(exception, GenerationNotConfigured)
                else "result_storage_unavailable"
            )
            self.store.claim(user_id, run_id, run.next_ordinal, parameters, refusal=refusal)
            self.store.reconcile(user_id, run_id)
        except Exception:
            current = self.store.get(user_id, run_id)
            if (
                current and current.current_job_id
                and not self.manager.is_inflight(current.current_job_id)
            ):
                self.store.fail_unowned_current(user_id, run_id)
            self.store.reconcile(user_id, run_id)
