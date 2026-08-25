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


@shared_task(bind=True, name="app.tasks.crawler.crawl_source")
def crawl_source(self, source_id: str, triggered_by: str = "scheduled") -> dict:
    db = SessionLocal()
    robots_checker = RobotsChecker(settings.USER_AGENT)
    fetcher = HttpFetcher()
    storage = SnapshotStorage()
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
        base_domain = urlparse(source.base_url).netloc

        while urls_to_crawl:
            url, depth = urls_to_crawl.pop(0)
            if url in visited_urls:
                continue
            if depth > source.max_depth:
                continue
            visited_urls.add(url)

            if source.robots_txt_enabled and not robots_checker.can_fetch(url):
                logger.info(f"Skipping {url}: blocked by robots.txt")
                continue

            if not _is_url_allowed(url, source):
                continue

            if source.respect_crawl_delay:
                delay = robots_checker.get_crawl_delay(url) or settings.CRAWL_DELAY_SECONDS
                time.sleep(delay)

            try:
                result = fetcher.fetch(url, extra_headers=source.headers or {})
                if not result:
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

                regulation = _find_or_create_regulation(
                    db, source, url, parsed, result
                )

                previous_snapshot = (
                    db.query(Snapshot)
                    .filter(Snapshot.regulation_id == regulation.id)
                    .order_by(Snapshot.captured_at.desc())
                    .first()
                )

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

                if previous_snapshot and previous_snapshot.content_hash != parsed.content_hash:
                    change = _detect_change(
                        db, previous_snapshot, snapshot, regulation, parsed
                    )
                    if change:
                        stats["changes_detected"] += 1

                for att_info in parsed.attachments:
                    try:
                        att_result = fetcher.fetch_attachment(
                            att_info["url"], extra_headers=source.headers or {}
                        )
                        if att_result:
                            file_hash = hashlib.sha256(att_result.content).hexdigest()
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
                                    url=att_info["url"],
                                    content_type=att_result.content_type,
                                    file_size=len(att_result.content),
                                    file_hash=file_hash,
                                    storage_path=storage_path,
                                    extracted_text=extracted_text[:100000] if extracted_text else None,
                                    extraction_status="success" if extract_status == "success" else "error",
                                )
                                db.add(attachment)
                                stats["attachments_downloaded"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to download attachment {att_info['url']}: {e}")

                regulation.last_seen_at = datetime.utcnow()
                regulation.content_hash = parsed.content_hash

                if depth < source.max_depth:
                    for link in parsed.links:
                        link_url = link["url"]
                        parsed_link = urlparse(link_url)
                        if parsed_link.netloc == base_domain and link_url not in visited_urls:
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


def _is_url_allowed(url: str, source: Source) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()

    if source.excluded_paths:
        for excluded in source.excluded_paths:
            if excluded.lower() in path:
                return False

    if source.allowed_paths:
        return any(allowed.lower() in path for allowed in source.allowed_paths)

    return True


def _find_or_create_regulation(
    db: Session, source: Source, url: str, parsed, fetch_result
) -> Regulation:
    content_hash = parsed.content_hash

    regulation = (
        db.query(Regulation)
        .filter(
            Regulation.source_id == source.id,
            Regulation.url == url,
        )
        .first()
    )

    if regulation:
        return regulation

    reg_number = _extract_regulation_number(parsed.title, parsed.text)
    issuing_authority = parsed.metadata.get("author")
    publish_date = _parse_date(parsed.metadata.get("publish_date") or parsed.metadata.get("published_time"))

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

    return regulation


def _detect_change(
    db: Session,
    previous_snapshot: Snapshot,
    current_snapshot: Snapshot,
    regulation: Regulation,
    parsed,
) -> Optional[Change]:
    differ = DiffEngine()
    diff_result = differ.compute_text_diff(
        previous_snapshot.content_text or "",
        current_snapshot.content_text or "",
    )

    if diff_result["stats"]["lines_changed"] == 0:
        return None

    change_type = ChangeType.CONTENT_UPDATE
    title = f"内容更新: {regulation.title[:200]}"
    summary = f"检测到 {diff_result['stats']['lines_added']} 行新增, {diff_result['stats']['lines_removed']} 行删除"

    if not previous_snapshot:
        change_type = ChangeType.NEW
        title = f"新法规: {regulation.title[:200]}"

    severity_str = diff_result.get("severity", "medium")
    severity = ChangeSeverity(severity_str) if severity_str in [s.value for s in ChangeSeverity] else ChangeSeverity.MEDIUM

    change = Change(
        regulation_id=regulation.id,
        crawl_run_id=current_snapshot.crawl_run_id,
        previous_snapshot_id=previous_snapshot.id,
        current_snapshot_id=current_snapshot.id,
        change_type=change_type,
        severity=severity,
        title=title,
        summary=summary,
        diff_content={
            "unified_diff": diff_result["unified_diff"],
            "sections": diff_result["sections"],
        },
        diff_stats=diff_result["stats"],
        changed_fields=[],
    )
    db.add(change)
    db.flush()

    review = Review(
        change_id=change.id,
        regulation_id=regulation.id,
        status=ReviewStatus.PENDING,
        assigned_at=datetime.utcnow(),
        due_at=datetime.utcnow() + timedelta(days=3),
    )
    db.add(review)

    regulation.updated_at = datetime.utcnow()

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
