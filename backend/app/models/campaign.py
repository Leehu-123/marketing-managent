from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    month_year = Column(String, nullable=False) # e.g. "06-2026"
    core_theme = Column(Text, nullable=False)
    focus_products = Column(String, nullable=True) # e.g. "Kính ốp bếp, Vách kính tắm, Cửa thủy lực DAFA"
    web_frequency = Column(Integer, default=3)
    fanpage_frequency = Column(Integer, default=4)
    web_content_pillars = Column(Text, nullable=True) # JSON array: [{"name": "...", "weight": 40}, ...]
    fanpage_content_pillars = Column(Text, nullable=True) # JSON array: [{"name": "...", "weight": 40}, ...]
    main_keywords = Column(String)  # JSON list
    campaign_type = Column(String, default="SEO") # SEO, Video, Mixed
    channel_id = Column(Integer, ForeignKey("video_channels.id"), nullable=True)
    research_data = Column(Text, nullable=True) # JSON or markdown string containing AI research for video scripts
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Quan hệ với ContentPlans
    plans = relationship("ContentPlan", back_populates="campaign", cascade="all, delete-orphan")
