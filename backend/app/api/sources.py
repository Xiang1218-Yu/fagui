from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.config import settings
from app.database import get_db
from app.models import CrawlRun, Source, User
from app.schemas import CrawlRunOut, SourceCreate, SourceOut, SourceUpdate

router = APIRouter(prefix="/api/sources", tags=["来源管理"])

FREQUENCY_MINUTES = {
    "hourly": 60,
    "every_6h": 360,
    "daily": 1440,
    "weekly": 10080,
}


def _trigger_crawl(db: Session, source: Source, trigger: str) -> CrawlRun:
    run = CrawlRun(source_id=source.id, trigger_type=trigger, status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)
    if settings.crawl_eager:
        from app.services.crawl import run_crawl

        run_crawl(db, run.id)
        db.refresh(run)
    else:
        from app.tasks.crawl_tasks import crawl_source_task

        crawl_source_task.delay(run.id)
    return run


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Source).order_by(Source.id)))


@router.post("", response_model=SourceOut)
def create_source(payload: SourceCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    source = Source(
        name=payload.name,
        org_type=payload.org_type,
        base_url=payload.base_url.rstrip("/"),
        homepage_url=payload.homepage_url,
        frequency=payload.frequency,
        interval_minutes=payload.interval_minutes or FREQUENCY_MINUTES.get(payload.frequency, 1440),
        enabled=payload.enabled,
        respect_robots=payload.respect_robots,
        allowed_paths=payload.allowed_paths or [],
        max_depth=payload.max_depth,
        description=payload.description,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="来源不存在")
    return source


@router.patch("/{source_id}", response_model=SourceOut)
def update_source(
    source_id: int,
    payload: SourceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="来源不存在")
    data = payload.model_dump(exclude_unset=True)
    if "frequency" in data and data["frequency"] in FREQUENCY_MINUTES and "interval_minutes" not in data:
        source.interval_minutes = FREQUENCY_MINUTES[data["frequency"]]
    for key, value in data.items():
        setattr(source, key, value)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="来源不存在")
    db.delete(source)
    db.commit()
    return {"ok": True}


@router.post("/{source_id}/crawl", response_model=CrawlRunOut)
def trigger_crawl(
    source_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="来源不存在")
    if not source.enabled:
        raise HTTPException(status_code=400, detail="来源已停用，请先启用")
    run = _trigger_crawl(db, source, trigger="manual")
    return run


@router.get("/{source_id}/runs", response_model=list[CrawlRunOut])
def list_source_runs(source_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(
        db.scalars(
            select(CrawlRun).where(CrawlRun.source_id == source_id).order_by(CrawlRun.id.desc()).limit(50)
        )
    )
