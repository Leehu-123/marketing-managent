from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    content_plan_id = Column(Integer, ForeignKey("content_plans.id"), unique=True, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True) # Nội dung bài viết SEO hoặc Fanpage status
    
    # Dành cho Website SEO
    meta_title = Column(String(100), nullable=True)
    meta_description = Column(String(250), nullable=True)
    headings_structure = Column(Text, nullable=True) # Lưu cấu trúc headings (ví dụ JSON dạng: {"H1": "...", "H2": [...]})
    
    # Dành cho Facebook Fanpage
    image_prompt = Column(Text, nullable=True) # Hướng dẫn thiết kế hình ảnh cho designer/AI
    caption = Column(Text, nullable=True)
    headline = Column(String(180), nullable=True)
    subheadline = Column(String(250), nullable=True)
    cta = Column(String(180), nullable=True)
    benefits_json = Column(Text, nullable=True)
    background_prompt = Column(Text, nullable=True)
    template_key = Column(String(80), nullable=True)
    product_slug = Column(String(120), nullable=True)
    aspect_ratio = Column(String(20), default="1:1", nullable=False)
    
    # Media & Tracking
    media_url = Column(String, nullable=True) # Đường dẫn file hoặc URL hình ảnh/video đã upload (Cột cũ, giữ lại để tương thích hoặc dùng cho Web)
    media_urls = Column(Text, nullable=True) # JSON array chứa danh sách các đường dẫn file (hỗ trợ nhiều ảnh cho Fanpage)
    fb_post_type = Column(String, default="post", nullable=False) # Định dạng bài Fanpage: "post", "story", "reel"
    utm_source = Column(String, default="saas_dafa", nullable=False)
    
    # Trạng thái và Kết quả
    status = Column(String, default="Pending Review", nullable=False) # "Pending Review", "Approved", "Published", "Failed"
    published_at = Column(DateTime, nullable=True)
    published_url = Column(String, nullable=True) # URL thực tế của bài đăng sau khi post thành công

    # Đa ngôn ngữ (Polylang)
    translations = Column(Text, nullable=True) # Lưu JSON dạng: {"en": {...}, "zh": {...}}

    # Quan hệ
    content_plan = relationship("ContentPlan", back_populates="post")
    metrics = relationship("AnalyticsMetric", back_populates="post", cascade="all, delete-orphan")
