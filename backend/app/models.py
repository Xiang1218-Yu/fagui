import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, Enum,
    ForeignKey, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class SourceStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class SourceType(str, enum.Enum):
    REGULATORY = "regulatory"
    ASSOCIATION = "association"
    CONSULTATION = "consultation"
    OTHER = "other"


class CrawlStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class RegulationStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    AMENDED = "amended"
    REPEALED = "repealed"
    SUPERSEDED = "superseded"


class ChangeType(str, enum.Enum):
    NEW = "new"
    CONTENT_UPDATE = "content_update"
    ATTACHMENT_UPDATE = "attachment_update"
    STATUS_CHANGE = "status_change"
    REPEAL = "repeal"


class ChangeSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"


class ImpactLevel(str, enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(256), nullable=False)
    url = Column(String(1024), nullable=False)
    base_url = Column(String(512), nullable=False, index=True)
    source_type = Column(Enum(SourceType), nullable=False, default=SourceType.REGULATORY)
    status = Column(Enum(SourceStatus), nullable=False, default=SourceStatus.ACTIVE)
    crawl_frequency_minutes = Column(Integer, nullable=False, default=1440)
    max_depth = Column(Integer, nullable=False, default=2)
    allowed_paths = Column(JSON, default=list)
    excluded_paths = Column(JSON, default=list)
    selector_config = Column(JSON, default=dict)
    robots_txt_enabled = Column(Boolean, default=True)
    respect_crawl_delay = Column(Boolean, default=True)
    headers = Column(JSON, default=dict)
    description = Column(Text)
    last_crawled_at = Column(DateTime(timezone=True))
    last_error = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(256))

    crawl_runs = relationship("CrawlRun", back_populates="source", cascade="all, delete-orphan")
    regulations = relationship("Regulation", back_populates="source")
    subscriptions = relationship("Subscription", back_populates="source")

    __table_args__ = (
        UniqueConstraint("url", name="uq_source_url"),
        Index("ix_source_status_type", "status", "source_type"),
    )


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    source_id = Column(String(36), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(CrawlStatus), nullable=False, default=CrawlStatus.PENDING)
    triggered_by = Column(String(64), nullable=False, default="scheduled")
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    pages_crawled = Column(Integer, default=0)
    pages_failed = Column(Integer, default=0)
    attachments_downloaded = Column(Integer, default=0)
    new_regulations = Column(Integer, default=0)
    changes_detected = Column(Integer, default=0)
    error_message = Column(Text)
    logs = Column(JSON, default=list)
    celery_task_id = Column(String(256))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    source = relationship("Source", back_populates="crawl_runs")
    snapshots = relationship("Snapshot", back_populates="crawl_run")
    changes = relationship("Change", back_populates="crawl_run")


class Regulation(Base):
    __tablename__ = "regulations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False, index=True)
    canonical_id = Column(String(36), index=True)
    title = Column(String(1024), nullable=False)
    url = Column(String(2048), nullable=False)
    regulation_number = Column(String(256), index=True)
    issuing_authority = Column(String(512))
    publish_date = Column(DateTime(timezone=True))
    effective_date = Column(DateTime(timezone=True))
    status = Column(Enum(RegulationStatus), nullable=False, default=RegulationStatus.PUBLISHED)
    summary = Column(Text)
    content_hash = Column(String(128), index=True)
    metadata_json = Column(JSON, default=dict)
    is_primary = Column(Boolean, default=True)
    merge_group_id = Column(String(36), index=True)
    merge_confidence = Column(Float)
    first_seen_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    source = relationship("Source", back_populates="regulations")
    snapshots = relationship("Snapshot", back_populates="regulation", cascade="all, delete-orphan")
    changes = relationship("Change", back_populates="regulation", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="regulation", cascade="all, delete-orphan")
    impact_assessments = relationship("ImpactAssessment", back_populates="regulation", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="regulation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_regulation_source_hash", "source_id", "content_hash"),
    )


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    regulation_id = Column(String(36), ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False, index=True)
    crawl_run_id = Column(String(36), ForeignKey("crawl_runs.id"), nullable=False, index=True)
    url = Column(String(2048), nullable=False)
    content_text = Column(Text)
    content_html = Column(Text)
    content_hash = Column(String(128), nullable=False, index=True)
    http_status = Column(Integer)
    response_headers = Column(JSON, default=dict)
    metadata_json = Column(JSON, default=dict)
    word_count = Column(Integer, default=0)
    snapshot_path = Column(String(1024))
    captured_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    regulation = relationship("Regulation", back_populates="snapshots")
    crawl_run = relationship("CrawlRun", back_populates="snapshots")
    attachments = relationship("Attachment", back_populates="snapshot")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    regulation_id = Column(String(36), ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id = Column(String(36), ForeignKey("snapshots.id"), nullable=True, index=True)
    filename = Column(String(512), nullable=False)
    url = Column(String(2048), nullable=False)
    content_type = Column(String(128))
    file_size = Column(Integer)
    file_hash = Column(String(128), index=True)
    storage_path = Column(String(1024))
    extracted_text = Column(Text)
    extraction_status = Column(String(32), default="pending")
    extraction_error = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    regulation = relationship("Regulation", back_populates="attachments")
    snapshot = relationship("Snapshot", back_populates="attachments")


class Change(Base):
    __tablename__ = "changes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    regulation_id = Column(String(36), ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False, index=True)
    crawl_run_id = Column(String(36), ForeignKey("crawl_runs.id"), nullable=False, index=True)
    previous_snapshot_id = Column(String(36), ForeignKey("snapshots.id"), nullable=True)
    current_snapshot_id = Column(String(36), ForeignKey("snapshots.id"), nullable=True)
    change_type = Column(Enum(ChangeType), nullable=False)
    severity = Column(Enum(ChangeSeverity), nullable=False, default=ChangeSeverity.MEDIUM)
    title = Column(String(1024), nullable=False)
    summary = Column(Text)
    diff_content = Column(JSON, default=dict)
    diff_stats = Column(JSON, default=dict)
    changed_fields = Column(JSON, default=list)
    attachment_changes = Column(JSON, default=list)
    is_reviewed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    regulation = relationship("Regulation", back_populates="changes", foreign_keys=[regulation_id])
    crawl_run = relationship("CrawlRun", back_populates="changes")
    review = relationship("Review", back_populates="change", uselist=False, cascade="all, delete-orphan")
    impact_assessment = relationship("ImpactAssessment", back_populates="change", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_change_type_reviewed", "change_type", "is_reviewed"),
        Index("ix_change_severity_created", "severity", "created_at"),
    )


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    change_id = Column(String(36), ForeignKey("changes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    regulation_id = Column(String(36), ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(ReviewStatus), nullable=False, default=ReviewStatus.PENDING)
    reviewer_id = Column(String(256))
    reviewer_name = Column(String(256))
    decision = Column(Text)
    notes = Column(Text)
    tags = Column(JSON, default=list)
    assigned_at = Column(DateTime(timezone=True))
    claimed_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    due_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    change = relationship("Change", back_populates="review")
    regulation = relationship("Regulation", back_populates="reviews")


class ImpactAssessment(Base):
    __tablename__ = "impact_assessments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    regulation_id = Column(String(36), ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False, index=True)
    change_id = Column(String(36), ForeignKey("changes.id", ondelete="CASCADE"), nullable=True)
    assessor_id = Column(String(256))
    assessor_name = Column(String(256))
    overall_level = Column(Enum(ImpactLevel), nullable=False, default=ImpactLevel.MEDIUM)
    affected_teams = Column(JSON, default=list)
    affected_systems = Column(JSON, default=list)
    affected_products = Column(JSON, default=list)
    compliance_areas = Column(JSON, default=list)
    analysis = Column(Text)
    required_actions = Column(Text)
    deadline = Column(DateTime(timezone=True))
    estimated_effort = Column(String(64))
    status = Column(String(32), default="draft")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    regulation = relationship("Regulation", back_populates="impact_assessments")
    change = relationship("Change", back_populates="impact_assessment")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(256), nullable=False)
    user_id = Column(String(256), nullable=False, index=True)
    user_name = Column(String(256))
    user_email = Column(String(512))
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=True)
    keywords = Column(JSON, default=list)
    severity_filter = Column(JSON, default=list)
    channels = Column(JSON, default=lambda: [NotificationChannel.IN_APP.value])
    is_active = Column(Boolean, default=True)
    last_notified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    source = relationship("Source", back_populates="subscriptions")
    notifications = relationship("Notification", back_populates="subscription", cascade="all, delete-orphan")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    change_id = Column(String(36), ForeignKey("changes.id", ondelete="SET NULL"), nullable=True)
    channel = Column(Enum(NotificationChannel), nullable=False)
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING)
    title = Column(String(1024), nullable=False)
    content = Column(Text)
    recipient = Column(String(512))
    sent_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    subscription = relationship("Subscription", back_populates="notifications")


class RegulationMergeLog(Base):
    __tablename__ = "regulation_merge_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    primary_regulation_id = Column(String(36), ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False, index=True)
    duplicate_regulation_id = Column(String(36), ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    match_reasons = Column(JSON, default=list)
    merged_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    merged_by = Column(String(64), default="auto")
