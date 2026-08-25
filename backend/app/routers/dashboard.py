from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from app.database import get_db
from app.models import (
    Source, Regulation, Change, Review, CrawlRun,
    SourceStatus, ReviewStatus, ChangeSeverity
)

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("")
def dashboard_stats(db: Session = Depends(get_db)):
    total_sources = db.query(func.count(Source.id)).scalar() or 0
    active_sources = db.query(func.count(Source.id)).filter(Source.status == SourceStatus.ACTIVE).scalar() or 0
    total_regulations = db.query(func.count(Regulation.id)).scalar() or 0
    pending_reviews = db.query(func.count(Review.id)).filter(Review.status == ReviewStatus.PENDING).scalar() or 0
    in_review_count = db.query(func.count(Review.id)).filter(Review.status == ReviewStatus.IN_REVIEW).scalar() or 0

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    changes_today = db.query(func.count(Change.id)).filter(Change.created_at >= today_start).scalar() or 0
    changes_this_week = db.query(func.count(Change.id)).filter(Change.created_at >= week_ago).scalar() or 0

    recent_crawls = (
        db.query(CrawlRun)
        .order_by(desc(CrawlRun.created_at))
        .limit(10)
        .all()
    )

    recent_crawl_list = []
    for run in recent_crawls:
        recent_crawl_list.append({
            "id": run.id,
            "source_name": run.source.name if run.source else "未知",
            "status": run.status.value,
            "pages_crawled": run.pages_crawled,
            "changes_detected": run.changes_detected,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        })

    severity_breakdown = {}
    for severity in ChangeSeverity:
        count = db.query(func.count(Change.id)).filter(Change.severity == severity).scalar() or 0
        severity_breakdown[severity.value] = count

    review_breakdown = {}
    for status in ReviewStatus:
        count = db.query(func.count(Review.id)).filter(Review.status == status).scalar() or 0
        review_breakdown[status.value] = count

    source_type_breakdown = {}
    from app.models import SourceType
    for st in SourceType:
        count = db.query(func.count(Source.id)).filter(Source.source_type == st).scalar() or 0
        source_type_breakdown[st.value] = count

    recent_changes = (
        db.query(Change)
        .order_by(desc(Change.created_at))
        .limit(5)
        .all()
    )
    recent_change_list = []
    for change in recent_changes:
        recent_change_list.append({
            "id": change.id,
            "title": change.title,
            "severity": change.severity.value,
            "change_type": change.change_type.value,
            "regulation_title": change.regulation.title if change.regulation else None,
            "source_name": change.regulation.source.name if change.regulation and change.regulation.source else None,
            "created_at": change.created_at.isoformat() if change.created_at else None,
        })

    return {
        "total_sources": total_sources,
        "active_sources": active_sources,
        "total_regulations": total_regulations,
        "pending_reviews": pending_reviews,
        "in_review_count": in_review_count,
        "changes_today": changes_today,
        "changes_this_week": changes_this_week,
        "severity_breakdown": severity_breakdown,
        "review_breakdown": review_breakdown,
        "source_type_breakdown": source_type_breakdown,
        "recent_crawls": recent_crawl_list,
        "recent_changes": recent_change_list,
    }
