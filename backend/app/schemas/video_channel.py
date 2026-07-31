from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class VideoChannelBase(BaseModel):
    name: str
    channel_type: str  # "brand", "kol_main", "kol_side"
    platform: str  # "TikTok", "YouTube", "Facebook"
    platform_channel_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    description: Optional[str] = None
    goal: Optional[str] = None
    vibe: Optional[str] = None
    target_audience: Optional[str] = None
    format_length: Optional[str] = None
    tone_of_voice: Optional[str] = None
    key_message: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True

class VideoChannelCreate(VideoChannelBase):
    pass

class VideoChannelUpdate(BaseModel):
    name: Optional[str] = None
    channel_type: Optional[str] = None
    platform: Optional[str] = None
    platform_channel_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    description: Optional[str] = None
    goal: Optional[str] = None
    vibe: Optional[str] = None
    target_audience: Optional[str] = None
    format_length: Optional[str] = None
    tone_of_voice: Optional[str] = None
    key_message: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None

class VideoChannelResponse(VideoChannelBase):
    id: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
