"""Celery tasks for crawling."""
from __future__ import annotations

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.models import CrawlRun, RunStatus, Source
from app.services import crawl_service


@celery_app.task(name="app.tasks.crawl_tasks.run_source_crawl")
def run_source_crawl(source_id: int, trigger: str = "scheduled") -> dict:
    db = SessionLocal()
    try:
        source = db.get(Source, source_id)
        if source is None:
            return {"error": "source not found"}
        run = CrawlRun(source_id=source.id, status=RunStatus.pending, trigger=trigger)
        db.add(run)
        db.commit()
        db.refresh(run)
        crawl_service.run_crawl(db, source, run)
        return {
            "run_id": run.id,
            "status": run.status.value,
            "changes": run.changes_detected,
            "message": run.message,
        }
    finally:
        db.close()


@celery_app.task(name="app.tasks.crawl_tasks.dispatch_due_sources")
def dispatch_due_sources() -> dict:
    """Celery-beat entrypoint: enqueue crawls for sources whose frequency is due."""
    db = SessionLocal()
    try:
        due = crawl_service.due_sources(db)
        for source in due:
            run_source_crawl.delay(source.id, "scheduled")
        return {"dispatched": [s.id for s in due]}
    finally:
        db.close()
