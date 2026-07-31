from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class AnalyticsMetric(Base):
    __tablename__ = "analytics_metrics"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Chỉ số Website (GA4)
    views = Column(Integer, default=0)
    time_on_page = Column(Float, default=0.0) # Tính bằng giây
    bounce_rate = Column(Float, default=0.0)  # Tỷ lệ phần trăm
    
    # Chỉ số Fanpage (Facebook Insights)
    reach = Column(Integer, default=0)
    engagement = Column(Integer, default=0)   # Tổng Like, Share, Comment
    video_views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)       # Link Clicks, Image Clicks
    reactions = Column(Integer, default=0)    # Like, Heart, Haha...
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)

    # Quan hệ
    post = relationship("Post", back_populates="metrics")
