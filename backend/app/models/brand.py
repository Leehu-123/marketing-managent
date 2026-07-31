from sqlalchemy import Column, Integer, String
from app.core.database import Base

class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String, nullable=True)
    tone_of_voice = Column(String, nullable=True)
    target_audience = Column(String, nullable=True)
    core_values = Column(String, nullable=True)
    product_knowledge = Column(String, nullable=True)
    
    hotline = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    address = Column(String, nullable=True)
