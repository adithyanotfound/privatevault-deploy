"""
Task Scheduler Service.
Queues tasks, assigns them to agents, handles retries and timeout tracking.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lork.models import Agent, AgentStatus, Task, TaskStatus
from lork.schemas import TaskCreate, TaskResponse
from lork.observability.logging import get_logger

log = get_logger(__name__)


class TaskNotFoundError(Exception):
    pass


class NoAvailableAgentError(Exception):
    pass


class TaskSchedulerService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def submit_task(self, organization_id: str, data: TaskCreate) -> TaskResponse:
        agent_id = data.agent_id

        if agent_id is None:
            agent = await self._select_agent(organization_id, data.task_type)
            agent_id = agent.id if agent else None

        task = Task(
            organization_id=organization_id,
            agent_id=agent_id,
            task_type=data.task_type,
            status=TaskStatus.QUEUED,
            priority=data.priority,
            input_data=data.input_data,
            timeout_seconds=data.timeout_seconds,
            max_retries=data.max_retries,
            scheduled_at=data.scheduled_at,
        )

        self._db.add(task)
        await self._db.flush()

        log.info(
            "task.submitted",
            task_id=task.id,
            task_type=task.task_type,
            agent_id=agent_id,
            priority=task.priority,
        )

        try:
            from lork.runtime.worker import dispatch_task

            dispatch_task.apply_async(
                args=[task.id, organization_id],
                priority=10 - data.priority,
                countdown=self._scheduled_countdown(data.scheduled_at),
            )
        except Exception as exc:
            log.warning("task.dispatch.failed", task_id=task.id, error=str(exc))

        return TaskResponse.model_validate(task)

    async def _select_agent(self, organization_id: str, task_type: str) -> Agent | None:
        result = await self._db.execute(
            select(Agent).where(
                Agent.organization_id == organization_id,
                Agent.status == AgentStatus.ACTIVE,
            )
        )

        agents = list(result.scalars().all())

        capable = [a for a in agents if task_type in (a.capabilities or [])]
        if capable:
            return capable[0]

        return agents[0] if agents else None

    @staticmethod
    def _scheduled_countdown(scheduled_at: datetime | None) -> int | None:
        if scheduled_at is None:
            return None

        now = datetime.now(timezone.utc)
        delta = (scheduled_at - now).total_seconds()

        return max(0, int(delta))
