"""Audit Log REST API — read-only access to the immutable audit trail."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from lork.storage.db import AsyncSession, get_db
from lork.control_plane.dependencies import get_current_org
from lork.models import AuditLog, AuditSeverity, Organization
from lork.schemas import AuditLogResponse, PaginatedResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    org: Annotated[Organization, Depends(get_current_org)],
    db: Annotated[AsyncSession, Depends(get_db)],
    agent_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    severity: AuditSeverity | None = Query(default=None),
    outcome: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaginatedResponse[AuditLogResponse]:
    """Query the audit trail with filtering."""

    base = select(AuditLog).where(AuditLog.organization_id == str(org.id))

    if agent_id:
        base = base.where(AuditLog.agent_id == agent_id)

    if event_type:
        base = base.where(AuditLog.event_type == event_type)

    if severity:
        base = base.where(AuditLog.severity == severity)

    if outcome:
        base = base.where(AuditLog.outcome == outcome)

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )
