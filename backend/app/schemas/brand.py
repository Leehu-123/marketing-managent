from typing import Optional
from pydantic import BaseModel

class BrandProfileBase(BaseModel):
    brand_name: Optional[str] = None
    tone_of_voice: Optional[str] = None
    target_audience: Optional[str] = None
    core_values: Optional[str] = None
    product_knowledge: Optional[str] = None
    hotline: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None

class BrandProfileCreate(BrandProfileBase):
    pass

class BrandProfileUpdate(BrandProfileBase):
    pass

class BrandProfileResponse(BrandProfileBase):
    id: int

    class Config:
        from_attributes = True
