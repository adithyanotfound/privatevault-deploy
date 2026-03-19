"""
Agent Registry REST API.
CRUD + lifecycle operations (activate, suspend, terminate, heartbeat).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from lork.control_plane.dependencies import get_agent_service, get_current_org
from lork.models import AgentStatus, Organization
from lork.schemas import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    PaginatedResponse,
)
from lork.control_plane.services.agent_registry_service import (
    AgentConflictError,
    AgentNotFoundError,
    AgentRegistryService,
)

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate,
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[AgentRegistryService, Depends(get_agent_service)],
) -> AgentResponse:
    try:
        return await svc.create_agent(str(org.id), body)
    except AgentConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=PaginatedResponse[AgentResponse])
async def list_agents(
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[AgentRegistryService, Depends(get_agent_service)],
    agent_status: AgentStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[AgentResponse]:
    return await svc.list_agents(str(org.id), status=agent_status, page=page, page_size=page_size)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[AgentRegistryService, Depends(get_agent_service)],
) -> AgentResponse:
    try:
        return await svc.get_agent(agent_id, str(org.id))
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    body: AgentUpdate,
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[AgentRegistryService, Depends(get_agent_service)],
) -> AgentResponse:
    try:
        return await svc.update_agent(agent_id, str(org.id), body)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{agent_id}/activate", response_model=AgentResponse)
async def activate_agent(
    agent_id: str,
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[AgentRegistryService, Depends(get_agent_service)],
) -> AgentResponse:
    try:
        return await svc.activate_agent(agent_id, str(org.id))
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{agent_id}/suspend", response_model=AgentResponse)
async def suspend_agent(
    agent_id: str,
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[AgentRegistryService, Depends(get_agent_service)],
) -> AgentResponse:
    try:
        return await svc.suspend_agent(agent_id, str(org.id))
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{agent_id}/terminate", response_model=AgentResponse)
async def terminate_agent(
    agent_id: str,
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[AgentRegistryService, Depends(get_agent_service)],
) -> AgentResponse:
    try:
        return await svc.terminate_agent(agent_id, str(org.id))
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{agent_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
async def agent_heartbeat(
    agent_id: str,
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[AgentRegistryService, Depends(get_agent_service)],
) -> None:
    try:
        await svc.record_heartbeat(agent_id, str(org.id))
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    org: Annotated[Organization, Depends(get_current_org)],
    svc: Annotated[AgentRegistryService, Depends(get_agent_service)],
) -> None:
    try:
        await svc.delete_agent(agent_id, str(org.id))
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
