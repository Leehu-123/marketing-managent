import os
import sys

# Add project root to sys.path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app import models

def reset_analytics():
    db = SessionLocal()
    try:
        # Reset all metrics to 0 or delete them
        # Let's just update all metrics to 0 so the next sync pulls fresh data
        db.query(models.AnalyticsMetric).update({
            "views": 0,
            "time_on_page": 0.0,
            "bounce_rate": 0.0,
            "reach": 0,
            "engagement": 0,
            "video_views": 0,
            "clicks": 0,
            "reactions": 0,
            "shares": 0,
            "comments": 0
        })
        db.commit()
        print("✅ Successfully reset all analytics metrics to 0.")
    except Exception as e:
        print(f"❌ Error resetting analytics: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_analytics()
