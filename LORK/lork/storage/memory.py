"""
lork/storage/memory.py
=======================
In-memory storage implementations for all LORK stores.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

from lork.models import (
    Agent,
    AgentStatus,
    LorkEvent,
    Policy,
    Run,
    Task,
    TaskStatus,
    Tenant,
)


class _InMemoryStore:

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def _set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._data[key] = deepcopy(value)

    async def _get(self, key: str) -> Any | None:
        async with self._lock:
            item = self._data.get(key)
            return deepcopy(item) if item is not None else None

    async def _delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)

    async def _values(self) -> list[Any]:
        async with self._lock:
            return [deepcopy(v) for v in self._data.values()]


class InMemoryTenantStore(_InMemoryStore):

    async def save(self, tenant: Tenant) -> None:
        await self._set(tenant.id, tenant)

    async def get_by_id(self, tenant_id: str) -> Tenant | None:
        return await self._get(tenant_id)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        for t in await self._values():
            if t.slug == slug:
                return t
        return None

    async def list_all(self) -> list[Tenant]:
        return await self._values()


class InMemoryAgentStore(_InMemoryStore):

    async def save(self, agent: Agent) -> None:
        await self._set(agent.id, agent)

    async def get_by_id(self, agent_id: str) -> Agent | None:
        return await self._get(agent_id)

    async def get_by_name(self, tenant_id: str, name: str) -> Agent | None:
        for agent in await self._values():
            if agent.tenant_id == tenant_id and agent.name == name:
                return agent
        return None

    async def list_by_tenant(
        self,
        tenant_id: str,
        status: AgentStatus | None = None,
        tags: dict[str, str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Agent]:

        agents = [
            a for a in await self._values()
            if a.tenant_id == tenant_id
        ]

        if status:
            agents = [a for a in agents if a.status == status]

        if tags:
            agents = [
                a for a in agents
                if all(a.tags.get(k) == v for k, v in tags.items())
            ]

        agents.sort(key=lambda a: a.created_at)

        return agents[offset: offset + limit]

    async def delete(self, agent_id: str) -> None:
        await self._delete(agent_id)


class InMemoryTaskStore(_InMemoryStore):

    async def save(self, task: Task) -> None:
        await self._set(task.id, task)

    async def get(self, task_id: str) -> Task | None:
        return await self._get(task_id)

    async def list_by_agent(
        self,
        agent_id: str,
        status: TaskStatus | None = None,
    ) -> list[Task]:

        tasks = [t for t in await self._values() if t.agent_id == agent_id]

        if status:
            tasks = [t for t in tasks if t.status == status]

        tasks.sort(key=lambda t: t.created_at)

        return tasks

    async def list_by_tenant(
        self,
        tenant_id: str,
        status: TaskStatus | None = None,
    ) -> list[Task]:

        tasks = [t for t in await self._values() if t.tenant_id == tenant_id]

        if status:
            tasks = [t for t in tasks if t.status == status]

        tasks.sort(key=lambda t: t.created_at)

        return tasks

    async def delete(self, task_id: str) -> None:
        await self._delete(task_id)


class InMemoryPolicyStore(_InMemoryStore):

    async def save(self, policy: Policy) -> None:
        await self._set(policy.id, policy)

    async def get(self, policy_id: str) -> Policy | None:
        return await self._get(policy_id)

    async def list_by_tenant(self, tenant_id: str) -> list[Policy]:
        return [p for p in await self._values() if p.tenant_id == tenant_id]

    async def list_for_agent(self, tenant_id: str, agent_id: str) -> list[Policy]:

        return [
            p for p in await self._values()
            if p.tenant_id == tenant_id and (not p.applies_to or agent_id in p.applies_to)
        ]

    async def delete(self, policy_id: str) -> None:
        await self._delete(policy_id)


class InMemoryRunStore(_InMemoryStore):

    async def save(self, run: Run) -> None:
        await self._set(run.id, run)

    async def get(self, run_id: str) -> Run | None:
        return await self._get(run_id)

    async def list_by_task(self, task_id: str) -> list[Run]:
        return [r for r in await self._values() if r.task_id == task_id]

    async def list_by_agent(self, agent_id: str, limit: int = 50) -> list[Run]:

        runs = [r for r in await self._values() if r.agent_id == agent_id]

        runs.sort(key=lambda r: r.started_at, reverse=True)

        return runs[:limit]


class InMemoryEventBus:

    def __init__(self) -> None:
        self._handlers: dict[str, list[Any]] = {}
        self._log: list[LorkEvent] = []

    def subscribe(self, event_type: str, handler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: LorkEvent) -> None:

        self._log.append(event)

        handlers = (
            self._handlers.get(event.type.value, [])
            + self._handlers.get("*", [])
        )

        if handlers:
            await asyncio.gather(
                *(h(event) for h in handlers),
                return_exceptions=True,
            )

    @property
    def events(self) -> list[LorkEvent]:
        return list(self._log)

    def events_of_type(self, event_type: str) -> list[LorkEvent]:
        return [e for e in self._log if e.type.value == event_type]
