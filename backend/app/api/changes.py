from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Attachment, Change, Document, Regulation, Review, Snapshot, Source, User, utcnow
from app.schemas import AttachmentDiff, AttachmentOut, AttachmentVersion, ChangeDetail, ChangeListItem, ReviewCreate, ReviewOut
from app.security import get_current_user, require_roles
from app.services import diffutil

router = APIRouter(prefix="/changes", tags=["changes"], dependencies=[Depends(get_current_user)])


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


def _attachment_version(db: Session, attachment_id: Optional[int]) -> Optional[AttachmentVersion]:
    """按附件版本行构造 AttachmentVersion，text 从该版本 text_path 读取。"""
    if attachment_id is None:
        return None
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        return None
    text = None
    if attachment.text_path:
        try:
            text = Path(attachment.text_path).read_text(encoding="utf-8")
        except OSError:
            text = None
    return AttachmentVersion(
        id=attachment.id,
        url=attachment.url,
        filename=attachment.filename,
        content_hash=attachment.content_hash,
        created_at=attachment.created_at,
        text=text,
    )


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
        select(Attachment)
        .where(Attachment.document_id == change.document_id)
        .order_by(Attachment.created_at.desc(), Attachment.id.desc())
    ).all()
    attachment_diff = None
    if change.old_attachment_id is not None or change.new_attachment_id is not None:
        old_version = _attachment_version(db, change.old_attachment_id)
        new_version = _attachment_version(db, change.new_attachment_id)
        attachment_diff = AttachmentDiff(
            old=old_version,
            new=new_version,
            unified_diff=diffutil.unified_diff_text(
                old_version.text if old_version else None,
                new_version.text if new_version else None,
                max_lines=400,
            ),
        )
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
            AttachmentOut(
                id=a.id, url=a.url, filename=a.filename, content_hash=a.content_hash, created_at=a.created_at
            )
            for a in attachments
        ],
        attachment_diff=attachment_diff,
        review=ReviewOut(
            reviewer=review.reviewer, decision=review.decision, comment=review.comment, decided_at=review.decided_at
        )
        if review
        else None,
    )


@router.post("/{change_id}/review", response_model=ChangeListItem)
def review_change(
    change_id: int,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "analyst")),
):
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
