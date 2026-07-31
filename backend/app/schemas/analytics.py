from datetime import datetime
from pydantic import BaseModel

class AnalyticsMetricBase(BaseModel):
    views: int = 0
    time_on_page: float = 0.0
    bounce_rate: float = 0.0
    reach: int = 0
    engagement: int = 0
    video_views: int = 0

class AnalyticsMetricCreate(AnalyticsMetricBase):
    post_id: int

class AnalyticsMetricResponse(AnalyticsMetricBase):
    id: int
    post_id: int
    recorded_at: datetime

    class Config:
        from_attributes = True
