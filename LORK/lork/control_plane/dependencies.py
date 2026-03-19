"""
FastAPI dependency injection.
Provides get_current_org, require_scopes, and service factories.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from lork.storage.db import AsyncSession, get_db
from lork.models import Organization
from lork.control_plane.services.agent_registry_service import AgentRegistryService
from lork.control_plane.services.auth_service import AuthService
from lork.control_plane.services.task_scheduler_service import TaskSchedulerService
from lork.observability.logging import get_logger
from lork.policy.engine import PolicyEngine
from lork.config import get_settings

log = get_logger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


async def _get_org_from_api_key(
    api_key_value: str | None,
    db: AsyncSession,
) -> Organization | None:
    if not api_key_value:
        return None

    svc = AuthService(db)
    result = await svc.validate_api_key(api_key_value)

    if result is None:
        return None

    _key, org = result
    return org


async def get_current_org(
    api_key: Annotated[str | None, Depends(_api_key_header)],
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Organization:
    """Resolves either X-API-Key or Bearer token to an Organization."""

    org: Organization | None = None

    if api_key:
        org = await _get_org_from_api_key(api_key, db)

    elif bearer:
        svc = AuthService(db)

        try:
            payload = svc.decode_token(bearer.credentials)

            from sqlalchemy import select
            from lork.models import Organization as OrgModel

            result = await db.execute(
                select(OrgModel).where(OrgModel.id == payload.get("sub"))
            )

            org = result.scalar_one_or_none()

        except Exception:
            pass

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing credentials",
        )

    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive",
        )

    return org


def get_agent_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentRegistryService:
    return AgentRegistryService(db)


def get_task_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskSchedulerService:
    return TaskSchedulerService(db)


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    return AuthService(db)


def get_policy_engine(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyEngine:

    settings = get_settings()

    return PolicyEngine(
        db,
        enforce_mode=settings.POLICY_ENFORCE_MODE,
    )
