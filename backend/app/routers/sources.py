from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models import Source, CrawlRun, SourceStatus, CrawlStatus
from app.schemas import (
    SourceCreate, SourceUpdate, SourceResponse,
    CrawlRunResponse, CrawlTriggerRequest, PaginatedResponse
)
from app.tasks.crawler import crawl_source

router = APIRouter(prefix="/api/sources", tags=["来源管理"])


@router.get("", response_model=PaginatedResponse)
def list_sources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Source)
    if status:
        query = query.filter(Source.status == status)
    if source_type:
        query = query.filter(Source.source_type == source_type)
    if keyword:
        query = query.filter(Source.name.ilike(f"%{keyword}%"))

    total = query.count()
    sources = query.order_by(desc(Source.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[SourceResponse.model_validate(s) for s in sources],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=SourceResponse, status_code=201)
def create_source(source_data: SourceCreate, db: Session = Depends(get_db)):
    existing = db.query(Source).filter(Source.url == source_data.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="该来源 URL 已存在")

    source = Source(**source_data.model_dump(exclude_unset=True))
    source.status = SourceStatus.ACTIVE
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/{source_id}", response_model=SourceResponse)
def get_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    return source


@router.put("/{source_id}", response_model=SourceResponse)
def update_source(source_id: str, source_data: SourceUpdate, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")

    update_data = source_data.model_dump(exclude_unset=True)
    if "status" in update_data:
        update_data["status"] = SourceStatus(update_data["status"])
    if "source_type" in update_data:
        from app.models import SourceType
        update_data["source_type"] = SourceType(update_data["source_type"])

    for key, value in update_data.items():
        setattr(source, key, value)

    source.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    db.delete(source)
    db.commit()


@router.post("/{source_id}/pause", response_model=SourceResponse)
def pause_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    source.status = SourceStatus.PAUSED
    db.commit()
    db.refresh(source)
    return source


@router.post("/{source_id}/resume", response_model=SourceResponse)
def resume_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    source.status = SourceStatus.ACTIVE
    db.commit()
    db.refresh(source)
    return source


@router.post("/{source_id}/crawl", response_model=CrawlRunResponse)
def trigger_crawl(source_id: str, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")

    task = crawl_source.delay(source_id, triggered_by="manual")

    crawl_run = CrawlRun(
        source_id=source_id,
        status=CrawlStatus.PENDING,
        triggered_by="manual",
        celery_task_id=task.id,
    )
    db.add(crawl_run)
    db.commit()
    db.refresh(crawl_run)
    return crawl_run


@router.get("/{source_id}/crawl-runs", response_model=PaginatedResponse)
def list_crawl_runs(
    source_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(CrawlRun).filter(CrawlRun.source_id == source_id)
    total = query.count()
    runs = query.order_by(desc(CrawlRun.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[CrawlRunResponse.model_validate(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("/crawl/trigger", response_model=dict)
def trigger_crawl_general(request: CrawlTriggerRequest, db: Session = Depends(get_db)):
    if request.source_id:
        source = db.query(Source).filter(Source.id == request.source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="来源不存在")
        task = crawl_source.delay(request.source_id, triggered_by=request.triggered_by)
        return {"task_id": task.id, "source_id": request.source_id}
    else:
        sources = db.query(Source).filter(Source.status == SourceStatus.ACTIVE).all()
        task_ids = []
        for source in sources:
            task = crawl_source.delay(source.id, triggered_by=request.triggered_by)
            task_ids.append({"source_id": source.id, "task_id": task.id})
        return {"triggered": len(task_ids), "tasks": task_ids}
