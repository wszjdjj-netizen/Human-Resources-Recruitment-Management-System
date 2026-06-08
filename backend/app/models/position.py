"""
职位模型（含岗位JD）
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, comment="职位名称")
    department = Column(String(100), nullable=False, comment="部门")
    location = Column(String(100), nullable=False, comment="工作地点")
    salary_range = Column(String(100), nullable=True, comment="薪资范围，如25K-40K")
    job_description = Column(Text, nullable=False, comment="岗位JD完整文本，用于AI匹配")
    requirements = Column(Text, nullable=True, comment="任职要求，可从JD中提取")
    status = Column(String(20), nullable=False, default="开放", comment="职位状态：开放/关闭")
    headcount = Column(Integer, nullable=True, comment="招聘人数")
    parsing_extra_prompt = Column(Text, nullable=True, comment="AI简历解析额外提示词（候选人画像/特殊要求等）")
    platform_url = Column(String(500), nullable=True, comment="外部招聘平台职位链接")
    platform_name = Column(String(100), nullable=True, comment="外部平台名称，如boss/猎聘/领英")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所属HR")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
