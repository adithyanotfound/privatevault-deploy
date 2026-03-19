"""
LORK Runtime Worker.

Executes agent tasks via Celery. Each task runs an LLM-backed agent loop
with tool use, policy enforcement, and step-by-step audit logging.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from celery import Task as CeleryTask
from tenacity import retry, stop_after_attempt, wait_exponential

from lork.runtime.celery_app import celery_app
from lork.config import get_settings
from lork.models import TaskStep
from lork.observability.logging import get_logger
from lork.runtime.executors.llm_executor import LLMExecutor
from lork.runtime.executors.tool_registry import ToolRegistry

log = get_logger(__name__)


class BaseTask(CeleryTask):
    """Base class with error handling and retry logic."""

    abstract = True

    def on_failure(self, exc: Exception, task_id: str, args: list, kwargs: dict, einfo: Any) -> None:
        log.error(
            "celery.task.failure",
            celery_task_id=task_id,
            error=str(exc),
            exc_type=type(exc).__name__,
        )

    def on_retry(self, exc: Exception, task_id: str, args: list, kwargs: dict, einfo: Any) -> None:
        log.warning("celery.task.retry", celery_task_id=task_id, error=str(exc))


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="lork.runtime.worker.dispatch_task",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def dispatch_task(self: CeleryTask, task_id: str, organization_id: str) -> dict[str, Any]:
    """Main task dispatch — runs the agent execution loop."""
    return asyncio.get_event_loop().run_until_complete(
        _execute_task(self, task_id, organization_id)
    )


async def _execute_task(
    celery_task: CeleryTask,
    task_id: str,
    organization_id: str,
) -> dict[str, Any]:

    from lork.storage.db import db_session
    from sqlalchemy import select
    from lork.models import Agent, Task

    log.info("task.execution.start", task_id=task_id, org=organization_id)
    start_time = time.perf_counter()

    async with db_session() as db:

        task_result = await db.execute(select(Task).where(Task.id == task_id))
        task = task_result.scalar_one_or_none()

        if task is None:
            log.error("task.execution.not_found", task_id=task_id)
            return {"error": "Task not found"}

        agent = None
        if task.agent_id:
            agent_result = await db.execute(select(Agent).where(Agent.id == task.agent_id))
            agent = agent_result.scalar_one_or_none()

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        task.celery_task_id = celery_task.request.id
        await db.flush()

        try:

            settings = get_settings()

            tool_registry = ToolRegistry()

            executor = LLMExecutor(
                provider=agent.llm_provider if agent else settings.DEFAULT_LLM_PROVIDER,
                model=agent.llm_model if agent else settings.DEFAULT_LLM_MODEL,
                system_prompt=agent.system_prompt if agent else "",
                max_steps=settings.AGENT_MAX_EXECUTION_STEPS,
                tool_registry=tool_registry,
            )

            result = await executor.run(
                task_type=task.task_type,
                input_data=task.input_data,
                agent_id=str(task.agent_id) if task.agent_id else None,
                organization_id=organization_id,
                db=db,
                task_id=task_id,
            )

            task.status = "completed"
            task.output_data = result
            task.completed_at = datetime.now(timezone.utc)
            await db.flush()

            duration = time.perf_counter() - start_time

            log.info(
                "task.execution.completed",
                task_id=task_id,
                duration_s=round(duration, 3),
            )

            return result

        except Exception as exc:

            duration = time.perf_counter() - start_time

            log.error(
                "task.execution.error",
                task_id=task_id,
                error=str(exc),
                duration_s=round(duration, 3),
                exc_info=True,
            )

            should_retry = task.retry_count < task.max_retries

            if should_retry:
                task.retry_count += 1
                task.status = "queued"
            else:
                task.status = "failed"
                task.completed_at = datetime.now(timezone.utc)

            task.error = str(exc)

            await db.flush()

            if should_retry:
                raise celery_task.retry(exc=exc, countdown=30 * task.retry_count)

            return {"error": str(exc)}


@celery_app.task(name="lork.runtime.worker.cleanup_stale_tasks")
def cleanup_stale_tasks() -> None:
    asyncio.get_event_loop().run_until_complete(_cleanup_stale())


async def _cleanup_stale() -> None:

    from datetime import timedelta
    from sqlalchemy import update
    from lork.storage.db import db_session
    from lork.models import Task, TaskStatus

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=300)

    async with db_session() as db:

        stmt = (
            update(Task)
            .where(
                Task.status == TaskStatus.RUNNING,
                Task.started_at < cutoff,
            )
            .values(status=TaskStatus.TIMED_OUT, completed_at=datetime.now(timezone.utc))
        )

        result = await db.execute(stmt)

        if result.rowcount:
            log.warning("task.cleanup.timed_out", count=result.rowcount)


@celery_app.task(name="lork.runtime.worker.check_agent_heartbeats")
def check_agent_heartbeats() -> None:
    asyncio.get_event_loop().run_until_complete(_check_heartbeats())


async def _check_heartbeats() -> None:

    from datetime import timedelta
    from sqlalchemy import update
    from lork.storage.db import db_session
    from lork.models import Agent, AgentStatus

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)

    async with db_session() as db:

        stmt = (
            update(Agent)
            .where(
                Agent.status == AgentStatus.ACTIVE,
                Agent.last_heartbeat_at < cutoff,
            )
            .values(status=AgentStatus.ERROR)
        )

        result = await db.execute(stmt)

        if result.rowcount:
            log.warning("agent.heartbeat.missed", count=result.rowcount)


def start() -> None:

    celery_app.worker_main(
        argv=[
            "worker",
            "--loglevel=info",
            "--queues=agent_tasks,maintenance",
            "--concurrency=4",
            "--max-tasks-per-child=100",
        ]
    )
