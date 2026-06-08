"""
候选人工作经历模型
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.database import Base


class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    company = Column(String(200), nullable=False, comment="公司名称")
    position = Column(String(200), nullable=False, comment="职位")
    start_date = Column(String(20), nullable=True, comment="起始时间")
    end_date = Column(String(20), nullable=True, comment="结束时间")
    description = Column(Text, nullable=True, comment="工作内容与成果描述")
