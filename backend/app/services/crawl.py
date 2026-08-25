import hashlib
import time
import traceback
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Change, CrawlRun, Document, ReviewTask, Snapshot, Source
from app.services import storage
from app.services.dedupe import find_or_create_regulation
from app.services.differ import compare_attachment_sets, summarize_change
from app.services.fetcher import fetch, make_client
from app.services.notifier import dispatch_event
from app.services.parser import (
    guess_extension,
    is_attachment_url,
    parse_html,
    extract_attachment_text,
)
from app.services.robots import RobotsChecker


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _same_origin(url: str, base_url: str) -> bool:
    a, b = urlsplit(url), urlsplit(base_url)
    return a.scheme in ("http", "https") and a.netloc == b.netloc


def _whitelisted(url: str, source: Source) -> bool:
    if not _same_origin(url, source.base_url):
        return False
    paths = source.allowed_paths or []
    if not paths:
        return True
    path = urlsplit(url).path
    return any(path.startswith(prefix) for prefix in paths)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CrawlLogger:
    def __init__(self, run: CrawlRun):
        self.run = run

    def log(self, message: str) -> None:
        line = f"[{_now().strftime('%H:%M:%S')}] {message}"
        self.run.log = (self.run.log or "") + line + "\n"


def _severity_for(change_type: str, has_reg_number: bool) -> str:
    if change_type == "new":
        return "medium"
    if change_type == "content_modified":
        return "high" if has_reg_number else "medium"
    if change_type == "attachment_modified":
        return "medium"
    return "low"


def run_crawl(db: Session, run_id: int) -> CrawlRun:
    run = db.get(CrawlRun, run_id)
    if run is None:
        raise ValueError(f"CrawlRun {run_id} 不存在")
    source = db.get(Source, run.source_id)
    logger = CrawlLogger(run)
    run.status = "running"
    run.started_at = _now()
    db.commit()

    pages_fetched = 0
    attachments_fetched = 0
    changes_detected = 0
    new_regulations = 0
    client: httpx.Client | None = None

    try:
        client = make_client()
        robots = RobotsChecker(respect=source.respect_robots)
        logger.log(f"开始采集来源「{source.name}」，入口 {source.homepage_url}，robots 遵守={'是' if source.respect_robots else '否'}")

        if not robots.can_fetch(source.homepage_url):
            raise RuntimeError("robots.txt 禁止抓取该入口页面")

        seen: set[str] = set()
        queue: list[tuple[str, int]] = [(source.homepage_url, 0)]
        max_pages = settings.crawl_max_pages
        max_depth = source.max_depth or settings.crawl_default_max_depth

        while queue and pages_fetched < max_pages:
            url, depth = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)

            if not _whitelisted(url, source):
                logger.log(f"跳过（不在来源白名单内）: {url}")
                continue
            if not robots.can_fetch(url):
                logger.log(f"跳过（robots.txt 不允许）: {url}")
                continue

            time.sleep(robots.crawl_delay(url))
            result = fetch(client, url)
            if not result.ok:
                logger.log(f"抓取失败 {url} -> {result.error}")
                continue

            is_html = "html" in result.content_type or result.url.lower().endswith((".html", ".htm", "/"))
            if not is_html:
                continue

            pages_fetched += 1
            parsed = parse_html(result.content, result.url)
            internal_links = [l for l in parsed.links if not l.is_attachment and _whitelisted(l.url, source)]
            is_index = len(internal_links) >= 3 and len(parsed.text) < 600
            logger.log(
                f"抓取页面: {result.url}（{len(result.content)} 字节，{len(parsed.links)} 个链接）"
                + ("，识别为列表/导航页" if is_index else "")
            )

            page_doc = db.query(Document).filter(Document.url_hash == _url_hash(result.url)).first()
            old_snapshot = None
            old_attachment_set: list[dict] = []
            if page_doc is not None:
                old_snapshot = db.get(Snapshot, page_doc.last_snapshot_id) if page_doc.last_snapshot_id else None
                for child in db.query(Document).filter(
                    Document.parent_id == page_doc.id, Document.doc_type == "attachment"
                ).all():
                    snap = db.get(Snapshot, child.last_snapshot_id) if child.last_snapshot_id else None
                    if snap:
                        old_attachment_set.append(
                            {
                                "url": child.url,
                                "name": child.attachment_name or child.title,
                                "content_hash": snap.content_hash,
                                "text_hash": snap.text_hash,
                            }
                        )

            new_snapshot = Snapshot(
                document_id=page_doc.id if page_doc else 0,
                crawl_run_id=run.id,
                status_code=result.status_code,
                content_type=result.content_type,
                size_bytes=len(result.content),
                content_hash=storage.content_sha256(result.content),
                text_hash=storage.text_sha256(parsed.text),
                title=parsed.title,
                is_attachment=False,
            )
            if page_doc is None:
                page_doc = Document(
                    source_id=source.id,
                    url=result.url,
                    url_hash=_url_hash(result.url),
                    title=parsed.title,
                    doc_type="page",
                    content_type=result.content_type,
                )
                db.add(page_doc)
                db.flush()
                new_snapshot.document_id = page_doc.id
            db.add(new_snapshot)
            db.flush()

            ext = guess_extension(result.url, result.content_type)
            new_snapshot.raw_path = storage.save_raw(source.id, page_doc.id, new_snapshot.id, ext, result.content)
            if parsed.text:
                new_snapshot.text_path = storage.save_text(source.id, page_doc.id, new_snapshot.id, parsed.text)
            db.flush()

            new_attachment_set: list[dict] = []
            for link in parsed.links:
                if not link.is_attachment:
                    continue
                if not _whitelisted(link.url, source):
                    logger.log(f"跳过附件（不在白名单）: {link.url}")
                    continue
                if not robots.can_fetch(link.url):
                    logger.log(f"跳过附件（robots 不允许）: {link.url}")
                    continue
                time.sleep(robots.crawl_delay(link.url))
                att_result = fetch(client, link.url)
                if not att_result.ok:
                    logger.log(f"附件抓取失败 {link.url} -> {att_result.error}")
                    continue
                attachments_fetched += 1
                att_text = extract_attachment_text(att_result.url, att_result.content_type, att_result.content)
                att_doc = db.query(Document).filter(Document.url_hash == _url_hash(att_result.url)).first()
                att_snapshot = Snapshot(
                    document_id=att_doc.id if att_doc else 0,
                    crawl_run_id=run.id,
                    status_code=att_result.status_code,
                    content_type=att_result.content_type,
                    size_bytes=len(att_result.content),
                    content_hash=storage.content_sha256(att_result.content),
                    text_hash=storage.text_sha256(att_text),
                    title=link.text or link.attachment_name,
                    is_attachment=True,
                )
                if att_doc is None:
                    att_doc = Document(
                        source_id=source.id,
                        parent_id=page_doc.id,
                        url=att_result.url,
                        url_hash=_url_hash(att_result.url),
                        title=link.text or link.attachment_name,
                        doc_type="attachment",
                        content_type=att_result.content_type,
                        attachment_name=link.attachment_name,
                    )
                    db.add(att_doc)
                    db.flush()
                    att_snapshot.document_id = att_doc.id
                else:
                    att_doc.parent_id = page_doc.id
                db.add(att_snapshot)
                db.flush()
                att_ext = guess_extension(att_result.url, att_result.content_type)
                att_snapshot.raw_path = storage.save_raw(source.id, att_doc.id, att_snapshot.id, att_ext, att_result.content)
                if att_text:
                    att_snapshot.text_path = storage.save_text(source.id, att_doc.id, att_snapshot.id, att_text)
                att_doc.content_hash = att_snapshot.content_hash
                att_doc.text_hash = att_snapshot.text_hash
                att_doc.last_snapshot_id = att_snapshot.id
                att_doc.last_seen_at = _now()
                new_attachment_set.append(
                    {
                        "url": att_doc.url,
                        "name": att_doc.attachment_name or att_doc.title,
                        "content_hash": att_snapshot.content_hash,
                        "text_hash": att_snapshot.text_hash,
                    }
                )
                logger.log(f"抓取附件: {att_doc.attachment_name or att_doc.title}（{att_snapshot.size_bytes} 字节）")

            page_doc.title = parsed.title or page_doc.title
            page_doc.content_type = result.content_type
            page_doc.content_hash = new_snapshot.content_hash
            page_doc.text_hash = new_snapshot.text_hash
            page_doc.last_snapshot_id = new_snapshot.id
            page_doc.last_seen_at = _now()
            db.flush()

            reg = None
            if is_index:
                page_doc.regulation_id = None
                logger.log("列表/导航页：仅留存快照，不参与法规归并与变更研判")
            else:
                reg, is_new_reg = find_or_create_regulation(
                    db, title=page_doc.title, text=parsed.text, url=page_doc.url, source=source
                )
                page_doc.regulation_id = reg.id
                for child in db.query(Document).filter(Document.parent_id == page_doc.id).all():
                    child.regulation_id = reg.id
                if is_new_reg:
                    new_regulations += 1
                    logger.log(f"归并为新法规: 「{reg.title}」（文号: {reg.reg_number or '未识别'}）")
                else:
                    logger.log(f"归并到既有法规: 「{reg.title}」（ID {reg.id}，多来源转载自动归并）")

            change_type = ""
            changed_fields: dict = {}
            if is_index:
                pass
            elif old_snapshot is None:
                change_type = "new"
                changed_fields = {
                    "new": True,
                    "body_changed": True,
                    "attachments": {"added": new_attachment_set, "removed": [], "modified": []},
                }
            else:
                body_changed = old_snapshot.text_hash != new_snapshot.text_hash
                title_changed = (old_snapshot.title or page_doc.title) != page_doc.title and bool(page_doc.title)
                att_diff = compare_attachment_sets(old_attachment_set, new_attachment_set)
                has_att_change = any(att_diff[k] for k in ("added", "removed", "modified"))
                if body_changed:
                    change_type = "content_modified"
                elif has_att_change:
                    change_type = "attachment_modified"
                elif title_changed:
                    change_type = "title_modified"
                if change_type:
                    changed_fields = {
                        "body_changed": body_changed,
                        "title_changed": title_changed,
                        "old_title": old_snapshot.title,
                        "new_title": page_doc.title,
                        "attachments": att_diff,
                    }

            if change_type:
                summary = "新采集到法规页面，已建立基线快照" if change_type == "new" else summarize_change(changed_fields)
                change = Change(
                    regulation_id=reg.id,
                    document_id=page_doc.id,
                    source_id=source.id,
                    from_snapshot_id=old_snapshot.id if old_snapshot else None,
                    to_snapshot_id=new_snapshot.id,
                    change_type=change_type,
                    status="pending_review",
                    severity=_severity_for(change_type, bool(reg.reg_number)),
                    title=page_doc.title,
                    summary=summary,
                    changed_fields=changed_fields,
                )
                db.add(change)
                db.flush()
                db.add(ReviewTask(change_id=change.id, status="pending"))
                changes_detected += 1
                logger.log(f"发现变更（{change_type}）: 「{page_doc.title}」-> 已进入复核队列")
                dispatch_event(
                    db,
                    event_type="change_detected",
                    title=f"[{source.name}] {summary}",
                    body=f"法规：{page_doc.title}\n链接：{page_doc.url}\n变更类型：{change_type}\n请前往复核队列确认。",
                    data={"change_id": change.id, "source_id": source.id, "regulation_id": reg.id},
                    source_id=source.id,
                )

            if depth < max_depth:
                for link in parsed.links:
                    if link.is_attachment:
                        continue
                    if not _whitelisted(link.url, source):
                        continue
                    if link.url not in seen and not any(u == link.url for u, _ in queue):
                        queue.append((link.url, depth + 1))

            db.commit()

        run.status = "success"
        run.finished_at = _now()
        run.pages_fetched = pages_fetched
        run.attachments_fetched = attachments_fetched
        run.changes_detected = changes_detected
        run.new_regulations = new_regulations
        run.stats = {
            "pages_fetched": pages_fetched,
            "attachments_fetched": attachments_fetched,
            "changes_detected": changes_detected,
            "new_regulations": new_regulations,
            "urls_seen": len(seen),
        }
        source.last_crawled_at = _now()
        logger.log(f"采集完成：页面 {pages_fetched}，附件 {attachments_fetched}，变更 {changes_detected}，新法规 {new_regulations}")
        db.commit()
    except Exception as exc:
        run.status = "failed"
        run.finished_at = _now()
        run.error = f"{type(exc).__name__}: {exc}"
        logger.log(f"采集异常终止: {run.error}")
        logger.log(traceback.format_exc())
        source.last_crawled_at = _now()
        db.commit()
    finally:
        if client is not None:
            client.close()

    return run
