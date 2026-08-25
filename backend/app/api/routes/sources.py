from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.models import CrawlRun, RunStatus, Source, User
from app.schemas.schemas import CrawlRunOut, SourceCreate, SourceOut, SourceUpdate
from app.services import crawl_service

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.execute(select(Source).order_by(Source.id)).scalars().all()


@router.post("", response_model=SourceOut, status_code=201)
def create_source(payload: SourceCreate, db: Session = Depends(get_db),
                  _: User = Depends(require_admin)):
    source = Source(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: int, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "source not found")
    return source


@router.put("/{source_id}", response_model=SourceOut)
def update_source(source_id: int, payload: SourceUpdate, db: Session = Depends(get_db),
                  _: User = Depends(require_admin)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: Session = Depends(get_db),
                  _: User = Depends(require_admin)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "source not found")
    db.delete(source)
    db.commit()


@router.post("/{source_id}/crawl", response_model=CrawlRunOut)
def trigger_crawl(source_id: int, db: Session = Depends(get_db),
                  _: User = Depends(require_admin)):
    """Trigger an on-demand crawl. Executes synchronously so the analyst sees
    results immediately; scheduled crawls run via Celery beat in the background."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "source not found")

    run = CrawlRun(source_id=source.id, status=RunStatus.pending, trigger="manual")
    db.add(run)
    db.commit()
    db.refresh(run)

    crawl_service.run_crawl(db, source, run)
    db.refresh(run)
    return run
