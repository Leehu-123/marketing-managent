from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

class AISetting(Base):
    __tablename__ = "ai_settings"

    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String, unique=True, index=True) # e.g., "OpenAI", "Gemini", "Claude"
    api_key = Column(String, nullable=True)
    base_url = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)

class IntegrationSetting(Base):
    __tablename__ = "integration_settings"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, unique=True, index=True) # "WordPress" or "Fanpage"
    url = Column(String, nullable=True) # for WordPress URL
    username = Column(String, nullable=True) # for WordPress
    access_token = Column(String, nullable=True) # for WP App Password or FB Access Token, or Client Secret for Google
    refresh_token = Column(String, nullable=True) # for OAuth 2.0 refresh tokens
    is_active = Column(Boolean, default=False)
