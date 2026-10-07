from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil

from app.core.database import get_db
from app.models import VideoContent, VideoDistribution, VideoPlan
from app.schemas.video_content import VideoContentResponse, VideoDistributionResponse
from app.services.ffmpeg_service import FFmpegService
from app.services.caption_service import CaptionService
from app.services.ai_service import AIService
from pydantic import BaseModel

class CaptionRequest(BaseModel):
    title: str
    vibe: str

class ThumbRequest(BaseModel):
    prompt: str
    headline: Optional[str] = None

router = APIRouter()

UPLOAD_DIR = "static/uploads/videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=VideoContentResponse)
async def upload_video(
    file: UploadFile = File(...),
    plan_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    # Save file
    file_path = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Get metadata
    info = FFmpegService.get_video_info(file_path)
    
    # Create VideoContent
    db_content = VideoContent(
        video_plan_id=plan_id,
        source_video_url=file_path,
        duration_seconds=info["duration"],
        resolution=info["resolution"],
        file_size_mb=info["size_mb"]
    )
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    
    # If plan_id exists, update plan status
    if plan_id:
        plan = db.query(VideoPlan).filter(VideoPlan.id == plan_id).first()
        if plan:
            plan.status = "ReadyToPublish"
            db.commit()
            
    return db_content

@router.get("/", response_model=List[VideoContentResponse])
def get_contents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    contents = db.query(VideoContent).offset(skip).limit(limit).all()
    return contents

@router.post("/generate-thumbnail")
def generate_thumbnail(req: ThumbRequest):
    safe_prompt = req.prompt + ", strictly absolutely NO text, NO letters, NO words, NO typography, blank space for text overlay."
    url = AIService.generate_image(safe_prompt)
    if not req.headline:
        return {"url": url}
        
    try:
        import httpx
        from PIL import Image, ImageDraw, ImageFont
        import io
        import time
        from app.core.config import settings
        
        resp = httpx.get(url, timeout=30.0)
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        
        txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        
        font_path = str(settings.BRAND_DIR / "fonts" / "BeVietnamPro-Black.ttf")
        if not os.path.exists(font_path):
            font_path = "arial.ttf"
            
        width, height = img.size
        font_size = int(width * 0.08)
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
            
        text = req.headline.upper()
        # Word wrap basic
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            left, top, right, bottom = draw.textbbox((0, 0), " ".join(current_line), font=font)
            if right - left > width * 0.9:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
            
        y = int(height * 0.15)
        for line in lines:
            left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
            text_w = right - left
            x = (width - text_w) // 2
            
            for adj in range(-3, 4):
                for adj2 in range(-3, 4):
                    draw.text((x+adj, y+adj2), line, font=font, fill="black")
            draw.text((x, y), line, font=font, fill="yellow")
            y += (bottom - top) + 10
            
        img = Image.alpha_composite(img, txt_layer).convert("RGB")
        out_filename = f"thumb_{int(time.time())}.jpg"
        out_path = os.path.join(UPLOAD_DIR, out_filename)
        img.save(out_path, "JPEG", quality=90)
        
        return {"url": f"/static/uploads/videos/{out_filename}"}
    except Exception as e:
        print("Lỗi vẽ chữ thumbnail:", e)
        return {"url": url}

@router.get("/{content_id}", response_model=VideoContentResponse)
def get_content(content_id: int, db: Session = Depends(get_db)):
    content = db.query(VideoContent).filter(VideoContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content

@router.delete("/{content_id}")
def delete_content(content_id: int, db: Session = Depends(get_db)):
    content = db.query(VideoContent).filter(VideoContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    db.delete(content)
    db.commit()
    return {"message": "Content deleted"}

@router.post("/{content_id}/thumbnail")
def generate_thumbnail(content_id: int, db: Session = Depends(get_db)):
    content = db.query(VideoContent).filter(VideoContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
        
    thumb_path = FFmpegService.extract_best_frame(content.source_video_url)
    content.thumbnail_url = thumb_path
    db.commit()
    return {"thumbnail_url": thumb_path}

@router.post("/{content_id}/distribute")
def distribute_to_channels(content_id: int, db: Session = Depends(get_db)):
    content = db.query(VideoContent).filter(VideoContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
        
    plan = content.video_plan
    if not plan:
        raise HTTPException(status_code=400, detail="Video is not linked to a plan")
        
    title = plan.title
    hashtags = ["#dafaglass", "#noithatcaocap"]
    
    # Create distributions for TikTok, YouTube, Facebook
    distributions = []
    
    # TikTok
    dist_tk = VideoDistribution(
        video_content_id=content_id,
        platform="TikTok",
        post_type="short",
        caption=CaptionService.generate_tiktok_caption(title, hashtags)
    )
    db.add(dist_tk)
    distributions.append(dist_tk)
    
    # YouTube Shorts
    yt_meta = CaptionService.generate_youtube_metadata(title, hashtags)
    dist_yt = VideoDistribution(
        video_content_id=content_id,
        platform="YouTube",
        post_type="short",
        title=yt_meta["title"],
        description=yt_meta["description"],
        hashtags=yt_meta["tags"]
    )
    db.add(dist_yt)
    distributions.append(dist_yt)
    
    # Facebook Reels
    dist_fb = VideoDistribution(
        video_content_id=content_id,
        platform="Facebook",
        post_type="reel",
        caption=CaptionService.generate_reels_caption(title, hashtags)
    )
    db.add(dist_fb)
    distributions.append(dist_fb)
    
    db.commit()
    return {"message": f"Created {len(distributions)} distribution items"}

@router.post("/generate-caption")
def generate_caption(req: CaptionRequest):
    prompt = f"Viết một đoạn caption ngắn gọn, hấp dẫn cho video ngắn có chủ đề: '{req.title}'. Phong cách văn bản (vibe) phải: {req.vibe}. Kèm theo 3-5 hashtag phù hợp. Không cần giải thích thêm."
    caption = AIService.generate_completion(prompt)
    if not caption:
        caption = f"Caption mặc định cho: {req.title}\n#dafaglass #video"
    return {"caption": caption}


class PublishPlanRequest(BaseModel):
    channel_id: Optional[int] = None
    scheduled_at: Optional[str] = None
    caption: Optional[str] = None
    publish_now: bool = False


@router.post("/plan/{plan_id}/publish-or-schedule")
async def publish_or_schedule_plan(plan_id: int, req: PublishPlanRequest, db: Session = Depends(get_db)):
    """Đăng ngay hoặc lên lịch đăng video liên kết với một Kế hoạch Video (VideoPlan)."""
    from datetime import datetime
    from app.models.video_channel import VideoChannel
    from app.services.meta_service import MetaService
    from app.services.youtube_service import YouTubeService
    from app.services.tiktok_service import TikTokService

    plan = db.query(VideoPlan).filter(VideoPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy kế hoạch video")

    content = plan.video_content
    if not content or not content.source_video_url:
        raise HTTPException(status_code=400, detail="Video chưa được tải lên file. Vui lòng tải video trước khi xuất bản!")

    # 1. Update VideoPlan metadata
    if req.caption:
        plan.saved_caption = req.caption
    if req.channel_id:
        plan.channel_id = req.channel_id
    if req.scheduled_at:
        try:
            plan.optimal_post_time = datetime.fromisoformat(req.scheduled_at.replace("Z", ""))
        except Exception:
            pass

    # 2. Resolve Channel & Platform
    channel = None
    if req.channel_id:
        channel = db.query(VideoChannel).filter(VideoChannel.id == req.channel_id).first()
    elif plan.channel_id:
        channel = db.query(VideoChannel).filter(VideoChannel.id == plan.channel_id).first()

    platform = channel.platform if channel else "Facebook"
    video_url = content.source_video_url
    caption_text = req.caption or plan.saved_caption or plan.title

    # 3. Find or create VideoDistribution
    dist = db.query(VideoDistribution).filter(
        VideoDistribution.video_content_id == content.id,
        VideoDistribution.platform == platform
    ).first()

    if not dist:
        dist = VideoDistribution(
            video_content_id=content.id,
            channel_id=channel.id if channel else None,
            platform=platform,
            post_type="short",
            title=plan.title,
            caption=caption_text,
            status="Pending"
        )
        db.add(dist)
        db.flush()
    else:
        dist.channel_id = channel.id if channel else dist.channel_id
        dist.title = plan.title
        dist.caption = caption_text

    ch_token = channel.access_token if channel else None
    ch_refresh = channel.refresh_token if channel else None
    ch_id = channel.platform_channel_id if channel else None

    # 4. Execute Publish Now OR Schedule
    if req.publish_now:
        try:
            post_id = None
            post_url = None

            if platform == "Facebook":
                res = await MetaService.upload_video_to_facebook(
                    file_path=video_url,
                    title=plan.title,
                    description=caption_text,
                    channel_token=ch_token,
                    channel_page_id=ch_id
                )
                if not res.get("success"):
                    raise Exception(res.get("error", "Lỗi upload video Facebook"))
                post_id = res.get("post_id")
                post_url = res.get("url")

            elif platform == "YouTube":
                res = YouTubeService.upload_video_or_short(
                    file_path=video_url,
                    title=plan.title,
                    description=caption_text,
                    is_short=True,
                    channel_token=ch_token,
                    channel_refresh=ch_refresh
                )
                if not res.get("success"):
                    raise Exception(res.get("error", "Lỗi upload video YouTube"))
                post_id = res.get("video_id")
                post_url = res.get("url")

            elif platform == "TikTok":
                post_id = TikTokService.upload_video(video_url, caption_text)
                post_url = f"https://www.tiktok.com/@video/{post_id}"
            else:
                raise Exception(f"Nền tảng '{platform}' chưa được hỗ trợ.")

            dist.platform_post_id = post_id
            dist.platform_post_url = post_url
            dist.status = "Published"
            dist.published_at = datetime.utcnow()
            dist.last_error = None
            plan.status = "Published"
            db.commit()

            return {
                "status": "published",
                "platform": platform,
                "post_id": post_id,
                "url": post_url,
                "message": f"Đã đăng video thành công lên {platform}!"
            }

        except Exception as e:
            dist.status = "Failed"
            dist.last_error = str(e)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Lỗi đăng video: {str(e)}")

    else:
        # Lên lịch đăng
        if not req.scheduled_at:
            raise HTTPException(status_code=400, detail="Vui lòng chọn thời gian lên lịch đăng!")
        try:
            sched_dt = datetime.fromisoformat(req.scheduled_at.replace("Z", ""))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Định dạng thời gian không hợp lệ: {e}")

        dist.status = "Scheduled"
        dist.scheduled_at = sched_dt
        dist.last_error = None
        plan.status = "Scheduled"
        db.commit()

        return {
            "status": "scheduled",
            "platform": platform,
            "scheduled_at": str(sched_dt),
            "message": f"Đã lên lịch đăng video lên {platform} vào lúc {sched_dt.strftime('%H:%M %d/%m/%Y')}!"
        }


