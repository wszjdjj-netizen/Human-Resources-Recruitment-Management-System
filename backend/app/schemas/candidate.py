"""
候选人相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from datetime import datetime


class CandidateEducationResponse(BaseModel):
    id: int
    school: str
    degree: str
    major: str
    start_date: str | None = None
    end_date: str | None = None

    class Config:
        from_attributes = True


class CandidateExperienceResponse(BaseModel):
    id: int
    company: str
    position: str
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None

    class Config:
        from_attributes = True


class CandidateSkillResponse(BaseModel):
    id: int
    skill_name: str
    proficiency: str | None = None

    class Config:
        from_attributes = True


class MatchResultResponse(BaseModel):
    id: int
    score: int
    analysis: str
    matched_at: datetime | None = None

    class Config:
        from_attributes = True


class CandidateListResponse(BaseModel):
    """候选人列表项"""
    id: int
    name: str
    phone: str | None = None
    email: str | None = None
    current_company: str | None = None
    current_position: str | None = None
    work_years: int | None = None
    status: str
    position_id: int | None = None
    source: str
    match_score: int | None = None  # 来自join查询
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class CandidateDetailResponse(BaseModel):
    """候选人详情"""
    id: int
    name: str
    phone: str | None = None
    email: str | None = None
    gender: str | None = None
    age: int | None = None
    current_company: str | None = None
    current_position: str | None = None
    work_years: int | None = None
    self_evaluation: str | None = None
    status: str
    position_id: int | None = None
    source: str
    resume_filename: str | None = None
    educations: list[CandidateEducationResponse] = []
    experiences: list[CandidateExperienceResponse] = []
    skills: list[CandidateSkillResponse] = []
    match_result: MatchResultResponse | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class CandidateUpdate(BaseModel):
    """更新候选人状态"""
    status: str = Field(..., description="新状态")


class CandidateBatchDelete(BaseModel):
    """批量删除候选人"""
    ids: list[int] = Field(..., min_length=1, description="候选人ID列表")
