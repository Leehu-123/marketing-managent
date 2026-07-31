from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class VideoPlan(Base):
    __tablename__ = "video_plans"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    channel_id = Column(Integer, ForeignKey("video_channels.id"), nullable=True)
    title = Column(String, nullable=False)  # Video concept title
    content_line = Column(String, nullable=False)  # "brand", "kol_entertainment", "kol_bts"
    vibe = Column(String, nullable=True)  # "professional", "funny", "lifestyle"
    target_platforms = Column(Text, nullable=True)  # JSON array: ["TikTok", "YouTube Shorts", "Reels"]
    optimal_post_time = Column(DateTime, nullable=True)
    trending_audio = Column(String, nullable=True)  # Suggested trending audio name
    trending_hashtags = Column(Text, nullable=True)  # JSON array of hashtags
    ai_prompt = Column(Text, nullable=True)  # Prompt cơ sở cho AI viết kịch bản
    saved_caption = Column(Text, nullable=True)  # Caption auto-generated after approval
    thumbnail_prompt = Column(Text, nullable=True)  # Prompt for AI Thumbnail
    thumbnail_url = Column(String, nullable=True)  # URL of the saved thumbnail
    status = Column(String, default="Draft")  # Draft/Approved/InProduction/ReadyToPublish/Published
    created_at = Column(DateTime, default=datetime.utcnow)
    # relationships
    campaign = relationship("Campaign", backref="video_plans")
    channel = relationship("VideoChannel", back_populates="video_plans")
    script = relationship("VideoScript", back_populates="video_plan", uselist=False, cascade="all, delete-orphan")
    video_content = relationship("VideoContent", back_populates="video_plan", uselist=False, cascade="all, delete-orphan")
