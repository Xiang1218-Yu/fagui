from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "fagui",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.crawl_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    beat_schedule={
        "dispatch-due-sources": {
            "task": "app.tasks.crawl_tasks.dispatch_due_sources",
            "schedule": 60.0,  # check every minute for sources whose frequency is due
        }
    },
)
