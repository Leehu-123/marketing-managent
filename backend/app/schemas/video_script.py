from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class ScriptSceneBase(BaseModel):
    scene_order: int
    start_time_sec: Optional[float] = None
    end_time_sec: Optional[float] = None
    duration_sec: Optional[float] = None
    frame_type: Optional[str] = None  # "close-up", "medium", "wide"
    setting: Optional[str] = None
    voiceover: Optional[str] = None
    on_screen_text: Optional[str] = None
    sound_effect: Optional[str] = None
    music_note: Optional[str] = None
    transition: Optional[str] = None
    editor_note: Optional[str] = None
    safe_zone_warning: Optional[str] = None

class ScriptSceneCreate(ScriptSceneBase):
    video_script_id: int

class ScriptSceneUpdate(BaseModel):
    scene_order: Optional[int] = None
    start_time_sec: Optional[float] = None
    end_time_sec: Optional[float] = None
    duration_sec: Optional[float] = None
    frame_type: Optional[str] = None
    setting: Optional[str] = None
    voiceover: Optional[str] = None
    on_screen_text: Optional[str] = None
    sound_effect: Optional[str] = None
    music_note: Optional[str] = None
    transition: Optional[str] = None
    editor_note: Optional[str] = None
    safe_zone_warning: Optional[str] = None

class ScriptSceneResponse(ScriptSceneBase):
    id: int
    video_script_id: int
    class Config:
        from_attributes = True

class VideoScriptBase(BaseModel):
    total_duration_seconds: Optional[int] = None
    hook_description: Optional[str] = None
    overall_notes: Optional[str] = None
    status: str = "Draft"

class VideoScriptCreate(VideoScriptBase):
    video_plan_id: int

class VideoScriptUpdate(BaseModel):
    total_duration_seconds: Optional[int] = None
    hook_description: Optional[str] = None
    overall_notes: Optional[str] = None
    status: Optional[str] = None

class VideoScriptResponse(VideoScriptBase):
    id: int
    video_plan_id: int
    scenes: List[ScriptSceneResponse] = []
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
