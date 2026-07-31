from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)  # "fb_comment", "tiktok_comment", "youtube_comment", "messenger", "zalo", "manual"
    source_post_id = Column(String, nullable=True)  # ID of source post/video
    source_platform = Column(String, nullable=True)  # "Facebook", "TikTok", "YouTube"
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    message = Column(Text, nullable=True)  # Original comment/message
    sentiment = Column(String, nullable=True)  # "positive", "negative", "inquiry"
    lead_score = Column(Integer, default=0)  # 0-100
    quality = Column(String, default="warm")  # "hot", "warm", "cold", "spam"
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="New")  # New/Contacting/Meeting/Closed-Won/Closed-Lost/Spam
    notes = Column(Text, nullable=True)
    follow_up_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    closed_value = Column(Float, nullable=True)  # Order value
    created_at = Column(DateTime, default=datetime.utcnow)
    # relationships
    assigned_user = relationship("User", backref="assigned_leads", foreign_keys=[assigned_to])
    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")

class LeadActivity(Base):
    __tablename__ = "lead_activities"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    activity_type = Column(String, nullable=False)  # "call", "message", "email", "meeting", "note", "status_change"
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # relationships
    lead = relationship("Lead", back_populates="activities")
    user = relationship("User")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = all users
    type = Column(String, nullable=False)  # "lead_new", "lead_reminder", "video_published", "channel_flop", "system"
    title = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    severity = Column(String, default="info")  # "info", "warning", "critical"
    is_read = Column(Boolean, default=False)
    action_url = Column(String, nullable=True)  # Link to relevant page
    created_at = Column(DateTime, default=datetime.utcnow)
    # relationships
    user = relationship("User", backref="notifications")
