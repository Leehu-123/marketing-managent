from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base

class SeedingTask(Base):
    __tablename__ = "seeding_tasks"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("seeding_campaigns.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("seeding_accounts.id"), nullable=True)
    target_url = Column(String, nullable=False)
    generated_content = Column(Text, nullable=True)
    status = Column(String, default="pending") # pending, success, failed
    error_message = Column(Text, nullable=True)
    task_type = Column(String, default="COMMENT") # COMMENT | REPLY_COMMENT | POST_GROUP
    parent_task_id = Column(Integer, nullable=True) # ID task comment cha (dùng cho REPLY_COMMENT)
    media_urls = Column(Text, nullable=True) # JSON list media cho task POST_GROUP
    retry_count = Column(Integer, default=0, nullable=False) # Số lần retry khi task bị kẹt in_progress
    executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
