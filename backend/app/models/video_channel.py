from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class VideoChannel(Base):
    __tablename__ = "video_channels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # "DAFA Glass Official", "KOL Minh Tu"
    channel_type = Column(String, nullable=False)  # "brand", "kol_main", "kol_side"
    platform = Column(String, nullable=False)  # "TikTok", "YouTube", "Facebook"
    platform_channel_id = Column(String, nullable=True)  # ID on platform
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    goal = Column(Text, nullable=True) # Mục tiêu và định hướng
    vibe = Column(String, nullable=True) # Vibe của kênh
    target_audience = Column(Text, nullable=True)
    format_length = Column(Text, nullable=True)
    tone_of_voice = Column(Text, nullable=True)
    key_message = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # relationships
    video_plans = relationship("VideoPlan", back_populates="channel", cascade="all, delete-orphan")
    distributions = relationship("VideoDistribution", back_populates="channel")
