"""Crawl orchestration: fetch pages+attachments, snapshot, detect changes,
merge regulations, and queue human review + notifications."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crawler import diff, fetcher, parser, storage
from app.services import email_service
from app.models.models import (
    ChangeEvent,
    ChangeType,
    CrawlRun,
    Document,
    ImpactLevel,
    Notification,
    Regulation,
    ReviewItem,
    ReviewStatus,
    RunStatus,
    Snapshot,
    Source,
    Subscription,
)

_IMPACT_ORDER = {
    ImpactLevel.unassessed: 0,
    ImpactLevel.low: 1,
    ImpactLevel.medium: 2,
    ImpactLevel.high: 3,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_or_create_document(db: Session, source: Source, url: str, title: str,
                            dedup_key: str) -> Document:
    doc = db.execute(
        select(Document).where(Document.source_id == source.id, Document.url == url)
    ).scalar_one_or_none()
    if doc is None:
        doc = Document(
            source_id=source.id, url=url, title=title, dedup_key=dedup_key,
            first_seen_at=_now(), last_seen_at=_now(),
        )
        db.add(doc)
        db.flush()
    else:
        doc.last_seen_at = _now()
        if title:
            doc.title = title
        if dedup_key:
            doc.dedup_key = dedup_key
    return doc


def _merge_regulation(db: Session, doc: Document, title: str, dedup_key: str) -> Regulation:
    """Attach the document to a canonical regulation, merging documents that share
    the same normalized dedup key across sources."""
    reg = db.execute(
        select(Regulation).where(Regulation.dedup_key == dedup_key)
    ).scalar_one_or_none()
    if reg is None:
        reg = Regulation(title=title, dedup_key=dedup_key)
        db.add(reg)
        db.flush()
    doc.regulation_id = reg.id
    return reg


def _create_change(db: Session, doc: Document, run: CrawlRun, change_type: ChangeType,
                   old_snap: Snapshot | None, new_snap: Snapshot, summary: str,
                   diff_text: str, similarity: float) -> ChangeEvent:
    change = ChangeEvent(
        document_id=doc.id,
        run_id=run.id,
        change_type=change_type,
        old_snapshot_id=old_snap.id if old_snap else None,
        new_snapshot_id=new_snap.id,
        summary=summary,
        diff_text=diff_text[:20000],
        similarity=similarity,
    )
    db.add(change)
    db.flush()
    # Every detected change enters the human-review queue as "pending".
    review = ReviewItem(change_id=change.id, status=ReviewStatus.pending)
    db.add(review)
    db.flush()
    _fanout_notifications(db, doc, change)
    return change


def _fanout_notifications(db: Session, doc: Document, change: ChangeEvent) -> None:
    subs = db.execute(select(Subscription).where(Subscription.enabled.is_(True))).scalars().all()
    for sub in subs:
        if sub.source_id and sub.source_id != doc.source_id:
            continue
        if sub.keyword and sub.keyword.lower() not in (doc.title or "").lower():
            continue
        # impact filter uses the document's current impact level (may be unassessed initially)
        if _IMPACT_ORDER[doc.impact_level] < _IMPACT_ORDER[sub.min_impact] and \
                doc.impact_level != ImpactLevel.unassessed:
            continue

        title = f"[{doc.title or '法规更新'}] 检测到{change.change_type.value}"
        notif = Notification(
            subscription_id=sub.id,
            change_id=change.id,
            title=title,
            body=change.summary,
            channel=sub.channel,
            delivery_status="created",
        )

        # For email subscriptions, actually deliver via SMTP and record the result.
        if sub.channel == "email":
            to_addr = sub.email or settings.notify_email_to
            body = (
                f"法规文档: {doc.title}\n"
                f"来源URL: {doc.url}\n"
                f"变更类型: {change.change_type.value}\n"
                f"摘要: {change.summary}\n"
            )
            status_, detail = email_service.send_email(to_addr, title, body)
            notif.delivery_status = status_
            notif.delivery_detail = detail
        else:
            notif.delivery_status = "sent"  # in-app notifications are delivered immediately
            notif.delivery_detail = "站内通知"

        db.add(notif)


def _latest_snapshot(db: Session, doc: Document, kind: str, url: str) -> Snapshot | None:
    return db.execute(
        select(Snapshot)
        .where(Snapshot.document_id == doc.id, Snapshot.kind == kind, Snapshot.url == url)
        .order_by(Snapshot.captured_at.desc())
    ).scalars().first()


def _process_page(db: Session, source: Source, run: CrawlRun, url: str,
                  client: httpx.Client, follow_links: bool = False) -> int:
    """Fetch and process one page + its attachments. When ``follow_links`` is
    True, also discover and crawl in-whitelist article links found on the page
    (used for the source entry page). Returns number of changes."""
    changes = 0
    allowed_hosts = fetcher.parse_allowed_hosts(source.url, source.allowed_hosts)
    result = fetcher.fetch(
        url,
        allowed_hosts=allowed_hosts,
        respect_robots=source.respect_robots,
        client=client,
    )
    run.pages_fetched += 1

    html = result.text or result.content.decode("utf-8", errors="ignore")
    title = parser.extract_title(html) or url
    body_text = parser.extract_html_text(html)
    revision = parser.find_revision_note(html)
    dedup_key = diff.dedup_key_for(title)

    doc = _get_or_create_document(db, source, url, title, dedup_key)
    _merge_regulation(db, doc, title, dedup_key)

    body_hash = diff.sha256_hex(body_text)
    prev = _latest_snapshot(db, doc, "page", url)

    raw_path, text_path = storage.store_snapshot(
        source.id, url, "page", result.content, body_text, body_hash
    )
    snap = Snapshot(
        run_id=run.id, document_id=doc.id, kind="page", url=url,
        content_type=result.content_type, http_status=result.status_code,
        raw_path=raw_path, text_path=text_path, content_hash=body_hash,
        text_excerpt=body_text[:800],
    )
    db.add(snap)
    db.flush()
    doc.latest_snapshot_id = snap.id

    if prev is None:
        # first time we see this document
        _create_change(
            db, doc, run, ChangeType.new, None, snap,
            summary=f"首次采集到《{title}》。{('修订记录: ' + revision) if revision else ''}",
            diff_text="", similarity=0.0,
        )
        changes += 1
    elif prev.content_hash != body_hash:
        old_text = storage.read_text(prev.text_path) or prev.text_excerpt
        similarity = diff.similarity_ratio(old_text, body_text)
        summary = diff.summarize_diff(old_text, body_text)
        if revision:
            summary += f" 修订记录: {revision}"
        _create_change(
            db, doc, run, ChangeType.body_changed, prev, snap,
            summary=summary, diff_text=diff.unified_diff(old_text, body_text),
            similarity=similarity,
        )
        changes += 1

    doc.latest_body_hash = body_hash

    # ---- attachments ----
    if source.fetch_attachments:
        attachments = parser.find_attachment_links(html, url)
        for att in attachments[:20]:  # cap per page
            changes += _process_attachment(db, source, run, doc, att["url"], client)

    # ---- content / article links on the entry page ----
    if follow_links and source.follow_links:
        links = parser.find_content_links(
            html, url, allowed_hosts, selector=source.link_selector,
            limit=max(0, source.max_links),
        )
        for link in links:
            try:
                # do not recurse further – article pages are crawled one level deep
                changes += _process_page(db, source, run, link["url"], client, follow_links=False)
            except fetcher.RobotsBlocked:
                run.robots_blocked += 1
            except fetcher.HostNotAllowed:
                # defensive: link discovery already filters, but re-validate at fetch time
                continue
            except fetcher.FetchError:
                continue

    return changes


def _process_attachment(db: Session, source: Source, run: CrawlRun, doc: Document,
                        att_url: str, client: httpx.Client) -> int:
    try:
        result = fetcher.fetch(
            att_url,
            allowed_hosts=fetcher.parse_allowed_hosts(source.url, source.allowed_hosts),
            respect_robots=source.respect_robots,
            client=client,
        )
    except fetcher.RobotsBlocked:
        run.robots_blocked += 1
        return 0
    except fetcher.FetchError:
        return 0

    run.attachments_fetched += 1
    filename = os.path.basename(urlparse(att_url).path) or "attachment"
    att_text = parser.extract_attachment_text(filename, result.content_type, result.content)
    content_hash = diff.sha256_hex(result.content)  # hash raw bytes for attachments

    prev = _latest_snapshot(db, doc, "attachment", att_url)
    raw_path, text_path = storage.store_snapshot(
        source.id, att_url, "attachment", result.content, att_text, content_hash
    )
    snap = Snapshot(
        run_id=run.id, document_id=doc.id, kind="attachment", url=att_url,
        filename=filename, content_type=result.content_type,
        http_status=result.status_code, raw_path=raw_path, text_path=text_path,
        content_hash=content_hash, text_excerpt=att_text[:800],
    )
    db.add(snap)
    db.flush()

    if prev is None:
        _create_change(
            db, doc, run, ChangeType.attachment_changed, None, snap,
            summary=f"新增附件《{filename}》。", diff_text="", similarity=0.0,
        )
        return 1
    if prev.content_hash != content_hash:
        old_text = storage.read_text(prev.text_path) or prev.text_excerpt
        similarity = diff.similarity_ratio(old_text, att_text)
        _create_change(
            db, doc, run, ChangeType.attachment_changed, prev, snap,
            summary=f"附件《{filename}》内容发生变化。" + diff.summarize_diff(old_text, att_text),
            diff_text=diff.unified_diff(old_text, att_text), similarity=similarity,
        )
        return 1
    return 0


def run_crawl(db: Session, source: Source, run: CrawlRun) -> CrawlRun:
    """Execute a crawl for a source within an existing run row."""
    run.status = RunStatus.running
    run.started_at = _now()
    db.commit()

    total_changes = 0
    try:
        with httpx.Client(
            timeout=settings.request_timeout,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=False,  # redirects are resolved+re-validated in fetcher
        ) as client:
            total_changes += _process_page(db, source, run, source.url, client, follow_links=True)
        run.changes_detected = total_changes
        run.status = RunStatus.success
        run.message = f"完成，检测到 {total_changes} 项变更。"
    except fetcher.HostNotAllowed as exc:
        run.status = RunStatus.skipped
        run.message = f"跳过：目标不在来源白名单内 ({exc})"
    except fetcher.RobotsBlocked as exc:
        run.robots_blocked += 1
        run.status = RunStatus.skipped
        run.message = f"跳过：被 robots.txt 拒绝 ({exc})"
    except Exception as exc:  # noqa: BLE001
        run.status = RunStatus.failed
        run.message = f"失败：{exc}"
    finally:
        run.finished_at = _now()
        source.last_run_at = run.finished_at
        db.commit()
    return run


def due_sources(db: Session) -> list[Source]:
    """Return enabled sources whose crawl frequency is due."""
    now = _now()
    sources = db.execute(select(Source).where(Source.enabled.is_(True))).scalars().all()
    due = []
    for s in sources:
        if s.last_run_at is None:
            due.append(s)
            continue
        last = s.last_run_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if now - last >= timedelta(minutes=s.frequency_minutes):
            due.append(s)
    return due
