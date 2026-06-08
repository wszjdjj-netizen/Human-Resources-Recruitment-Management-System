"""
候选人技能标签模型
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    skill_name = Column(String(100), nullable=False, comment="技能名称，如Python")
    proficiency = Column(String(50), nullable=True, comment="熟练程度：了解/熟练/精通")
