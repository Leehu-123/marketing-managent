from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app import models
from app.services.ai_service import AIService
# from app.services.cms_service import CMSService
# from app.services.meta_service import MetaService

router = APIRouter(prefix="/seo-workspace", tags=["SEO Workspace"])

class KeywordRequest(BaseModel):
    post_id: int
    main_keywords: str

class OutlineRequest(BaseModel):
    post_id: int
    competitor_urls: List[str] = []
    
class MetaRequest(BaseModel):
    post_id: int
    target_keyword: str
    
class DraftSectionRequest(BaseModel):
    post_id: int
    section_title: str
    section_context: str

@router.post("/step1-keywords")
def expand_keywords(req: KeywordRequest, db: Session = Depends(get_db)):
    """
    Step 1: Mở rộng và gom nhóm từ khóa (Keyword Clustering)
    """
    post = db.query(models.Post).filter(models.Post.id == req.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
        
    prompt = f"Phân tích và gom nhóm (Clustering) cho các từ khóa sau: {req.main_keywords}. Trả về các LSI keywords, long-tail keywords liên quan để bổ sung vào bài viết. Format dưới dạng list (JSON array các string)."
    
    try:
        import json
        result = AIService.generate_completion(prompt)
        # Giả sử AI trả về JSON array, ta thử parse
        try:
            keywords = json.loads(result)
        except:
            keywords = [k.strip() for k in result.split("\n") if k.strip() and "-" in k]
        
        return {"main_keywords": req.main_keywords, "lsi_keywords": keywords}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/step2-outline")
def generate_outline(req: OutlineRequest, db: Session = Depends(get_db)):
    """
    Step 2: Phân tích đối thủ và sinh Outline
    """
    post = db.query(models.Post).filter(models.Post.id == req.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
        
    prompt = f"Lập dàn ý (Outline) chi tiết chuẩn SEO cho bài viết chủ đề: '{post.title}'. Phân tích thêm góc nhìn cạnh tranh nếu có. Trả về cấu trúc JSON dạng: {{\"H1\": \"...\", \"H2\": [\"...\", \"...\"]}}"
    
    try:
        import json
        result = AIService.generate_completion(prompt)
        try:
            outline = json.loads(result)
        except:
            outline = {"H1": post.title, "H2": ["Giới thiệu", "Nội dung chính", "Kết luận"]}
            
        post.headings_structure = json.dumps(outline, ensure_ascii=False)
        db.commit()
        return {"outline": outline}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/step3-meta")
def optimize_meta(req: MetaRequest, db: Session = Depends(get_db)):
    """
    Step 3: Tối ưu thẻ Tiêu đề & Meta Description
    """
    post = db.query(models.Post).filter(models.Post.id == req.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
        
    prompt = f"Viết 1 Meta Title (dưới 60 ký tự) và 1 Meta Description (dưới 160 ký tự) chuẩn SEO cho bài viết '{post.title}', chứa từ khóa '{req.target_keyword}'. Trả về JSON: {{\"meta_title\": \"...\", \"meta_description\": \"...\"}}"
    
    try:
        import json
        result = AIService.generate_completion(prompt)
        try:
            meta = json.loads(result)
            post.meta_title = meta.get("meta_title", "")
            post.meta_description = meta.get("meta_description", "")
            db.commit()
            return meta
        except:
            return {"meta_title": post.title, "meta_description": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/step4-draft-section")
def draft_section(req: DraftSectionRequest, db: Session = Depends(get_db)):
    """
    Step 4: Viết nháp từng phần (Section by Section)
    """
    post = db.query(models.Post).filter(models.Post.id == req.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
        
    prompt = f"Viết nội dung chuẩn SEO cho mục (H2/H3) mang tiêu đề '{req.section_title}' trong bài viết '{post.title}'. Yêu cầu viết dài khoảng 200-300 chữ, có bôi đậm từ khóa quan trọng. Định dạng HTML (chỉ thẻ p, ul, li). Context bổ sung: {req.section_context}"
    
    try:
        result = AIService.generate_completion(prompt)
        # Tạm thời append vào body
        if post.body:
            post.body += f"\n<h2>{req.section_title}</h2>\n{result}"
        else:
            post.body = f"<h2>{req.section_title}</h2>\n{result}"
        db.commit()
        return {"section_html": f"<h2>{req.section_title}</h2>\n{result}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/step5-score")
def score_onpage(req: KeywordRequest, db: Session = Depends(get_db)):
    """
    Step 5: Chấm điểm SEO Onpage
    """
    post = db.query(models.Post).filter(models.Post.id == req.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
        
    # Logic chấm điểm cơ bản
    score = 100
    issues = []
    
    if not post.meta_title or len(post.meta_title) < 10:
        score -= 10
        issues.append("Meta title quá ngắn hoặc trống.")
    if not post.meta_description or len(post.meta_description) < 50:
        score -= 10
        issues.append("Meta description quá ngắn hoặc trống.")
        
    keyword = req.main_keywords.lower()
    if post.body and keyword not in post.body.lower():
        score -= 15
        issues.append(f"Không tìm thấy từ khóa '{keyword}' trong nội dung.")
        
    return {"seo_score": max(0, score), "issues": issues}

@router.post("/step6-publish")
async def publish_post(post_id: int, db: Session = Depends(get_db)):
    """
    Step 6: Technical Check & Publish (CMS API / Meta API)
    """
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
        
    content_plan = post.content_plan
    platform = content_plan.platform if content_plan else "Web"
    post_format = content_plan.format if content_plan else "Long article"

    result = None
    if platform == "Web":
        from app.services.cms_service import CMSService
        result = await CMSService.publish_post(
            title=post.title,
            body=post.body or "",
            meta_title=post.meta_title,
            meta_description=post.meta_description,
            media_url=post.media_url,
        )
    elif platform == "Fanpage":
        from app.services.meta_service import MetaService
        result = await MetaService.publish_post(
            title=post.title,
            body=post.body or "",
            post_format=post_format,
            media_url=post.media_url,
        )
    else:
        from app.services.cms_service import CMSService
        result = await CMSService.publish_post(
            title=post.title,
            body=post.body or "",
            meta_title=post.meta_title,
            meta_description=post.meta_description,
            media_url=post.media_url,
        )

    if result and result.get("success"):
        post.status = "Published"
        post.published_at = datetime.now()
        post.published_url = result.get("url", "")
        db.commit()
        return {
            "message": "Đăng bài thành công",
            "status": "Published",
            "published_url": post.published_url
        }
    else:
        error_msg = result.get("error", "Đăng bài thất bại") if result else "Không có phản hồi từ dịch vụ xuất bản"
        post.status = "Failed"
        db.commit()
        raise HTTPException(status_code=400, detail=f"Không thể xuất bản bài viết: {error_msg}")
