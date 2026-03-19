"""
lork/control_plane/scheduler.py
================================
Task Scheduler — assigns tasks to runtime workers.
"""

from __future__ import annotations

import asyncio
import heapq
import logging
from typing import Protocol

from lork.models import (
    Agent,
    Task,
    TaskInput,
    TaskStatus,
    EventType,
    LorkEvent,
    new_id,
    utc_now,
)

from lork.exceptions import (
    AgentNotFoundError,
    SchedulerOverloadedError,
    TaskDeadlineExceededError,
    TaskNotFoundError,
)

logger = logging.getLogger(__name__)

MAX_QUEUE_SIZE = 100_000
DEADLINE_CHECK_INTERVAL_SECONDS = 10


class TaskStore(Protocol):
    async def save(self, task: Task) -> None: ...
    async def get(self, task_id: str) -> Task | None: ...
    async def list_by_agent(self, agent_id: str, status: TaskStatus | None = None) -> list[Task]: ...
    async def list_by_tenant(self, tenant_id: str, status: TaskStatus | None = None) -> list[Task]: ...
    async def delete(self, task_id: str) -> None: ...


class EventBus(Protocol):
    async def publish(self, event: LorkEvent) -> None: ...


class AgentRegistry(Protocol):
    async def assert_runnable(self, agent_id: str) -> Agent: ...


class _QueueItem:
    __slots__ = ("neg_priority", "created_at", "task_id")

    def __init__(self, task: Task) -> None:
        self.neg_priority = -task.priority
        self.created_at = task.created_at
        self.task_id = task.id

    def __lt__(self, other):
        if self.neg_priority != other.neg_priority:
            return self.neg_priority < other.neg_priority
        return self.created_at < other.created_at


class Scheduler:

    def __init__(
        self,
        store: TaskStore,
        event_bus: EventBus,
        agent_registry: AgentRegistry,
    ) -> None:
        self._store = store
        self._bus = event_bus
        self._registry = agent_registry
        self._heap: list[_QueueItem] = []
        self._lock = asyncio.Lock()
        self._sweeper_task: asyncio.Task | None = None


    async def start(self) -> None:
        self._sweeper_task = asyncio.create_task(self._deadline_sweeper())
        logger.info("scheduler.started")


    async def stop(self) -> None:
        if self._sweeper_task:
            self._sweeper_task.cancel()
            try:
                await self._sweeper_task
            except asyncio.CancelledError:
                pass
        logger.info("scheduler.stopped")


    async def submit(
        self,
        tenant_id: str,
        agent_id: str,
        task_type: str,
        payload: dict,
        priority: int = 5,
        deadline_at: str | None = None,
        metadata: dict | None = None,
    ) -> Task:

        await self._registry.assert_runnable(agent_id)

        async with self._lock:

            if len(self._heap) >= MAX_QUEUE_SIZE:
                raise SchedulerOverloadedError("Task queue is full")

            task = Task(
                id=new_id(),
                tenant_id=tenant_id,
                agent_id=agent_id,
                input=TaskInput(type=task_type, payload=payload or {}),
                status=TaskStatus.QUEUED,
                priority=max(1, min(10, priority)),
                deadline_at=deadline_at,
                created_at=utc_now(),
                updated_at=utc_now(),
                metadata=metadata or {},
            )

            await self._store.save(task)

            heapq.heappush(self._heap, _QueueItem(task))

        await self._bus.publish(
            LorkEvent(
                type=EventType.TASK_CREATED,
                tenant_id=tenant_id,
                source="scheduler",
                payload={"task_id": task.id, "agent_id": agent_id},
            )
        )

        return task


    async def claim(self, worker_id: str) -> Task | None:

        async with self._lock:

            while self._heap:

                item = heapq.heappop(self._heap)

                task = await self._store.get(item.task_id)

                if not task:
                    continue

                if task.status != TaskStatus.QUEUED:
                    continue

                assigned = task.model_copy(
                    update={
                        "status": TaskStatus.ASSIGNED,
                        "updated_at": utc_now(),
                        "metadata": {**task.metadata, "worker_id": worker_id},
                    }
                )

                await self._store.save(assigned)

                await self._bus.publish(
                    LorkEvent(
                        type=EventType.TASK_ASSIGNED,
                        tenant_id=assigned.tenant_id,
                        source="scheduler",
                        payload={"task_id": assigned.id, "worker_id": worker_id},
                    )
                )

                return assigned

        return None


    async def mark_running(self, task_id: str) -> Task:
        return await self._update_status(task_id, TaskStatus.RUNNING)


    async def mark_succeeded(self, task_id: str) -> Task:

        task = await self._update_status(task_id, TaskStatus.SUCCEEDED)

        await self._bus.publish(
            LorkEvent(
                type=EventType.TASK_COMPLETED,
                tenant_id=task.tenant_id,
                source="scheduler",
                payload={"task_id": task_id},
            )
        )

        return task


    async def mark_failed(self, task_id: str, error: str) -> Task:

        task = await self._update_status(task_id, TaskStatus.FAILED)

        task = task.model_copy(update={"metadata": {**task.metadata, "error": error}})

        await self._store.save(task)

        await self._bus.publish(
            LorkEvent(
                type=EventType.TASK_FAILED,
                tenant_id=task.tenant_id,
                source="scheduler",
                payload={"task_id": task_id, "error": error},
            )
        )

        return task


    async def cancel(self, task_id: str) -> Task:

        task = await self._update_status(task_id, TaskStatus.CANCELLED)

        await self._bus.publish(
            LorkEvent(
                type=EventType.TASK_CANCELLED,
                tenant_id=task.tenant_id,
                source="scheduler",
                payload={"task_id": task_id},
            )
        )

        return task


    async def get(self, task_id: str) -> Task:

        task = await self._store.get(task_id)

        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        return task


    async def list_for_agent(
        self,
        agent_id: str,
        status: TaskStatus | None = None,
    ) -> list[Task]:

        return await self._store.list_by_agent(agent_id, status)


    async def queue_depth(self) -> int:

        async with self._lock:
            return len(self._heap)


    async def _update_status(self, task_id: str, new_status: TaskStatus) -> Task:

        task = await self._store.get(task_id)

        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        updated = task.model_copy(
            update={
                "status": new_status,
                "updated_at": utc_now(),
            }
        )

        await self._store.save(updated)

        return updated


    async def _deadline_sweeper(self) -> None:

        while True:

            await asyncio.sleep(DEADLINE_CHECK_INTERVAL_SECONDS)

            try:
                await self._sweep_deadlines()
            except Exception:
                logger.exception("deadline_sweeper error — continuing")


    async def _sweep_deadlines(self) -> None:

        now = utc_now()

        async with self._lock:

            surviving = []

            for item in self._heap:

                task = await self._store.get(item.task_id)

                if task and task.deadline_at and task.deadline_at < now:

                    expired = task.model_copy(
                        update={
                            "status": TaskStatus.TIMEOUT,
                            "updated_at": utc_now(),
                        }
                    )

                    await self._store.save(expired)

                    logger.info("task.timeout task=%s", task.id)

                else:
                    surviving.append(item)

            self._heap = surviving

            heapq.heapify(self._heap)
