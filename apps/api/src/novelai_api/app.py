"""FastAPI entry point with stable errors and cookie-based authentication."""

import asyncio
import sqlite3
import threading
import time
from collections import deque
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .account_balance import AccountBalance, BalanceFailure, BalanceProvider, BalanceService
from .advice import (
    TRAIT_TIMEOUT_SECONDS,
    AdviceFailure,
    AdviceRequest,
    AdviceResult,
    AdviceRunner,
    AdviceService,
    trait_advice_text,
)
from .auth import current_user, issue_session, revoke_session
from .codex_advice import CodexAdviceRunner
from .config import Settings
from .dataset_plan import DatasetRunCreate
from .db import Database
from .generations import (
    ExperimentConflict,
    ExperimentDeleted,
    ExperimentDetail,
    ExperimentPage,
    ExperimentRename,
    GenerationManager,
    GenerationNotConfigured,
    GenerationRequest,
    GenerationView,
    HistoryPage,
    ImageProvider,
    ReferenceImageUse,
    ResultStorageUnavailable,
    ResultStore,
)
from .gpt_images import GptImageProvider
from .mcp_account import NovelAiMcpBalanceProvider
from .mcp_images import NovelAiMcpProvider
from .prompt_snapshots import (
    PromptSnapshot,
    PromptSnapshotConflict,
    PromptSnapshotCreate,
    PromptSnapshotPage,
    PromptSnapshotStore,
)
from .reference_images import (
    MAX_REFERENCE_BYTES,
    ReferenceFailure,
    ReferenceImage,
    ReferenceImageList,
    ReferenceImageStore,
)
from .reruns import (
    RerunBatchCreate,
    RerunEdits,
    RerunRefused,
    rerun_parameters,
)
from .security import SESSION_COOKIE, SESSION_LIFETIME_SECONDS
from .style_experiments import (
    ActiveRun,
    ActiveRuns,
    ContinuationRefused,
    ReferenceMissing,
    RunConflict,
    RunCreate,
    RunState,
    StyleExperimentService,
)
from .tags import SearchFailure, SearchRequest, SearchResults, TagSearch
from .thumbnails import ThumbnailBusy, ThumbnailCache


class ApiError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class UserInfo(BaseModel):
    id: str
    label: str


class SessionRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)


class HealthStatus(BaseModel):
    status: str


class GenerationAccepted(BaseModel):
    id: str
    status: str


class RerunRequest(RerunEdits):
    pass


def rerun_refusal(refused: RerunRefused) -> JSONResponse:
    if refused.code == "rerun_image_missing":
        raise HTTPException(
            status_code=404,
            detail=ApiError(code="not_found", message="Image not found").model_dump(),
        )
    return error(409 if refused.code == "job_active" else 422, refused.code, refused.message)


def error(status: int, code: str, message: str, *, retryable: bool = False) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ApiError(code=code, message=message, retryable=retryable).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


class LoginLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        now = time.monotonic()
        with self._lock:
            if len(self._attempts) >= 4096:
                self._attempts = {
                    key: attempts
                    for key, attempts in self._attempts.items()
                    if attempts and attempts[-1] > now - 60
                }
                if len(self._attempts) >= 4096 and client not in self._attempts:
                    del self._attempts[next(iter(self._attempts))]
            attempts = self._attempts.setdefault(client, deque())
            while attempts and attempts[0] <= now - 60:
                attempts.popleft()
            if len(attempts) >= 5:
                return False
            attempts.append(now)
            return True


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
    *,
    image_provider: ImageProvider | None = None,
    result_cache: ResultStore | None = None,
    tag_search: TagSearch | None = None,
    advice_runner: AdviceRunner | None = None,
    balance_provider: BalanceProvider | None = None,
    gpt_image_provider: ImageProvider | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    database = database or Database(settings.sqlite_path)
    limiter = LoginLimiter()
    if image_provider is None and settings.novelai_mcp_token is not None:
        image_provider = NovelAiMcpProvider(settings.novelai_mcp_url, settings.novelai_mcp_token)
    if gpt_image_provider is None and settings.gpt_image_api_key and settings.gpt_image_endpoint:
        gpt_image_provider = GptImageProvider(
            settings.gpt_image_endpoint, settings.gpt_image_api_key, settings.gpt_image_model,
        )
    manager = GenerationManager(
        database, image_provider, cache=result_cache, gpt_provider=gpt_image_provider,
        gpt_parallelism=settings.gpt_image_concurrency,
    )
    experiments = StyleExperimentService(database, manager)
    thumbnails = ThumbnailCache()
    snapshots = PromptSnapshotStore(database)
    references = ReferenceImageStore(database)
    tag_search = tag_search or TagSearch(
        settings.tag_search_url, settings.public_origin, settings.tag_search_key
    )
    if advice_runner is None and settings.codex_api_key:
        advice_runner = CodexAdviceRunner(
            settings.codex_api_key,
            base_url=settings.codex_base_url,
            model=settings.codex_model,
        )
    advice_service = AdviceService(advice_runner)
    if balance_provider is None and settings.novelai_mcp_token:
        balance_provider = NovelAiMcpBalanceProvider(
            settings.novelai_mcp_url, settings.novelai_mcp_token,
        )
    balance_service = BalanceService(balance_provider)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if database.check_ready():
            manager.start()
            experiments.start()
        try:
            yield
        finally:
            await asyncio.to_thread(experiments.stop)
            await asyncio.to_thread(manager.stop)
            await balance_service.close()
            if isinstance(advice_runner, CodexAdviceRunner):
                await advice_runner.close()

    app = FastAPI(title="NovelAI Workspace API", lifespan=lifespan)
    app.state.database = database
    app.state.generations = manager
    app.state.experiments = experiments
    app.state.thumbnails = thumbnails
    app.state.balance = balance_service

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        _request: Request, _exception: RequestValidationError
    ) -> JSONResponse:
        return error(422, "validation_error", "Invalid request")

    @app.exception_handler(sqlite3.Error)
    async def database_error(_request: Request, _exception: sqlite3.Error) -> JSONResponse:
        return error(503, "not_ready", "Database unavailable", retryable=True)

    @app.middleware("http")
    async def enforce_origin(request: Request, call_next: Callable) -> Response:
        if request.url.path.startswith("/api/") and request.method not in {
            "GET", "HEAD", "OPTIONS"
        }:
            if request.headers.get("origin") != settings.public_origin:
                return error(403, "forbidden_origin", "Invalid request origin")
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def require_user(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> UserInfo:
        if session:
            try:
                user = current_user(database, session)
            except sqlite3.Error:
                raise HTTPException(
                    status_code=503,
                    detail=ApiError(
                        code="not_ready", message="Database unavailable", retryable=True
                    ).model_dump(),
                ) from None
            if user is not None:
                return UserInfo(**user)
        raise HTTPException(
            status_code=401,
            detail=ApiError(code="unauthenticated", message="Authentication required").model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exception: HTTPException) -> JSONResponse:
        if isinstance(exception.detail, dict) and "code" in exception.detail:
            return JSONResponse(
                status_code=exception.status_code,
                content=exception.detail,
                headers={"Cache-Control": "no-store"},
            )
        return error(exception.status_code, "request_error", "Request failed")

    @app.get("/api/health/live", response_model=HealthStatus)
    def live() -> HealthStatus:
        return HealthStatus(status="ok")

    @app.get(
        "/api/account/balance",
        response_model=AccountBalance,
        responses={
            401: {"model": ApiError}, 422: {"model": ApiError}, 429: {"model": ApiError},
            502: {"model": ApiError}, 503: {"model": ApiError}, 504: {"model": ApiError},
        },
    )
    async def account_balance(
        _user: Annotated[UserInfo, Depends(require_user)],
    ) -> AccountBalance | JSONResponse:
        try:
            return await balance_service.get()
        except BalanceFailure as exception:
            return error(
                exception.status, exception.code, exception.message, retryable=exception.retryable,
            )

    @app.get("/api/health/ready", response_model=HealthStatus, responses={503: {"model": ApiError}})
    def ready() -> HealthStatus | JSONResponse:
        if not database.check_ready():
            return error(503, "not_ready", "Database unavailable", retryable=True)
        return HealthStatus(status="ok")

    @app.post(
        "/api/auth/session",
        response_model=UserInfo,
        responses={
            401: {"model": ApiError},
            403: {"model": ApiError},
            422: {"model": ApiError},
            429: {"model": ApiError},
            503: {"model": ApiError},
        },
    )
    def login(
        payload: SessionRequest, request: Request, response: Response
    ) -> UserInfo | JSONResponse:
        client = request.client.host if request.client else "unknown"
        if not limiter.allow(client):
            return error(429, "rate_limited", "Too many login attempts", retryable=True)
        try:
            result = issue_session(database, payload.token)
        except sqlite3.Error:
            return error(503, "not_ready", "Database unavailable", retryable=True)
        if result is None:
            return error(401, "invalid_token", "Invalid access token")
        session, user = result
        response.set_cookie(
            SESSION_COOKIE,
            session,
            max_age=SESSION_LIFETIME_SECONDS,
            secure=True,
            httponly=True,
            samesite="lax",
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return UserInfo(**user)

    @app.get(
        "/api/auth/session",
        response_model=UserInfo,
        responses={401: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError}},
    )
    def session(user: Annotated[UserInfo, Depends(require_user)]) -> UserInfo:
        return user

    @app.delete(
        "/api/auth/session",
        status_code=204,
        responses={
            401: {"model": ApiError},
            403: {"model": ApiError},
            422: {"model": ApiError},
            503: {"model": ApiError},
        },
    )
    def logout(
        response: Response,
        _user: Annotated[UserInfo, Depends(require_user)],
        session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    ) -> None:
        if session:
            revoke_session(database, session)
        response.delete_cookie(SESSION_COOKIE, secure=True, httponly=True, samesite="lax", path="/")

    def own_job(user: UserInfo, job_id: str):
        job = manager.store.get(user.id, job_id)
        if job is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Generation not found").model_dump(),
            )
        return job

    @app.get(
        "/api/prompt-snapshots",
        response_model=PromptSnapshotPage,
        responses={401: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError}},
    )
    def list_prompt_snapshots(
        user: Annotated[UserInfo, Depends(require_user)],
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=9_007_199_254_740_991),
    ) -> PromptSnapshotPage:
        return snapshots.list(user.id, limit=limit, offset=offset)

    @app.post(
        "/api/prompt-snapshots",
        status_code=201,
        response_model=PromptSnapshot,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 409: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def create_prompt_snapshot(
        payload: PromptSnapshotCreate, user: Annotated[UserInfo, Depends(require_user)],
    ) -> PromptSnapshot | JSONResponse:
        try:
            return snapshots.create(user.id, payload)
        except PromptSnapshotConflict:
            return error(
                409, "prompt_snapshot_conflict", "Prompt snapshot already exists or changed",
            )

    def own_snapshot(user: UserInfo, snapshot_id: str) -> PromptSnapshot:
        saved = snapshots.get(user.id, snapshot_id)
        if saved is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Prompt snapshot not found").model_dump(),
            )
        return saved

    @app.get(
        "/api/prompt-snapshots/{snapshot_id}",
        response_model=PromptSnapshot,
        responses={
            401: {"model": ApiError}, 404: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def get_prompt_snapshot(
        snapshot_id: UUID, user: Annotated[UserInfo, Depends(require_user)],
    ) -> PromptSnapshot:
        return own_snapshot(user, str(snapshot_id))

    @app.delete(
        "/api/prompt-snapshots/{snapshot_id}",
        status_code=204,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def delete_prompt_snapshot(
        snapshot_id: UUID, user: Annotated[UserInfo, Depends(require_user)],
    ) -> None:
        if not snapshots.delete(user.id, str(snapshot_id)):
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Prompt snapshot not found").model_dump(),
            )

    @app.post(
        "/api/generations",
        status_code=202,
        response_model=GenerationAccepted,
        responses={
            401: {"model": ApiError},
            403: {"model": ApiError},
            409: {"model": ApiError},
            422: {"model": ApiError},
            429: {"model": ApiError},
            503: {"model": ApiError},
        },
    )
    def submit_generation(
        payload: GenerationRequest, user: Annotated[UserInfo, Depends(require_user)]
    ) -> GenerationAccepted | JSONResponse:
        if payload.reference is not None:
            # Reference images are frozen only by server-owned character dataset runs.
            return error(422, "validation_error", "Reference images are only used by dataset runs")
        try:
            job_id = manager.submit(user.id, payload)
        except GenerationNotConfigured:
            return error(503, "provider_unavailable", "Image generation is not configured")
        except ResultStorageUnavailable:
            return error(503, "result_storage_unavailable", "Image storage is unavailable")
        except ExperimentConflict:
            return error(409, "experiment_conflict", "Experiment group already exists or changed")
        if job_id is None:
            return error(429, "queue_full", "Generation queue is full", retryable=True)
        return GenerationAccepted(id=job_id, status="queued")

    @app.get(
        "/api/generations",
        response_model=HistoryPage,
        responses={
            401: {"model": ApiError},
            422: {"model": ApiError},
            503: {"model": ApiError},
        },
    )
    def list_generations(
        user: Annotated[UserInfo, Depends(require_user)],
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=9_007_199_254_740_991),
        manual_only: bool = Query(default=False),
    ) -> HistoryPage:
        return manager.store.list(user.id, limit=limit, offset=offset, manual_only=manual_only)

    @app.get(
        "/api/generations/{job_id}",
        response_model=GenerationView,
        responses={
            401: {"model": ApiError},
            404: {"model": ApiError},
            422: {"model": ApiError},
            503: {"model": ApiError},
        },
    )
    def get_generation(
        job_id: str, user: Annotated[UserInfo, Depends(require_user)]
    ) -> GenerationView:
        job = own_job(user, job_id)
        return manager.view(job, user.id)

    @app.get(
        "/api/style-experiments",
        response_model=ExperimentPage,
        responses={
            401: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def list_style_experiments(
        user: Annotated[UserInfo, Depends(require_user)],
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=9_007_199_254_740_991),
    ) -> ExperimentPage:
        return manager.store.experiments(user.id, limit=limit, offset=offset)

    def own_run(user: UserInfo, run_id: str) -> RunState:
        run = experiments.store.get(user.id, run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Experiment run not found").model_dump(),
            )
        return run

    @app.post(
        "/api/style-experiment-runs",
        status_code=202,
        response_model=RunState,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 409: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def create_style_run(
        payload: RunCreate, user: Annotated[UserInfo, Depends(require_user)],
    ) -> RunState | JSONResponse:
        try:
            return experiments.store.create(user.id, payload)
        except RunConflict as exception:
            return error(409, exception.code, "Experiment run conflicts with existing work")

    @app.post(
        "/api/dataset-runs",
        status_code=202,
        response_model=RunState,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 409: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def create_dataset_run(
        payload: DatasetRunCreate, user: Annotated[UserInfo, Depends(require_user)],
    ) -> RunState | JSONResponse:
        # Dataset runs share the durable run lifecycle; read/Stop use the style run routes.
        resolved = None
        if payload.character is not None and payload.character.mode == "gpt" and (
            manager.gpt_provider is None
        ):
            return error(503, "gpt_image_unavailable", "GPT image generation is not configured")
        if (
            payload.gpt_concurrency is not None
            and payload.gpt_concurrency > manager.parallelism("gpt")
        ):
            return error(
                422, "gpt_concurrency_too_high", "GPT concurrency exceeds the server limit",
            )
        if payload.character is not None:
            # Pin each owner reference to its current digest; later edits cannot change a run.
            resolved = []
            for reference_id in payload.character.reference_ids:
                item = references.get(user.id, str(reference_id))
                if item is None:
                    return error(422, "reference_not_found", "Reference image not found")
                resolved.append(ReferenceImageUse(id=item.id, sha256=item.sha256))
        try:
            return experiments.store.create(user.id, payload, references=resolved)
        except ReferenceMissing:
            return error(422, "reference_not_found", "Reference image not found")
        except RunConflict as exception:
            return error(409, exception.code, "Experiment run conflicts with existing work")

    @app.get(
        "/api/style-experiment-runs/active",
        response_model=ActiveRun,
        responses={
            401: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def active_style_run(user: Annotated[UserInfo, Depends(require_user)]) -> ActiveRun:
        return ActiveRun(run=experiments.store.active(user.id))

    @app.get(
        "/api/style-experiment-runs/queue",
        response_model=ActiveRuns,
        responses={
            401: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def queued_style_runs(user: Annotated[UserInfo, Depends(require_user)]) -> ActiveRuns:
        # Unfinished runs oldest first; each lane executes its queue_position 0 run.
        return ActiveRuns(runs=experiments.store.queue(user.id))

    @app.get(
        "/api/style-experiment-runs/{run_id}",
        response_model=RunState,
        responses={
            401: {"model": ApiError}, 404: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def get_style_run(
        run_id: UUID, user: Annotated[UserInfo, Depends(require_user)],
    ) -> RunState:
        return own_run(user, str(run_id))

    @app.post(
        "/api/style-experiment-runs/{run_id}/stop",
        response_model=RunState,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def stop_style_run(
        run_id: UUID, user: Annotated[UserInfo, Depends(require_user)],
    ) -> RunState:
        run = experiments.store.stop(user.id, str(run_id))
        return run if run is not None else own_run(user, str(run_id))

    class RunContinuation(BaseModel):
        id: UUID

    def reference_digest(user_id: str, reference_id: str) -> str | None:
        item = references.get(user_id, reference_id)
        return item.sha256 if item is not None else None

    @app.post(
        "/api/rerun-batches",
        status_code=202,
        response_model=RunState,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            409: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def create_rerun_batch(
        payload: RerunBatchCreate, user: Annotated[UserInfo, Depends(require_user)],
    ) -> RunState | JSONResponse:
        # A durable queued batch of paid re-runs of one training set's finished groups.
        # The server submits each item in turn, so the owner may close the page. Retrying
        # with the same id returns the same batch.
        existing = experiments.store.get(user.id, str(payload.id))
        if existing is None:
            source_run = own_run(user, str(payload.experiment_id))
            if source_run.kind != "dataset":
                return error(422, "rerun_unsupported", "Only training-set images can be re-run")
            if source_run.lane == "gpt" and manager.gpt_provider is None:
                return error(
                    503, "gpt_image_unavailable", "GPT image generation is not configured",
                )
            for position, item in enumerate(payload.items, start=1):
                job = manager.store.get(user.id, item.job_id)
                context = job.parameters.experiment if job is not None else None
                if job is None or context is None or str(context.id) != source_run.id:
                    return error(
                        422, "rerun_source_missing",
                        f"Item {position}: group is not part of this training set",
                    )
                try:
                    rerun_parameters(job, item)
                except RerunRefused as refused:
                    return error(
                        409 if refused.code == "job_active" else 422, refused.code,
                        f"Item {position}: {refused.message}",
                    )
            base = (source_run.parameters, source_run.lane)
        else:
            base = (existing.parameters, existing.lane)
        try:
            return experiments.store.create(user.id, payload, rerun_base=base)
        except RunConflict as exception:
            return error(409, exception.code, "Experiment run conflicts with existing work")

    @app.post(
        "/api/style-experiment-runs/{run_id}/continue",
        status_code=202,
        response_model=RunState,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            409: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def continue_style_run(
        run_id: UUID, payload: RunContinuation,
        user: Annotated[UserInfo, Depends(require_user)],
    ) -> RunState | JSONResponse:
        # A new run for the never-claimed items of a stopped dataset run; retries with the
        # same new id return the same run.
        source = own_run(user, str(run_id))
        if source.lane == "gpt" and manager.gpt_provider is None:
            return error(503, "gpt_image_unavailable", "GPT image generation is not configured")
        try:
            created = experiments.store.continue_run(
                user.id, str(run_id), payload.id, reference_digest,
                gpt_model=settings.gpt_image_model,
            )
        except ContinuationRefused as exception:
            status = 409 if exception.code == "experiment_run_active" else 422
            return error(status, exception.code, "The run cannot be continued")
        except ReferenceMissing:
            return error(422, "reference_not_found", "Reference image not found")
        except RunConflict as exception:
            return error(409, exception.code, "Experiment run conflicts with existing work")
        if created is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Experiment run not found").model_dump(),
            )
        return created

    class RunParallelism(BaseModel):
        parallelism: int = Field(ge=1, le=16)

    @app.put(
        "/api/style-experiment-runs/{run_id}/parallelism",
        response_model=RunState,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            409: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def set_run_parallelism(
        run_id: UUID, payload: RunParallelism, user: Annotated[UserInfo, Depends(require_user)],
    ) -> RunState | JSONResponse:
        if payload.parallelism > manager.parallelism("gpt"):
            return error(
                422, "gpt_concurrency_too_high", "GPT concurrency exceeds the server limit",
            )
        result = experiments.store.set_parallelism(user.id, str(run_id), payload.parallelism)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Experiment run not found").model_dump(),
            )
        if result == "not_gpt":
            return error(422, "parallelism_unsupported", "Only GPT image runs are concurrent")
        if result == "finished":
            return error(409, "experiment_run_finished", "The run has already finished")
        return result

    @app.get(
        "/api/style-experiments/{experiment_id}",
        response_model=ExperimentDetail,
        responses={
            401: {"model": ApiError}, 404: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def get_style_experiment(
        experiment_id: UUID, user: Annotated[UserInfo, Depends(require_user)],
        limit: int = Query(default=1, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=9_007_199_254_740_991),
    ) -> ExperimentDetail:
        saved = manager.store.experiment(user.id, str(experiment_id), limit=limit, offset=offset)
        if saved is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Experiment not found").model_dump(),
            )
        summary, items, next_offset = saved
        return ExperimentDetail(
            summary=summary, items=manager.views(items, user.id),
            next_offset=next_offset,
        )

    @app.delete(
        "/api/style-experiments/{experiment_id}",
        response_model=ExperimentDeleted,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            409: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def delete_style_experiment(
        experiment_id: UUID, user: Annotated[UserInfo, Depends(require_user)],
    ) -> ExperimentDeleted | JSONResponse:
        outcome = manager.store.delete_experiment(user.id, str(experiment_id))
        if outcome is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Experiment not found").model_dump(),
            )
        status, job_ids, images = outcome
        if status == "experiment_active":
            return error(409, "experiment_run_active", "Experiment run is still active")
        if status == "active":
            return error(409, "job_active", "A group of this experiment is still running")
        for job_id in job_ids:
            manager.cache.discard(job_id)
            thumbnails.discard(job_id)
        return ExperimentDeleted(deleted_groups=len(job_ids), deleted_images=images)

    @app.put(
        "/api/style-experiments/{experiment_id}/name",
        status_code=204,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def rename_style_experiment(
        experiment_id: UUID, payload: ExperimentRename,
        user: Annotated[UserInfo, Depends(require_user)],
    ) -> None:
        if not manager.store.rename_experiment(user.id, str(experiment_id), payload.name):
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Experiment not found").model_dump(),
            )

    @app.get(
        "/api/generation-results/{job_id}/images/{image_id}",
        response_class=Response,
        responses={
            200: {"content": {"image/png": {}}},
            401: {"model": ApiError},
            404: {"model": ApiError},
            422: {"model": ApiError},
            503: {"model": ApiError},
        },
    )
    def get_image(
        job_id: str, image_id: int, user: Annotated[UserInfo, Depends(require_user)]
    ) -> Response:
        job = own_job(user, job_id)
        image = (
            manager.cache.image(job_id, user.id, image_id) if job.status == "succeeded" else None
        )
        if image is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Image not found").model_dump(),
            )
        return Response(
            content=image.data,
            media_type="image/png",
            headers={
                "Content-Disposition": (
                    f'inline; filename="generation-{job_id}-{image_id + 1}.png"'
                ),
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
            },
        )

    @app.get(
        "/api/generation-results/{job_id}/images/{image_id}/thumbnail",
        response_class=Response,
        responses={
            200: {"content": {"image/webp": {}}},
            401: {"model": ApiError},
            404: {"model": ApiError},
            422: {"model": ApiError},
            503: {"model": ApiError},
        },
    )
    def get_thumbnail(
        job_id: str, image_id: int, user: Annotated[UserInfo, Depends(require_user)]
    ) -> Response:
        # Same ownership/expiry rules as the full PNG; a cached preview is only served
        # while the retained original is still available.
        job = own_job(user, job_id)
        info = manager.cache.describe(job_id, user.id) if job.status == "succeeded" else None
        data = None
        if info is not None and 0 <= image_id < info.image_count:
            data = thumbnails.get(job_id, user.id, image_id)
            if data is None:
                image = manager.cache.image(job_id, user.id, image_id)
                if image is not None:
                    try:
                        data = thumbnails.render(job_id, user.id, image_id, image.data)
                    except ThumbnailBusy:
                        return error(503, "thumbnail_busy", "Previews are busy", retryable=True)
                    except (OSError, ValueError):
                        data = None
        if data is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Image not found").model_dump(),
            )
        return Response(
            content=data,
            media_type="image/webp",
            headers={
                "Content-Disposition": (
                    f'inline; filename="generation-{job_id}-{image_id + 1}-preview.webp"'
                ),
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
            },
        )

    def discard_target(user: UserInfo, job_id: str, image_index: int) -> None:
        job = own_job(user, job_id)
        if job.status != "succeeded" or not 0 <= image_index < job.image_count:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Image not found").model_dump(),
            )

    @app.put(
        "/api/generations/{job_id}/images/{image_index}/discard",
        status_code=204,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def discard_image(
        job_id: str, image_index: int, user: Annotated[UserInfo, Depends(require_user)],
    ) -> None:
        discard_target(user, job_id, image_index)
        manager.store.set_discarded(user.id, job_id, image_index, True)

    @app.delete(
        "/api/generations/{job_id}/images/{image_index}/discard",
        status_code=204,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def restore_image(
        job_id: str, image_index: int, user: Annotated[UserInfo, Depends(require_user)],
    ) -> None:
        discard_target(user, job_id, image_index)
        manager.store.set_discarded(user.id, job_id, image_index, False)

    @app.post(
        "/api/generations/{job_id}/rerun",
        status_code=202,
        response_model=GenerationAccepted,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            409: {"model": ApiError}, 422: {"model": ApiError}, 429: {"model": ApiError},
            503: {"model": ApiError},
        },
    )
    def rerun_generation(
        job_id: str, payload: RerunRequest, user: Annotated[UserInfo, Depends(require_user)],
    ) -> GenerationAccepted | JSONResponse:
        # One explicit paid generation: the same frozen dataset group with a new random
        # seed and one sample. The shown image may be marked discarded in the same click.
        job = own_job(user, job_id)
        try:
            parameters = rerun_parameters(job, payload)
        except RerunRefused as refused:
            return rerun_refusal(refused)
        reference = job.parameters.reference
        if reference is not None and reference.mode == "gpt" and manager.gpt_provider is None:
            return error(503, "gpt_image_unavailable", "GPT image generation is not configured")
        try:
            new_id = manager.submit(user.id, parameters, create=manager.store.create_rerun)
        except GenerationNotConfigured:
            return error(503, "provider_unavailable", "Image generation is not configured")
        except ResultStorageUnavailable:
            return error(503, "result_storage_unavailable", "Image storage is unavailable")
        except ExperimentConflict:
            return error(409, "experiment_conflict", "Training-set group is not available")
        if new_id is None:
            return error(429, "queue_full", "Generation queue is full", retryable=True)
        if payload.discard_index is not None:
            manager.store.set_discarded(user.id, job.id, payload.discard_index, True)
        return GenerationAccepted(id=new_id, status="queued")

    @app.delete(
        "/api/generations/{job_id}",
        status_code=204,
        responses={
            401: {"model": ApiError},
            403: {"model": ApiError},
            404: {"model": ApiError},
            409: {"model": ApiError},
            422: {"model": ApiError},
            503: {"model": ApiError},
        },
    )
    def delete_generation(job_id: str, user: Annotated[UserInfo, Depends(require_user)]) -> None:
        outcome = manager.store.delete(user.id, job_id)
        if outcome is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Generation not found").model_dump(),
            )
        if outcome == "active":
            raise HTTPException(
                status_code=409,
                detail=ApiError(
                    code="job_active", message="Generation is still running"
                ).model_dump(),
            )
        if outcome == "experiment_active":
            raise HTTPException(
                status_code=409,
                detail=ApiError(
                    code="experiment_run_active", message="Experiment run is still active",
                ).model_dump(),
            )
        manager.cache.discard(job_id)
        thumbnails.discard(job_id)

    @app.post(
        "/api/tags/search",
        response_model=SearchResults,
        responses={
            401: {"model": ApiError},
            403: {"model": ApiError},
            422: {"model": ApiError},
            429: {
                "model": ApiError,
                "headers": {
                    "Retry-After": {
                        "description": (
                            "Optional on upstream rate limits; delta-seconds or HTTP-date."
                        ),
                        "schema": {"type": "string"},
                    }
                },
            },
            502: {"model": ApiError},
            503: {"model": ApiError},
            504: {"model": ApiError},
        },
    )
    def search_tags(
        payload: SearchRequest, _user: Annotated[UserInfo, Depends(require_user)]
    ) -> SearchResults | JSONResponse:
        try:
            return tag_search.search(payload)
        except SearchFailure as exception:
            response = error(
                exception.status,
                exception.code,
                exception.message,
                retryable=exception.retryable,
            )
            if exception.status == 429 and exception.retry_after is not None:
                response.headers["Retry-After"] = exception.retry_after
            return response

    class Capabilities(BaseModel):
        gpt_image: bool
        gpt_image_model: str | None
        # Server cap for one GPT run's concurrency (NAI_GPT_IMAGE_CONCURRENCY).
        gpt_concurrency_max: int | None = None

    @app.get(
        "/api/capabilities",
        response_model=Capabilities,
        responses={401: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError}},
    )
    def capabilities(_user: Annotated[UserInfo, Depends(require_user)]) -> Capabilities:
        available = manager.gpt_provider is not None
        return Capabilities(
            gpt_image=available,
            gpt_image_model=settings.gpt_image_model if available else None,
            gpt_concurrency_max=manager.parallelism("gpt") if available else None,
        )

    def reference_error(exception: ReferenceFailure) -> JSONResponse:
        return error(exception.status, exception.code, exception.message)

    @app.get(
        "/api/reference-images",
        response_model=ReferenceImageList,
        responses={401: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError}},
    )
    def list_reference_images(
        user: Annotated[UserInfo, Depends(require_user)],
    ) -> ReferenceImageList:
        return ReferenceImageList(items=references.list(user.id))

    @app.post(
        "/api/reference-images",
        status_code=201,
        response_model=ReferenceImage,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 409: {"model": ApiError},
            413: {"model": ApiError}, 415: {"model": ApiError}, 422: {"model": ApiError},
            503: {"model": ApiError},
        },
        openapi_extra={"requestBody": {"required": True, "content": {
            "image/png": {"schema": {"type": "string", "format": "binary"}},
            "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
        }}},
    )
    async def upload_reference_image(
        request: Request, user: Annotated[UserInfo, Depends(require_user)],
    ) -> ReferenceImage | JSONResponse:
        # Raw image body: no multipart dependency, bounded before decoding anything.
        content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type not in ("image/png", "image/jpeg"):
            return error(415, "unsupported_media_type", "Upload a PNG or JPEG image")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_REFERENCE_BYTES:
                return error(413, "reference_too_large", "Reference image exceeds 8 MiB")
        try:
            return await asyncio.to_thread(references.add, user.id, bytes(body), source="upload")
        except ReferenceFailure as exception:
            return reference_error(exception)

    class ReferenceFromResult(BaseModel):
        job_id: str = Field(min_length=1, max_length=64)
        image_index: int = Field(ge=0, le=7)

    @app.post(
        "/api/reference-images/from-result",
        status_code=201,
        response_model=ReferenceImage,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            409: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def reference_from_result(
        payload: ReferenceFromResult, user: Annotated[UserInfo, Depends(require_user)],
    ) -> ReferenceImage | JSONResponse:
        job = own_job(user, payload.job_id)
        image = (
            manager.cache.image(payload.job_id, user.id, payload.image_index)
            if job.status == "succeeded" else None
        )
        if image is None:
            return error(404, "not_found", "Image not found or expired")
        try:
            return references.add(user.id, image.data, source="result")
        except ReferenceFailure as exception:
            return reference_error(exception)

    @app.get(
        "/api/reference-images/{image_id}/image",
        response_class=Response,
        responses={
            200: {"content": {"image/png": {}, "image/jpeg": {}}},
            401: {"model": ApiError}, 404: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def get_reference_image(
        image_id: UUID, user: Annotated[UserInfo, Depends(require_user)],
    ) -> Response:
        found = references.read(user.id, str(image_id))
        if found is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Reference image not found").model_dump(),
            )
        item, data = found
        return Response(
            content=data, media_type=item.mime_type,
            headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
        )

    @app.get(
        "/api/reference-images/{image_id}/thumbnail",
        response_class=Response,
        responses={
            200: {"content": {"image/webp": {}}},
            401: {"model": ApiError}, 404: {"model": ApiError},
            422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def get_reference_thumbnail(
        image_id: UUID, user: Annotated[UserInfo, Depends(require_user)],
    ) -> Response:
        # Reference bytes never change under one id, so a cached preview stays valid until
        # deletion; ownership is re-checked against the stored image on every request.
        found = references.read(user.id, str(image_id))
        if found is None:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Reference image not found").model_dump(),
            )
        item, original = found
        key = f"reference:{item.id}:{item.sha256}"
        data = thumbnails.get(key, user.id, 0)
        if data is None:
            try:
                data = thumbnails.render(key, user.id, 0, original, formats=("PNG", "JPEG"))
            except ThumbnailBusy:
                return error(503, "thumbnail_busy", "Previews are busy", retryable=True)
            except (OSError, ValueError) as exception:
                raise HTTPException(
                    status_code=404,
                    detail=ApiError(code="not_found", message="Reference image not found")
                    .model_dump(),
                ) from exception
        return Response(
            content=data, media_type="image/webp",
            headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
        )

    @app.delete(
        "/api/reference-images/{image_id}",
        status_code=204,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 404: {"model": ApiError},
            409: {"model": ApiError}, 422: {"model": ApiError}, 503: {"model": ApiError},
        },
    )
    def delete_reference_image(
        image_id: UUID, user: Annotated[UserInfo, Depends(require_user)],
    ) -> None:
        try:
            deleted = references.delete(user.id, str(image_id))
        except ReferenceFailure as exception:
            raise HTTPException(
                status_code=exception.status,
                detail=ApiError(code=exception.code, message=exception.message).model_dump(),
            ) from exception
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Reference image not found").model_dump(),
            )
        thumbnails.discard_prefix(f"reference:{image_id}:")

    class TraitAdviceRequest(BaseModel):
        reference_ids: list[UUID] = Field(min_length=1, max_length=4)
        traits: str = Field(default="", max_length=1000)

    @app.post(
        "/api/reference-images/trait-advice",
        response_model=AdviceResult,
        responses={
            401: {"model": ApiError}, 403: {"model": ApiError}, 422: {"model": ApiError},
            429: {"model": ApiError}, 502: {"model": ApiError}, 503: {"model": ApiError},
            504: {"model": ApiError},
        },
    )
    async def trait_advice(
        payload: TraitAdviceRequest, user: Annotated[UserInfo, Depends(require_user)],
    ) -> AdviceResult | JSONResponse:
        if len(set(payload.reference_ids)) != len(payload.reference_ids):
            return error(422, "validation_error", "Duplicate reference image")
        images = []
        for reference_id in payload.reference_ids:
            found = await asyncio.to_thread(references.read, user.id, str(reference_id))
            if found is None:
                return error(422, "reference_not_found", "Reference image not found")
            images.append(found[1])
        try:
            return await advice_service.advise(
                trait_advice_text(payload.traits), images=images, timeout=TRAIT_TIMEOUT_SECONDS,
            )
        except AdviceFailure as exception:
            return error(
                exception.status, exception.code, exception.message,
                retryable=exception.retryable,
            )

    @app.post(
        "/api/advice",
        response_model=AdviceResult,
        responses={
            401: {"model": ApiError},
            403: {"model": ApiError},
            422: {"model": ApiError},
            429: {"model": ApiError},
            502: {"model": ApiError},
            503: {"model": ApiError},
            504: {"model": ApiError},
        },
    )
    async def advise(
        payload: AdviceRequest, _user: Annotated[UserInfo, Depends(require_user)]
    ) -> AdviceResult | JSONResponse:
        try:
            return await advice_service.advise(payload.input)
        except AdviceFailure as exception:
            return error(
                exception.status,
                exception.code,
                exception.message,
                retryable=exception.retryable,
            )

    return app


app = create_app()
