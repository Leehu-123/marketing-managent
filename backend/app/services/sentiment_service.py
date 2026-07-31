class SentimentService:
    @staticmethod
    def analyze_comment(text: str) -> dict:
        """Mock Sentiment Analysis"""
        text_lower = text.lower()
        if any(word in text_lower for word in ["nhiêu", "giá", "inbox", "ib", "mua", "tư vấn"]):
            return {"sentiment": "inquiry", "is_lead": True}
        elif any(word in text_lower for word in ["đẹp", "tốt", "chất lượng", "ok"]):
            return {"sentiment": "positive", "is_lead": False}
        elif any(word in text_lower for word in ["tệ", "chê", "đắt", "kém"]):
            return {"sentiment": "negative", "is_lead": False}
        return {"sentiment": "neutral", "is_lead": False}
