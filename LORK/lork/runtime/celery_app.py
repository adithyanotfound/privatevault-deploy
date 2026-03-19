"""
Celery application — task queue for async agent execution.
"""
from __future__ import annotations

from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from lork.config import get_settings
from lork.observability.logging import configure_logging, get_logger

log = get_logger(__name__)


def create_celery_app() -> Celery:
    settings = get_settings()

    app = Celery(
        "lork",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["lork.runtime.worker"],
    )

    app.conf.update(
        task_serializer=settings.CELERY_TASK_SERIALIZER,
        result_serializer="json",
        accept_content=["json"],
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_routes={
            "lork.runtime.worker.dispatch_task": {"queue": "agent_tasks"},
            "lork.runtime.worker.cleanup_stale_tasks": {"queue": "maintenance"},
        },
        beat_schedule={
            "cleanup-stale-tasks": {
                "task": "lork.runtime.worker.cleanup_stale_tasks",
                "schedule": 60.0,
            },
            "agent-heartbeat-check": {
                "task": "lork.runtime.worker.check_agent_heartbeats",
                "schedule": 30.0,
            },
        },
        timezone="UTC",
        enable_utc=True,
        task_soft_time_limit=280,
        task_time_limit=300,
        worker_max_tasks_per_child=100,
        broker_connection_retry_on_startup=True,
    )

    return app


celery_app = create_celery_app()


@worker_ready.connect
def on_worker_ready(**kwargs: object) -> None:
    configure_logging()
    log.info("celery.worker.ready")


@worker_shutdown.connect
def on_worker_shutdown(**kwargs: object) -> None:
    log.info("celery.worker.shutdown")
