from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Attachment, Change, Document, Regulation, Review, Snapshot, Source, utcnow
from app.schemas import AttachmentOut, ChangeDetail, ChangeListItem, ReviewCreate, ReviewOut
from app.services import diffutil

router = APIRouter(prefix="/changes", tags=["changes"])


def _to_item(change: Change, regulation: Regulation, document: Document, source: Source) -> ChangeListItem:
    return ChangeListItem(
        id=change.id,
        regulation_id=change.regulation_id,
        regulation_title=regulation.canonical_title,
        document_url=document.url,
        source_name=source.name,
        change_type=change.change_type,
        status=change.status,
        diff_summary=change.diff_summary,
        detected_at=change.detected_at,
    )


def _base_stmt():
    return (
        select(Change, Regulation, Document, Source)
        .join(Regulation, Change.regulation_id == Regulation.id)
        .join(Document, Change.document_id == Document.id)
        .join(Source, Document.source_id == Source.id)
    )


def _read_snapshot_text(db: Session, snapshot_id: Optional[int]) -> Optional[str]:
    """从快照 text_path 读取文本，快照或文件缺失返回 None。"""
    if snapshot_id is None:
        return None
    snapshot = db.get(Snapshot, snapshot_id)
    if snapshot is None or not snapshot.text_path:
        return None
    try:
        return Path(snapshot.text_path).read_text(encoding="utf-8")
    except OSError:
        return None


@router.get("", response_model=list[ChangeListItem])
def list_changes(
    status: Optional[str] = None,
    regulation_id: Optional[int] = None,
    source_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    stmt = _base_stmt().order_by(Change.detected_at.desc(), Change.id.desc())
    if status:
        stmt = stmt.where(Change.status == status)
    if regulation_id is not None:
        stmt = stmt.where(Change.regulation_id == regulation_id)
    if source_id is not None:
        stmt = stmt.where(Document.source_id == source_id)
    return [_to_item(*row) for row in db.execute(stmt).all()]


@router.get("/{change_id}", response_model=ChangeDetail)
def get_change(change_id: int, db: Session = Depends(get_db)):
    row = db.execute(_base_stmt().where(Change.id == change_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="变更不存在")
    change, regulation, document, source = row
    old_text = _read_snapshot_text(db, change.old_snapshot_id)
    new_text = _read_snapshot_text(db, change.new_snapshot_id)
    unified = diffutil.unified_diff_text(old_text, new_text, max_lines=400)
    attachments = db.scalars(
        select(Attachment).where(Attachment.document_id == change.document_id).order_by(Attachment.id)
    ).all()
    review = db.scalar(
        select(Review).where(Review.change_id == change.id).order_by(Review.id.desc()).limit(1)
    )
    item = _to_item(change, regulation, document, source)
    return ChangeDetail(
        **item.model_dump(),
        old_text=old_text,
        new_text=new_text,
        unified_diff=unified,
        attachments=[
            AttachmentOut(id=a.id, url=a.url, filename=a.filename, content_hash=a.content_hash)
            for a in attachments
        ],
        review=ReviewOut(
            reviewer=review.reviewer, decision=review.decision, comment=review.comment, decided_at=review.decided_at
        )
        if review
        else None,
    )


@router.post("/{change_id}/review", response_model=ChangeListItem)
def review_change(change_id: int, payload: ReviewCreate, db: Session = Depends(get_db)):
    change = db.get(Change, change_id)
    if change is None:
        raise HTTPException(status_code=404, detail="变更不存在")
    review = Review(
        change_id=change.id,
        reviewer=payload.reviewer,
        decision=payload.decision,
        comment=payload.comment,
        decided_at=utcnow(),
    )
    change.status = payload.decision
    db.add(review)
    db.commit()
    row = db.execute(_base_stmt().where(Change.id == change_id)).first()
    return _to_item(*row)
