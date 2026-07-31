from sqlalchemy.orm import Session
from app.models import Lead, LeadActivity, User
from typing import Optional
from datetime import datetime

class LeadService:
    @staticmethod
    def create_lead(db: Session, data: dict) -> Lead:
        lead = Lead(**data)
        # Score the lead
        score = 0
        if lead.phone: score += 40
        if lead.email: score += 20
        if lead.message and len(lead.message) > 10: score += 20
        if lead.sentiment == "inquiry": score += 20
        
        lead.lead_score = score
        if score >= 80: lead.quality = "hot"
        elif score >= 40: lead.quality = "warm"
        else: lead.quality = "cold"
        
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def assign_round_robin(db: Session, lead: Lead) -> Optional[User]:
        """Mock round-robin assignment logic"""
        sales_users = db.query(User).filter(User.role == "sales").all()
        if not sales_users:
            return None
        import random
        assigned = random.choice(sales_users)
        lead.assigned_to = assigned.id
        db.commit()
        return assigned

    @staticmethod
    def log_activity(db: Session, lead_id: int, user_id: int, activity_type: str, description: str):
        activity = LeadActivity(
            lead_id=lead_id,
            user_id=user_id,
            activity_type=activity_type,
            description=description
        )
        db.add(activity)
        db.commit()
