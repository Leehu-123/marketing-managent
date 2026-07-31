from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class TrendCache(Base):
    __tablename__ = "trend_cache"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False)  # "TikTok", "Google", "YouTube"
    category = Column(String, nullable=False)  # "keyword", "audio", "challenge", "hashtag"
    keyword = Column(String, nullable=False)
    volume = Column(Integer, nullable=True)
    growth_rate = Column(Float, nullable=True)
    region = Column(String, default="VN")
    cached_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

class BannedKeyword(Base):
    __tablename__ = "banned_keywords"
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, nullable=False)
    category = Column(String, nullable=True)  # "hate", "violence", "medical", "spam"
    safe_alternative = Column(String, nullable=True)  # Safe replacement word
    platform = Column(String, default="all")
    created_at = Column(DateTime, default=datetime.utcnow)
