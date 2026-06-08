"""
平台搜人与本地 runner 的 Pydantic 模型
"""
from pydantic import BaseModel, Field


class PlatformAccount(BaseModel):
    id: int | None = None
    platform: str
    status: str
    account_name: str | None = None
    auth_type: str | None = None
    has_credential: bool = False
    last_sync: str | None = None


class PlatformAccountUpsert(BaseModel):
    platform: str = Field(..., max_length=50)
    account_name: str | None = Field(None, max_length=120)
    credential: str | None = Field(None, description="Cookie、OAuth Token 或平台凭据")
    auth_type: str = Field("cookie", max_length=30)


class SourcingTaskCreate(BaseModel):
    position_id: int
    name: str | None = None
    platforms: list[str] = Field(default_factory=list)
    keywords: str | None = None
    locations: str | None = None
    min_score: int = Field(60, ge=0, le=100)
    target_count: int = Field(20, ge=1, le=200)
    auto_greeting: bool = False
    greeting_template: str | None = None


class SourcingTaskLogEntry(BaseModel):
    id: int
    level: str
    stage: str | None = None
    message: str
    detail: str | None = None
    created_at: str | None = None


class SourcingTaskScreenshotEntry(BaseModel):
    id: int
    stage: str | None = None
    caption: str | None = None
    source_url: str | None = None
    created_at: str | None = None


class SourcingOutreachEntry(BaseModel):
    id: int
    candidate_id: int
    candidate_name: str | None = None
    platform: str
    message: str
    review_status: str
    status: str
    profile_url: str | None = None
    failure_reason: str | None = None
    created_at: str | None = None
    approved_at: str | None = None
    sent_at: str | None = None


class SourcingOutreachAuditEntry(BaseModel):
    id: int
    outreach_id: int | None = None
    actor_type: str
    action: str
    detail: str | None = None
    created_at: str | None = None


class SourcingTaskResponse(BaseModel):
    id: int
    position_id: int
    position_title: str | None = None
    name: str
    platforms: list[str]
    keywords: str | None = None
    locations: str | None = None
    min_score: int
    target_count: int
    auto_greeting: bool
    greeting_template: str | None = None
    status: str
    status_detail: str | None = None
    pending_action: str | None = None
    current_platform: str | None = None
    imported_count: int
    reviewed_count: int
    deduped_count: int
    contacted_count: int
    pending_outreach_count: int
    approved_outreach_count: int
    failed_outreach_count: int
    screenshots_count: int
    logs_count: int
    last_error: str | None = None
    runner_name: str | None = None
    last_heartbeat: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str | None = None


class SourcingTaskDetail(SourcingTaskResponse):
    position_location: str | None = None
    position_department: str | None = None
    position_platform_url: str | None = None
    logs: list[SourcingTaskLogEntry] = Field(default_factory=list)
    screenshots: list[SourcingTaskScreenshotEntry] = Field(default_factory=list)
    outreach: list[SourcingOutreachEntry] = Field(default_factory=list)
    outreach_audit: list[SourcingOutreachAuditEntry] = Field(default_factory=list)


class TaskLaunchResponse(BaseModel):
    task_id: int
    status: str
    local_runner_url: str
    backend_base_url: str
    runner_token: str
    session_id: str
    expires_at: str


class OutreachReviewRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|skip)$")


class RunnerLaunchRequest(BaseModel):
    task_id: int
    backend_base_url: str
    runner_token: str
    session_id: str


class RunnerTaskLogCreate(BaseModel):
    level: str = Field("info", max_length=20)
    stage: str | None = Field(None, max_length=50)
    message: str = Field(..., min_length=1, max_length=1000)
    detail: str | None = Field(None, max_length=5000)


class RunnerTaskStatusUpdate(BaseModel):
    status: str = Field(..., max_length=30)
    status_detail: str | None = Field(None, max_length=1000)
    pending_action: str | None = Field(None, max_length=50)
    current_platform: str | None = Field(None, max_length=50)
    runner_name: str | None = Field(None, max_length=120)
    last_error: str | None = Field(None, max_length=5000)
    finished: bool = False


class RunnerScreenshotCreate(BaseModel):
    content_base64: str = Field(..., min_length=1, max_length=8_000_000)
    mime_type: str = Field("image/png", max_length=50, pattern="^image/(png|jpeg|webp)$")
    stage: str | None = Field(None, max_length=50)
    caption: str | None = Field(None, max_length=300)
    source_url: str | None = Field(None, max_length=500)


class RunnerEducationPayload(BaseModel):
    school: str | None = None
    degree: str | None = None
    major: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class RunnerExperiencePayload(BaseModel):
    company: str | None = None
    position: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class RunnerSkillPayload(BaseModel):
    skill_name: str
    proficiency: str | None = None


class RunnerCandidatePayload(BaseModel):
    platform: str = Field(..., max_length=50)
    external_id: str | None = Field(None, max_length=200)
    profile_url: str | None = Field(None, max_length=500)
    name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=100)
    gender: str | None = Field(None, max_length=10)
    age: int | None = Field(None, ge=0, le=100)
    current_company: str | None = Field(None, max_length=200)
    current_position: str | None = Field(None, max_length=200)
    work_years: int | None = Field(None, ge=0, le=60)
    self_evaluation: str | None = Field(None, max_length=2000)
    raw_text: str = Field(..., min_length=20, max_length=30000)
    educations: list[RunnerEducationPayload] = Field(default_factory=list)
    experiences: list[RunnerExperiencePayload] = Field(default_factory=list)
    skills: list[RunnerSkillPayload] = Field(default_factory=list)
    greeting_message: str | None = Field(None, max_length=2000)


class RunnerCandidateBatchUpsert(BaseModel):
    candidates: list[RunnerCandidatePayload] = Field(default_factory=list, max_length=50)


class RunnerCandidateBatchResult(BaseModel):
    imported_count: int
    duplicate_count: int
    filtered_count: int
    imported_candidates: list[dict] = Field(default_factory=list)
    duplicates: list[dict] = Field(default_factory=list)


class RunnerTaskContext(BaseModel):
    task: dict
    position: dict
    platforms: list[dict]
    pending_outreach: list[dict] = Field(default_factory=list)


class RunnerOutreachDeliveryUpdate(BaseModel):
    status: str = Field(..., pattern="^(sent|failed|replied)$")
    external_message_id: str | None = Field(None, max_length=200)
    external_thread_id: str | None = Field(None, max_length=200)
    detail: str | None = None
    payload: dict | None = None
