from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class TrendCacheBase(BaseModel):
    platform: str
    category: str  # "keyword", "audio", "challenge", "hashtag"
    keyword: str
    volume: Optional[int] = None
    growth_rate: Optional[float] = None
    region: str = "VN"

class TrendCacheCreate(TrendCacheBase):
    pass

class TrendCacheResponse(TrendCacheBase):
    id: int
    cached_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class BannedKeywordBase(BaseModel):
    keyword: str
    category: Optional[str] = None
    safe_alternative: Optional[str] = None
    platform: str = "all"

class BannedKeywordCreate(BannedKeywordBase):
    pass

class BannedKeywordResponse(BannedKeywordBase):
    id: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class TrendResearchResponse(BaseModel):
    keywords: list = []
    audios: list = []
    challenges: list = []
    hashtags: list = []
    policy_warnings: list = []
