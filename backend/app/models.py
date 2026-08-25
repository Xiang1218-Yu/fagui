from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    """统一的 UTC 当前时间（naive，便于 sqlite/PG 一致存储）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    allowed_paths: Mapped[list] = mapped_column(JSON, default=list)
    frequency_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    respect_robots: Mapped[bool] = mapped_column(Boolean, default=True)
    max_pages: Mapped[int] = mapped_column(Integer, default=50)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    runs: Mapped[list["CrawlRun"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    attachments_fetched: Mapped[int] = mapped_column(Integer, default=0)
    changes_detected: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    source: Mapped[Source] = relationship(back_populates="runs")
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source_id", "url", name="uq_documents_source_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    title: Mapped[str] = mapped_column(String(500), default="")
    latest_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    source: Mapped[Source] = relationship(back_populates="documents")
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    changes: Mapped[list["Change"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("crawl_runs.id"))
    raw_path: Mapped[str] = mapped_column(String(1000))
    text_path: Mapped[str] = mapped_column(String(1000))
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="snapshots")
    run: Mapped[CrawlRun] = relationship(back_populates="snapshots")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    filename: Mapped[str] = mapped_column(String(500), default="")
    content_hash: Mapped[str] = mapped_column(String(64))
    snapshot_path: Mapped[str] = mapped_column(String(1000))
    text_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="attachments")


class Regulation(Base):
    __tablename__ = "regulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_title: Mapped[str] = mapped_column(String(500))
    regulation_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    authority: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    changes: Mapped[list["Change"]] = relationship(back_populates="regulation", cascade="all, delete-orphan")


class Change(Base):
    __tablename__ = "changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    regulation_id: Mapped[int] = mapped_column(ForeignKey("regulations.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    change_type: Mapped[str] = mapped_column(String(30))
    old_snapshot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("snapshots.id"), nullable=True)
    new_snapshot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("snapshots.id"), nullable=True)
    diff_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending_review")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    regulation: Mapped[Regulation] = relationship(back_populates="changes")
    document: Mapped[Document] = relationship(back_populates="changes")
    reviews: Mapped[list["Review"]] = relationship(back_populates="change", cascade="all, delete-orphan")
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="change", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="change", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    change_id: Mapped[int] = mapped_column(ForeignKey("changes.id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(100))
    decision: Mapped[str] = mapped_column(String(20))
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    change: Mapped[Change] = relationship(back_populates="reviews")


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    change_id: Mapped[int] = mapped_column(ForeignKey("changes.id"), index=True)
    business_area: Mapped[str] = mapped_column(String(200))
    impact_level: Mapped[str] = mapped_column(String(10))
    analysis: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    change: Mapped[Change] = relationship(back_populates="assessments")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(20))
    target: Mapped[str] = mapped_column(String(500))
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    source_ids: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    notifications: Mapped[list["Notification"]] = relationship(back_populates="subscription", cascade="all, delete-orphan")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    change_id: Mapped[int] = mapped_column(ForeignKey("changes.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    subscription: Mapped[Subscription] = relationship(back_populates="notifications")
    change: Mapped[Change] = relationship(back_populates="notifications")
