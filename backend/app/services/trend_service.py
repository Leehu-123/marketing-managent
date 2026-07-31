import random
import datetime
from app.core.config import settings

class TrendService:
    @staticmethod
    def fetch_tiktok_trends() -> dict:
        """Mock fetching trends from TikTok Creative Center API"""
        print("[MOCK TIKTOK] Fetching trends...")
        return {
            "keywords": [
                {"keyword": "kính cường lực siêu mỏng", "growth": 125.5},
                {"keyword": "thiết kế nội thất hiện đại 2026", "growth": 89.0},
                {"keyword": "biến hình kính râm", "growth": 210.3}
            ],
            "audios": [
                {"name": "Trending Chill Vibe - DJ X", "uses": 15400},
                {"name": "Gõ cửa trái tim Remix", "uses": 8900}
            ],
            "hashtags": ["#dafaglass", "#noithatcaocap", "#kinhcuongluc", "#xuhuongnoithat"]
        }

    @staticmethod
    def fetch_google_trends() -> dict:
        """Mock fetching Google Trends"""
        print("[MOCK GOOGLE] Fetching search trends...")
        return {
            "keywords": [
                "báo giá kính ốp bếp",
                "vách tắm kính cường lực",
                "kính hộp cách âm cách nhiệt"
            ]
        }

    @staticmethod
    def check_policy(text: str) -> dict:
        """Mock Policy Checker"""
        warnings = []
        lower_text = text.lower()
        if "giảm cân" in lower_text or "chữa bệnh" in lower_text:
            warnings.append("Lỗi y tế: Nên dùng từ 'hỗ trợ vóc dáng', 'hỗ trợ sức khỏe'")
        if "cam kết 100%" in lower_text or "số 1" in lower_text:
            warnings.append("Lỗi spam/cam kết: Nên dùng 'chất lượng hàng đầu', 'giá tốt'")
        return {
            "is_safe": len(warnings) == 0,
            "warnings": warnings
        }
