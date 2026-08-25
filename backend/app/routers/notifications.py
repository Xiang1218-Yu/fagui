from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models import Notification, Subscription, NotificationStatus
from app.schemas import NotificationResponse, PaginatedResponse

router = APIRouter(prefix="/api/notifications", tags=["通知消息"])


@router.get("", response_model=PaginatedResponse)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Notification).join(
        Subscription, Notification.subscription_id == Subscription.id
    )

    if user_id:
        query = query.filter(Subscription.user_id == user_id)
    if status:
        query = query.filter(Notification.status == status)
    if channel:
        query = query.filter(Notification.channel == channel)

    total = query.count()
    notifications = (
        query.order_by(desc(Notification.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/unread-count")
def unread_count(user_id: str = Query(...), db: Session = Depends(get_db)):
    count = (
        db.query(Notification)
        .join(Subscription, Notification.subscription_id == Subscription.id)
        .filter(
            Subscription.user_id == user_id,
            Notification.status != NotificationStatus.READ,
        )
        .count()
    )
    return {"unread_count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(notification_id: str, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")

    notification.status = NotificationStatus.READ
    notification.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/read-all")
def mark_all_as_read(user_id: str = Query(...), db: Session = Depends(get_db)):
    notifications = (
        db.query(Notification)
        .join(Subscription, Notification.subscription_id == Subscription.id)
        .filter(
            Subscription.user_id == user_id,
            Notification.status != NotificationStatus.READ,
        )
        .all()
    )
    now = datetime.utcnow()
    for n in notifications:
        n.status = NotificationStatus.READ
        n.read_at = now
    db.commit()
    return {"marked_read": len(notifications)}
