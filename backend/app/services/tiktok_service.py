class TikTokService:
    @staticmethod
    def upload_video(file_path: str, caption: str) -> str:
        """Mock TikTok Content Publishing API"""
        print(f"[MOCK TIKTOK] Uploading video: {file_path}")
        return "tt_post_123456"

    @staticmethod
    def fetch_metrics(post_id: str) -> dict:
        """Mock fetching metrics"""
        import random
        return {
            "views": random.randint(1000, 50000),
            "likes": random.randint(100, 5000),
            "comments": random.randint(10, 500),
            "shares": random.randint(5, 100),
            "saves": random.randint(20, 300)
        }
