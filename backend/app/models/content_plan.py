from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class ContentPlan(Base):
    __tablename__ = "content_plans"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    title = Column(String, nullable=False)
    platform = Column(String, nullable=False) # "Web" or "Fanpage"
    format = Column(String, nullable=False)   # "Long article", "Image post", "Video"
    content_pillar = Column(String, nullable=True, default="Khác") # Tuyến nội dung
    target_keywords = Column(String, nullable=True) # Từ khóa SEO mục tiêu
    scheduled_at = Column(DateTime, nullable=False)
    status = Column(String, default="Draft", nullable=False) # "Draft", "Pending Approval", "Approved"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Quan hệ
    campaign = relationship("Campaign", back_populates="plans")
    post = relationship("Post", back_populates="content_plan", uselist=False, cascade="all, delete-orphan")
