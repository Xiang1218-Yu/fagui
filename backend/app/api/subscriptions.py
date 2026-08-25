from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Source, Subscription, User
from app.schemas import SubscriptionCreate, SubscriptionOut, SubscriptionUpdate

router = APIRouter(prefix="/api/subscriptions", tags=["订阅通知"])


@router.get("", response_model=list[SubscriptionOut])
def list_subscriptions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Subscription).where(Subscription.user_id == user.id).order_by(Subscription.id.desc())
    if user.role == "admin":
        stmt = select(Subscription).order_by(Subscription.id.desc())
    return list(db.scalars(stmt))


@router.post("", response_model=SubscriptionOut)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sub = Subscription(
        user_id=user.id,
        name=payload.name,
        channel=payload.channel,
        event_types=payload.event_types,
        source_ids=payload.source_ids,
        keywords=payload.keywords,
        destination=payload.destination,
        enabled=payload.enabled,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.patch("/{subscription_id}", response_model=SubscriptionOut)
def update_subscription(
    subscription_id: int,
    payload: SubscriptionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sub = db.get(Subscription, subscription_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="订阅不存在")
    if sub.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权操作他人订阅")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(sub, key, value)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/{subscription_id}")
def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sub = db.get(Subscription, subscription_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="订阅不存在")
    if sub.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权操作他人订阅")
    db.delete(sub)
    db.commit()
    return {"ok": True}


@router.get("/meta/options")
def subscription_options(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    sources = [{"id": s.id, "name": s.name} for s in db.scalars(select(Source).order_by(Source.id))]
    return {
        "channels": [
            {"value": "inapp", "label": "站内通知"},
            {"value": "email", "label": "邮件（模拟发送，记录在通知中心）"},
            {"value": "webhook", "label": "Webhook（模拟投递，记录在通知中心）"},
        ],
        "event_types": [
            {"value": "change_detected", "label": "检测到法规变更"},
            {"value": "review_decided", "label": "复核结论出具"},
            {"value": "impact_published", "label": "影响研判发布"},
        ],
        "sources": sources,
    }
