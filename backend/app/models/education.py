"""
候选人教育经历模型
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class CandidateEducation(Base):
    __tablename__ = "candidate_educations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    school = Column(String(200), nullable=False, comment="学校名称")
    degree = Column(String(100), nullable=False, comment="学历：本科/硕士/博士/大专等")
    major = Column(String(200), nullable=False, comment="专业")
    start_date = Column(String(20), nullable=True, comment="起始时间，如2018-09")
    end_date = Column(String(20), nullable=True, comment="结束时间，如2022-06")
