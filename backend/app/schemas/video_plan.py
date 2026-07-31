from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class VideoPlanBase(BaseModel):
    title: str
    content_line: str  # "brand", "kol_entertainment", "kol_bts"
    vibe: Optional[str] = None
    target_platforms: Optional[str] = None  # JSON string
    optimal_post_time: Optional[datetime] = None
    trending_audio: Optional[str] = None
    trending_hashtags: Optional[str] = None  # JSON string
    ai_prompt: Optional[str] = None
    saved_caption: Optional[str] = None
    thumbnail_prompt: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str = "Draft"

class VideoPlanCreate(VideoPlanBase):
    campaign_id: Optional[int] = None
    channel_id: Optional[int] = None

class VideoPlanUpdate(BaseModel):
    title: Optional[str] = None
    content_line: Optional[str] = None
    vibe: Optional[str] = None
    channel_id: Optional[int] = None
    target_platforms: Optional[str] = None
    optimal_post_time: Optional[datetime] = None
    trending_audio: Optional[str] = None
    trending_hashtags: Optional[str] = None
    ai_prompt: Optional[str] = None
    saved_caption: Optional[str] = None
    thumbnail_prompt: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: Optional[str] = None

class VideoPlanResponse(VideoPlanBase):
    id: int
    campaign_id: Optional[int] = None
    channel_id: Optional[int] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class ContentProportion(BaseModel):
    name: str
    percentage: int

# For AI generation request
class VideoMonthlyPlanRequest(BaseModel):
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    month_year: str  # "06-2026"
    objective: str  # Monthly goal
    product_description: Optional[str] = None
    total_posts: int = 10
    content_proportions: List[ContentProportion] = []
    channel_id: Optional[int] = None
