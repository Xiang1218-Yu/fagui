"""SQLAlchemy ORM models for the regulation-change intelligence platform."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SourceType(str, enum.Enum):
    regulator = "regulator"          # 监管网站
    association = "association"       # 行业协会
    consultation = "consultation"    # 公开征求意见


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    skipped = "skipped"


class ChangeType(str, enum.Enum):
    new = "new"                      # 新增法规
    body_changed = "body_changed"    # 正文变化
    attachment_changed = "attachment_changed"  # 附件变化
    metadata_changed = "metadata_changed"      # 修订记录/元数据变化


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    dismissed = "dismissed"


class ImpactLevel(str, enum.Enum):
    unassessed = "unassessed"
    low = "low"
    medium = "medium"
    high = "high"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128), default="")
    role: Mapped[str] = mapped_column(String(32), default="analyst")  # admin | analyst
    password_hash: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Source(Base):
    """A whitelisted source that the crawler is allowed to collect from."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), default=SourceType.regulator)
    # host whitelist – comma separated hosts that this source may fetch
    allowed_hosts: Mapped[str] = mapped_column(String(1000), default="")
    frequency_minutes: Mapped[int] = mapped_column(Integer, default=1440)  # crawl frequency
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    respect_robots: Mapped[bool] = mapped_column(Boolean, default=True)
    fetch_attachments: Mapped[bool] = mapped_column(Boolean, default=True)
    follow_links: Mapped[bool] = mapped_column(Boolean, default=True)   # crawl article links on the entry page
    max_links: Mapped[int] = mapped_column(Integer, default=20)         # cap of content links per crawl
    link_selector: Mapped[str] = mapped_column(String(200), default="") # optional CSS selector for article links
    notes: Mapped[str] = mapped_column(Text, default="")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    runs: Mapped[list["CrawlRun"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class CrawlRun(Base):
    """A single execution of the crawler for a source."""

    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.pending)
    trigger: Mapped[str] = mapped_column(String(32), default="manual")  # manual | scheduled
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    attachments_fetched: Mapped[int] = mapped_column(Integer, default=0)
    changes_detected: Mapped[int] = mapped_column(Integer, default=0)
    robots_blocked: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped["Source"] = relationship(back_populates="runs")
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Document(Base):
    """A logical regulation document tracked across crawls (dedup / merge target)."""

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source_id", "url", name="uq_document_source_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    title: Mapped[str] = mapped_column(String(500), default="")
    # normalized key used to merge the same regulation coming from multiple sources
    dedup_key: Mapped[str] = mapped_column(String(255), index=True, default="")
    regulation_id: Mapped[int | None] = mapped_column(
        ForeignKey("regulations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    latest_body_hash: Mapped[str] = mapped_column(String(64), default="")
    latest_snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_level: Mapped[ImpactLevel] = mapped_column(Enum(ImpactLevel), default=ImpactLevel.unassessed)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped["Source"] = relationship(back_populates="documents")
    regulation: Mapped["Regulation | None"] = relationship(back_populates="documents")
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Regulation(Base):
    """A canonical regulation that may be reported by several sources/documents."""

    __tablename__ = "regulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    dedup_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    identifier: Mapped[str] = mapped_column(String(255), default="")  # 文号 / 编号
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documents: Mapped[list["Document"]] = relationship(back_populates="regulation")


class Snapshot(Base):
    """A traceable snapshot of a page or attachment captured during a run."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("crawl_runs.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="page")  # page | attachment
    url: Mapped[str] = mapped_column(String(1000))
    filename: Mapped[str] = mapped_column(String(300), default="")
    content_type: Mapped[str] = mapped_column(String(120), default="")
    http_status: Mapped[int] = mapped_column(Integer, default=0)
    raw_path: Mapped[str] = mapped_column(String(600), default="")   # stored raw bytes path
    text_path: Mapped[str] = mapped_column(String(600), default="")  # extracted text path
    content_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    text_excerpt: Mapped[str] = mapped_column(Text, default="")
    revision_note: Mapped[str] = mapped_column(String(500), default="")  # 修订记录/发布日期等元数据
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped["CrawlRun"] = relationship(back_populates="snapshots")
    document: Mapped["Document"] = relationship(back_populates="snapshots")


class ChangeEvent(Base):
    """A detected change between two snapshots of a document."""

    __tablename__ = "change_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("crawl_runs.id", ondelete="CASCADE"), index=True)
    change_type: Mapped[ChangeType] = mapped_column(Enum(ChangeType), default=ChangeType.body_changed)
    old_snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    diff_text: Mapped[str] = mapped_column(Text, default="")
    similarity: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    review: Mapped["ReviewItem | None"] = relationship(back_populates="change", uselist=False)


class ReviewItem(Base):
    """A human-review record for a detected change."""

    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    change_id: Mapped[int] = mapped_column(ForeignKey("change_events.id", ondelete="CASCADE"), unique=True)
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.pending)
    impact_level: Mapped[ImpactLevel] = mapped_column(Enum(ImpactLevel), default=ImpactLevel.unassessed)
    assignee: Mapped[str] = mapped_column(String(64), default="")
    decision_note: Mapped[str] = mapped_column(Text, default="")
    impact_note: Mapped[str] = mapped_column(Text, default="")           # 影响研判结论
    affected_business: Mapped[str] = mapped_column(String(500), default="")  # 受影响业务
    reviewed_by: Mapped[str] = mapped_column(String(64), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    change: Mapped["ChangeEvent"] = relationship(back_populates="review")


class Subscription(Base):
    """An analyst subscription to changes matching a filter."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    subscriber: Mapped[str] = mapped_column(String(64), default="")
    keyword: Mapped[str] = mapped_column(String(200), default="")
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    min_impact: Mapped[ImpactLevel] = mapped_column(Enum(ImpactLevel), default=ImpactLevel.low)
    channel: Mapped[str] = mapped_column(String(32), default="inapp")  # inapp | email
    email: Mapped[str] = mapped_column(String(200), default="")        # recipient for email channel
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    """A notification generated for a subscription when a change matches."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    change_id: Mapped[int | None] = mapped_column(
        ForeignKey("change_events.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text, default="")
    channel: Mapped[str] = mapped_column(String(32), default="inapp")       # inapp | email
    delivery_status: Mapped[str] = mapped_column(String(32), default="created")  # created|sent|failed|skipped
    delivery_detail: Mapped[str] = mapped_column(String(500), default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
