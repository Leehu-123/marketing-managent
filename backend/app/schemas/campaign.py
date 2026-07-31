from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class CampaignBase(BaseModel):
    name: str
    month_year: str # e.g. "06-2026"
    core_theme: str
    focus_products: Optional[str] = None
    main_keywords: Optional[str] = None
    web_frequency: int = 3
    fanpage_frequency: int = 4
    web_content_pillars: Optional[str] = None
    fanpage_content_pillars: Optional[str] = None
    campaign_type: str = "SEO"
    channel_id: Optional[int] = None
    research_data: Optional[str] = None

class CampaignCreate(CampaignBase):
    pass

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    month_year: Optional[str] = None
    core_theme: Optional[str] = None
    focus_products: Optional[str] = None
    main_keywords: Optional[str] = None
    web_frequency: Optional[int] = None
    fanpage_frequency: Optional[int] = None
    web_content_pillars: Optional[str] = None
    fanpage_content_pillars: Optional[str] = None
    campaign_type: Optional[str] = None
    channel_id: Optional[int] = None
    research_data: Optional[str] = None

class CampaignResponse(CampaignBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
