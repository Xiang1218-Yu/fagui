from celery import Celery
from app.config import settings

celery_app = Celery(
    "regulatory_intel",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.crawler",
        "app.tasks.processor",
        "app.tasks.notifier",
        "app.tasks.scheduler",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,
    beat_schedule={
        "scheduled-crawl-check": {
            "task": "app.tasks.scheduler.check_scheduled_crawls",
            "schedule": 300.0,
        },
        "process-pending-notifications": {
            "task": "app.tasks.notifier.process_pending_notifications",
            "schedule": 60.0,
        },
    },
)
