"""
Task Orchestration REST API.
Submit, monitor, and cancel tasks.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from lork.control_plane.dependencies import get_current_org, get_task_service
from lork.models import Organization, Task, TaskStatus
from lork.schemas import PaginatedResponse, TaskCreate, TaskResponse
from lork.storage.db import AsyncSession, get_db
from lork.control_plane.services.task_scheduler_service import (
    TaskNotFoundError,
    TaskSchedulerService,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def submit_task(
    body: TaskCreate,
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[TaskSchedulerService, Depends(get_task_service)],
) -> TaskResponse:
    """Submit a new task for execution by an AI agent."""
    return await svc.submit_task(str(org.id), body)


@router.get("", response_model=PaginatedResponse[TaskResponse])
async def list_tasks(
    org: Annotated[Organization, Depends(get_current_org)],
    db: Annotated[AsyncSession, Depends(get_db)],
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    agent_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[TaskResponse]:

    base = select(Task).where(Task.organization_id == str(org.id))

    if task_status:
        base = base.where(Task.status == task_status)

    if agent_id:
        base = base.where(Task.agent_id == agent_id)

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(Task.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return PaginatedResponse(
        items=[TaskResponse.model_validate(t) for t in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[TaskSchedulerService, Depends(get_task_service)],
) -> TaskResponse:

    try:
        return await svc.get_task(task_id, str(org.id))
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[TaskSchedulerService, Depends(get_task_service)],
) -> TaskResponse:

    try:
        return await svc.cancel_task(task_id, str(org.id))
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
