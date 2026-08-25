from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CrawlRun, Source
from app.schemas import RunOut
from app.security import get_current_user

router = APIRouter(prefix="/runs", tags=["runs"], dependencies=[Depends(get_current_user)])


def _to_out(run: CrawlRun, source_name: str) -> RunOut:
    return RunOut(
        id=run.id,
        source_id=run.source_id,
        source_name=source_name,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        pages_fetched=run.pages_fetched,
        attachments_fetched=run.attachments_fetched,
        changes_detected=run.changes_detected,
        error=run.error,
    )


@router.get("", response_model=list[RunOut])
def list_runs(source_id: Optional[int] = None, limit: int = 50, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    stmt = (
        select(CrawlRun, Source.name)
        .join(Source, CrawlRun.source_id == Source.id)
        .order_by(CrawlRun.id.desc())
        .limit(limit)
    )
    if source_id is not None:
        stmt = stmt.where(CrawlRun.source_id == source_id)
    return [_to_out(run, name) for run, name in db.execute(stmt).all()]


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        select(CrawlRun, Source.name).join(Source, CrawlRun.source_id == Source.id).where(CrawlRun.id == run_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="采集记录不存在")
    run, name = row
    return _to_out(run, name)
