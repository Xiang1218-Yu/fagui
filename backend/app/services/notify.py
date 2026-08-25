from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Change, Document, Notification, Regulation, Source, Subscription, utcnow


def _matches(sub: Subscription, document: Document, regulation: Optional[Regulation], source: Source) -> bool:
    """keywords 命中法规/文档标题，或 source_ids 包含该来源；两者皆空则全量匹配。"""
    keywords = sub.keywords or []
    source_ids = sub.source_ids or []
    if not keywords and not source_ids:
        return True
    titles = [t for t in [regulation.canonical_title if regulation else "", document.title or ""] if t]
    if any(kw and any(kw in t for t in titles) for kw in keywords):
        return True
    return source.id in source_ids


def dispatch_for_change(
    session: Session,
    change: Change,
    document: Document,
    regulation: Optional[Regulation],
    source: Source,
) -> None:
    """按订阅投递变更通知，每次投递写 notifications 记录。"""
    subs = session.scalars(select(Subscription).where(Subscription.enabled.is_(True))).all()
    for sub in subs:
        if not _matches(sub, document, regulation, source):
            continue
        notif = Notification(
            subscription_id=sub.id,
            change_id=change.id,
            channel=sub.channel,
            status="sent",
            created_at=utcnow(),
        )
        try:
            if sub.channel == "webhook":
                payload = {
                    "change_id": change.id,
                    "change_type": change.change_type,
                    "regulation_id": regulation.id if regulation else None,
                    "regulation_title": regulation.canonical_title if regulation else None,
                    "document_url": document.url,
                    "document_title": document.title,
                    "source_name": source.name,
                    "diff_summary": change.diff_summary,
                    "detected_at": change.detected_at.isoformat() if change.detected_at else None,
                }
                resp = httpx.post(sub.target, json=payload, timeout=10)
                if resp.status_code >= 400:
                    raise RuntimeError(f"HTTP {resp.status_code}")
            # email 渠道仅模拟，视为成功发送
            notif.status = "sent"
            notif.error = None
            notif.sent_at = utcnow()
        except Exception as exc:  # 投递失败不影响主流程
            notif.status = "failed"
            notif.error = str(exc)[:500]
        session.add(notif)
