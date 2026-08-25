from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Change, CrawlRun, Notification, Regulation, ReviewTask, Source, User

router = APIRouter(prefix="/api/dashboard", tags=["看板"])


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    day_ago = datetime.utcnow() - timedelta(hours=24)

    sources_total = db.scalar(select(func.count(Source.id))) or 0
    sources_enabled = db.scalar(select(func.count(Source.id)).where(Source.enabled.is_(True))) or 0
    regulations_total = db.scalar(select(func.count(Regulation.id))) or 0
    changes_pending = db.scalar(
        select(func.count(Change.id)).where(Change.status == "pending_review")
    ) or 0
    review_pending = db.scalar(
        select(func.count(ReviewTask.id)).where(ReviewTask.status.in_(["pending", "claimed"]))
    ) or 0
    runs_24h = db.scalar(
        select(func.count(CrawlRun.id)).where(CrawlRun.started_at >= day_ago)
    ) or 0
    unread = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id, Notification.is_read.is_(False)
        )
    ) or 0

    recent_changes = list(
        db.scalars(select(Change).order_by(Change.detected_at.desc(), Change.id.desc()).limit(8))
    )
    recent_runs = list(db.scalars(select(CrawlRun).order_by(CrawlRun.id.desc()).limit(8)))
    sources = {s.id: s.name for s in db.scalars(select(Source))}

    return {
        "cards": {
            "sources_total": sources_total,
            "sources_enabled": sources_enabled,
            "regulations_total": regulations_total,
            "changes_pending": changes_pending,
            "review_pending": review_pending,
            "runs_24h": runs_24h,
            "unread_notifications": unread,
        },
        "recent_changes": [
            {
                "id": c.id,
                "title": c.title,
                "change_type": c.change_type,
                "status": c.status,
                "severity": c.severity,
                "source_name": sources.get(c.source_id, ""),
                "detected_at": c.detected_at,
            }
            for c in recent_changes
        ],
        "recent_runs": [
            {
                "id": r.id,
                "source_name": sources.get(r.source_id, ""),
                "status": r.status,
                "trigger_type": r.trigger_type,
                "pages_fetched": r.pages_fetched,
                "changes_detected": r.changes_detected,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
            }
            for r in recent_runs
        ],
    }
