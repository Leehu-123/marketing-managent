from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base

class SeedingCampaign(Base):
    __tablename__ = "seeding_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    platform = Column(String, nullable=False) # facebook, tiktok, youtube
    campaign_type = Column(String, nullable=False) # POST_GROUP, COMMENT
    target_urls = Column(Text, nullable=True) # JSON list of URLs
    ai_instructions = Column(Text, nullable=True)
    account_ids = Column(Text, nullable=True) # JSON list of account IDs
    status = Column(String, default="pending") # pending, running, completed
    schedule_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
