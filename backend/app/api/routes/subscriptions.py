from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Notification, Subscription, User
from app.schemas.schemas import (
    NotificationOut,
    SubscriptionCreate,
    SubscriptionOut,
)
from app.services import email_service

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[SubscriptionOut])
def list_subscriptions(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.execute(select(Subscription).order_by(Subscription.id)).scalars().all()


@router.post("", response_model=SubscriptionOut, status_code=201)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db),
                        _: User = Depends(get_current_user)):
    sub = Subscription(**payload.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/{sub_id}", status_code=204)
def delete_subscription(sub_id: int, db: Session = Depends(get_db),
                        _: User = Depends(get_current_user)):
    sub = db.get(Subscription, sub_id)
    if sub is None:
        raise HTTPException(404, "subscription not found")
    db.delete(sub)
    db.commit()


class EmailTest(BaseModel):
    to: str


@router.post("/test-email", response_model=dict)
def test_email(payload: EmailTest, _: User = Depends(get_current_user)):
    """Send a test email to verify SMTP configuration end-to-end."""
    status_, detail = email_service.send_email(
        payload.to, "法规情报平台 · 邮件通知测试", "这是一封测试邮件，用于验证 SMTP 配置是否可用。"
    )
    return {"status": status_, "detail": detail, "smtp_configured": email_service.is_configured()}


notif_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notif_router.get("", response_model=list[NotificationOut])
def list_notifications(unread_only: bool = False, limit: int = 100,
                       db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(Notification).order_by(Notification.id.desc()).limit(limit)
    if unread_only:
        stmt = select(Notification).where(Notification.is_read.is_(False)).order_by(
            Notification.id.desc()
        ).limit(limit)
    return db.execute(stmt).scalars().all()


@notif_router.post("/{notif_id}/read", response_model=NotificationOut)
def mark_read(notif_id: int, db: Session = Depends(get_db),
              _: User = Depends(get_current_user)):
    notif = db.get(Notification, notif_id)
    if notif is None:
        raise HTTPException(404, "notification not found")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@notif_router.post("/read-all", response_model=dict)
def mark_all_read(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.execute(select(Notification).where(Notification.is_read.is_(False))).scalars().all()
    for n in rows:
        n.is_read = True
    db.commit()
    return {"marked": len(rows)}
