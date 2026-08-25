import logging
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database import SessionLocal
from app.models import (
    Subscription, Notification, Change, Regulation,
    NotificationChannel, NotificationStatus, ReviewStatus
)

logger = logging.getLogger(__name__)


@shared_task(name="app.tasks.notifier.process_pending_notifications")
def process_pending_notifications() -> dict:
    db = SessionLocal()
    stats = {"sent": 0, "failed": 0, "skipped": 0}
    try:
        since = datetime.utcnow() - timedelta(hours=1)
        new_changes = (
            db.query(Change)
            .filter(
                Change.created_at >= since,
                Change.is_reviewed == False,
            )
            .all()
        )

        subscriptions = (
            db.query(Subscription)
            .filter(Subscription.is_active == True)
            .all()
        )

        for change in new_changes:
            regulation = db.query(Regulation).filter(Regulation.id == change.regulation_id).first()
            if not regulation:
                continue

            for sub in subscriptions:
                if not _matches_subscription(change, regulation, sub):
                    continue

                for channel in sub.channels or ["in_app"]:
                    existing = (
                        db.query(Notification)
                        .filter(
                            Notification.subscription_id == sub.id,
                            Notification.change_id == change.id,
                            Notification.channel == channel,
                        )
                        .first()
                    )
                    if existing:
                        continue

                    notification = Notification(
                        subscription_id=sub.id,
                        change_id=change.id,
                        channel=NotificationChannel(channel),
                        status=NotificationStatus.PENDING,
                        title=f"法规变更提醒: {change.title[:200]}",
                        content=change.summary,
                        recipient=sub.user_email if channel == "email" else sub.user_id,
                    )
                    db.add(notification)
                    stats["sent"] += 1

        db.commit()

        _deliver_notifications(db)

        return stats
    except Exception as e:
        logger.error(f"Notification processing failed: {e}", exc_info=True)
        db.rollback()
        return stats
    finally:
        db.close()


def _matches_subscription(change: Change, regulation: Regulation, sub: Subscription) -> bool:
    if sub.source_id and regulation.source_id != sub.source_id:
        return False

    if sub.severity_filter:
        if change.severity.value not in sub.severity_filter:
            return False

    if sub.keywords:
        text = f"{regulation.title} {change.summary or ''} {change.title}"
        text_lower = text.lower()
        if not any(kw.lower() in text_lower for kw in sub.keywords):
            return False

    return True


def _deliver_notifications(db: Session):
    pending = (
        db.query(Notification)
        .filter(Notification.status == NotificationStatus.PENDING)
        .limit(100)
        .all()
    )

    for notification in pending:
        try:
            if notification.channel == NotificationChannel.IN_APP:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
            elif notification.channel == NotificationChannel.EMAIL:
                _send_email_notification(notification)
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
            elif notification.channel == NotificationChannel.WEBHOOK:
                _send_webhook_notification(notification)
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)[:500]
            logger.error(f"Failed to deliver notification {notification.id}: {e}")

    db.commit()


def _send_email_notification(notification: Notification):
    logger.info(f"Email notification would be sent to {notification.recipient}: {notification.title}")


def _send_webhook_notification(notification: Notification):
    logger.info(f"Webhook notification would be sent: {notification.title}")
