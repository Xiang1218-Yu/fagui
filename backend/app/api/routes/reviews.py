from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import ChangeEvent, Document, ReviewItem, ReviewStatus, User
from app.schemas.schemas import ReviewAssign, ReviewDecision, ReviewOut

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewOut])
def list_reviews(status: str | None = None, db: Session = Depends(get_db),
                 _: User = Depends(get_current_user)):
    stmt = select(ReviewItem).order_by(ReviewItem.id.desc())
    if status:
        stmt = select(ReviewItem).where(ReviewItem.status == status).order_by(
            ReviewItem.id.desc()
        )
    items = db.execute(stmt).scalars().all()
    result = []
    for item in items:
        out = ReviewOut.model_validate(item)
        change = db.get(ChangeEvent, item.change_id)
        if change is not None:
            from app.schemas.schemas import ChangeOut

            out.change = ChangeOut.model_validate(change)
        result.append(out)
    return result


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(review_id: int, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    item = db.get(ReviewItem, review_id)
    if item is None:
        raise HTTPException(404, "review not found")
    out = ReviewOut.model_validate(item)
    change = db.get(ChangeEvent, item.change_id)
    if change is not None:
        from app.schemas.schemas import ChangeOut

        out.change = ChangeOut.model_validate(change)
    return out


@router.post("/{review_id}/assign", response_model=ReviewOut)
def assign_review(review_id: int, payload: ReviewAssign, db: Session = Depends(get_db),
                  _: User = Depends(get_current_user)):
    item = db.get(ReviewItem, review_id)
    if item is None:
        raise HTTPException(404, "review not found")
    item.assignee = payload.assignee
    db.commit()
    db.refresh(item)
    return ReviewOut.model_validate(item)


@router.post("/{review_id}/decide", response_model=ReviewOut)
def decide_review(review_id: int, payload: ReviewDecision, db: Session = Depends(get_db),
                  _: User = Depends(get_current_user)):
    """Analyst confirms/dismisses a change and records the impact assessment."""
    item = db.get(ReviewItem, review_id)
    if item is None:
        raise HTTPException(404, "review not found")

    item.status = payload.status
    item.impact_level = payload.impact_level
    item.decision_note = payload.decision_note
    item.impact_note = payload.impact_note
    item.affected_business = payload.affected_business
    item.reviewed_by = payload.reviewed_by
    item.reviewed_at = datetime.now(timezone.utc)

    # propagate the impact level onto the underlying document (impact assessment result)
    if payload.status == ReviewStatus.confirmed:
        change = db.get(ChangeEvent, item.change_id)
        if change is not None:
            doc = db.get(Document, change.document_id)
            if doc is not None:
                doc.impact_level = payload.impact_level

    db.commit()
    db.refresh(item)
    out = ReviewOut.model_validate(item)
    change = db.get(ChangeEvent, item.change_id)
    if change is not None:
        from app.schemas.schemas import ChangeOut

        out.change = ChangeOut.model_validate(change)
    return out
