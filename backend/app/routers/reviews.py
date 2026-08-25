from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models import Review, Change, Regulation, ReviewStatus, Source
from app.schemas import ReviewCreate, ReviewUpdate, ReviewResponse, PaginatedResponse

router = APIRouter(prefix="/api/reviews", tags=["复核队列"])


@router.get("", response_model=PaginatedResponse)
def list_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    reviewer_id: Optional[str] = None,
    regulation_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Review)

    if status:
        query = query.filter(Review.status == status)
    if reviewer_id:
        query = query.filter(Review.reviewer_id == reviewer_id)
    if regulation_id:
        query = query.filter(Review.regulation_id == regulation_id)

    total = query.count()
    reviews = (
        query.order_by(desc(Review.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for review in reviews:
        item = ReviewResponse.model_validate(review).model_dump()
        if review.change:
            change_data = {
                "id": review.change.id,
                "regulation_id": review.change.regulation_id,
                "crawl_run_id": review.change.crawl_run_id,
                "change_type": review.change.change_type.value,
                "severity": review.change.severity.value,
                "title": review.change.title,
                "summary": review.change.summary,
                "is_reviewed": review.change.is_reviewed,
                "created_at": review.change.created_at,
                "regulation_title": review.regulation.title if review.regulation else None,
                "source_name": review.regulation.source.name if review.regulation and review.regulation.source else None,
            }
            item["change"] = change_data
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/stats/summary")
def review_stats(db: Session = Depends(get_db)):
    stats = {}
    for status in ReviewStatus:
        count = db.query(func.count(Review.id)).filter(Review.status == status).scalar()
        stats[status.value] = count
    return stats


@router.get("/by-change/{change_id}", response_model=ReviewResponse)
def get_review_by_change(change_id: str, db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.change_id == change_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="该变更暂无复核记录")
    return review


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(review_id: str, db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="复核记录不存在")
    return review


@router.post("/{review_id}/claim", response_model=ReviewResponse)
def claim_review(
    review_id: str,
    reviewer_id: str = Query(...),
    reviewer_name: str = Query(...),
    db: Session = Depends(get_db),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="复核记录不存在")
    if review.status != ReviewStatus.PENDING:
        raise HTTPException(status_code=400, detail="该复核任务已被处理")

    review.status = ReviewStatus.IN_REVIEW
    review.reviewer_id = reviewer_id
    review.reviewer_name = reviewer_name
    review.claimed_at = datetime.utcnow()
    review.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    return review


@router.put("/{review_id}", response_model=ReviewResponse)
def update_review(review_id: str, review_data: ReviewUpdate, db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="复核记录不存在")

    update_data = review_data.model_dump(exclude_unset=True)

    if "status" in update_data and update_data["status"]:
        new_status = ReviewStatus(update_data["status"])
        review.status = new_status
        if new_status in (ReviewStatus.CONFIRMED, ReviewStatus.DISMISSED, ReviewStatus.ESCALATED):
            review.completed_at = datetime.utcnow()
            if review.change:
                review.change.is_reviewed = True

    for key, value in update_data.items():
        if key != "status" and value is not None:
            setattr(review, key, value)

    review.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    return review
