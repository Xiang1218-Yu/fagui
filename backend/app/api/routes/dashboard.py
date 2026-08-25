from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    ChangeEvent,
    Document,
    Notification,
    Regulation,
    ReviewItem,
    ReviewStatus,
    Source,
    User,
)
from app.schemas.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    return DashboardStats(
        sources=db.scalar(select(func.count(Source.id))) or 0,
        active_sources=db.scalar(select(func.count(Source.id)).where(Source.enabled.is_(True))) or 0,
        documents=db.scalar(select(func.count(Document.id))) or 0,
        regulations=db.scalar(select(func.count(Regulation.id))) or 0,
        pending_reviews=db.scalar(
            select(func.count(ReviewItem.id)).where(ReviewItem.status == ReviewStatus.pending)
        ) or 0,
        changes_last_7d=db.scalar(
            select(func.count(ChangeEvent.id)).where(ChangeEvent.created_at >= week_ago)
        ) or 0,
        unread_notifications=db.scalar(
            select(func.count(Notification.id)).where(Notification.is_read.is_(False))
        ) or 0,
    )
