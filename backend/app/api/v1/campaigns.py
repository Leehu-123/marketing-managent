from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas
from app.services.ai_service import AIService

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

@router.post("/", response_model=schemas.CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(campaign: schemas.CampaignCreate, db: Session = Depends(get_db)):
    """
    Tạo một chiến dịch marketing mới cho tháng.
    """
    db_campaign = models.Campaign(
        name=campaign.name,
        month_year=campaign.month_year,
        core_theme=campaign.core_theme,
        focus_products=campaign.focus_products,
        main_keywords=campaign.main_keywords,
        web_frequency=campaign.web_frequency,
        fanpage_frequency=campaign.fanpage_frequency,
        web_content_pillars=campaign.web_content_pillars,
        fanpage_content_pillars=campaign.fanpage_content_pillars,
        campaign_type=campaign.campaign_type,
        channel_id=campaign.channel_id
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign

@router.get("/", response_model=List[schemas.CampaignResponse])
def list_campaigns(type: str = None, db: Session = Depends(get_db)):
    """
    Lấy danh sách tất cả các chiến dịch đã tạo.
    """
    query = db.query(models.Campaign)
    if type:
        query = query.filter(models.Campaign.campaign_type == type)
    return query.order_by(models.Campaign.created_at.desc()).all()

@router.get("/{id}", response_model=schemas.CampaignResponse)
def get_campaign(id: int, db: Session = Depends(get_db)):
    """
    Lấy thông tin chi tiết một chiến dịch.
    """
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Không tìm thấy chiến dịch")
    return db_campaign

@router.delete("/{id}")
def delete_campaign(id: int, db: Session = Depends(get_db)):
    """
    Xóa một chiến dịch. Bài viết đã Published sẽ được giữ lại (tách khỏi chiến dịch).
    Chỉ xóa các bài chưa Published (Draft, Pending Review, Approved, Failed).
    """
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Khong tim thay chien dich")
    
    # Tìm các ContentPlan có bài Published
    published_plans = db.query(models.ContentPlan).filter(
        models.ContentPlan.campaign_id == id
    ).all()
    
    preserved_count = 0
    for plan in published_plans:
        if plan.post and plan.post.status == "Published":
            # Tách plan khỏi campaign để không bị cascade delete
            plan.campaign_id = None
            preserved_count += 1
            
    # Video plans
    from app.models.video_plan import VideoPlan
    db.query(VideoPlan).filter(VideoPlan.campaign_id == id).delete()
    
    db.flush()  # Đảm bảo tách xong trước khi xóa campaign
    
    # Xóa campaign (cascade sẽ xóa các plan còn lại + post chưa published)
    db.delete(db_campaign)
    db.commit()
    
    return {
        "message": f"Da xoa chien dich. {preserved_count} bai viet da dang duoc giu lai.",
        "preserved_posts": preserved_count
    }

@router.post("/{id}/generate-plan", response_model=List[schemas.ContentPlanResponse])
def generate_campaign_plan(id: int, db: Session = Depends(get_db)):
    """
    [Module 1 - Bước 1] Gọi AI Agent sinh kế hoạch nội dung chi tiết cho tháng dựa trên thông tin chiến dịch.
    """
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Không tìm thấy chiến dịch")
    
    # Xóa các kế hoạch cũ (Draft) nếu có để sinh lại
    db.query(models.ContentPlan).filter(
        models.ContentPlan.campaign_id == id,
        models.ContentPlan.status == "Draft"
    ).delete()
    db.commit()

    # Gọi AI sinh kế hoạch
    ai_plans = AIService.generate_content_plan(
        core_theme=db_campaign.core_theme,
        month_year=db_campaign.month_year,
        focus_products=db_campaign.focus_products,
        keywords=db_campaign.main_keywords,
        web_freq=db_campaign.web_frequency,
        fanpage_freq=db_campaign.fanpage_frequency,
        web_content_pillars=db_campaign.web_content_pillars,
        fanpage_content_pillars=db_campaign.fanpage_content_pillars
    )

    created_plans = []
    # Phân tích ngày giờ đăng bài: tháng_year có dạng MM-YYYY
    try:
        month_str, year_str = db_campaign.month_year.split("-")
        month = int(month_str)
        year = int(year_str)
    except Exception:
        # Nếu lỗi format, mặc định lấy tháng hiện tại
        now = datetime.now()
        month, year = now.month, now.year

    for plan in ai_plans:
        # Tính toán ngày đăng dự kiến dựa trên số offset ngày được sinh
        offset_days = plan.get("scheduled_days_offset", 1)
        scheduled_date = datetime(year, month, 1, 9, 0, 0) + timedelta(days=offset_days - 1)
        
        db_plan = models.ContentPlan(
            campaign_id=id,
            title=plan.get("title"),
            platform=plan.get("platform"),
            format=plan.get("format"),
            content_pillar=plan.get("content_pillar", "Khác"),
            target_keywords=plan.get("target_keywords"),
            scheduled_at=scheduled_date,
            status="Draft"
        )
        db.add(db_plan)
        created_plans.append(db_plan)
        
    db.commit()
    for p in created_plans:
        db.refresh(p)
        
    return created_plans

@router.get("/{id}/plans", response_model=List[schemas.ContentPlanResponse])
def get_campaign_plans(id: int, db: Session = Depends(get_db)):
    """
    Lấy danh sách các kế hoạch nội dung của chiến dịch.
    """
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Không tìm thấy chiến dịch")
    return db.query(models.ContentPlan).filter(models.ContentPlan.campaign_id == id).order_by(models.ContentPlan.scheduled_at.asc()).all()

@router.post("/{id}/approve-all", response_model=List[schemas.ContentPlanResponse])
def approve_all_plans(id: int, db: Session = Depends(get_db)):
    """
    Duyệt toàn bộ kế hoạch nội dung của chiến dịch. 
    Trạng thái chuyển sang 'Approved'. Đồng thời tự động khởi tạo bài đăng chi tiết nháp (Post) để chuyển sang Module 2.
    """
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Không tìm thấy chiến dịch")
        
    plans = db.query(models.ContentPlan).filter(
        models.ContentPlan.campaign_id == id,
        models.ContentPlan.status != "Approved"
    ).all()
    
    for plan in plans:
        plan.status = "Approved"
        
        # Kiểm tra xem Post đã tồn tại chưa để tránh trùng lặp
        existing_post = db.query(models.Post).filter(models.Post.content_plan_id == plan.id).first()
        if not existing_post:
            # Tạo bài đăng trống trước, nội dung sẽ được sinh tự động ở Module 2
            # Hoặc ở đây chúng ta có thể gọi AI sinh nội dung luôn cho tiện và nhanh!
            # Để tối ưu hóa trải nghiệm người dùng, ta sẽ sinh nội dung nháp sẵn luôn:
            post_data = AIService.generate_post_content(
                title=plan.title,
                platform=plan.platform,
                format_type=plan.format,
                focus_products=db_campaign.focus_products,
                keywords=plan.target_keywords or db_campaign.main_keywords
            )
            
            db_post = models.Post(
                content_plan_id=plan.id,
                title=plan.title,
                body=post_data.get("body"),
                meta_title=post_data.get("meta_title"),
                meta_description=post_data.get("meta_description"),
                headings_structure=post_data.get("headings_structure"),
                image_prompt=post_data.get("image_prompt"),
                caption=post_data.get("caption"),
                headline=post_data.get("headline"),
                subheadline=post_data.get("subheadline"),
                cta=post_data.get("cta"),
                benefits_json=post_data.get("benefits_json"),
                background_prompt=post_data.get("background_prompt"),
                template_key=post_data.get("template_key"),
                product_slug=post_data.get("product_slug"),
                aspect_ratio=post_data.get("aspect_ratio", "1:1"),
                utm_source=post_data.get("utm_source", "saas_dafa"),
                status="Pending Review" # Người quản trị cần Review trước khi Approved bài đăng chi tiết
            )
            db.add(db_post)
            
    db.commit()
    
    return db.query(models.ContentPlan).filter(models.ContentPlan.campaign_id == id).order_by(models.ContentPlan.scheduled_at.asc()).all()

@router.post("/{id}/research", response_model=schemas.CampaignResponse)
def run_video_research(id: int, db: Session = Depends(get_db)):
    """
    Thực hiện AI Research cho chiến dịch video, phân tích trend, hook, format và cập nhật vào `research_data`.
    """
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Không tìm thấy chiến dịch")
        
    try:
        platform = "TikTok/Reels/Shorts" # Mặc định
        research_result = AIService.generate_video_research(
            campaign_name=db_campaign.name,
            core_theme=db_campaign.core_theme,
            platform=platform
        )
        db_campaign.research_data = research_result
        db.commit()
        db.refresh(db_campaign)
        return db_campaign
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
