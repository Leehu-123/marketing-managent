from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class VideoContentBase(BaseModel):
    source_video_url: Optional[str] = None
    source_video_hash: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    resolution: Optional[str] = None
    file_size_mb: Optional[float] = None
    cloud_storage_path: Optional[str] = None
    status: str = "Uploaded"

class VideoContentCreate(VideoContentBase):
    video_plan_id: Optional[int] = None

class VideoContentUpdate(BaseModel):
    thumbnail_url: Optional[str] = None
    cloud_storage_path: Optional[str] = None
    status: Optional[str] = None

class VideoContentResponse(VideoContentBase):
    id: int
    video_plan_id: Optional[int] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class VideoDistributionBase(BaseModel):
    platform: str
    post_type: Optional[str] = None  # "short", "long", "reel", "story"
    caption: Optional[str] = None
    hashtags: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: str = "Pending"

class VideoDistributionCreate(VideoDistributionBase):
    video_content_id: int
    channel_id: Optional[int] = None

class VideoDistributionUpdate(BaseModel):
    caption: Optional[str] = None
    hashtags: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None

class VideoDistributionResponse(VideoDistributionBase):
    id: int
    video_content_id: int
    channel_id: Optional[int] = None
    processed_video_url: Optional[str] = None
    processed_hash: Optional[str] = None
    published_at: Optional[datetime] = None
    platform_post_id: Optional[str] = None
    platform_post_url: Optional[str] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
