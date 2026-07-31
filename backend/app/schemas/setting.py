from typing import Optional
from pydantic import BaseModel

class AISettingBase(BaseModel):
    provider_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    is_active: bool = False

class AISettingCreate(AISettingBase):
    pass

class AISettingUpdate(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    is_active: Optional[bool] = None

class AISettingResponse(AISettingBase):
    id: int

    class Config:
        from_attributes = True

class AITestRequest(BaseModel):
    provider_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None

class IntegrationSettingBase(BaseModel):
    platform: str
    url: Optional[str] = None
    username: Optional[str] = None
    access_token: Optional[str] = None
    is_active: bool = False

class IntegrationSettingCreate(IntegrationSettingBase):
    pass

class IntegrationSettingUpdate(BaseModel):
    url: Optional[str] = None
    username: Optional[str] = None
    access_token: Optional[str] = None
    is_active: Optional[bool] = None

class IntegrationSettingResponse(IntegrationSettingBase):
    id: int

    class Config:
        from_attributes = True
