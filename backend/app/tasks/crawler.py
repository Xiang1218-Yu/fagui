import hashlib
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse, urljoin
from celery import shared_task
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Source, CrawlRun, Regulation, Snapshot, Attachment, Change,
    Review, SourceStatus, CrawlStatus, ChangeType, ChangeSeverity,
    RegulationStatus, ReviewStatus
)
from app.services.robots import RobotsChecker
from app.services.fetcher import HttpFetcher
from app.services.parser import ContentParser
from app.services.storage import SnapshotStorage
from app.services.differ import DiffEngine
from app.services.merger import RegulationMerger
from app.config import settings

logger = logging.getLogger(__name__)


def _is_host_allowed(url: str, source: Source) -> bool:
    """统一校验页面和附件的 host 是否在来源白名单内。"""
    try:
        parsed_url = urlparse(url)
        parsed_base = urlparse(source.base_url)
        if parsed_url.scheme not in ("http", "https"):
            return False
        if parsed_url.netloc != parsed_base.netloc:
            return False
    except Exception:
        return False
    return True


def _is_path_allowed(url: str, source: Source) -> bool:
    """校验 URL 路径是否符合允许/排除规则。"""
    parsed = urlparse(url)
    path = parsed.path.lower()

    if source.excluded_paths:
        for excluded in source.excluded_paths:
            if excluded.lower().strip("/") in path:
                return False

    if source.allowed_paths:
        return any(allowed.lower().strip("/") in path for allowed in source.allowed_paths)

    return True


def _can_crawl_url(url: str, source: Source, robots_checker: RobotsChecker) -> bool:
    """统一的 URL 校验：host 白名单 + 路径规则 + robots.txt。"""
    if not _is_host_allowed(url, source):
        logger.debug(f"Skipping {url}: host not in whitelist")
        return False
    if not _is_path_allowed(url, source):
        logger.debug(f"Skipping {url}: path not allowed")
        return False
    if source.robots_txt_enabled and not robots_checker.can_fetch(url):
        logger.info(f"Skipping {url}: blocked by robots.txt")
        return False
    return True


@shared_task(bind=True, name="app.tasks.crawler.crawl_source")
def crawl_source(self, source_id: str, triggered_by: str = "scheduled") -> dict:
    db = SessionLocal()
    robots_checker = RobotsChecker(settings.USER_AGENT)
    fetcher = HttpFetcher()
    storage = SnapshotStorage()
    differ = DiffEngine()
    stats = {
        "pages_crawled": 0,
        "pages_failed": 0,
        "attachments_downloaded": 0,
        "new_regulations": 0,
        "changes_detected": 0,
        "errors": [],
    }

    crawl_run = None
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return {"error": "Source not found", "source_id": source_id}

        crawl_run = CrawlRun(
            source_id=source_id,
            status=CrawlStatus.RUNNING,
            triggered_by=triggered_by,
            started_at=datetime.utcnow(),
            celery_task_id=self.request.id,
        )
        db.add(crawl_run)
        db.commit()
        db.refresh(crawl_run)

        parser = ContentParser(source.selector_config)
        visited_urls = set()
        urls_to_crawl = [(source.url, 0)]

        while urls_to_crawl:
            url, depth = urls_to_crawl.pop(0)
            if url in visited_urls:
                continue
            if depth > source.max_depth:
                continue
            visited_urls.add(url)

            if not _can_crawl_url(url, source, robots_checker):
                continue

            if source.respect_crawl_delay:
                delay = robots_checker.get_crawl_delay(url) or settings.CRAWL_DELAY_SECONDS
                time.sleep(delay)

            try:
                result = fetcher.fetch(url, extra_headers=source.headers or {})
                if not result:
                    stats["pages_failed"] += 1
                    continue

                if not _is_host_allowed(result.final_url, source):
                    logger.warning(
                        f"Skipping {url}: redirected to {result.final_url} which is outside host whitelist"
                    )
                    stats["pages_failed"] += 1
                    continue

                if "text/html" not in result.content_type and "application/xhtml" not in result.content_type:
                    continue

                parsed = parser.parse(result.text, url)
                stats["pages_crawled"] += 1

                url_hash = storage.hash_url(url)
                snapshot_path = storage.save_snapshot(
                    source_id=source_id,
                    url_hash=url_hash,
                    content_html=parsed.html,
                    content_text=parsed.text,
                    metadata=parsed.metadata,
                )

                regulation, is_new = _find_or_create_regulation(
                    db, source, url, parsed, result
                )

                previous_snapshot = (
                    db.query(Snapshot)
                    .filter(Snapshot.regulation_id == regulation.id)
                    .order_by(Snapshot.captured_at.desc())
                    .first()
                )

                previous_attachment_map = {}
                if previous_snapshot:
                    prev_atts = (
                        db.query(Attachment)
                        .filter(
                            Attachment.regulation_id == regulation.id,
                            Attachment.snapshot_id == previous_snapshot.id,
                        )
                        .all()
                    )
                    for att in prev_atts:
                        previous_attachment_map[att.url] = {
                            "id": att.id,
                            "filename": att.filename,
                            "url": att.url,
                            "file_hash": att.file_hash,
                            "file_size": att.file_size,
                            "content_type": att.content_type,
                        }

                snapshot = Snapshot(
                    regulation_id=regulation.id,
                    crawl_run_id=crawl_run.id,
                    url=url,
                    content_text=parsed.text,
                    content_html=parsed.html,
                    content_hash=parsed.content_hash,
                    http_status=result.status_code,
                    response_headers=result.headers,
                    metadata_json=parsed.metadata,
                    word_count=parsed.word_count,
                    snapshot_path=snapshot_path,
                )
                db.add(snapshot)
                db.flush()

                if is_new:
                    change = _create_new_regulation_change(
                        db, crawl_run.id, snapshot, regulation, parsed
                    )
                    if change:
                        stats["new_regulations"] += 1
                        stats["changes_detected"] += 1
                elif previous_snapshot and previous_snapshot.content_hash != parsed.content_hash:
                    change = _create_content_update_change(
                        db, previous_snapshot, snapshot, regulation, parsed, differ
                    )
                    if change:
                        stats["changes_detected"] += 1

                current_attachment_map = {}
                failed_attachment_urls: set[str] = set()
                for att_info in parsed.attachments:
                    att_url = att_info["url"]

                    if not _can_crawl_url(att_url, source, robots_checker):
                        logger.info(f"Skipping attachment {att_url}: failed host/robots check")
                        continue

                    try:
                        att_result = fetcher.fetch_attachment(
                            att_url, extra_headers=source.headers or {}
                        )
                        if not att_result:
                            failed_attachment_urls.add(att_url)
                            stats["pages_failed"] += 1
                            continue

                        if not _is_host_allowed(att_result.final_url, source):
                            logger.warning(
                                f"Skipping attachment {att_url}: redirected to "
                                f"{att_result.final_url} outside host whitelist"
                            )
                            failed_attachment_urls.add(att_url)
                            stats["pages_failed"] += 1
                            continue

                        effective_url = att_result.final_url
                        file_hash = hashlib.sha256(att_result.content).hexdigest()

                        current_attachment_map[att_url] = {
                            "filename": att_info["filename"],
                            "url": att_url,
                            "effective_url": effective_url,
                            "file_hash": file_hash,
                            "file_size": len(att_result.content),
                            "content_type": att_result.content_type,
                        }

                        existing_att = (
                            db.query(Attachment)
                            .filter(
                                Attachment.regulation_id == regulation.id,
                                Attachment.file_hash == file_hash,
                            )
                            .first()
                        )
                        if not existing_att:
                            storage_path = storage.save_attachment(
                                source_id, att_info["filename"],
                                att_result.content, file_hash
                            )
                            extracted_text, extract_status = parser.parse_attachment_text(
                                att_result.content,
                                att_result.content_type,
                                att_info["filename"],
                            )
                            attachment = Attachment(
                                regulation_id=regulation.id,
                                snapshot_id=snapshot.id,
                                filename=att_info["filename"][:512],
                                url=att_url,
                                content_type=att_result.content_type,
                                file_size=len(att_result.content),
                                file_hash=file_hash,
                                storage_path=storage_path,
                                extracted_text=extracted_text[:100000] if extracted_text else None,
                                extraction_status="success" if extract_status == "success" else "error",
                            )
                            db.add(attachment)
                            stats["attachments_downloaded"] += 1
                        else:
                            existing_att.snapshot_id = snapshot.id
                    except Exception as e:
                        logger.warning(f"Failed to download attachment {att_url}: {e}")
                        failed_attachment_urls.add(att_url)
                        stats["errors"].append(f"attachment {att_url}: {str(e)[:150]}")

                if not is_new:
                    att_change = _detect_attachment_changes(
                        db, crawl_run.id, regulation, snapshot,
                        previous_attachment_map, current_attachment_map,
                        failed_attachment_urls,
                    )
                    if att_change:
                        stats["changes_detected"] += 1

                regulation.last_seen_at = datetime.utcnow()
                regulation.content_hash = parsed.content_hash

                if depth < source.max_depth:
                    for link in parsed.links:
                        link_url = link["url"]
                        if _can_crawl_url(link_url, source, robots_checker) and link_url not in visited_urls:
                            urls_to_crawl.append((link_url, depth + 1))

                db.commit()

            except Exception as e:
                stats["pages_failed"] += 1
                stats["errors"].append(f"{url}: {str(e)[:200]}")
                logger.error(f"Error crawling {url}: {e}", exc_info=True)
                db.rollback()

        source.last_crawled_at = datetime.utcnow()
        source.status = SourceStatus.ACTIVE
        source.last_error = None

        crawl_run.status = CrawlStatus.SUCCESS if stats["pages_failed"] == 0 else CrawlStatus.PARTIAL
        crawl_run.completed_at = datetime.utcnow()
        crawl_run.pages_crawled = stats["pages_crawled"]
        crawl_run.pages_failed = stats["pages_failed"]
        crawl_run.attachments_downloaded = stats["attachments_downloaded"]
        crawl_run.new_regulations = stats["new_regulations"]
        crawl_run.changes_detected = stats["changes_detected"]
        crawl_run.logs = stats["errors"]

        db.commit()

        if stats["changes_detected"] > 0:
            from app.tasks.notifier import process_pending_notifications
            process_pending_notifications.delay()

        return stats

    except Exception as e:
        logger.error(f"Crawl failed for source {source_id}: {e}", exc_info=True)
        if crawl_run:
            crawl_run.status = CrawlStatus.FAILED
            crawl_run.completed_at = datetime.utcnow()
            crawl_run.error_message = str(e)[:1000]
            db.commit()
        if source:
            source.status = SourceStatus.ERROR
            source.last_error = str(e)[:500]
            db.commit()
        raise
    finally:
        db.close()


def _find_or_create_regulation(
    db: Session, source: Source, url: str, parsed, fetch_result
) -> tuple[Regulation, bool]:
    """查找或创建法规，返回 (regulation, is_new)。"""
    regulation = (
        db.query(Regulation)
        .filter(
            Regulation.source_id == source.id,
            Regulation.url == url,
        )
        .first()
    )

    if regulation:
        return regulation, False

    content_hash = parsed.content_hash
    reg_number = _extract_regulation_number(parsed.title, parsed.text)
    issuing_authority = parsed.metadata.get("author")
    publish_date = _parse_date(
        parsed.metadata.get("publish_date") or parsed.metadata.get("published_time")
    )

    regulation = Regulation(
        source_id=source.id,
        title=parsed.title,
        url=url,
        regulation_number=reg_number,
        issuing_authority=issuing_authority,
        publish_date=publish_date,
        status=RegulationStatus.PUBLISHED,
        summary=parsed.text[:500],
        content_hash=content_hash,
        metadata_json=parsed.metadata,
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
    )
    db.add(regulation)
    db.flush()

    try:
        merger = RegulationMerger(db)
        merger.auto_merge(regulation, threshold=0.85)
    except Exception as e:
        logger.warning(f"Auto-merge failed: {e}")

    return regulation, True


def _create_review_for_change(
    db: Session, change: Change, regulation: Regulation
) -> Review:
    review = Review(
        change_id=change.id,
        regulation_id=regulation.id,
        status=ReviewStatus.PENDING,
        assigned_at=datetime.utcnow(),
        due_at=datetime.utcnow() + timedelta(days=3),
    )
    db.add(review)
    return review


def _create_new_regulation_change(
    db: Session,
    crawl_run_id: str,
    snapshot: Snapshot,
    regulation: Regulation,
    parsed,
) -> Optional[Change]:
    """新法规首次发现时创建 NEW 类型变更 + 复核任务。"""
    word_count = parsed.word_count
    att_count = len(parsed.attachments)

    summary_parts = [f"新收录法规，正文约 {word_count} 字"]
    if att_count > 0:
        summary_parts.append(f"包含 {att_count} 个附件")

    change = Change(
        regulation_id=regulation.id,
        crawl_run_id=crawl_run_id,
        previous_snapshot_id=None,
        current_snapshot_id=snapshot.id,
        change_type=ChangeType.NEW,
        severity=ChangeSeverity.MEDIUM,
        title=f"新法规收录: {regulation.title[:200]}",
        summary="；".join(summary_parts),
        diff_content={
            "sections": [],
            "note": "首次采集，无历史版本可对比",
        },
        diff_stats={
            "lines_added": word_count,
            "lines_removed": 0,
            "lines_changed": word_count,
            "total_before": 0,
            "total_after": word_count,
            "change_ratio": 1.0,
        },
        changed_fields=[],
        attachment_changes=[],
    )
    db.add(change)
    db.flush()
    _create_review_for_change(db, change, regulation)
    regulation.updated_at = datetime.utcnow()
    logger.info(f"Created NEW regulation change for {regulation.title[:80]}")
    return change


def _create_content_update_change(
    db: Session,
    previous_snapshot: Snapshot,
    current_snapshot: Snapshot,
    regulation: Regulation,
    parsed,
    differ: DiffEngine,
) -> Optional[Change]:
    """正文内容变化时创建 CONTENT_UPDATE 类型变更 + 复核任务。"""
    diff_result = differ.compute_text_diff(
        previous_snapshot.content_text or "",
        current_snapshot.content_text or "",
    )

    if diff_result["stats"]["lines_changed"] == 0:
        return None

    severity_str = diff_result.get("severity", "medium")
    severity = ChangeSeverity(severity_str) if severity_str in [s.value for s in ChangeSeverity] else ChangeSeverity.MEDIUM

    stats = diff_result["stats"]
    summary = f"正文变更：新增 {stats['lines_added']} 行，删除 {stats['lines_removed']} 行，变更比例 {stats['change_ratio']*100:.1f}%"

    change = Change(
        regulation_id=regulation.id,
        crawl_run_id=current_snapshot.crawl_run_id,
        previous_snapshot_id=previous_snapshot.id,
        current_snapshot_id=current_snapshot.id,
        change_type=ChangeType.CONTENT_UPDATE,
        severity=severity,
        title=f"正文更新: {regulation.title[:200]}",
        summary=summary,
        diff_content={
            "unified_diff": diff_result["unified_diff"],
            "sections": diff_result["sections"],
        },
        diff_stats=stats,
        changed_fields=[],
        attachment_changes=[],
    )
    db.add(change)
    db.flush()
    _create_review_for_change(db, change, regulation)
    regulation.updated_at = datetime.utcnow()
    logger.info(f"Created CONTENT_UPDATE change for {regulation.title[:80]}")
    return change


def _detect_attachment_changes(
    db: Session,
    crawl_run_id: str,
    regulation: Regulation,
    snapshot: Snapshot,
    previous_map: dict[str, dict],
    current_map: dict[str, dict],
    failed_urls: Optional[set[str]] = None,
) -> Optional[Change]:
    """对比前后快照的附件，检测新增/删除/修改，创建 ATTACHMENT_UPDATE 变更。

    抓取失败的附件（在 failed_urls 中）不会被误报为删除，因为我们无法确认
    它是真的从页面上消失了还是仅仅下载失败。
    """
    failed_urls = failed_urls or set()
    prev_urls = set(previous_map.keys())
    curr_urls = set(current_map.keys())

    added_urls = curr_urls - prev_urls
    removed_urls = (prev_urls - curr_urls) - failed_urls

    added = [current_map[u] for u in added_urls]
    removed = [previous_map[u] for u in removed_urls]
    modified = []
    for url in prev_urls & curr_urls:
        old = previous_map[url]
        new = current_map[url]
        if old.get("file_hash") != new.get("file_hash"):
            modified.append({"before": old, "after": new})

    if not added and not removed and not modified:
        return None

    attachment_changes = {
        "added": [{"filename": a["filename"], "url": a["url"], "file_hash": a["file_hash"][:16]} for a in added],
        "removed": [{"filename": r["filename"], "url": r["url"]} for r in removed],
        "modified": [{"filename": m["after"]["filename"], "url": m["after"]["url"]} for m in modified],
    }

    parts = []
    if added:
        parts.append(f"新增 {len(added)} 个附件")
    if removed:
        parts.append(f"删除 {len(removed)} 个附件")
    if modified:
        parts.append(f"修改 {len(modified)} 个附件")
    if failed_urls:
        parts.append(f"{len(failed_urls)} 个附件下载失败（未计入删除）")
    summary = "附件变更：" + "，".join(parts)

    total_changes = len(added) + len(removed) + len(modified)
    if total_changes >= 3:
        severity = ChangeSeverity.HIGH
    elif removed or modified:
        severity = ChangeSeverity.MEDIUM
    else:
        severity = ChangeSeverity.LOW

    change = Change(
        regulation_id=regulation.id,
        crawl_run_id=crawl_run_id,
        previous_snapshot_id=None,
        current_snapshot_id=snapshot.id,
        change_type=ChangeType.ATTACHMENT_UPDATE,
        severity=severity,
        title=f"附件更新: {regulation.title[:200]}",
        summary=summary,
        diff_content={
            "note": "附件变更，请查看附件列表",
        },
        diff_stats={
            "attachments_added": len(added),
            "attachments_removed": len(removed),
            "attachments_modified": len(modified),
        },
        changed_fields=[],
        attachment_changes=attachment_changes,
    )
    db.add(change)
    db.flush()
    _create_review_for_change(db, change, regulation)
    regulation.updated_at = datetime.utcnow()
    logger.info(f"Created ATTACHMENT_UPDATE change for {regulation.title[:80]}: {summary}")
    return change


def _extract_regulation_number(title: str, text: str) -> Optional[str]:
    patterns = [
        r"[（(]\d{4}[年）)][^)）]*号",
        r"第\s*\d+\s*号",
        r"\d{4}\s*年\s*第\s*\d+\s*号",
        r"令\s*第\s*\d+\s*号",
    ]
    for pattern in patterns:
        match = re.search(pattern, title + " " + text[:1000])
        if match:
            return match.group(0).strip()
    return None


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        from dateutil import parser
        return parser.parse(date_str)
    except (ValueError, TypeError):
        return None
