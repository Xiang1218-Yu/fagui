"""Pydantic schemas (request/response DTOs)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.models import (
    ChangeType,
    ImpactLevel,
    ReviewStatus,
    RunStatus,
    SourceType,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Source ----------
class SourceBase(BaseModel):
    name: str
    url: str
    source_type: SourceType = SourceType.regulator
    allowed_hosts: str = ""
    frequency_minutes: int = 1440
    enabled: bool = True
    respect_robots: bool = True
    fetch_attachments: bool = True
    follow_links: bool = True
    max_links: int = 20
    link_selector: str = ""
    notes: str = ""


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    source_type: SourceType | None = None
    allowed_hosts: str | None = None
    frequency_minutes: int | None = None
    enabled: bool | None = None
    respect_robots: bool | None = None
    fetch_attachments: bool | None = None
    follow_links: bool | None = None
    max_links: int | None = None
    link_selector: str | None = None
    notes: str | None = None


class SourceOut(ORMModel, SourceBase):
    id: int
    last_run_at: datetime | None = None
    created_at: datetime


# ---------- Crawl run ----------
class CrawlRunOut(ORMModel):
    id: int
    source_id: int
    status: RunStatus
    trigger: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pages_fetched: int
    attachments_fetched: int
    changes_detected: int
    robots_blocked: int
    message: str
    created_at: datetime


# ---------- Snapshot ----------
class SnapshotOut(ORMModel):
    id: int
    run_id: int
    document_id: int
    kind: str
    url: str
    filename: str
    content_type: str
    http_status: int
    content_hash: str
    text_excerpt: str
    captured_at: datetime


# ---------- Document / Regulation ----------
class DocumentOut(ORMModel):
    id: int
    source_id: int
    url: str
    title: str
    dedup_key: str
    regulation_id: int | None = None
    latest_body_hash: str
    impact_level: ImpactLevel
    first_seen_at: datetime
    last_seen_at: datetime


class RegulationOut(ORMModel):
    id: int
    title: str
    dedup_key: str
    identifier: str
    created_at: datetime


# ---------- Change ----------
class ChangeOut(ORMModel):
    id: int
    document_id: int
    run_id: int
    change_type: ChangeType
    old_snapshot_id: int | None = None
    new_snapshot_id: int | None = None
    summary: str
    similarity: float
    created_at: datetime


class ChangeDetail(ChangeOut):
    diff_text: str
    document: DocumentOut | None = None


# ---------- Review ----------
class ReviewOut(ORMModel):
    id: int
    change_id: int
    status: ReviewStatus
    impact_level: ImpactLevel
    assignee: str
    decision_note: str
    impact_note: str
    affected_business: str
    reviewed_by: str
    reviewed_at: datetime | None = None
    created_at: datetime
    change: ChangeOut | None = None


class ReviewDecision(BaseModel):
    status: ReviewStatus
    impact_level: ImpactLevel = ImpactLevel.unassessed
    decision_note: str = ""
    impact_note: str = ""
    affected_business: str = ""
    reviewed_by: str = ""


class ReviewAssign(BaseModel):
    assignee: str


# ---------- Subscription / Notification ----------
class SubscriptionBase(BaseModel):
    name: str
    subscriber: str = ""
    keyword: str = ""
    source_id: int | None = None
    min_impact: ImpactLevel = ImpactLevel.low
    channel: str = "inapp"
    email: str = ""
    enabled: bool = True


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionOut(ORMModel, SubscriptionBase):
    id: int
    created_at: datetime


class NotificationOut(ORMModel):
    id: int
    subscription_id: int | None = None
    change_id: int | None = None
    title: str
    body: str
    channel: str
    delivery_status: str
    delivery_detail: str
    is_read: bool
    created_at: datetime


# ---------- Dashboard ----------
class DashboardStats(BaseModel):
    sources: int
    active_sources: int
    documents: int
    regulations: int
    pending_reviews: int
    changes_last_7d: int
    unread_notifications: int
