from celery import Celery

from app.config import settings

celery_app = Celery(
    "fagui",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=["app.tasks.crawl_tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-due-sources": {
            "task": "fagui.crawl_due_sources",
            "schedule": 60.0,
        },
    },
)
