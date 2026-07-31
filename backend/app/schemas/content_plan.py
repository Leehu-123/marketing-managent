from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ContentPlanBase(BaseModel):
    title: str
    platform: str # "Web" or "Fanpage"
    format: str   # "Long article", "Image post", "Video"
    content_pillar: Optional[str] = "Khác"
    target_keywords: Optional[str] = None
    scheduled_at: datetime
    status: str = "Draft" # "Draft", "Pending Approval", "Approved"

class ContentPlanCreate(ContentPlanBase):
    campaign_id: int

class ContentPlanUpdate(BaseModel):
    title: Optional[str] = None
    platform: Optional[str] = None
    format: Optional[str] = None
    content_pillar: Optional[str] = None
    target_keywords: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None

class ContentPlanResponse(ContentPlanBase):
    id: int
    campaign_id: int
    created_at: datetime

    class Config:
        from_attributes = True
