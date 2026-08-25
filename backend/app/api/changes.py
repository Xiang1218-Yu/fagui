from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Change, Document, Regulation, ReviewTask, Snapshot, Source, User
from app.schemas import ChangeOut
from app.services.differ import line_diff
from app.services.storage import read_text

router = APIRouter(prefix="/api/changes", tags=["变更对比"])


@router.get("", response_model=list[ChangeOut])
def list_changes(
    status_filter: str | None = None,
    change_type: str | None = None,
    source_id: int | None = None,
    regulation_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Change).order_by(Change.detected_at.desc(), Change.id.desc()).limit(300)
    if status_filter:
        stmt = stmt.where(Change.status == status_filter)
    if change_type:
        stmt = stmt.where(Change.change_type == change_type)
    if source_id is not None:
        stmt = stmt.where(Change.source_id == source_id)
    if regulation_id is not None:
        stmt = stmt.where(Change.regulation_id == regulation_id)
    return list(db.scalars(stmt))


@router.get("/{change_id}")
def get_change(change_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    change = db.get(Change, change_id)
    if change is None:
        raise HTTPException(status_code=404, detail="变更不存在")

    old_snap = db.get(Snapshot, change.from_snapshot_id) if change.from_snapshot_id else None
    new_snap = db.get(Snapshot, change.to_snapshot_id)
    document = db.get(Document, change.document_id)
    regulation = db.get(Regulation, change.regulation_id) if change.regulation_id else None
    source = db.get(Source, change.source_id)
    review = db.scalar(select(ReviewTask).where(ReviewTask.change_id == change.id))

    old_text = read_text(old_snap.text_path) if old_snap else ""
    new_text = read_text(new_snap.text_path) if new_snap else ""

    diff_rows = line_diff(old_text, new_text) if old_text or new_text else []

    return {
        "change": ChangeOut.model_validate(change),
        "document": {
            "id": document.id,
            "url": document.url,
            "title": document.title,
            "doc_type": document.doc_type,
            "attachment_name": document.attachment_name,
        },
        "regulation": {"id": regulation.id, "title": regulation.title, "reg_number": regulation.reg_number}
        if regulation
        else None,
        "source": {"id": source.id, "name": source.name, "org_type": source.org_type} if source else None,
        "review": {
            "id": review.id,
            "status": review.status,
            "decision": review.decision,
            "comment": review.comment,
            "assignee_id": review.assignee_id,
        }
        if review
        else None,
        "old_snapshot": {
            "id": old_snap.id,
            "fetched_at": old_snap.fetched_at,
            "title": old_snap.title,
            "content_hash": old_snap.content_hash,
            "text_hash": old_snap.text_hash,
            "size_bytes": old_snap.size_bytes,
            "crawl_run_id": old_snap.crawl_run_id,
        }
        if old_snap
        else None,
        "new_snapshot": {
            "id": new_snap.id,
            "fetched_at": new_snap.fetched_at,
            "title": new_snap.title,
            "content_hash": new_snap.content_hash,
            "text_hash": new_snap.text_hash,
            "size_bytes": new_snap.size_bytes,
            "crawl_run_id": new_snap.crawl_run_id,
        }
        if new_snap
        else None,
        "old_text": old_text,
        "new_text": new_text,
        "diff_rows": diff_rows,
    }


@router.patch("/{change_id}/severity", response_model=ChangeOut)
def set_severity(
    change_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    change = db.get(Change, change_id)
    if change is None:
        raise HTTPException(status_code=404, detail="变更不存在")
    severity = payload.get("severity")
    if severity not in ("high", "medium", "low"):
        raise HTTPException(status_code=400, detail="严重级别无效")
    change.severity = severity
    db.commit()
    db.refresh(change)
    return change
