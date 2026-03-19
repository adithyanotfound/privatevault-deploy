"""Health check endpoints — used by load balancers and k8s probes."""
from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from lork.config import get_settings
from lork.storage.db import check_db_connection
from lork.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Full health check — checks DB and Redis connectivity."""
    settings = get_settings()
    checks: dict[str, bool] = {}

    # Database
    checks["database"] = await check_db_connection()

    # Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(str(settings.REDIS_URL), socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False

    all_ok = all(checks.values())

    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT.value,
        checks=checks,
    )


@router.get("/health/live")
async def liveness() -> JSONResponse:
    """Kubernetes liveness probe — just confirms process is running."""
    return JSONResponse({"status": "ok"})


@router.get("/health/ready")
async def readiness() -> JSONResponse:
    """Kubernetes readiness probe — confirms DB is reachable."""
    db_ok = await check_db_connection()

    if not db_ok:
        return JSONResponse({"status": "not_ready", "db": False}, status_code=503)

    return JSONResponse({"status": "ready"})
