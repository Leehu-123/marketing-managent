from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class VideoScript(Base):
    __tablename__ = "video_scripts"
    id = Column(Integer, primary_key=True, index=True)
    video_plan_id = Column(Integer, ForeignKey("video_plans.id"), unique=True, nullable=False)
    total_duration_seconds = Column(Integer, nullable=True)
    hook_description = Column(Text, nullable=True)  # 3-second hook description
    overall_notes = Column(Text, nullable=True)
    status = Column(String, default="Draft")  # Draft/Reviewed/Approved
    created_at = Column(DateTime, default=datetime.utcnow)
    # relationships
    video_plan = relationship("VideoPlan", back_populates="script")
    scenes = relationship("ScriptScene", back_populates="script", cascade="all, delete-orphan", order_by="ScriptScene.scene_order")

class ScriptScene(Base):
    __tablename__ = "script_scenes"
    id = Column(Integer, primary_key=True, index=True)
    video_script_id = Column(Integer, ForeignKey("video_scripts.id"), nullable=False)
    scene_order = Column(Integer, nullable=False)
    start_time_sec = Column(Float, nullable=True)
    end_time_sec = Column(Float, nullable=True)
    duration_sec = Column(Float, nullable=True)
    frame_type = Column(String, nullable=True)  # "close-up", "medium", "wide", "top-down"
    setting = Column(String, nullable=True)  # "showroom DAFA", "outdoor"
    voiceover = Column(Text, nullable=True)  # Script dialogue
    on_screen_text = Column(Text, nullable=True)  # Text overlay
    sound_effect = Column(String, nullable=True)  # SFX suggestion
    music_note = Column(String, nullable=True)  # Music for this section
    transition = Column(String, nullable=True)  # Scene transition effect
    editor_note = Column(Text, nullable=True)  # Technical notes for editor
    safe_zone_warning = Column(Text, nullable=True)  # Safe zone reminders
    # relationships
    script = relationship("VideoScript", back_populates="scenes")
