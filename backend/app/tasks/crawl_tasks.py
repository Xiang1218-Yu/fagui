from datetime import datetime, timedelta, timezone

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import CrawlRun, Source
from app.services.crawl import run_crawl


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@celery_app.task(name="fagui.crawl_source")
def crawl_source_task(run_id: int) -> dict:
    db = SessionLocal()
    try:
        run = run_crawl(db, run_id)
        return {"run_id": run.id, "status": run.status, "changes": run.changes_detected}
    finally:
        db.close()


@celery_app.task(name="fagui.crawl_due_sources")
def crawl_due_sources() -> dict:
    db = SessionLocal()
    enqueued: list[int] = []
    try:
        now = datetime.now(timezone.utc)
        sources = db.query(Source).filter(Source.enabled.is_(True), Source.status == "active").all()
        for source in sources:
            last = _as_aware(source.last_crawled_at)
            due = last is None or now - last >= timedelta(minutes=max(source.interval_minutes, 1))
            if not due:
                continue
            run = CrawlRun(source_id=source.id, trigger_type="scheduled", status="pending")
            db.add(run)
            db.commit()
            crawl_source_task.delay(run.id)
            enqueued.append(run.id)
        return {"enqueued": enqueued}
    finally:
        db.close()
