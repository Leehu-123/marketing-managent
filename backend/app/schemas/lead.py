from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class LeadBase(BaseModel):
    source: str
    source_post_id: Optional[str] = None
    source_platform: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    message: Optional[str] = None
    sentiment: Optional[str] = None
    lead_score: int = 0
    quality: str = "warm"
    status: str = "New"
    notes: Optional[str] = None
    follow_up_at: Optional[datetime] = None

class LeadCreate(LeadBase):
    assigned_to: Optional[int] = None

class LeadUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    quality: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    follow_up_at: Optional[datetime] = None
    assigned_to: Optional[int] = None
    closed_value: Optional[float] = None

class LeadResponse(LeadBase):
    id: int
    assigned_to: Optional[int] = None
    closed_at: Optional[datetime] = None
    closed_value: Optional[float] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class LeadActivityBase(BaseModel):
    activity_type: str
    description: Optional[str] = None

class LeadActivityCreate(LeadActivityBase):
    lead_id: int
    user_id: Optional[int] = None

class LeadActivityResponse(LeadActivityBase):
    id: int
    lead_id: int
    user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class NotificationBase(BaseModel):
    type: str
    title: str
    message: Optional[str] = None
    severity: str = "info"
    action_url: Optional[str] = None

class NotificationCreate(NotificationBase):
    user_id: Optional[int] = None

class NotificationResponse(NotificationBase):
    id: int
    user_id: Optional[int] = None
    is_read: bool = False
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
