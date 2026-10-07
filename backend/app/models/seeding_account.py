from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class SeedingAccount(Base):
    __tablename__ = "seeding_accounts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, index=True, nullable=False) # facebook, tiktok, youtube
    username = Column(String, index=True, nullable=False)
    password = Column(String, nullable=True) # Optional if using cookies
    two_fa_secret = Column(String, nullable=True) # For generating TOTP codes
    cookies = Column(String, nullable=True) # Stored as JSON string
    access_token = Column(String, nullable=True)
    proxy = Column(String, nullable=True)
    status = Column(String, default="active") # active, locked, checkpoint
    note = Column(String, nullable=True) # Ghi chú / Tên gợi nhớ phân biệt tài khoản
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
