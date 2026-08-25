from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(ORMModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SourceBase(BaseModel):
    name: str
    org_type: str = "regulator"
    base_url: str
    homepage_url: str
    frequency: str = "daily"
    interval_minutes: int = 1440
    enabled: bool = True
    respect_robots: bool = True
    allowed_paths: list[str] = Field(default_factory=list)
    max_depth: int = 2
    description: str = ""


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: str | None = None
    org_type: str | None = None
    base_url: str | None = None
    homepage_url: str | None = None
    frequency: str | None = None
    interval_minutes: int | None = None
    enabled: bool | None = None
    respect_robots: bool | None = None
    allowed_paths: list[str] | None = None
    max_depth: int | None = None
    description: str | None = None


class SourceOut(ORMModel):
    id: int
    name: str
    org_type: str
    base_url: str
    homepage_url: str
    frequency: str
    interval_minutes: int
    enabled: bool
    respect_robots: bool
    allowed_paths: list
    max_depth: int
    description: str
    status: str
    last_crawled_at: datetime | None = None
    created_at: datetime


class CrawlRunOut(ORMModel):
    id: int
    source_id: int
    trigger_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    pages_fetched: int
    attachments_fetched: int
    changes_detected: int
    new_regulations: int
    error: str
    stats: dict


class CrawlRunDetail(CrawlRunOut):
    log: str
    source: SourceOut | None = None


class SnapshotOut(ORMModel):
    id: int
    document_id: int
    crawl_run_id: int
    fetched_at: datetime
    status_code: int
    content_type: str
    size_bytes: int
    content_hash: str
    text_hash: str
    title: str
    is_attachment: bool
    http_error: str


class DocumentOut(ORMModel):
    id: int
    source_id: int
    regulation_id: int | None = None
    parent_id: int | None = None
    url: str
    title: str
    doc_type: str
    content_type: str
    attachment_name: str
    content_hash: str
    text_hash: str
    first_seen_at: datetime
    last_seen_at: datetime


class RegulationOut(ORMModel):
    id: int
    title: str
    reg_number: str | None = None
    authority: str
    publish_date: str | None = None
    effective_date: str | None = None
    canonical_url: str
    status: str
    summary: str
    tags: list
    created_at: datetime
    updated_at: datetime


class ChangeOut(ORMModel):
    id: int
    regulation_id: int | None = None
    document_id: int
    source_id: int
    from_snapshot_id: int | None = None
    to_snapshot_id: int
    change_type: str
    status: str
    severity: str
    title: str
    summary: str
    changed_fields: dict
    detected_at: datetime
    decided_at: datetime | None = None


class ReviewTaskOut(ORMModel):
    id: int
    change_id: int
    status: str
    assignee_id: int | None = None
    decision: str
    comment: str
    created_at: datetime
    claimed_at: datetime | None = None
    decided_at: datetime | None = None


class ReviewDecisionRequest(BaseModel):
    decision: str
    comment: str = ""


class ImpactBase(BaseModel):
    change_id: int | None = None
    regulation_id: int | None = None
    risk_level: str = "medium"
    affected_teams: list[str] = Field(default_factory=list)
    affected_business: str = ""
    impact_summary: str = ""
    action_items: list[str] = Field(default_factory=list)
    status: str = "draft"


class ImpactCreate(ImpactBase):
    pass


class ImpactUpdate(BaseModel):
    risk_level: str | None = None
    affected_teams: list[str] | None = None
    affected_business: str | None = None
    impact_summary: str | None = None
    action_items: list[str] | None = None
    status: str | None = None


class ImpactOut(ORMModel):
    id: int
    change_id: int | None = None
    regulation_id: int | None = None
    analyst_id: int
    risk_level: str
    affected_teams: list
    affected_business: str
    impact_summary: str
    action_items: list
    status: str
    created_at: datetime
    updated_at: datetime


class SubscriptionBase(BaseModel):
    name: str
    channel: str = "inapp"
    event_types: list[str] = Field(default_factory=list)
    source_ids: list[int] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    destination: str = ""
    enabled: bool = True


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    name: str | None = None
    channel: str | None = None
    event_types: list[str] | None = None
    source_ids: list[int] | None = None
    keywords: list[str] | None = None
    destination: str | None = None
    enabled: bool | None = None


class SubscriptionOut(ORMModel):
    id: int
    user_id: int
    name: str
    channel: str
    event_types: list
    source_ids: list
    keywords: list
    destination: str
    enabled: bool
    created_at: datetime


class NotificationOut(ORMModel):
    id: int
    event_type: str
    title: str
    body: str
    data: dict
    is_read: bool
    send_status: str
    created_at: datetime
