from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import VideoScript, ScriptScene, VideoPlan
from app.schemas.video_script import VideoScriptCreate, VideoScriptUpdate, VideoScriptResponse, ScriptSceneUpdate
from app.services.scriptwriter_service import ScriptwriterService

router = APIRouter()

@router.post("/{plan_id}/generate", response_model=VideoScriptResponse)
def generate_script(plan_id: int, duration_sec: int = 30, db: Session = Depends(get_db)):
    db_plan = db.query(VideoPlan).filter(VideoPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    from app.services.ai_service import AIService
    import json
    
    plats = []
    try:
        plats = json.loads(db_plan.target_platforms) if db_plan.target_platforms else []
    except:
        pass
    platform = plats[0] if plats else "TikTok"
    vibe = db_plan.vibe or "Chuyên nghiệp"

    scenes = AIService.generate_video_script(
        title=db_plan.title,
        content_line=db_plan.content_line,
        platform=platform,
        ai_prompt=db_plan.ai_prompt,
        vibe=vibe
    )
    
    # Create Script
    db_script = VideoScript(
        video_plan_id=plan_id,
        total_duration_seconds=duration_sec,
        hook_description=scenes[0].get("voiceover", "") if scenes else "",
        overall_notes=f"Vibe chủ đạo: {vibe}"
    )
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    
    # Create Scenes
    for i, scene_data in enumerate(scenes):
        db_scene = ScriptScene(
            video_script_id=db_script.id,
            scene_order=scene_data.get("scene_order", i+1),
            duration_sec=scene_data.get("duration_sec", 5.0),
            frame_type=scene_data.get("frame_type", ""),
            setting=scene_data.get("setting", ""),
            voiceover=scene_data.get("voiceover", ""),
            on_screen_text=scene_data.get("on_screen_text", ""),
            sound_effect=scene_data.get("audio", ""),
            music_note=scene_data.get("transition", ""),
            editor_note=scene_data.get("visuals", "")
        )
        db.add(db_scene)
        
    db.commit()
    db.refresh(db_script)
    return db_script

@router.get("/", response_model=List[VideoScriptResponse])
def get_scripts(db: Session = Depends(get_db)):
    return db.query(VideoScript).order_by(VideoScript.created_at.desc()).all()

@router.get("/{script_id}", response_model=VideoScriptResponse)
def get_script(script_id: int, db: Session = Depends(get_db)):
    db_script = db.query(VideoScript).filter(VideoScript.id == script_id).first()
    if not db_script:
        raise HTTPException(status_code=404, detail="Script not found")
    return db_script

@router.put("/{script_id}", response_model=VideoScriptResponse)
def update_script(script_id: int, script: VideoScriptUpdate, db: Session = Depends(get_db)):
    db_script = db.query(VideoScript).filter(VideoScript.id == script_id).first()
    if not db_script:
        raise HTTPException(status_code=404, detail="Script not found")
        
    update_data = script.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_script, key, value)
        
    if update_data.get("status") == "Approved":
        plan = db_script.video_plan
        if plan:
            from app.services.ai_service import AIService
            import json
            
            plats = []
            try:
                plats = json.loads(plan.target_platforms) if plan.target_platforms else []
            except:
                pass
            platform = plats[0] if plats else "TikTok"
            vibe = plan.vibe or "Chuyên nghiệp"
            
            # Generate Caption
            is_kol = any(w in vibe.lower() for w in ["kol", "hài", "giải trí", "cá nhân", "drama", "trend", "vlog"])
            brand_note = "TUYỆT ĐỐI KHÔNG nhắc đến kính, sản phẩm hay thương hiệu DAFA Glass. Chỉ tập trung vào phong cách kênh." if is_kol else "Có thể nhắc nhẹ về sản phẩm kính hoặc thương hiệu DAFA Glass."
            
            prompt = f"Viết một đoạn caption ngắn gọn, hấp dẫn cho video ngắn có chủ đề: '{plan.title}'. Nền tảng đích: {platform}. Phong cách: {vibe}. {brand_note} Kèm hashtag phù hợp. LƯU Ý: CHỈ TRẢ VỀ NỘI DUNG CAPTION, KHÔNG GIẢI THÍCH, KHÔNG CHÀO HỎI."
            caption = AIService.generate_completion(prompt)
            if not caption:
                caption = f"Caption cho: {plan.title}"
            plan.saved_caption = caption

            # Generate Thumbnail Prompt
            thumb_prompt = f"Viết prompt ảnh bìa (thumbnail) kích thước 9:16 cho video chủ đề: '{plan.title}'. Phong cách: {vibe}. {brand_note} Mô tả thật rõ hình ảnh để AI có thể tạo. LƯU Ý: YÊU CẦU TRẢ VỀ TOÀN BỘ PROMPT BẰNG TIẾNG ANH (ENGLISH) để Midjourney/DALL-E hiểu được tốt nhất."
            thumb_res = AIService.generate_completion(thumb_prompt)
            if not thumb_res:
                thumb_res = f"9:16 portrait thumbnail, {plan.title}"
            plan.thumbnail_prompt = thumb_res

            plan.status = "InProduction"
            db.add(plan)
        
    db.commit()
    db.refresh(db_script)
    return db_script

@router.put("/{script_id}/scenes/{scene_id}")
def update_scene(script_id: int, scene_id: int, scene: ScriptSceneUpdate, db: Session = Depends(get_db)):
    db_scene = db.query(ScriptScene).filter(ScriptScene.id == scene_id, ScriptScene.video_script_id == script_id).first()
    if not db_scene:
        raise HTTPException(status_code=404, detail="Scene not found")
        
    update_data = scene.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_scene, key, value)
        
    db.commit()
    return {"message": "Scene updated"}

@router.post("/{script_id}/export")
def export_script(script_id: int, format: str = "pdf"):
    if format == "pdf":
        url = ScriptwriterService.export_pdf(script_id)
    else:
        url = ScriptwriterService.export_excel(script_id)
    return {"url": url}

@router.delete("/{script_id}")
def delete_script(script_id: int, db: Session = Depends(get_db)):
    db_script = db.query(VideoScript).filter(VideoScript.id == script_id).first()
    if not db_script:
        raise HTTPException(status_code=404, detail="Script not found")
        
    plan = db.query(VideoPlan).filter(VideoPlan.id == db_script.video_plan_id).first()
    if plan:
        db.delete(plan)
        
    db.delete(db_script)
    db.commit()
    return {"status": "success", "message": "Đã xóa kịch bản và kế hoạch"}
