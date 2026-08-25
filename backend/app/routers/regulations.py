from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import Optional

from app.database import get_db
from app.models import Regulation, Source, Snapshot, Attachment, Change
from app.schemas import (
    RegulationResponse, SnapshotResponse, AttachmentResponse, PaginatedResponse
)

router = APIRouter(prefix="/api/regulations", tags=["法规管理"])


@router.get("", response_model=PaginatedResponse)
def list_regulations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_id: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    is_primary: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Regulation)

    if source_id:
        query = query.filter(Regulation.source_id == source_id)
    if status:
        query = query.filter(Regulation.status == status)
    if is_primary is not None:
        query = query.filter(Regulation.is_primary == is_primary)
    if keyword:
        query = query.filter(
            or_(
                Regulation.title.ilike(f"%{keyword}%"),
                Regulation.regulation_number.ilike(f"%{keyword}%"),
                Regulation.issuing_authority.ilike(f"%{keyword}%"),
            )
        )

    total = query.count()
    regulations = (
        query.order_by(desc(Regulation.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for reg in regulations:
        item = RegulationResponse.model_validate(reg).model_dump()
        item["source_name"] = reg.source.name if reg.source else None
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{regulation_id}", response_model=RegulationResponse)
def get_regulation(regulation_id: str, db: Session = Depends(get_db)):
    reg = db.query(Regulation).filter(Regulation.id == regulation_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="法规不存在")
    result = RegulationResponse.model_validate(reg).model_dump()
    result["source_name"] = reg.source.name if reg.source else None
    return result


@router.get("/{regulation_id}/snapshots", response_model=PaginatedResponse)
def list_snapshots(
    regulation_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    reg = db.query(Regulation).filter(Regulation.id == regulation_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="法规不存在")

    query = db.query(Snapshot).filter(Snapshot.regulation_id == regulation_id)
    total = query.count()
    snapshots = (
        query.order_by(desc(Snapshot.captured_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        items=[SnapshotResponse.model_validate(s) for s in snapshots],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{regulation_id}/attachments", response_model=PaginatedResponse)
def list_attachments(
    regulation_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    reg = db.query(Regulation).filter(Regulation.id == regulation_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="法规不存在")

    query = db.query(Attachment).filter(Attachment.regulation_id == regulation_id)
    total = query.count()
    attachments = (
        query.order_by(desc(Attachment.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        items=[AttachmentResponse.model_validate(a) for a in attachments],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{regulation_id}/changes", response_model=PaginatedResponse)
def list_regulation_changes(
    regulation_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    reg = db.query(Regulation).filter(Regulation.id == regulation_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="法规不存在")

    query = db.query(Change).filter(Change.regulation_id == regulation_id)
    total = query.count()
    changes = (
        query.order_by(desc(Change.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    from app.schemas import ChangeResponse
    items = [ChangeResponse.model_validate(c).model_dump() for c in changes]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("/{regulation_id}/merge")
def merge_regulations(
    regulation_id: str,
    duplicate_id: str = Query(...),
    confidence: float = Query(..., ge=0, le=1),
    db: Session = Depends(get_db),
):
    from app.services.merger import RegulationMerger
    merger = RegulationMerger(db)
    reasons = ["手动确认归并"]
    result = merger.merge_regulations(
        primary_id=regulation_id,
        duplicate_id=duplicate_id,
        confidence=confidence,
        reasons=reasons,
        merged_by="manual",
    )
    if not result:
        raise HTTPException(status_code=400, detail="归并失败，请检查法规 ID")
    return {"id": result.id, "merge_group_id": result.merge_group_id}
