from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

class SeedingAccountBase(BaseModel):
    platform: str
    username: str
    password: Optional[str] = None
    two_fa_secret: Optional[str] = None
    cookies: Optional[str] = None
    access_token: Optional[str] = None
    proxy: Optional[str] = None
    status: Optional[str] = "active"

class SeedingAccountCreate(SeedingAccountBase):
    pass

class SeedingAccountUpdate(BaseModel):
    password: Optional[str] = None
    cookies: Optional[str] = None
    access_token: Optional[str] = None
    proxy: Optional[str] = None
    status: Optional[str] = None

class SeedingAccountResponse(SeedingAccountBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SeedingCampaignBase(BaseModel):
    name: str
    platform: str
    campaign_type: str
    target_urls: Optional[str] = None
    ai_instructions: Optional[str] = None
    schedule_time: Optional[datetime] = None
    status: Optional[str] = "pending"
    account_ids: Optional[str] = None # JSON list of account IDs
    post_content: Optional[str] = None
    media_urls: Optional[str] = None
    daily_schedule_time: Optional[str] = None
    is_daily_repeat: Optional[bool] = False

class SeedingCampaignCreate(SeedingCampaignBase):
    pass

class SeedingCampaignUpdate(BaseModel):
    name: Optional[str] = None
    target_urls: Optional[str] = None
    ai_instructions: Optional[str] = None
    account_ids: Optional[str] = None
    status: Optional[str] = None
    post_content: Optional[str] = None
    media_urls: Optional[str] = None
    daily_schedule_time: Optional[str] = None
    is_daily_repeat: Optional[bool] = None
    campaign_type: Optional[str] = None

class SeedingCampaignResponse(SeedingCampaignBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SeedingTaskBase(BaseModel):
    campaign_id: int
    account_id: Optional[int] = None
    target_url: str
    generated_content: Optional[str] = None
    status: Optional[str] = "pending"
    error_message: Optional[str] = None
    task_type: Optional[str] = "COMMENT"
    parent_task_id: Optional[int] = None
    media_urls: Optional[str] = None

class SeedingTaskCreate(SeedingTaskBase):
    pass

class SeedingTaskUpdate(BaseModel):
    status: Optional[str] = None
    error_message: Optional[str] = None
    account_id: Optional[int] = None
    generated_content: Optional[str] = None

class SeedingTaskResponse(SeedingTaskBase):
    id: int
    executed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class GenerateContentRequest(BaseModel):
    post_content: str
    instruction: str

class TaskWithDetails(BaseModel):
    """Schema enriched trả về cho Client Automation - gồm task + campaign + account info."""
    id: int
    campaign_id: int
    account_id: Optional[int] = None
    target_url: str
    status: str
    # Campaign info
    campaign_name: str
    campaign_type: str
    platform: str
    ai_instructions: Optional[str] = None
    # Account info
    account_username: Optional[str] = None
    account_password: Optional[str] = None
    account_cookies: Optional[str] = None
    account_proxy: Optional[str] = None
    account_two_fa_secret: Optional[str] = None
    # Extended fields for reply & media
    task_type: Optional[str] = "COMMENT"
    parent_task_id: Optional[int] = None
    parent_comment_content: Optional[str] = None
    media_urls: Optional[str] = None
    post_content: Optional[str] = None
