from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import CrawlRun, User
from app.schemas import CrawlRunDetail, CrawlRunOut

router = APIRouter(prefix="/api/crawl-runs", tags=["采集运行"])


@router.get("", response_model=list[CrawlRunOut])
def list_runs(
    source_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(CrawlRun).order_by(CrawlRun.id.desc()).limit(200)
    if source_id is not None:
        stmt = stmt.where(CrawlRun.source_id == source_id)
    if status_filter:
        stmt = stmt.where(CrawlRun.status == status_filter)
    return list(db.scalars(stmt))


@router.get("/{run_id}", response_model=CrawlRunDetail)
def get_run(run_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    run = db.get(CrawlRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="采集运行不存在")
    return run
