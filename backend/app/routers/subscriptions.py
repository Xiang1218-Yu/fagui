from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from app.database import get_db
from app.models import Subscription, Source
from app.schemas import (
    SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse, PaginatedResponse
)

router = APIRouter(prefix="/api/subscriptions", tags=["订阅通知"])


@router.get("", response_model=PaginatedResponse)
def list_subscriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Subscription)
    if user_id:
        query = query.filter(Subscription.user_id == user_id)
    if is_active is not None:
        query = query.filter(Subscription.is_active == is_active)

    total = query.count()
    subscriptions = (
        query.order_by(desc(Subscription.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        items=[SubscriptionResponse.model_validate(s) for s in subscriptions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=SubscriptionResponse, status_code=201)
def create_subscription(data: SubscriptionCreate, db: Session = Depends(get_db)):
    if data.source_id:
        source = db.query(Source).filter(Source.id == data.source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="关联来源不存在")

    sub = Subscription(**data.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(subscription_id: str, db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return sub


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: str,
    data: SubscriptionUpdate,
    db: Session = Depends(get_db),
):
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(sub, key, value)

    from datetime import datetime
    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/{subscription_id}", status_code=204)
def delete_subscription(subscription_id: str, db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    db.delete(sub)
    db.commit()
