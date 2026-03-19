"""
Agent Registry Service.
All agent lifecycle operations with full audit trail.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lork.models import Agent, AgentStatus, AuditLog, AuditSeverity
from lork.schemas import AgentCreate, AgentResponse, AgentUpdate, PaginatedResponse
from lork.observability.logging import get_logger

log = get_logger(__name__)


class AgentNotFoundError(Exception):
    pass


class AgentConflictError(Exception):
    pass


class AgentRegistryService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_agent(
        self,
        organization_id: str,
        data: AgentCreate,
        created_by: str | None = None,
    ) -> AgentResponse:

        existing = await self._db.execute(
            select(Agent).where(
                Agent.organization_id == organization_id,
                Agent.name == data.name,
            )
        )

        if existing.scalar_one_or_none():
            raise AgentConflictError(
                f"Agent '{data.name}' already exists in this organization"
            )

        agent = Agent(
            organization_id=organization_id,
            name=data.name,
            description=data.description,
            permissions=data.permissions,
            capabilities=data.capabilities,
            llm_provider=data.llm_provider,
            llm_model=data.llm_model,
            system_prompt=data.system_prompt,
            max_concurrent_tasks=data.max_concurrent_tasks,
            task_timeout_seconds=data.task_timeout_seconds,
            metadata_=data.metadata,
            tags=data.tags,
            status=AgentStatus.PENDING,
        )

        self._db.add(agent)
        await self._db.flush()

        self._db.add(
            AuditLog(
                organization_id=organization_id,
                agent_id=agent.id,
                event_type="agent.created",
                action="agent.create",
                resource=f"agent:{agent.id}",
                outcome="allowed",
                severity=AuditSeverity.INFO,
                details={"name": agent.name, "created_by": created_by},
            )
        )

        log.info("agent.created", agent_id=agent.id, name=agent.name)

        return AgentResponse.model_validate(agent)
