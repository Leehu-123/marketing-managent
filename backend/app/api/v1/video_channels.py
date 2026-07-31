from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import VideoChannel
from app.schemas.video_channel import VideoChannelCreate, VideoChannelUpdate, VideoChannelResponse

router = APIRouter()

@router.post("/", response_model=VideoChannelResponse)
def create_channel(channel: VideoChannelCreate, db: Session = Depends(get_db)):
    db_channel = VideoChannel(**channel.model_dump())
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel

@router.get("/", response_model=List[VideoChannelResponse])
def get_channels(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(VideoChannel).offset(skip).limit(limit).all()

@router.get("/{channel_id}", response_model=VideoChannelResponse)
def get_channel(channel_id: int, db: Session = Depends(get_db)):
    db_channel = db.query(VideoChannel).filter(VideoChannel.id == channel_id).first()
    if not db_channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return db_channel

@router.put("/{channel_id}", response_model=VideoChannelResponse)
def update_channel(channel_id: int, channel: VideoChannelUpdate, db: Session = Depends(get_db)):
    db_channel = db.query(VideoChannel).filter(VideoChannel.id == channel_id).first()
    if not db_channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    update_data = channel.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_channel, key, value)
        
    db.commit()
    db.refresh(db_channel)
    return db_channel

@router.delete("/{channel_id}")
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    db_channel = db.query(VideoChannel).filter(VideoChannel.id == channel_id).first()
    if not db_channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(db_channel)
    db.commit()
    return {"message": "Channel deleted successfully"}
