"""FastAPI entry point with stable errors and cookie-based authentication."""

import asyncio
import sqlite3
import threading
import time
from collections import deque
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import Cookie, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .advice import AdviceFailure, AdviceRequest, AdviceResult, AdviceRunner, AdviceService
from .auth import current_user, issue_session, revoke_session
from .codex_advice import CodexAdviceRunner
from .config import Settings
from .db import Database
from .generations import (
    GenerationManager,
    GenerationRequest,
    GenerationView,
    HistoryPage,
    ImageProvider,
    ResultCache,
)
from .mcp_images import NovelAiMcpProvider
from .security import SESSION_COOKIE, SESSION_LIFETIME_SECONDS
from .tags import SearchFailure, SearchRequest, SearchResults, TagSearch


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
    result_cache: ResultCache | None = None,
    tag_search: TagSearch | None = None,
    advice_runner: AdviceRunner | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    database = database or Database(settings.sqlite_path)
    limiter = LoginLimiter()
    if image_provider is None and settings.novelai_mcp_token is not None:
        image_provider = NovelAiMcpProvider(settings.novelai_mcp_url, settings.novelai_mcp_token)
    manager = GenerationManager(database, image_provider, cache=result_cache)
    tag_search = tag_search or TagSearch(
        settings.tag_search_url, settings.public_origin, settings.tag_search_key
    )
    if advice_runner is None and settings.codex_api_key:
        advice_runner = CodexAdviceRunner(settings.codex_api_key)
    advice_service = AdviceService(advice_runner)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if database.check_ready():
            manager.start()
        try:
            yield
        finally:
            await asyncio.to_thread(manager.stop)
            if isinstance(advice_runner, CodexAdviceRunner):
                await advice_runner.close()

    app = FastAPI(title="NovelAI Workspace API", lifespan=lifespan)
    app.state.database = database
    app.state.generations = manager

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
    def session(user: UserInfo = Depends(require_user)) -> UserInfo:
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
        _user: UserInfo = Depends(require_user),
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

    @app.post(
        "/api/generations",
        status_code=202,
        response_model=GenerationAccepted,
        responses={
            401: {"model": ApiError},
            403: {"model": ApiError},
            422: {"model": ApiError},
            429: {"model": ApiError},
            503: {"model": ApiError},
        },
    )
    def submit_generation(
        payload: GenerationRequest, user: UserInfo = Depends(require_user)
    ) -> GenerationAccepted | JSONResponse:
        try:
            job_id = manager.submit(user.id, payload)
        except RuntimeError:
            return error(503, "provider_unavailable", "Image generation is not configured")
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
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=9_007_199_254_740_991),
        user: UserInfo = Depends(require_user),
    ) -> HistoryPage:
        return manager.store.list(user.id, limit=limit, offset=offset)

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
    def get_generation(job_id: str, user: UserInfo = Depends(require_user)) -> GenerationView:
        job = own_job(user, job_id)
        result = manager.cache.get(job_id, user.id) if job.status == "succeeded" else None
        return GenerationView(
            **job.model_dump(),
            image_urls=[
                f"/api/generation-results/{job_id}/images/{index}"
                for index in range(len(result.images))
            ]
            if result else [],
            result_expires_at=result.expires_at if result else None,
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
        job_id: str, image_id: int, user: UserInfo = Depends(require_user)
    ) -> Response:
        job = own_job(user, job_id)
        result = manager.cache.get(job_id, user.id) if job.status == "succeeded" else None
        if result is None or image_id < 0 or image_id >= len(result.images):
            raise HTTPException(
                status_code=404,
                detail=ApiError(code="not_found", message="Image not found").model_dump(),
            )
        return Response(
            content=result.images[image_id].data,
            media_type="image/png",
            headers={
                "Content-Disposition": (
                    f'inline; filename="generation-{job_id}-{image_id + 1}.png"'
                ),
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
            },
        )

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
    def delete_generation(job_id: str, user: UserInfo = Depends(require_user)) -> None:
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
        manager.cache.discard(job_id)

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
        payload: SearchRequest, _user: UserInfo = Depends(require_user)
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
        payload: AdviceRequest, _user: UserInfo = Depends(require_user)
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
