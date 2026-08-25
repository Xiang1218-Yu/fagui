from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------- Source ----------
class SourceCreate(BaseModel):
    name: str
    base_url: str
    allowed_paths: list[str] = Field(default_factory=list)
    frequency_minutes: int = 1440
    enabled: bool = True
    respect_robots: bool = True
    max_pages: int = 50


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    allowed_paths: Optional[list[str]] = None
    frequency_minutes: Optional[int] = None
    enabled: Optional[bool] = None
    respect_robots: Optional[bool] = None
    max_pages: Optional[int] = None


class SourceOut(BaseModel):
    id: int
    name: str
    base_url: str
    allowed_paths: list[str]
    frequency_minutes: int
    enabled: bool
    respect_robots: bool
    max_pages: int
    last_run_at: Optional[datetime]
    created_at: datetime


class RunQueued(BaseModel):
    run_id: Optional[int]
    status: str


# ---------- Run ----------
class RunOut(BaseModel):
    id: int
    source_id: int
    source_name: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    pages_fetched: int
    attachments_fetched: int
    changes_detected: int
    error: Optional[str]


# ---------- Change ----------
class ChangeListItem(BaseModel):
    id: int
    regulation_id: int
    regulation_title: str
    document_url: str
    source_name: str
    change_type: str
    status: str
    diff_summary: str
    detected_at: datetime


class AttachmentOut(BaseModel):
    id: int
    url: str
    filename: str
    content_hash: str
    created_at: datetime


class AttachmentVersion(BaseModel):
    id: int
    url: str
    filename: str
    content_hash: str
    created_at: datetime
    text: Optional[str]


class AttachmentDiff(BaseModel):
    old: Optional["AttachmentVersion"]
    new: Optional["AttachmentVersion"]
    unified_diff: Optional[str]


class ReviewOut(BaseModel):
    reviewer: str
    decision: str
    comment: Optional[str]
    decided_at: datetime


class ChangeDetail(ChangeListItem):
    old_text: Optional[str]
    new_text: Optional[str]
    unified_diff: Optional[str]
    attachments: list[AttachmentOut]
    attachment_diff: Optional[AttachmentDiff]
    review: Optional[ReviewOut]


class ReviewCreate(BaseModel):
    reviewer: str
    decision: Literal["confirmed", "dismissed"]
    comment: Optional[str] = None


# ---------- Regulation ----------
class RegulationOut(BaseModel):
    id: int
    canonical_title: str
    regulation_no: Optional[str]
    authority: Optional[str]
    change_count: int
    pending_count: int
    latest_change_at: Optional[datetime]


class RegulationDetail(RegulationOut):
    changes: list[ChangeListItem]


# ---------- Assessment ----------
class AssessmentCreate(BaseModel):
    change_id: int
    business_area: str
    impact_level: Literal["high", "medium", "low"]
    analysis: str
    recommendation: Optional[str] = None
    created_by: str


class AssessmentUpdate(BaseModel):
    business_area: Optional[str] = None
    impact_level: Optional[Literal["high", "medium", "low"]] = None
    analysis: Optional[str] = None
    recommendation: Optional[str] = None


class AssessmentOut(BaseModel):
    id: int
    change_id: int
    regulation_title: str
    business_area: str
    impact_level: str
    analysis: str
    recommendation: Optional[str]
    created_by: str
    created_at: datetime


# ---------- Subscription ----------
class SubscriptionCreate(BaseModel):
    name: str
    channel: Literal["webhook", "email"]
    target: str
    keywords: list[str] = Field(default_factory=list)
    source_ids: list[int] = Field(default_factory=list)
    enabled: bool = True


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    channel: Optional[Literal["webhook", "email"]] = None
    target: Optional[str] = None
    keywords: Optional[list[str]] = None
    source_ids: Optional[list[int]] = None
    enabled: Optional[bool] = None


class SubscriptionOut(BaseModel):
    id: int
    name: str
    channel: str
    target: str
    keywords: list[str]
    source_ids: list[int]
    enabled: bool
    created_at: datetime


# ---------- Auth ----------
Role = Literal["admin", "analyst", "viewer"]


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime


class TokenResponse(BaseModel):
    token: str
    user: UserOut


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: Role


# ---------- Notification ----------
class NotificationOut(BaseModel):
    id: int
    subscription_id: int
    subscription_name: str
    change_id: int
    change_title: str
    channel: str
    status: str
    error: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]
