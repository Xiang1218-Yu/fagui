from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import CrawlRun, Snapshot, User
from app.schemas.schemas import CrawlRunOut, SnapshotOut

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[CrawlRunOut])
def list_runs(source_id: int | None = None, limit: int = 100, db: Session = Depends(get_db),
              _: User = Depends(get_current_user)):
    stmt = select(CrawlRun).order_by(CrawlRun.id.desc()).limit(limit)
    if source_id is not None:
        stmt = select(CrawlRun).where(CrawlRun.source_id == source_id).order_by(
            CrawlRun.id.desc()
        ).limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/{run_id}/snapshots", response_model=list[SnapshotOut])
def run_snapshots(run_id: int, db: Session = Depends(get_db),
                  _: User = Depends(get_current_user)):
    return db.execute(
        select(Snapshot).where(Snapshot.run_id == run_id).order_by(Snapshot.id)
    ).scalars().all()
