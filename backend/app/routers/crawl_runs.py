from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import CrawlRun, Source, Change, Review, Regulation
from app.schemas import CrawlRunResponse, PaginatedResponse

router = APIRouter(prefix="/api/crawl-runs", tags=["采集运行"])


@router.get("", response_model=PaginatedResponse)
def list_crawl_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(CrawlRun)
    if source_id:
        query = query.filter(CrawlRun.source_id == source_id)
    if status:
        query = query.filter(CrawlRun.status == status)

    total = query.count()
    runs = (
        query.order_by(desc(CrawlRun.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for run in runs:
        item = CrawlRunResponse.model_validate(run)
        if run.source:
            item_dict = item.model_dump()
            item_dict["source_name"] = run.source.name
            items.append(item_dict)
        else:
            items.append(item.model_dump())

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{run_id}", response_model=CrawlRunResponse)
def get_crawl_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(CrawlRun).filter(CrawlRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="采集运行记录不存在")
    return run


@router.get("/{run_id}/logs")
def get_crawl_run_logs(run_id: str, db: Session = Depends(get_db)):
    run = db.query(CrawlRun).filter(CrawlRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="采集运行记录不存在")
    return {
        "id": run.id,
        "status": run.status.value,
        "logs": run.logs or [],
        "pages_crawled": run.pages_crawled,
        "pages_failed": run.pages_failed,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
