from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CrawlRun, Source, User
from app.schemas import RunQueued, SourceCreate, SourceOut, SourceUpdate
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/sources", tags=["sources"], dependencies=[Depends(get_current_user)])


def _to_out(source: Source, last_run_at) -> SourceOut:
    return SourceOut(
        id=source.id,
        name=source.name,
        base_url=source.base_url,
        allowed_paths=source.allowed_paths or [],
        frequency_minutes=source.frequency_minutes,
        enabled=source.enabled,
        respect_robots=source.respect_robots,
        max_pages=source.max_pages,
        last_run_at=last_run_at,
        created_at=source.created_at,
    )


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    sources = db.scalars(select(Source).order_by(Source.id)).all()
    last_map = dict(
        db.execute(select(CrawlRun.source_id, func.max(CrawlRun.started_at)).group_by(CrawlRun.source_id)).all()
    )
    return [_to_out(s, last_map.get(s.id)) for s in sources]


@router.post("", response_model=SourceOut)
def create_source(payload: SourceCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if db.scalar(select(Source).where(Source.base_url == payload.base_url)):
        raise HTTPException(status_code=400, detail="base_url 已存在")
    source = Source(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return _to_out(source, None)


@router.patch("/{source_id}", response_model=SourceOut)
def update_source(
    source_id: int, payload: SourceUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))
):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="来源不存在")
    data = payload.model_dump(exclude_unset=True)
    new_base_url = data.get("base_url")
    if new_base_url and new_base_url != source.base_url:
        if db.scalar(select(Source).where(Source.base_url == new_base_url)):
            raise HTTPException(status_code=400, detail="base_url 已存在")
    for key, value in data.items():
        setattr(source, key, value)
    db.commit()
    db.refresh(source)
    last_run_at = db.scalar(select(func.max(CrawlRun.started_at)).where(CrawlRun.source_id == source.id))
    return _to_out(source, last_run_at)


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="来源不存在")
    db.delete(source)
    db.commit()
    return None


@router.post("/{source_id}/run", response_model=RunQueued)
def run_source(source_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "analyst"))):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="来源不存在")
    try:
        from app.workers.tasks import crawl_source as crawl_task

        crawl_task.delay(source_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"任务入队失败：{exc}")
    return RunQueued(run_id=None, status="queued")
