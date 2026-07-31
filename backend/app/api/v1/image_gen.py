from typing import List
import json
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.services.image_gen_service import ImageGenService
from pydantic import BaseModel

router = APIRouter(prefix="/image-gen", tags=["AI Image Generation"])


class GenerateRequest(BaseModel):
    custom_prompt: str = None
    product_slug: str = None
    template_key: str = None
    headline: str = None
    subheadline: str = None
    cta: str = None
    aspect_ratio: str = "1:1"


class PromptPreviewRequest(BaseModel):
    title: str
    body: str = ""
    platform: str = "Web"

class SlotPromptTranslateRequest(BaseModel):
    caption: str
    title: str = ""


@router.post("/posts/{post_id}/generate")
def generate_image_for_post(post_id: int, req: GenerateRequest = None, db: Session = Depends(get_db)):
    """AI tự động tạo ảnh cho bài viết dựa trên nội dung."""
    try:
        body = req if req else GenerateRequest()
        result = ImageGenService.generate_for_post(
            post_id,
            custom_prompt=body.custom_prompt,
            product_slug=body.product_slug,
            template_key=body.template_key,
            headline=body.headline,
            subheadline=body.subheadline,
            cta=body.cta,
            aspect_ratio=body.aspect_ratio,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview-prompt")
def preview_image_prompt(req: PromptPreviewRequest):
    """Xem trước prompt tạo ảnh mà không thực sự tạo ảnh."""
    prompt = ImageGenService.generate_image_prompt(
        article_title=req.title,
        article_body=req.body,
        platform=req.platform
    )
    return {"prompt": prompt}


@router.post("/translate-slot-prompt")
def translate_slot_prompt(req: SlotPromptTranslateRequest):
    """Dịch ghi chú ảnh tiếng Việt thành prompt ảnh tiếng Anh để provider bám nội dung tốt hơn."""
    caption = (req.caption or "").strip()
    if not caption:
        return {"prompt": "", "translated": False}

    try:
        from app.services.ai_service import AIService
        instruction = f"""
Convert the Vietnamese image description below into a concise ENGLISH image-generation prompt.
Return ONLY the English prompt, no quotes, no explanation.
Keep the exact visual meaning. Do not add Vietnamese words.
Context/article title: {req.title or ''}
Vietnamese description: {caption}
Requirements to append naturally: photorealistic professional architecture/interior/product photography, premium DAFA Glass mood, natural light, sharp details, no text, no letters, no logo, no watermark, no collage.
""".strip()
        result = (AIService.generate_completion(instruction) or "").strip()
        if result:
            # Dọn các wrapper thường gặp
            result = result.strip().strip('"').strip("'")
            return {"prompt": result, "translated": True}
    except Exception as e:
        print(f"[IMAGE_GEN] translate_slot_prompt error: {e}")

    fallback = (
        "Photorealistic professional image for a Vietnamese glass/construction article. "
        f"Main subject based on this Vietnamese description: {caption}. "
        "Realistic architecture/interior/product photography, natural light, premium DAFA Glass mood, sharp details. "
        "No text, no letters, no logo, no watermark, no collage."
    )
    return {"prompt": fallback, "translated": False}

@router.post("/logo")
def upload_logo(file: UploadFile = File(...)):
    """Upload logo thương hiệu (ghi đè file cũ)."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".png", ".jpg", ".jpeg", ".svg", ".webp"]:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ .png, .jpg, .jpeg, .svg, .webp")

    # Xóa các file logo cũ
    brand_dir = settings.BRAND_DIR
    brand_dir.mkdir(parents=True, exist_ok=True)
    for old in brand_dir.glob("logo.*"):
        old.unlink()

    logo_path = brand_dir / f"logo{file_ext}"
    with logo_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"logo_url": f"/uploads/brand/logo{file_ext}", "message": "Upload logo thành công"}


@router.get("/logo")
def get_logo():
    """Lấy URL logo hiện tại."""
    brand_dir = settings.BRAND_DIR
    logos = list(brand_dir.glob("logo.*"))
    if logos:
        return {"logo_url": f"/uploads/brand/{logos[0].name}", "exists": True}
    return {"logo_url": None, "exists": False}


@router.get("/products-folders")
def list_product_folders():
    """Lấy danh sách các thư mục sản phẩm và ảnh bên trong."""
    products_dir = settings.BRAND_DIR / "products"
    if not products_dir.exists():
        products_dir.mkdir(parents=True, exist_ok=True)

    folders = []
    # Quét các thư mục con trong products_dir
    for item in products_dir.iterdir():
        if item.is_dir():
            images = []
            for f in item.iterdir():
                if f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
                    images.append({"filename": f.name, "url": f"/uploads/brand/products/{item.name}/{f.name}"})
            description = ""
            desc_file = item / "description.txt"
            if desc_file.exists():
                try:
                    with desc_file.open("r", encoding="utf-8") as f:
                        description = f.read()
                except:
                    pass
            folders.append({"folder_name": item.name, "images": images, "description": description})
    return {"folders": folders}


@router.post("/products-folders")
def create_product_folder(req: dict):
    """Tạo thư mục sản phẩm mới."""
    folder_name = req.get("folder_name")
    if not folder_name:
        raise HTTPException(status_code=400, detail="Thiếu folder_name")
        
    # Tạo slug an toàn cho tên thư mục
    import re
    import unicodedata
    # Loại bỏ dấu tiếng việt
    slug = unicodedata.normalize('NFKD', folder_name).encode('ASCII', 'ignore').decode('utf-8')
    # Thay thế ký tự đặc biệt bằng gạch nối
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', slug).strip('-').lower()
    
    if not slug:
        raise HTTPException(status_code=400, detail="Tên thư mục không hợp lệ")

    products_dir = settings.BRAND_DIR / "products"
    target_dir = products_dir / slug
    if target_dir.exists():
        raise HTTPException(status_code=400, detail="Thư mục đã tồn tại")
        
    target_dir.mkdir(parents=True, exist_ok=True)
    return {"folder_name": slug, "message": "Tạo thư mục thành công"}


@router.delete("/products-folders/{folder_name}")
def delete_product_folder(folder_name: str):
    """Xóa thư mục sản phẩm và toàn bộ ảnh bên trong."""
    target_dir = settings.BRAND_DIR / "products" / folder_name
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Không tìm thấy thư mục")
        
    shutil.rmtree(target_dir)
    return {"message": f"Đã xóa thư mục {folder_name}"}


@router.post("/products-folders/{folder_name}/images")
def upload_images_to_folder(folder_name: str, files: List[UploadFile] = File(...)):
    """Upload ảnh vào một thư mục cụ thể."""
    target_dir = settings.BRAND_DIR / "products" / folder_name
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Không tìm thấy thư mục")

    uploaded = []
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".png", ".jpg", ".jpeg", ".webp"]:
            continue

        file_name = f"img_{datetime.now().strftime('%Y%m%d%H%M%S%f')}{file_ext}"
        dest = target_dir / file_name
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        uploaded.append({"filename": file_name, "url": f"/uploads/brand/products/{folder_name}/{file_name}"})

    return {"uploaded": uploaded, "message": "Upload thành công"}


@router.post("/products-folders/{folder_name}/description")
def update_product_description(folder_name: str, req: dict):
    """Cập nhật mô tả chi tiết cho thư mục sản phẩm."""
    target_dir = settings.BRAND_DIR / "products" / folder_name
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Không tìm thấy thư mục")
        
    description = req.get("description", "")
    desc_file = target_dir / "description.txt"
    with desc_file.open("w", encoding="utf-8") as f:
        f.write(description)
        
    return {"message": "Đã lưu mô tả sản phẩm thành công"}


@router.delete("/products-folders/{folder_name}/images/{filename}")
def delete_image_from_folder(folder_name: str, filename: str):
    """Xóa 1 ảnh cụ thể trong 1 thư mục."""
    file_path = settings.BRAND_DIR / "products" / folder_name / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file")
    file_path.unlink()
    return {"message": f"Đã xóa ảnh {filename}"}
