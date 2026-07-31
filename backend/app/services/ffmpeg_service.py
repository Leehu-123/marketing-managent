import hashlib
import os
import random

class FFmpegService:
    @staticmethod
    def anti_spam_reencode(source_path: str) -> str:
        """Mock FFmpeg re-encoding to change MD5 hash"""
        print(f"[MOCK FFMPEG] Processing anti-spam for: {source_path}")
        # In a real app, this would call subprocess.run(['ffmpeg', ...])
        new_path = source_path.replace(".mp4", "_processed.mp4")
        new_hash = hashlib.md5(str(random.random()).encode()).hexdigest()
        return new_path, new_hash

    @staticmethod
    def extract_best_frame(source_path: str) -> str:
        """Mock extracting best frame for thumbnail"""
        print(f"[MOCK FFMPEG] Extracting thumbnail from: {source_path}")
        return source_path.replace(".mp4", "_thumb.jpg")
        
    @staticmethod
    def get_video_info(source_path: str) -> dict:
        """Mock getting video metadata"""
        return {
            "duration": 60,
            "resolution": "1080x1920",
            "size_mb": 15.5
        }
