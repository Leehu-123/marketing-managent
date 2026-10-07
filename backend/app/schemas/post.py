from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class PostBase(BaseModel):
    title: str
    body: Optional[str] = None
    
    # Web SEO
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    headings_structure: Optional[str] = None
    
    # Fanpage / Creative image fields
    image_prompt: Optional[str] = None
    caption: Optional[str] = None
    headline: Optional[str] = None
    subheadline: Optional[str] = None
    cta: Optional[str] = None
    benefits_json: Optional[str] = None
    background_prompt: Optional[str] = None
    template_key: Optional[str] = None
    product_slug: Optional[str] = None
    aspect_ratio: str = "1:1"
    
    # Media & Tracking
    media_url: Optional[str] = None
    media_urls: Optional[str] = "[]"
    fb_post_type: str = "post"
    utm_source: str = "saas_dafa"
    status: str = "Pending Review" # "Pending Review", "Approved", "Published", "Failed"
    translations: Optional[str] = None
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None

class PostCreate(PostBase):
    content_plan_id: int

class PostUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    headings_structure: Optional[str] = None
    image_prompt: Optional[str] = None
    caption: Optional[str] = None
    headline: Optional[str] = None
    subheadline: Optional[str] = None
    cta: Optional[str] = None
    benefits_json: Optional[str] = None
    background_prompt: Optional[str] = None
    template_key: Optional[str] = None
    product_slug: Optional[str] = None
    aspect_ratio: Optional[str] = None
    media_url: Optional[str] = None
    media_urls: Optional[str] = None
    fb_post_type: Optional[str] = None
    utm_source: Optional[str] = None
    status: Optional[str] = None
    translations: Optional[str] = None
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None

class PostResponse(PostBase):
    id: int
    content_plan_id: int

    class Config:
        from_attributes = True
