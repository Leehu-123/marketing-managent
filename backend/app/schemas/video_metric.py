from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class VideoMetricBase(BaseModel):
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    avg_watch_time_sec: float = 0.0
    retention_rate: float = 0.0
    engagement_rate: float = 0.0
    reach: int = 0
    impressions: int = 0

class VideoMetricCreate(VideoMetricBase):
    video_distribution_id: int

class VideoMetricResponse(VideoMetricBase):
    id: int
    video_distribution_id: int
    recorded_at: Optional[datetime] = None
    class Config:
        from_attributes = True
