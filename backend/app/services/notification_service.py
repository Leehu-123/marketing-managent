from sqlalchemy.orm import Session
from app.models import Notification

class NotificationService:
    @staticmethod
    def send_in_app(db: Session, user_id: int, notif_type: str, title: str, message: str, severity: str = "info", url: str = None):
        notif = Notification(
            user_id=user_id,
            type=notif_type,
            title=title,
            message=message,
            severity=severity,
            action_url=url
        )
        db.add(notif)
        db.commit()

    @staticmethod
    def send_telegram(telegram_id: str, message: str):
        """Mock Telegram Bot API"""
        if not telegram_id: return
        print(f"[MOCK TELEGRAM] Sending to {telegram_id}: {message}")
