from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import ChangeEvent, Document, Snapshot, User
from app.schemas.schemas import ChangeDetail, ChangeOut, SnapshotOut

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("", response_model=list[ChangeOut])
def list_changes(document_id: int | None = None, change_type: str | None = None,
                 limit: int = 200, db: Session = Depends(get_db),
                 _: User = Depends(get_current_user)):
    stmt = select(ChangeEvent).order_by(ChangeEvent.id.desc()).limit(limit)
    conditions = []
    if document_id is not None:
        conditions.append(ChangeEvent.document_id == document_id)
    if change_type:
        conditions.append(ChangeEvent.change_type == change_type)
    if conditions:
        stmt = select(ChangeEvent).where(*conditions).order_by(
            ChangeEvent.id.desc()
        ).limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/{change_id}", response_model=ChangeDetail)
def get_change(change_id: int, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    change = db.get(ChangeEvent, change_id)
    if change is None:
        raise HTTPException(404, "change not found")
    doc = db.get(Document, change.document_id)
    detail = ChangeDetail.model_validate(change)
    if doc is not None:
        from app.schemas.schemas import DocumentOut

        detail.document = DocumentOut.model_validate(doc)
    return detail


@router.get("/{change_id}/snapshots", response_model=dict)
def change_snapshots(change_id: int, db: Session = Depends(get_db),
                     _: User = Depends(get_current_user)):
    """Return the old & new snapshots referenced by a change for side-by-side view."""
    change = db.get(ChangeEvent, change_id)
    if change is None:
        raise HTTPException(404, "change not found")
    old_snap = db.get(Snapshot, change.old_snapshot_id) if change.old_snapshot_id else None
    new_snap = db.get(Snapshot, change.new_snapshot_id) if change.new_snapshot_id else None
    return {
        "old": SnapshotOut.model_validate(old_snap) if old_snap else None,
        "new": SnapshotOut.model_validate(new_snap) if new_snap else None,
        "old_text": _read(old_snap),
        "new_text": _read(new_snap),
        "diff_text": change.diff_text,
    }


def _read(snap: Snapshot | None) -> str:
    if snap is None:
        return ""
    from app.crawler import storage

    return storage.read_text(snap.text_path) or snap.text_excerpt
