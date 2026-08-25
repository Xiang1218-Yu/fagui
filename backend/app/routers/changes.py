from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from typing import Optional

from app.database import get_db
from app.models import Change, Regulation, Snapshot, Review, Source, ReviewStatus
from app.schemas import (
    ChangeResponse, ChangeDetailResponse, PaginatedResponse, DiffResult
)
from app.services.differ import DiffEngine
from app.services.storage import SnapshotStorage

router = APIRouter(prefix="/api/changes", tags=["变更对比"])


@router.get("", response_model=PaginatedResponse)
def list_changes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    regulation_id: Optional[str] = None,
    change_type: Optional[str] = None,
    severity: Optional[str] = None,
    is_reviewed: Optional[bool] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Change).join(Regulation, Change.regulation_id == Regulation.id)

    if regulation_id:
        query = query.filter(Change.regulation_id == regulation_id)
    if change_type:
        query = query.filter(Change.change_type == change_type)
    if severity:
        query = query.filter(Change.severity == severity)
    if is_reviewed is not None:
        query = query.filter(Change.is_reviewed == is_reviewed)
    if keyword:
        query = query.filter(
            or_(
                Change.title.ilike(f"%{keyword}%"),
                Change.summary.ilike(f"%{keyword}%"),
                Regulation.title.ilike(f"%{keyword}%"),
            )
        )

    total = query.count()
    changes = (
        query.order_by(desc(Change.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for change in changes:
        item = ChangeResponse.model_validate(change).model_dump()
        item["regulation_title"] = change.regulation.title if change.regulation else None
        item["source_name"] = change.regulation.source.name if change.regulation and change.regulation.source else None
        review = db.query(Review).filter(Review.change_id == change.id).first()
        item["review_status"] = review.status.value if review else None
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{change_id}", response_model=ChangeDetailResponse)
def get_change(change_id: str, db: Session = Depends(get_db)):
    change = db.query(Change).filter(Change.id == change_id).first()
    if not change:
        raise HTTPException(status_code=404, detail="变更记录不存在")

    result = ChangeDetailResponse.model_validate(change).model_dump()
    result["regulation_title"] = change.regulation.title if change.regulation else None
    result["source_name"] = change.regulation.source.name if change.regulation and change.regulation.source else None

    if change.regulation:
        result["regulation"] = change.regulation

    return result


@router.get("/{change_id}/diff")
def get_change_diff(change_id: str, db: Session = Depends(get_db)):
    change = db.query(Change).filter(Change.id == change_id).first()
    if not change:
        raise HTTPException(status_code=404, detail="变更记录不存在")

    storage = SnapshotStorage()

    before_text = ""
    after_text = ""

    if change.previous_snapshot_id:
        prev_snapshot = db.query(Snapshot).filter(Snapshot.id == change.previous_snapshot_id).first()
        if prev_snapshot:
            if prev_snapshot.snapshot_path:
                data = storage.load_snapshot(prev_snapshot.snapshot_path)
                if data:
                    before_text = data.get("content_text", "")
            if not before_text:
                before_text = prev_snapshot.content_text or ""

    if change.current_snapshot_id:
        curr_snapshot = db.query(Snapshot).filter(Snapshot.id == change.current_snapshot_id).first()
        if curr_snapshot:
            if curr_snapshot.snapshot_path:
                data = storage.load_snapshot(curr_snapshot.snapshot_path)
                if data:
                    after_text = data.get("content_text", "")
            if not after_text:
                after_text = curr_snapshot.content_text or ""

    differ = DiffEngine()
    diff_result = differ.compute_text_diff(before_text, after_text)

    return {
        "change_id": change_id,
        "before_text": before_text[:50000],
        "after_text": after_text[:50000],
        "diff_html": diff_result["diff_html"],
        "unified_diff": diff_result["unified_diff"],
        "stats": diff_result["stats"],
        "sections": diff_result["sections"],
        "severity": diff_result["severity"],
    }


@router.post("/{change_id}/mark-reviewed")
def mark_change_reviewed(change_id: str, db: Session = Depends(get_db)):
    change = db.query(Change).filter(Change.id == change_id).first()
    if not change:
        raise HTTPException(status_code=404, detail="变更记录不存在")
    change.is_reviewed = True
    db.commit()
    return {"id": change_id, "is_reviewed": True}
