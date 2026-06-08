"""
AI匹配结果模型
"""
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, nullable=False, comment="匹配分数 0-100")
    analysis = Column(Text, nullable=False, comment="AI生成的匹配分析理由")
    matched_at = Column(DateTime, server_default=func.now(), comment="匹配时间")
