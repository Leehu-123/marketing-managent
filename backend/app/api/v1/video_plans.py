from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import VideoPlan
from app.schemas.video_plan import VideoPlanCreate, VideoPlanUpdate, VideoPlanResponse, VideoMonthlyPlanRequest
from app.services.ai_service import AIService

router = APIRouter()

@router.post("/generate", response_model=List[VideoPlanResponse])
def generate_monthly_plan(request: VideoMonthlyPlanRequest, db: Session = Depends(get_db)):
    from app.models.video_channel import VideoChannel
    channel = None
    if request.channel_id:
        channel = db.query(VideoChannel).filter(VideoChannel.id == request.channel_id).first()
        
    vibe = channel.vibe if channel and channel.vibe else "Năng động, thu hút"
    platform = channel.platform if channel else "TikTok"
    
    channel_info = None
    if channel:
        channel_info = {
            "target_audience": channel.target_audience,
            "format_length": channel.format_length,
            "tone_of_voice": channel.tone_of_voice,
            "key_message": channel.key_message
        }
    else:
        channel_info = {}
        
    if request.campaign_id:
        from app.models.campaign import Campaign
        camp = db.query(Campaign).filter(Campaign.id == request.campaign_id).first()
        if camp and getattr(camp, "research_data", None):
            channel_info["research_data"] = camp.research_data
    
    plans_data = AIService.generate_video_plan(
        campaign_name=request.campaign_name or f"Chiến dịch tháng {request.month_year}",
        month_year=request.month_year,
        objective=request.objective,
        total_posts=request.total_posts,
        content_proportions=[{"name": p.name, "percentage": p.percentage} for p in request.content_proportions],
        vibe=vibe,
        platform=platform,
        channel_info=channel_info
    )
    
    from datetime import datetime
    created_plans = []
    for plan_dict in plans_data:
        opt_time_str = plan_dict.get("optimal_post_time")
        if isinstance(opt_time_str, str) and "T" in opt_time_str:
            try:
                plan_dict["optimal_post_time"] = datetime.strptime(opt_time_str[:19], "%Y-%m-%dT%H:%M:%S")
            except Exception:
                plan_dict["optimal_post_time"] = None

        import json
        if isinstance(plan_dict.get("target_platforms"), list):
            plan_dict["target_platforms"] = json.dumps(plan_dict["target_platforms"], ensure_ascii=False)
        if isinstance(plan_dict.get("trending_hashtags"), list):
            plan_dict["trending_hashtags"] = json.dumps(plan_dict["trending_hashtags"], ensure_ascii=False)

        valid_keys = {"title", "content_line", "vibe", "target_platforms", "optimal_post_time", "trending_audio", "trending_hashtags", "ai_prompt", "status"}
        filtered_dict = {k: v for k, v in plan_dict.items() if k in valid_keys}
        
        if "title" not in filtered_dict or not filtered_dict["title"]:
            filtered_dict["title"] = "Chưa có tiêu đề"
        if "content_line" not in filtered_dict or not filtered_dict["content_line"]:
            filtered_dict["content_line"] = "General"
            
        # Đảm bảo ai_prompt không bị trống
        if "ai_prompt" not in filtered_dict or not filtered_dict["ai_prompt"] or len(filtered_dict["ai_prompt"]) < 10:
            hook_hint = "Hãy kết hợp xu hướng mới nhất để làm video"
            if "research_data" in channel_info:
                hook_hint = f"Hãy sử dụng dữ liệu Research sau: {channel_info['research_data'][:200]}..."
            filtered_dict["ai_prompt"] = f"Viết kịch bản chi tiết cho video '{filtered_dict['title']}'. {hook_hint}"

        db_plan = VideoPlan(**filtered_dict, campaign_id=request.campaign_id, channel_id=request.channel_id)
        db.add(db_plan)
        created_plans.append(db_plan)
        
    db.commit()
    for p in created_plans:
        db.refresh(p)
        
    return created_plans

@router.get("/", response_model=List[VideoPlanResponse])
def get_plans(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(VideoPlan).offset(skip).limit(limit).all()

@router.get("/{plan_id}", response_model=VideoPlanResponse)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    db_plan = db.query(VideoPlan).filter(VideoPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return db_plan

@router.get("/campaign/{campaign_id}/plans", response_model=List[VideoPlanResponse])
def get_campaign_video_plans(campaign_id: int, db: Session = Depends(get_db)):
    """Lấy danh sách các kế hoạch video của một chiến dịch."""
    plans = db.query(VideoPlan).filter(VideoPlan.campaign_id == campaign_id).order_by(VideoPlan.optimal_post_time.asc()).all()
    return plans

@router.put("/{plan_id}", response_model=VideoPlanResponse)
def update_plan(plan_id: int, plan: VideoPlanUpdate, db: Session = Depends(get_db)):
    db_plan = db.query(VideoPlan).filter(VideoPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    update_data = plan.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_plan, key, value)
        
    db.commit()
    db.refresh(db_plan)
    return db_plan

@router.delete("/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    db_plan = db.query(VideoPlan).filter(VideoPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    db.delete(db_plan)
    db.commit()
    return {"message": "Plan deleted"}

@router.post("/{plan_id}/approve")
def approve_plan(plan_id: int, db: Session = Depends(get_db)):
    from app.services.ai_service import AIService
    from app.models.video_script import VideoScript, ScriptScene
    import json

    db_plan = db.query(VideoPlan).filter(VideoPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    db_plan.status = "Approved"
    
    # Sinh kịch bản nếu chưa có
    existing_script = db.query(VideoScript).filter(VideoScript.video_plan_id == db_plan.id).first()
    if not existing_script:
        platforms = json.loads(db_plan.target_platforms) if db_plan.target_platforms else ["TikTok"]
        platform = platforms[0] if len(platforms) > 0 else "TikTok"
        
        scenes_data = AIService.generate_video_script(db_plan.title, db_plan.content_line, platform, db_plan.ai_prompt)
        
        db_script = VideoScript(
            video_plan_id=db_plan.id,
            total_duration_seconds=45,
            hook_description="Hook 3s đầu",
            status="Draft"
        )
        db.add(db_script)
        db.flush() # Lấy db_script.id
        
        for scene in scenes_data:
            db_scene = ScriptScene(
                video_script_id=db_script.id,
                scene_order=scene.get("scene_order", 1),
                setting=scene.get("setting", ""),
                frame_type=scene.get("frame_type", ""),
                voiceover=scene.get("voiceover", ""),
                on_screen_text=scene.get("on_screen_text", ""),
                transition=scene.get("transition", ""),
                music_note=scene.get("audio", ""),
                editor_note=scene.get("visuals", "")
            )
            db.add(db_scene)

    db.commit()
    return {"message": "Plan approved and script generated"}

@router.post("/approve-all")
def approve_all_plans(campaign_id: int, db: Session = Depends(get_db)):
    from app.services.ai_service import AIService
    from app.models.video_script import VideoScript, ScriptScene
    import json
    
    plans = db.query(VideoPlan).filter(VideoPlan.campaign_id == campaign_id, VideoPlan.status == "Draft").all()
    for p in plans:
        p.status = "Approved"
        
        # Kiểm tra xem Script đã tồn tại chưa
        existing_script = db.query(VideoScript).filter(VideoScript.video_plan_id == p.id).first()
        if not existing_script:
            platforms = json.loads(p.target_platforms) if p.target_platforms else ["TikTok"]
            platform = platforms[0] if len(platforms) > 0 else "TikTok"
            
            # Sinh kịch bản
            scenes_data = AIService.generate_video_script(p.title, p.content_line, platform, p.ai_prompt)
            
            db_script = VideoScript(
                video_plan_id=p.id,
                total_duration_seconds=45,
                hook_description="Hook 3s đầu",
                status="Draft"
            )
            db.add(db_script)
            db.flush() # Lấy db_script.id
            
            for scene in scenes_data:
                db_scene = ScriptScene(
                    video_script_id=db_script.id,
                    scene_order=scene.get("scene_order", 1),
                    setting=scene.get("setting", ""),
                    frame_type=scene.get("frame_type", ""),
                    voiceover=scene.get("voiceover", ""),
                    on_screen_text=scene.get("on_screen_text", ""),
                    transition=scene.get("transition", ""),
                    music_note=scene.get("audio", ""),
                    editor_note=scene.get("visuals", "")
                )
                db.add(db_scene)

    db.commit()
    return {"message": f"{len(plans)} plans approved and scripts generated"}
