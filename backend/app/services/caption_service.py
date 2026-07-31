class CaptionService:
    @staticmethod
    def generate_tiktok_caption(title: str, hashtags: list) -> str:
        """Generate short, engaging TikTok caption"""
        tag_str = " ".join(hashtags)
        return f"🔥 {title}\n👉 Mua ngay tại giỏ hàng!\n{tag_str}"
        
    @staticmethod
    def generate_youtube_metadata(title: str, hashtags: list) -> dict:
        """Generate YouTube Title, Description, Tags"""
        tag_str = ", ".join([t.replace("#", "") for t in hashtags])
        return {
            "title": f"{title} | DAFA Glass Official",
            "description": f"Xem chi tiết sản phẩm: {title}\nLiên hệ: 0912345678\nWebsite: dafaglass.com",
            "tags": tag_str
        }

    @staticmethod
    def generate_reels_caption(title: str, hashtags: list) -> str:
        """Generate Facebook Reels caption with CTA"""
        tag_str = " ".join(hashtags)
        return f"✨ {title}\n📩 Inbox page để nhận báo giá chi tiết!\n{tag_str}"
