from typing import List
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app import models, schemas

router = APIRouter(prefix="/posts", tags=["Posts & Production"])

@router.get("/", response_model=List[schemas.PostResponse])
def list_posts(db: Session = Depends(get_db)):
    """
    Lấy danh sách tất cả các bài viết.
    """
    return db.query(models.Post).all()

@router.get("/by-plan/{plan_id}", response_model=schemas.PostResponse)
def get_post_by_plan(plan_id: int, db: Session = Depends(get_db)):
    """
    Lấy thông tin bài viết theo content_plan_id.
    """
    db_post = db.query(models.Post).filter(models.Post.content_plan_id == plan_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết cho kế hoạch này")
    return db_post

@router.get("/{id}", response_model=schemas.PostResponse)
def get_post(id: int, db: Session = Depends(get_db)):
    """
    Lấy thông tin chi tiết bài viết (nội dung SEO Website hoặc status Facebook Fanpage).
    """
    db_post = db.query(models.Post).filter(models.Post.id == id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
    return db_post

@router.put("/{id}", response_model=schemas.PostResponse)
def update_post(id: int, post: schemas.PostUpdate, db: Session = Depends(get_db)):
    """
    [Module 2] Cho phép người quản trị chỉnh sửa bài đăng chi tiết (sửa chữ, SEO Tags, v.v.).
    """
    import json
    db_post = db.query(models.Post).filter(models.Post.id == id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Khong tim thay bai viet")
    
    update_data = post.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_post, key, value)
    
    # Đồng bộ media_url với media_urls
    if "media_urls" in update_data:
        try:
            urls = json.loads(update_data["media_urls"])
            if isinstance(urls, list) and urls:
                db_post.media_url = urls[0]
            else:
                db_post.media_url = ""
        except:
            db_post.media_url = ""
        
    db.commit()
    db.refresh(db_post)
    return db_post

@router.post("/{id}/approve", response_model=schemas.PostResponse)
def approve_post(id: int, db: Session = Depends(get_db)):
    """
    [Module 2] Phê duyệt bài viết chi tiết để sẵn sàng cho Auto-Posting Worker đăng bài.
    """
    db_post = db.query(models.Post).filter(models.Post.id == id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Khong tim thay bai viet")
    
    db_post.status = "Approved"
    db.commit()
    db.refresh(db_post)
    return db_post

@router.post("/{id}/publish", response_model=schemas.PostResponse)
async def publish_post_now(id: int, db: Session = Depends(get_db)):
    """
    Đăng bài trực tiếp ngay lập tức lên Web (WordPress) hoặc Fanpage (Meta).
    """
    db_post = db.query(models.Post).filter(models.Post.id == id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")

    content_plan = db_post.content_plan
    platform = content_plan.platform if content_plan else "Web"
    post_format = content_plan.format if content_plan else "Long article"

    if platform == "Web":
        from app.services.cms_service import CMSService
        result = await CMSService.publish_post(
            title=db_post.title,
            body=db_post.body or "",
            meta_title=db_post.meta_title,
            meta_description=db_post.meta_description,
            media_url=db_post.media_url,
        )
    elif platform == "Fanpage":
        from app.services.meta_service import MetaService
        result = await MetaService.publish_post(
            title=db_post.title,
            body=db_post.body or "",
            post_format=post_format,
            media_url=db_post.media_url,
        )
    else:
        from app.services.cms_service import CMSService
        result = await CMSService.publish_post(
            title=db_post.title,
            body=db_post.body or "",
            meta_title=db_post.meta_title,
            meta_description=db_post.meta_description,
            media_url=db_post.media_url,
        )

    if result and result.get("success"):
        db_post.status = "Published"
        db_post.published_at = datetime.now()
        db_post.published_url = result.get("url", "")
        db.commit()
        db.refresh(db_post)
        return db_post
    else:
        error_msg = result.get("error", "Đăng bài thất bại") if result else "Không có phản hồi từ dịch vụ"
        db_post.status = "Failed"
        db.commit()
        raise HTTPException(status_code=400, detail=f"Không thể đăng bài: {error_msg}")

@router.post("/{id}/revert", response_model=schemas.PostResponse)
def revert_post(id: int, db: Session = Depends(get_db)):
    """
    Chuyển bài viết từ Approved về Pending Review để chỉnh sửa lại.
    """
    db_post = db.query(models.Post).filter(models.Post.id == id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Khong tim thay bai viet")
    
    if db_post.status not in ("Approved", "Failed"):
        raise HTTPException(status_code=400, detail="Chi co the revert bai Approved hoac Failed")
    
    db_post.status = "Pending Review"
    db.commit()
    db.refresh(db_post)
    return db_post

@router.delete("/{id}")
def delete_post(id: int, db: Session = Depends(get_db)):
    """
    Xóa một bài viết cụ thể. Đồng thời xóa file media trên disk.
    """
    import json
    db_post = db.query(models.Post).filter(models.Post.id == id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Khong tim thay bai viet")
    
    # Xóa file media trên disk
    media_files = []
    if db_post.media_urls:
        try:
            urls = json.loads(db_post.media_urls)
            if isinstance(urls, list):
                media_files.extend(urls)
        except:
            pass
    if db_post.media_url and db_post.media_url not in media_files:
        media_files.append(db_post.media_url)
    
    for url in media_files:
        if url.startswith("/uploads/"):
            file_path = settings.UPLOAD_DIR / url.replace("/uploads/", "")
            if file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
    
    # Xóa content plan liên quan (nếu có)
    content_plan = db.query(models.ContentPlan).filter(models.ContentPlan.id == db_post.content_plan_id).first()
    
    db.delete(db_post)
    if content_plan:
        db.delete(content_plan)
    db.commit()
    
    return {"message": "Da xoa bai viet thanh cong"}

@router.post("/{id}/upload-media", response_model=schemas.PostResponse)
def upload_post_media(id: int, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """
    [Module 2] Hỗ trợ người quản trị upload nhiều file hình ảnh hoặc video trực tiếp lên bài viết.
    """
    import json
    db_post = db.query(models.Post).filter(models.Post.id == id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")
        
    uploaded_urls = []
    
    for file in files:
        # Validate định dạng file
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".mp4", ".png", ".jpg", ".jpeg", ".webp"]:
            raise HTTPException(status_code=400, detail=f"File {file.filename} không được hỗ trợ. Chỉ hỗ trợ .mp4, .png, .jpg, .jpeg, .webp")
            
        # Lưu file cục bộ vào thư mục uploads
        file_name = f"post_{id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}{file_ext}"
        dest_path = settings.UPLOAD_DIR / file_name
        
        try:
            with dest_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi lưu file {file.filename}: {str(e)}")
            
        uploaded_urls.append(f"/uploads/{file_name}")
        
    # Lấy danh sách URL hiện có
    current_urls = []
    if db_post.media_urls and db_post.media_urls != "[]":
        try:
            current_urls = json.loads(db_post.media_urls)
            if not isinstance(current_urls, list):
                current_urls = []
        except:
            current_urls = []
            
    # Giữ lại media_url cũ nếu nó không nằm trong media_urls (tương thích ngược)
    if db_post.media_url and db_post.media_url not in current_urls and not current_urls:
        current_urls.append(db_post.media_url)
        
    # Nối mảng mới
    current_urls.extend(uploaded_urls)
    
    # Cập nhật DB
    db_post.media_urls = json.dumps(current_urls)
    if current_urls:
        db_post.media_url = current_urls[0] # Cột cũ trỏ về ảnh đầu tiên
        
    db.commit()
    db.refresh(db_post)
    return db_post

@router.post("/{id}/upload-inline-image")
def upload_inline_image(id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload ảnh minh họa inline cho bài viết Web. Trả về URL ảnh để chèn vào body HTML."""
    db_post = db.query(models.Post).filter(models.Post.id == id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ .png, .jpg, .jpeg, .webp, .gif")

    file_name = f"inline_{id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}{file_ext}"
    dest_path = settings.UPLOAD_DIR / file_name

    try:
        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu file: {str(e)}")

    return {"url": f"/uploads/{file_name}", "filename": file_name}

from fastapi import Body

@router.post("/{id}/generate-slot-image")
def generate_slot_image(id: int, slot_data: dict = Body(...), db: Session = Depends(get_db)):
    """
    Generate ảnh AI cho một Image Slot cụ thể trong bài SEO.
    Body: {"slot_index": 1, "prompt": "English AI prompt...", "caption": "Chú thích tiếng Việt..."}
    """
    import json
    db_post = db.query(models.Post).filter(models.Post.id == id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Khong tim thay bai viet")
    
    slot_index = slot_data.get("slot_index", 0)
    prompt = slot_data.get("prompt", "")
    caption = slot_data.get("caption", "")
    
    if not prompt:
        # Fallback tự động nếu prompt trống
        prompt = db_post.image_prompt if db_post.image_prompt else f"Ảnh minh họa chuyên nghiệp cho chủ đề: {db_post.title}"

    # Làm prompt bám sát slot hơn. Nhiều provider tạo ảnh hiểu prompt tiếng Việt chưa tốt,
    # nên bọc lại bằng yêu cầu tiếng Anh nhưng giữ nguyên ý chính từ prompt người dùng.
    final_prompt = f"""
Photorealistic professional image for a Vietnamese glass/construction article.
Main image requirement from editor: {prompt}
Article title/context: {db_post.title}

Follow the editor requirement exactly. The main subject must match the editor prompt, not a generic glass facade.
Style: realistic architecture/interior/product photography, premium DAFA Glass brand mood, natural light, sharp details.
Strictly no text, no letters, no logo, no watermark, no poster, no collage, no distorted typography.
""".strip()

    # Gọi image-gen service
    from app.services.image_gen_service import ImageGenService
    try:
        image_url = ImageGenService.generate_image(prompt=final_prompt)
        if not image_url:
            raise HTTPException(status_code=500, detail="Không thể tạo ảnh từ nhà cung cấp AI")
        
        # Lưu trực tiếp vào body nếu placeholder vẫn còn trong DB.
        # Frontend cũng sẽ tự replace để hỗ trợ nội dung đang chỉnh chưa lưu.
        if db_post.body:
            import re
            display_caption = caption or prompt
            safe_prompt = prompt[:240].replace("'", "")
            safe_alt = display_caption[:80].replace("'", "")
            safe_fig = display_caption[:140].replace("'", "")
            img_tag = f"<figure class='inline-img-wrapper' data-slot='{slot_index}' data-prompt='{safe_prompt}' data-caption='{safe_fig}'><img src='{image_url}' alt='{safe_alt}' class='inline-img'><figcaption>{safe_fig}</figcaption></figure>"
            new_body = re.sub(rf"<!--\s*IMAGE_SLOT_{slot_index}\s*-->", img_tag, db_post.body)
            new_body = re.sub(rf"<!--\s*IMAGE_SLOT_PROMPT_{slot_index}:[\s\S]*?-->", "", new_body)
            if new_body != db_post.body:
                db_post.body = new_body
                db.commit()

        return {"url": image_url, "slot_index": slot_index, "prompt_used": final_prompt, "caption": caption or prompt}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tạo ảnh: {str(e)}")

# Cần import datetime vì trong tên file có sử dụng datetime
from datetime import datetime
