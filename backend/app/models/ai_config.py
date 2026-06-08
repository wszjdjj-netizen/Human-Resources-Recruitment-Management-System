"""
User-scoped AI provider configuration.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class UserAIProviderConfig(Base):
    __tablename__ = "user_ai_provider_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider_id = Column(String(80), nullable=False)
    name = Column(String(120), nullable=False)
    endpoint = Column(String(500), nullable=False)
    encrypted_api_key = Column(Text, nullable=False)
    model = Column(String(120), nullable=False)
    parsing_mode = Column(String(30), nullable=False, default="generic")
    is_active = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
