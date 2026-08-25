from celery import Celery

from app.config import settings

celery_app = Celery(
    "regintel",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    timezone="UTC",
    beat_schedule={
        "dispatch-due-sources": {
            "task": "app.workers.tasks.dispatch_due_sources",
            "schedule": 60.0,
        }
    },
)
