"""
面试管理 Schemas
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


# ---------- 基础 ----------

class InterviewBase(BaseModel):
    candidate_id: int
    position_id: Optional[int] = None
    title: Optional[str] = None
    platform: str = "feishu"
    meeting_url: str
    scheduled_at: datetime
    duration_minutes: int = 60
    status: str = "已预约"


class InterviewCreate(InterviewBase):
    pass


class InterviewUpdate(BaseModel):
    title: Optional[str] = None
    platform: Optional[str] = None
    meeting_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None


# ---------- 候选人 / 岗位 / 创建人简要信息（用于列表 / 详情联表展示） ----------

class _MiniUser(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class _MiniCandidate(BaseModel):
    id: int
    name: str
    current_company: Optional[str] = None
    current_position: Optional[str] = None
    work_years: Optional[int] = None

    class Config:
        from_attributes = True


class _MiniPosition(BaseModel):
    id: int
    title: str
    department: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- 响应 ----------

class InterviewResponse(BaseModel):
    id: int
    candidate_id: int
    position_id: Optional[int] = None
    user_id: int
    title: Optional[str] = None
    platform: str
    meeting_url: str
    scheduled_at: datetime
    duration_minutes: int
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    candidate: Optional[_MiniCandidate] = None
    position: Optional[_MiniPosition] = None
    creator: Optional[_MiniUser] = None
    # 仅详情接口返回该字段；列表接口为 None
    record: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class InterviewListItem(InterviewResponse):
    """列表项：在 InterviewResponse 基础上预留扩展位"""
    pass


# ---------- 转写 / 总结 / 笔记 ----------

class InterviewTranscriptUpdate(BaseModel):
    transcript: str


class InterviewNotesUpdate(BaseModel):
    notes: str


class InterviewSummaryRequest(BaseModel):
    """手动触发 AI 总结时的可选入参"""
    extra_context: Optional[str] = Field(default=None, description="HR 额外提示词")


class InterviewSummaryResponse(BaseModel):
    interview_id: int
    summary: Dict[str, Any]
    is_mock: bool = False
    summarized_at: Optional[datetime] = None


# ---------- 演示用：内置转写剧本 ----------

class MockScriptLine(BaseModel):
    speaker: str          # "面试官" / "候选人"
    text: str


class MockScriptResponse(BaseModel):
    interview_id: int
    script: List[MockScriptLine]


# ---------- 通用 ----------

class MessageResponse(BaseModel):
    message: str
    interview_id: Optional[int] = None
