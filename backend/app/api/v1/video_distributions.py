from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

from app.core.database import get_db
from app.models import VideoDistribution
from app.schemas.video_content import VideoDistributionResponse, VideoDistributionUpdate
from app.services.ffmpeg_service import FFmpegService
from app.services.tiktok_service import TikTokService
from app.services.youtube_service import YouTubeService
from app.services.meta_service import MetaService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[VideoDistributionResponse])
def get_distributions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(VideoDistribution).offset(skip).limit(limit).all()

@router.post("/{dist_id}/process")
def process_anti_spam(dist_id: int, db: Session = Depends(get_db)):
    dist = db.query(VideoDistribution).filter(VideoDistribution.id == dist_id).first()
    if not dist:
        raise HTTPException(status_code=404, detail="Distribution not found")
        
    source_url = dist.video_content.source_video_url if dist.video_content else None
    if not source_url:
        raise HTTPException(status_code=400, detail="Không tìm thấy video gốc để xử lý")

    new_path, new_hash = FFmpegService.anti_spam_reencode(source_url)
    dist.processed_video_url = new_path
    dist.processed_hash = new_hash
    db.commit()
    
    return {"processed_url": new_path, "hash": new_hash}

@router.post("/{dist_id}/publish")
async def publish_now(dist_id: int, db: Session = Depends(get_db)):
    """Đăng ngay video này lên nền tảng chỉ định (Facebook, YouTube, TikTok)."""
    dist = db.query(VideoDistribution).filter(VideoDistribution.id == dist_id).first()
    if not dist:
        raise HTTPException(status_code=404, detail="Distribution not found")
        
    video_url = dist.processed_video_url or (dist.video_content.source_video_url if dist.video_content else None)
    if not video_url:
        raise HTTPException(status_code=400, detail="Không tìm thấy file video để đăng")

    channel = dist.channel
    ch_token = channel.access_token if channel else None
    ch_refresh = channel.refresh_token if channel else None
    ch_id = channel.platform_channel_id if channel else None

    # Title fallback
    plan_title = dist.video_content.video_plan.title if (dist.video_content and dist.video_content.video_plan) else "DAFA Glass Video"
    video_title = dist.title or plan_title
    video_desc = dist.caption or dist.description or ""

    try:
        post_id = None
        post_url = None

        if dist.platform == "Facebook":
            res = await MetaService.upload_video_to_facebook(
                file_path=video_url,
                title=video_title,
                description=video_desc,
                channel_token=ch_token,
                channel_page_id=ch_id
            )
            if not res.get("success"):
                raise Exception(res.get("error", "Lỗi upload video Facebook"))
            post_id = res.get("post_id")
            post_url = res.get("url")

        elif dist.platform == "YouTube":
            res = YouTubeService.upload_video_or_short(
                file_path=video_url,
                title=video_title,
                description=video_desc,
                is_short=(dist.post_type == "short"),
                channel_token=ch_token,
                channel_refresh=ch_refresh
            )
            if not res.get("success"):
                raise Exception(res.get("error", "Lỗi upload video YouTube"))
            post_id = res.get("video_id")
            post_url = res.get("url")

        elif dist.platform == "TikTok":
            post_id = TikTokService.upload_video(video_url, dist.caption or "")
            post_url = f"https://www.tiktok.com/@video/{post_id}"
            
        else:
            raise Exception(f"Nền tảng '{dist.platform}' chưa được hỗ trợ.")

        dist.platform_post_id = post_id
        dist.platform_post_url = post_url
        dist.status = "Published"
        dist.published_at = datetime.utcnow()
        dist.last_error = None
        db.commit()

        logger.info(f"[DISTRIBUTION] Published #{dist.id} to {dist.platform} -> {post_url}")
        return {
            "status": "success",
            "platform": dist.platform,
            "post_id": post_id,
            "url": post_url
        }
        
    except Exception as e:
        dist.status = "Failed"
        dist.last_error = str(e)
        db.commit()
        logger.error(f"[DISTRIBUTION] Lỗi publish #{dist.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{dist_id}")
def update_distribution(dist_id: int, dist_data: VideoDistributionUpdate, db: Session = Depends(get_db)):
    dist = db.query(VideoDistribution).filter(VideoDistribution.id == dist_id).first()
    if not dist:
        raise HTTPException(status_code=404, detail="Distribution not found")
        
    update_data = dist_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dist, key, value)
        
    db.commit()
    return dist
