"""
职位相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from datetime import datetime


class PositionCreate(BaseModel):
    """创建职位"""
    title: str = Field(..., min_length=1, max_length=200, description="职位名称")
    department: str = Field(..., min_length=1, max_length=100, description="部门")
    location: str = Field(..., min_length=1, max_length=100, description="工作地点")
    salary_range: str | None = Field(None, max_length=100, description="薪资范围")
    job_description: str = Field(..., min_length=1, description="岗位JD")
    requirements: str | None = Field(None, description="任职要求")
    status: str = Field("开放", description="职位状态")
    headcount: int | None = Field(None, ge=1, description="招聘人数")
    parsing_extra_prompt: str | None = Field(None, description="AI简历解析额外提示词")
    platform_url: str | None = Field(None, max_length=500, description="外部平台链接")
    platform_name: str | None = Field(None, max_length=100, description="外部平台名称")


class PositionUpdate(BaseModel):
    """更新职位"""
    title: str | None = Field(None, max_length=200)
    department: str | None = Field(None, max_length=100)
    location: str | None = Field(None, max_length=100)
    salary_range: str | None = Field(None, max_length=100)
    job_description: str | None = None
    requirements: str | None = None
    status: str | None = None
    headcount: int | None = Field(None, ge=1)
    parsing_extra_prompt: str | None = Field(None, description="AI简历解析额外提示词")
    platform_url: str | None = Field(None, max_length=500)
    platform_name: str | None = Field(None, max_length=100)


class PositionResponse(BaseModel):
    """职位响应"""
    id: int
    title: str
    department: str
    location: str
    salary_range: str | None = None
    job_description: str
    requirements: str | None = None
    status: str
    headcount: int | None = None
    parsing_extra_prompt: str | None = None
    platform_url: str | None = None
    platform_name: str | None = None
    user_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class JDParseRequest(BaseModel):
    """JD解析请求"""
    text: str | None = Field(None, description="粘贴的JD文本")
    url: str | None = Field(None, description="职位链接URL")


class JDParseResponse(BaseModel):
    """JD解析结果"""
    title: str
    department: str
    location: str
    salary_range: str | None = None
    job_description: str
    requirements: str | None = None
