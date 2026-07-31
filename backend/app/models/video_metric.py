from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class VideoMetric(Base):
    __tablename__ = "video_metrics"
    id = Column(Integer, primary_key=True, index=True)
    video_distribution_id = Column(Integer, ForeignKey("video_distributions.id"), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    avg_watch_time_sec = Column(Float, default=0.0)
    retention_rate = Column(Float, default=0.0)  # % viewers who watch to end
    engagement_rate = Column(Float, default=0.0)  # (L+C+S)/V * 100
    reach = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    # relationships
    distribution = relationship("VideoDistribution", back_populates="metrics")
