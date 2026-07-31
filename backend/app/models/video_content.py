from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class VideoContent(Base):
    __tablename__ = "video_contents"
    id = Column(Integer, primary_key=True, index=True)
    video_plan_id = Column(Integer, ForeignKey("video_plans.id"), unique=True, nullable=True)
    source_video_url = Column(String, nullable=True)  # Uploaded video file path
    source_video_hash = Column(String, nullable=True)  # MD5 hash of original
    thumbnail_url = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    resolution = Column(String, nullable=True)  # "1080x1920"
    file_size_mb = Column(Float, nullable=True)
    cloud_storage_path = Column(String, nullable=True)  # S3/GDrive path
    status = Column(String, default="Uploaded")  # Uploaded/Processing/ReadyToPublish
    created_at = Column(DateTime, default=datetime.utcnow)
    # relationships
    video_plan = relationship("VideoPlan", back_populates="video_content")
    distributions = relationship("VideoDistribution", back_populates="video_content", cascade="all, delete-orphan")

class VideoDistribution(Base):
    __tablename__ = "video_distributions"
    id = Column(Integer, primary_key=True, index=True)
    video_content_id = Column(Integer, ForeignKey("video_contents.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("video_channels.id"), nullable=True)
    platform = Column(String, nullable=False)  # "TikTok", "YouTube", "Facebook"
    post_type = Column(String, nullable=True)  # "short", "long", "reel", "story"
    processed_video_url = Column(String, nullable=True)  # Anti-spam processed video
    processed_hash = Column(String, nullable=True)  # New MD5 hash
    caption = Column(Text, nullable=True)  # Platform-specific caption
    hashtags = Column(Text, nullable=True)  # JSON array
    title = Column(String, nullable=True)  # YouTube title
    description = Column(Text, nullable=True)  # YouTube description
    thumbnail_url = Column(String, nullable=True)  # Platform-specific thumbnail
    scheduled_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    platform_post_id = Column(String, nullable=True)  # Post ID on platform
    platform_post_url = Column(String, nullable=True)
    status = Column(String, default="Pending")  # Pending/Scheduled/Publishing/Published/Failed
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # relationships
    video_content = relationship("VideoContent", back_populates="distributions")
    channel = relationship("VideoChannel", back_populates="distributions")
    metrics = relationship("VideoMetric", back_populates="distribution", cascade="all, delete-orphan")
