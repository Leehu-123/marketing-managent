from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
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
    post_content = Column(Text, nullable=True) # Nội dung bài viết soạn sẵn (cho POST_GROUP)
    media_urls = Column(Text, nullable=True) # JSON list đường dẫn ảnh/video đính kèm
    daily_schedule_time = Column(String, nullable=True) # Giờ đăng hàng ngày VD: "08:30"
    is_daily_repeat = Column(Boolean, default=False) # Bật/tắt đăng lặp lại hàng ngày
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
