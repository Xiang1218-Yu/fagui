from datetime import timedelta

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import CrawlRun, Source, utcnow
from app.services.crawler import crawl_source as do_crawl
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.dispatch_due_sources")
def dispatch_due_sources():
    """扫描到期的启用来源并逐个派发采集任务。"""
    due_ids = []
    with SessionLocal() as session:
        sources = session.scalars(select(Source).where(Source.enabled.is_(True))).all()
        for source in sources:
            last_started = session.scalar(
                select(func.max(CrawlRun.started_at)).where(CrawlRun.source_id == source.id)
            )
            if last_started is None or utcnow() - last_started >= timedelta(minutes=source.frequency_minutes):
                due_ids.append(source.id)
    for source_id in due_ids:
        crawl_source.delay(source_id)
    return due_ids


@celery_app.task(name="app.workers.tasks.crawl_source")
def crawl_source(source_id: int):
    with SessionLocal() as session:
        do_crawl(source_id, session)
