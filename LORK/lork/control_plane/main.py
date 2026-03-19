"""
LORK Control Plane — FastAPI application factory.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from lork.config import get_settings
from lork.storage.db import dispose_engine
from lork.control_plane.api import agents, audit_logs as audit, health, policies, tasks
from lork.observability.logging import configure_logging, get_logger

log = get_logger(__name__)

# ── Prometheus metrics ────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "lork_http_requests_total",
    "Total HTTP request count",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "lork_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)


class MetricsMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: object) -> Response:
        start = time.perf_counter()

        response: Response = await call_next(request)  # type: ignore

        duration = time.perf_counter() - start
        route = request.url.path

        REQUEST_COUNT.labels(request.method, route, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, route).observe(duration)

        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject request ID into logs and responses."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        import uuid

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response: Response = await call_next(request)  # type: ignore
        response.headers["X-Request-ID"] = request_id

        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:

    configure_logging()
    settings = get_settings()

    log.info(
        "lork.startup",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT.value,
    )

    yield

    await dispose_engine()
    log.info("lork.shutdown")


def create_app() -> FastAPI:

    settings = get_settings()

    app = FastAPI(
        title="LORK Control Plane",
        description="Production control plane for AI agents",
        version=settings.APP_VERSION,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Middleware
    if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:

        log.warning(
            "request.validation_error",
            errors=exc.errors(),
            path=request.url.path,
        )

        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors(), "body": str(exc.body)},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:

        log.error(
            "request.unhandled_error",
            error=str(exc),
            path=request.url.path,
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Routers
    prefix = settings.API_PREFIX

    app.include_router(health.router)
    app.include_router(agents.router, prefix=prefix)
    app.include_router(policies.router, prefix=prefix)
    app.include_router(tasks.router, prefix=prefix)
    app.include_router(audit.router, prefix=prefix)

    # Metrics
    if settings.PROMETHEUS_ENABLED:

        @app.get("/metrics", include_in_schema=False)
        async def metrics() -> Response:
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()


def start() -> None:

    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "lork.control_plane.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        workers=settings.API_WORKERS,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    start()
