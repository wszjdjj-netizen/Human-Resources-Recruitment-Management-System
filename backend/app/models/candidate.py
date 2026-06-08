"""
候选人模型（简历主表）
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="姓名")
    phone = Column(String(20), nullable=True, comment="电话")
    email = Column(String(100), nullable=True, comment="邮箱")
    gender = Column(String(10), nullable=True, comment="性别")
    age = Column(Integer, nullable=True, comment="年龄")
    current_company = Column(String(200), nullable=True, comment="当前公司")
    current_position = Column(String(200), nullable=True, comment="当前职位")
    work_years = Column(Integer, nullable=True, comment="总工作年限")
    self_evaluation = Column(Text, nullable=True, comment="自我评价")
    resume_filename = Column(String(500), nullable=True, comment="原始简历文件名")
    resume_raw_text = Column(Text, nullable=True, comment="简历原始文本（备份，用于重新解析）")
    status = Column(String(20), nullable=False, default="待联系", comment="候选人状态：待联系/已联系/面试中/已通过/已淘汰")
    source = Column(String(50), nullable=False, default="主动投递", comment="来源：主动投递/平台搜寻/手动导入")
    source_platform = Column(String(50), nullable=True, comment="来源平台：BOSS直聘/猎聘/领英等")
    source_uid = Column(String(200), nullable=True, comment="平台侧候选人唯一ID")
    source_profile_url = Column(String(500), nullable=True, comment="平台候选人详情页链接")
    dedupe_fingerprint = Column(String(64), nullable=True, comment="平台搜人去重指纹")
    sourcing_task_id = Column(Integer, ForeignKey("sourcing_tasks.id"), nullable=True, comment="来源搜人任务")
    last_sourced_at = Column(DateTime, nullable=True, comment="最近一次从平台抓取到该候选人的时间")
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True, comment="关联职位")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所属HR")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
