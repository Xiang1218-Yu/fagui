from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Change, Notification, Regulation, Subscription
from app.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Notification, Subscription.name, Regulation.canonical_title)
        .join(Subscription, Notification.subscription_id == Subscription.id)
        .join(Change, Notification.change_id == Change.id)
        .join(Regulation, Change.regulation_id == Regulation.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(100)
    ).all()
    return [
        NotificationOut(
            id=notif.id,
            subscription_id=notif.subscription_id,
            subscription_name=sub_name,
            change_id=notif.change_id,
            change_title=reg_title,
            channel=notif.channel,
            status=notif.status,
            error=notif.error,
            created_at=notif.created_at,
            sent_at=notif.sent_at,
        )
        for notif, sub_name, reg_title in rows
    ]
