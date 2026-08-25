from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, HttpUrl


class SourceBase(BaseModel):
    name: str = Field(..., max_length=256)
    url: str = Field(..., max_length=1024)
    base_url: str = Field(..., max_length=512)
    source_type: str = "regulatory"
    crawl_frequency_minutes: int = Field(1440, ge=5, le=10080)
    max_depth: int = Field(2, ge=0, le=10)
    allowed_paths: list[str] = []
    excluded_paths: list[str] = []
    selector_config: dict[str, Any] = {}
    robots_txt_enabled: bool = True
    respect_crawl_delay: bool = True
    headers: dict[str, str] = {}
    description: Optional[str] = None


class SourceCreate(SourceBase):
    created_by: Optional[str] = None


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    base_url: Optional[str] = None
    source_type: Optional[str] = None
    status: Optional[str] = None
    crawl_frequency_minutes: Optional[int] = Field(None, ge=5, le=10080)
    max_depth: Optional[int] = Field(None, ge=0, le=10)
    allowed_paths: Optional[list[str]] = None
    excluded_paths: Optional[list[str]] = None
    selector_config: Optional[dict[str, Any]] = None
    robots_txt_enabled: Optional[bool] = None
    respect_crawl_delay: Optional[bool] = None
    headers: Optional[dict[str, str]] = None
    description: Optional[str] = None


class SourceResponse(SourceBase):
    id: str
    status: str
    last_crawled_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


class CrawlRunResponse(BaseModel):
    id: str
    source_id: str
    status: str
    triggered_by: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pages_crawled: int
    pages_failed: int
    attachments_downloaded: int
    new_regulations: int
    changes_detected: int
    error_message: Optional[str] = None
    celery_task_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RegulationResponse(BaseModel):
    id: str
    source_id: str
    canonical_id: Optional[str] = None
    title: str
    url: str
    regulation_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    publish_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    status: str
    summary: Optional[str] = None
    content_hash: Optional[str] = None
    is_primary: bool
    merge_group_id: Optional[str] = None
    merge_confidence: Optional[float] = None
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime
    source_name: Optional[str] = None

    class Config:
        from_attributes = True


class SnapshotResponse(BaseModel):
    id: str
    regulation_id: str
    crawl_run_id: str
    url: str
    content_hash: str
    http_status: Optional[int] = None
    word_count: int
    snapshot_path: Optional[str] = None
    captured_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class AttachmentResponse(BaseModel):
    id: str
    regulation_id: str
    snapshot_id: Optional[str] = None
    filename: str
    url: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    extraction_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChangeResponse(BaseModel):
    id: str
    regulation_id: str
    crawl_run_id: str
    previous_snapshot_id: Optional[str] = None
    current_snapshot_id: Optional[str] = None
    change_type: str
    severity: str
    title: str
    summary: Optional[str] = None
    diff_stats: dict[str, Any] = {}
    changed_fields: list[Any] = []
    attachment_changes: Any = []
    is_reviewed: bool
    created_at: datetime
    regulation_title: Optional[str] = None
    source_name: Optional[str] = None
    review_status: Optional[str] = None
    review_id: Optional[str] = None

    class Config:
        from_attributes = True


class ChangeDetailResponse(ChangeResponse):
    diff_content: dict[str, Any] = {}
    regulation: Optional[RegulationResponse] = None


class ReviewCreate(BaseModel):
    status: str = "in_review"
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    notes: Optional[str] = None


class ReviewUpdate(BaseModel):
    status: Optional[str] = None
    decision: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None


class ReviewResponse(BaseModel):
    id: str
    change_id: str
    regulation_id: str
    status: str
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    decision: Optional[str] = None
    notes: Optional[str] = None
    tags: list[str] = []
    assigned_at: Optional[datetime] = None
    claimed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    change: Optional[ChangeResponse] = None

    class Config:
        from_attributes = True


class ImpactAssessmentCreate(BaseModel):
    change_id: Optional[str] = None
    overall_level: str = "medium"
    affected_teams: list[str] = []
    affected_systems: list[str] = []
    affected_products: list[str] = []
    compliance_areas: list[str] = []
    analysis: Optional[str] = None
    required_actions: Optional[str] = None
    deadline: Optional[datetime] = None
    estimated_effort: Optional[str] = None
    assessor_id: Optional[str] = None
    assessor_name: Optional[str] = None


class ImpactAssessmentUpdate(BaseModel):
    overall_level: Optional[str] = None
    affected_teams: Optional[list[str]] = None
    affected_systems: Optional[list[str]] = None
    affected_products: Optional[list[str]] = None
    compliance_areas: Optional[list[str]] = None
    analysis: Optional[str] = None
    required_actions: Optional[str] = None
    deadline: Optional[datetime] = None
    estimated_effort: Optional[str] = None
    status: Optional[str] = None


class ImpactAssessmentResponse(BaseModel):
    id: str
    regulation_id: str
    change_id: Optional[str] = None
    assessor_id: Optional[str] = None
    assessor_name: Optional[str] = None
    overall_level: str
    affected_teams: list[str] = []
    affected_systems: list[str] = []
    affected_products: list[str] = []
    compliance_areas: list[str] = []
    analysis: Optional[str] = None
    required_actions: Optional[str] = None
    deadline: Optional[datetime] = None
    estimated_effort: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    name: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    source_id: Optional[str] = None
    keywords: list[str] = []
    severity_filter: list[str] = []
    channels: list[str] = ["in_app"]


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[list[str]] = None
    severity_filter: Optional[list[str]] = None
    channels: Optional[list[str]] = None
    is_active: Optional[bool] = None
    source_id: Optional[str] = None


class SubscriptionResponse(BaseModel):
    id: str
    name: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    source_id: Optional[str] = None
    keywords: list[str] = []
    severity_filter: list[str] = []
    channels: list[str] = []
    is_active: bool
    last_notified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: str
    subscription_id: str
    change_id: Optional[str] = None
    channel: str
    status: str
    title: str
    content: Optional[str] = None
    recipient: Optional[str] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlTriggerRequest(BaseModel):
    source_id: Optional[str] = None
    triggered_by: str = "manual"


class DiffResult(BaseModel):
    before_text: str
    after_text: str
    diff_html: str
    stats: dict[str, int]
    changed_sections: list[dict[str, Any]]


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class DashboardStats(BaseModel):
    total_sources: int
    active_sources: int
    total_regulations: int
    pending_reviews: int
    changes_today: int
    changes_this_week: int
    recent_crawls: list[dict[str, Any]]
    severity_breakdown: dict[str, int]
