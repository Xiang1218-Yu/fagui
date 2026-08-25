import logging
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Source, CrawlRun, SourceStatus, CrawlStatus
from app.tasks.crawler import crawl_source

logger = logging.getLogger(__name__)


@shared_task(name="app.tasks.scheduler.check_scheduled_crawls")
def check_scheduled_crawls() -> dict:
    db = SessionLocal()
    triggered = []
    try:
        now = datetime.utcnow()
        sources = (
            db.query(Source)
            .filter(Source.status == SourceStatus.ACTIVE)
            .all()
        )

        for source in sources:
            frequency = timedelta(minutes=source.crawl_frequency_minutes)
            should_crawl = False

            if not source.last_crawled_at:
                should_crawl = True
            elif now - source.last_crawled_at >= frequency:
                recent_running = (
                    db.query(CrawlRun)
                    .filter(
                        CrawlRun.source_id == source.id,
                        CrawlRun.status.in_([CrawlStatus.PENDING, CrawlStatus.RUNNING]),
                        CrawlRun.created_at >= now - timedelta(hours=1),
                    )
                    .first()
                )
                if not recent_running:
                    should_crawl = True

            if should_crawl:
                task = crawl_source.delay(source.id, triggered_by="scheduled")
                triggered.append({"source_id": source.id, "task_id": task.id})
                logger.info(f"Triggered scheduled crawl for source {source.name}")

        return {"triggered": len(triggered), "sources": triggered}
    except Exception as e:
        logger.error(f"Scheduler check failed: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()
