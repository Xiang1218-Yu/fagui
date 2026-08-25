from sqlalchemy.orm import Session

from app.models import Notification, Subscription

EVENT_LABELS = {
    "change_detected": "检测到法规变更",
    "review_decided": "复核结论已出具",
    "impact_published": "影响研判已发布",
}


def _match_keywords(keywords: list[str], haystack: str) -> bool:
    if not keywords:
        return True
    return any(kw and kw in haystack for kw in keywords)


def dispatch_event(
    db: Session,
    *,
    event_type: str,
    title: str,
    body: str,
    data: dict | None = None,
    source_id: int | None = None,
) -> int:
    subscriptions = db.query(Subscription).filter(Subscription.enabled.is_(True)).all()
    sent = 0
    for sub in subscriptions:
        if event_type not in (sub.event_types or []):
            continue
        if sub.source_ids and source_id is not None and source_id not in sub.source_ids:
            continue
        if not _match_keywords(sub.keywords or [], f"{title}\n{body}"):
            continue

        send_status = "sent"
        if sub.channel == "email":
            send_status = "simulated"
        elif sub.channel == "webhook":
            send_status = "simulated"

        notification = Notification(
            user_id=sub.user_id,
            subscription_id=sub.id,
            event_type=event_type,
            title=title,
            body=body,
            data=data or {},
            send_status=send_status,
        )
        db.add(notification)
        sent += 1
    db.flush()
    return sent
