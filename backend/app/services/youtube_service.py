class YouTubeService:
    @staticmethod
    def upload_video(file_path: str, metadata: dict) -> str:
        """Mock YouTube Data API v3 (Long Video)"""
        print(f"[MOCK YOUTUBE] Uploading video: {file_path}")
        return "yt_vid_123456"

    @staticmethod
    def upload_short(file_path: str, metadata: dict) -> str:
        """Mock YouTube Data API v3 (Shorts)"""
        print(f"[MOCK YOUTUBE] Uploading Shorts: {file_path}")
        return "yt_short_123456"

    @staticmethod
    def fetch_metrics(video_id: str) -> dict:
        """Mock fetching metrics"""
        import random
        return {
            "views": random.randint(500, 20000),
            "likes": random.randint(50, 1000),
            "comments": random.randint(5, 200)
        }
