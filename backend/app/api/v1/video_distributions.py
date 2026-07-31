from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.models import VideoDistribution
from app.schemas.video_content import VideoDistributionResponse, VideoDistributionUpdate
from app.services.ffmpeg_service import FFmpegService
from app.services.tiktok_service import TikTokService
from app.services.youtube_service import YouTubeService

router = APIRouter()

@router.get("/", response_model=List[VideoDistributionResponse])
def get_distributions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(VideoDistribution).offset(skip).limit(limit).all()

@router.post("/{dist_id}/process")
def process_anti_spam(dist_id: int, db: Session = Depends(get_db)):
    dist = db.query(VideoDistribution).filter(VideoDistribution.id == dist_id).first()
    if not dist:
        raise HTTPException(status_code=404, detail="Distribution not found")
        
    source_url = dist.video_content.source_video_url
    new_path, new_hash = FFmpegService.anti_spam_reencode(source_url)
    
    dist.processed_video_url = new_path
    dist.processed_hash = new_hash
    db.commit()
    
    return {"processed_url": new_path, "hash": new_hash}

@router.post("/{dist_id}/publish")
def publish_now(dist_id: int, db: Session = Depends(get_db)):
    dist = db.query(VideoDistribution).filter(VideoDistribution.id == dist_id).first()
    if not dist:
        raise HTTPException(status_code=404, detail="Distribution not found")
        
    video_url = dist.processed_video_url or dist.video_content.source_video_url
    
    try:
        post_id = None
        if dist.platform == "TikTok":
            post_id = TikTokService.upload_video(video_url, dist.caption)
        elif dist.platform == "YouTube":
            post_id = YouTubeService.upload_short(video_url, {"title": dist.title, "description": dist.description})
        else: # Facebook
            post_id = f"fb_mock_{dist_id}"
            
        dist.platform_post_id = post_id
        dist.status = "Published"
        dist.published_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "post_id": post_id}
        
    except Exception as e:
        dist.status = "Failed"
        dist.last_error = str(e)
        db.commit()
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
