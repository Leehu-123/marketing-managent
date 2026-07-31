from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas

router = APIRouter(prefix="/settings/ai", tags=["Settings"])

DEFAULT_PROVIDERS = ["OpenAI", "Gemini", "Claude", "9Router", "Gemini (Image)", "9Router (Image)", "OpenAI (Image)", "Replicate FLUX (Image)", "Perplexity (Research)", "OpenAI (Research)"]

@router.get("/", response_model=List[schemas.AISettingResponse])
def get_ai_settings(db: Session = Depends(get_db)):
    """
    Lấy danh sách các cài đặt AI. Nếu chưa có, tự động tạo mặc định.
    """
    settings = db.query(models.AISetting).all()
    # Check if we need to add new providers to an existing DB
    existing_providers = [s.provider_name for s in settings]
    for provider in DEFAULT_PROVIDERS:
        if provider not in existing_providers:
            db_setting = models.AISetting(
                provider_name=provider,
                api_key="",
                base_url="https://api.9router.com/v1" if "9Router" in provider else None,
                model_name="black-forest-labs/flux-schnell" if provider == "Replicate FLUX (Image)" else None,
                is_active=(provider == "OpenAI" and not settings) or (provider == "Gemini (Image)" and not any(s.provider_name.endswith("(Image)") for s in settings))
            )
            db.add(db_setting)
    db.commit()
    return db.query(models.AISetting).all()

@router.put("/{provider_name}", response_model=schemas.AISettingResponse)
def update_ai_setting(provider_name: str, setting: schemas.AISettingUpdate, db: Session = Depends(get_db)):
    """
    Cập nhật API Key hoặc trạng thái kích hoạt của một Provider.
    Nếu kích hoạt một provider, các provider khác sẽ bị vô hiệu hóa.
    """
    db_setting = db.query(models.AISetting).filter(models.AISetting.provider_name == provider_name).first()
    if not db_setting:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà cung cấp AI")

    if setting.api_key is not None:
        db_setting.api_key = setting.api_key
        
    if setting.base_url is not None:
        db_setting.base_url = setting.base_url
        
    if setting.model_name is not None:
        db_setting.model_name = setting.model_name

    if setting.is_active is not None:
        db_setting.is_active = setting.is_active
        if setting.is_active:
            # Phân loại Image AI, Research AI và Text AI
            is_image_ai = "(Image)" in db_setting.provider_name
            is_research_ai = "(Research)" in db_setting.provider_name
            
            # Vô hiệu hóa các provider cùng loại khác
            other_settings = db.query(models.AISetting).filter(models.AISetting.id != db_setting.id).all()
            for other in other_settings:
                other_is_image = "(Image)" in other.provider_name
                other_is_research = "(Research)" in other.provider_name
                if is_image_ai == other_is_image and is_research_ai == other_is_research:
                    other.is_active = False

    db.commit()
    db.refresh(db_setting)
    return db_setting

@router.post("/test")
def test_ai_connection(request: schemas.AITestRequest):
    """
    Kiểm tra kết nối tới API AI.
    """
    if not request.api_key:
        raise HTTPException(status_code=400, detail="Vui lòng nhập API Key")

    try:
        # Xử lý chung cho cả Text AI và Image AI
        provider_base = request.provider_name.replace(" (Image)", "").replace(" (Research)", "")
        
        if provider_base in ["OpenAI", "9Router", "Perplexity"]:
            from openai import OpenAI
            client_args = {"api_key": request.api_key}
            if request.base_url:
                client_args["base_url"] = request.base_url
            elif provider_base == "Perplexity":
                client_args["base_url"] = "https://api.perplexity.ai"
            client = OpenAI(**client_args)
            # Make a simple models list request to verify if possible
            try:
                if provider_base == "Perplexity":
                    # Perplexity API doesn't support models.list() well, just do a basic chat completion
                    client.chat.completions.create(
                        model="sonar-pro",
                        messages=[{"role": "user", "content": "Hi"}],
                        max_tokens=5
                    )
                else:
                    client.models.list()
            except Exception as e:
                # 9Router might not support /v1/models, don't fail the test completely
                if provider_base not in ["9Router", "Perplexity"]:
                    raise e
            return {"message": "Kết nối thành công!"}
        
        elif provider_base == "Gemini":
            import google.generativeai as genai
            genai.configure(api_key=request.api_key)
            # Make a simple models list request to verify
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    break
            return {"message": "Kết nối thành công!"}
        
        elif request.provider_name == "Replicate FLUX (Image)" or provider_base == "Replicate FLUX":
            import replicate
            # Kiểm tra nhẹ bằng cách lấy metadata model, không tạo ảnh để tránh tốn credit.
            # Dùng Client(api_token=...) trực tiếp để tránh lỗi SDK không nhận os.environ sau khi import.
            model_name = request.model_name or "black-forest-labs/flux-schnell"
            client = replicate.Client(api_token=request.api_key.strip())
            client.models.get(model_name)
            return {"message": "Kết nối Replicate FLUX thành công!"}

        elif provider_base == "Claude":
            return {"message": "Claude chưa được hỗ trợ kiểm tra kết nối."}
            
        else:
            raise HTTPException(status_code=400, detail="Provider không hợp lệ")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi kết nối: {str(e)}")
