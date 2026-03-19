"""
lork/control_plane/agent_registry.py
=====================================
Agent Registry — the source of truth for all registered AI agents.

Responsibilities:
  - Register, activate, suspend, and retire agents.
  - Look up agents by ID, name, tenant, or tags.
  - Validate agent configuration before persistence.
  - Emit lifecycle events on every state change.
"""

from __future__ import annotations

import logging
from typing import Protocol

from lork.models import (
    Agent,
    AgentPermissions,
    AgentStatus,
    EventType,
    LorkEvent,
    new_id,
    utc_now,
)

from lork.exceptions import (
    AgentAlreadyExistsError,
    AgentNotFoundError,
    AgentSuspendedError,
    InvalidAgentConfigError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Storage interface
# ---------------------------------------------------------------------------

class AgentStore(Protocol):

    async def save(self, agent: Agent) -> None: ...

    async def get_by_id(self, agent_id: str) -> Agent | None: ...

    async def get_by_name(self, tenant_id: str, name: str) -> Agent | None: ...

    async def list_by_tenant(
        self,
        tenant_id: str,
        status: AgentStatus | None = None,
        tags: dict[str, str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Agent]: ...

    async def delete(self, agent_id: str) -> None: ...


class EventBus(Protocol):

    async def publish(self, event: LorkEvent) -> None: ...


# ---------------------------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------------------------

class AgentRegistry:

    def __init__(self, store: AgentStore, event_bus: EventBus) -> None:
        self._store = store
        self._bus = event_bus


    async def register(
        self,
        tenant_id: str,
        name: str,
        description: str = "",
        permissions: AgentPermissions | None = None,
        tags: dict[str, str] | None = None,
    ) -> Agent:

        self._validate_name(name)

        existing = await self._store.get_by_name(tenant_id, name)

        if existing:
            raise AgentAlreadyExistsError(
                f"Agent '{name}' already exists in tenant '{tenant_id}'.",
                tenant_id=tenant_id,
                name=name,
            )

        agent = Agent(
            id=new_id(),
            tenant_id=tenant_id,
            name=name,
            description=description,
            status=AgentStatus.PENDING,
            permissions=permissions or AgentPermissions(),
            tags=tags or {},
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        await self._store.save(agent)

        await self._bus.publish(
            LorkEvent(
                type=EventType.AGENT_REGISTERED,
                tenant_id=tenant_id,
                source="agent_registry",
                payload={"agent_id": agent.id, "name": name},
            )
        )

        logger.info("agent.registered tenant=%s agent=%s name=%s", tenant_id, agent.id, name)

        return agent


    async def activate(self, agent_id: str) -> Agent:

        agent = await self._require_agent(agent_id)

        agent = self._transition(agent, AgentStatus.ACTIVE)

        await self._store.save(agent)

        await self._bus.publish(
            LorkEvent(
                type=EventType.AGENT_ACTIVATED,
                tenant_id=agent.tenant_id,
                source="agent_registry",
                payload={"agent_id": agent_id},
            )
        )

        return agent


    async def suspend(self, agent_id: str, reason: str = "") -> Agent:

        agent = await self._require_agent(agent_id)

        agent = self._transition(agent, AgentStatus.SUSPENDED)

        await self._store.save(agent)

        await self._bus.publish(
            LorkEvent(
                type=EventType.AGENT_SUSPENDED,
                tenant_id=agent.tenant_id,
                source="agent_registry",
                payload={"agent_id": agent_id, "reason": reason},
            )
        )

        return agent


    async def retire(self, agent_id: str) -> Agent:

        agent = await self._require_agent(agent_id)

        agent = self._transition(agent, AgentStatus.RETIRED)

        await self._store.save(agent)

        await self._bus.publish(
            LorkEvent(
                type=EventType.AGENT_RETIRED,
                tenant_id=agent.tenant_id,
                source="agent_registry",
                payload={"agent_id": agent_id},
            )
        )

        return agent


    async def get(self, agent_id: str) -> Agent:

        return await self._require_agent(agent_id)


    async def list(
        self,
        tenant_id: str,
        status: AgentStatus | None = None,
        tags: dict[str, str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Agent]:

        return await self._store.list_by_tenant(
            tenant_id=tenant_id,
            status=status,
            tags=tags,
            limit=limit,
            offset=offset,
        )


    async def update_permissions(
        self,
        agent_id: str,
        permissions: AgentPermissions,
    ) -> Agent:

        agent = await self._require_agent(agent_id)

        updated = agent.model_copy(
            update={
                "permissions": permissions,
                "updated_at": utc_now(),
            }
        )

        await self._store.save(updated)

        return updated


    async def assert_runnable(self, agent_id: str) -> Agent:

        agent = await self._require_agent(agent_id)

        if agent.status == AgentStatus.SUSPENDED:
            raise AgentSuspendedError(
                f"Agent '{agent_id}' is suspended and cannot run tasks.",
                agent_id=agent_id,
            )

        if agent.status != AgentStatus.ACTIVE:
            raise AgentSuspendedError(
                f"Agent '{agent_id}' is in '{agent.status}' state.",
                agent_id=agent_id,
            )

        return agent


    async def _require_agent(self, agent_id: str) -> Agent:

        agent = await self._store.get_by_id(agent_id)

        if not agent:
            raise AgentNotFoundError(
                f"Agent '{agent_id}' not found.",
                agent_id=agent_id,
            )

        return agent


    @staticmethod
    def _transition(agent: Agent, new_status: AgentStatus) -> Agent:

        return agent.model_copy(
            update={
                "status": new_status,
                "updated_at": utc_now(),
            }
        )


    @staticmethod
    def _validate_name(name: str) -> None:

        if not name or not name.replace("_", "").replace("-", "").isalnum():
            raise InvalidAgentConfigError(
                f"Agent name '{name}' is invalid.",
                name=name,
            )

        if len(name) > 128:
            raise InvalidAgentConfigError(
                f"Agent name too long ({len(name)} chars). Max 128.",
                name=name,
            )
