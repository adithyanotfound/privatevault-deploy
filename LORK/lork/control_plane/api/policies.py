"""
Policy Management REST API.
Create, update, delete policies and run ad-hoc policy checks.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from lork.control_plane.dependencies import get_current_org, get_policy_engine
from lork.models import Organization, Policy
from lork.schemas import (
    PaginatedResponse,
    PolicyCheckRequest,
    PolicyCheckResponse,
    PolicyCreate,
    PolicyResponse,
    PolicyUpdate,
)
from lork.storage.db import AsyncSession, get_db
from lork.policy.engine import PolicyContext, PolicyEngine, record_policy_decision

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    body: PolicyCreate,
    org: Annotated[Organization, Depends(get_current_org)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyResponse:

    policy = Policy(
        organization_id=str(org.id),
        name=body.name,
        description=body.description,
        effect=body.effect,
        priority=body.priority,
        rule=body.rule.model_dump(),
        applies_to_agents=body.applies_to_agents,
    )

    db.add(policy)
    await db.flush()

    return PolicyResponse.model_validate(policy)


@router.get("", response_model=PaginatedResponse[PolicyResponse])
async def list_policies(
    org: Annotated[Organization, Depends(get_current_org)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[PolicyResponse]:

    base = select(Policy).where(Policy.organization_id == str(org.id))

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(Policy.priority.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return PaginatedResponse(
        items=[PolicyResponse.model_validate(p) for p in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("/check", response_model=PolicyCheckResponse)
async def check_policy(
    body: PolicyCheckRequest,
    org: Annotated[Organization, Depends(get_current_org)],
    engine: Annotated[PolicyEngine, Depends(get_policy_engine)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyCheckResponse:

    ctx = PolicyContext(
        agent_id=body.agent_id,
        organization_id=str(org.id),
        action=body.action,
        resource=body.resource,
        extra=body.context,
    )

    decision = await engine.check(ctx)

    await record_policy_decision(db, ctx, decision)

    return decision
