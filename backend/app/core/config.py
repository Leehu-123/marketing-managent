import os
from pathlib import Path
from dotenv import load_dotenv

# Tìm đường dẫn gốc của backend để load .env chính xác
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
dotenv_path = BACKEND_DIR / ".env"

if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()

class Settings:
    ENV: str = os.getenv("ENV", "development")
    
    # Database URL: sqlite:///./dafa_glass.db hoặc postgresql://user:password@localhost/db
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dafa_glass.db")
    
    # Mock Settings
    MOCK_AI: bool = os.getenv("MOCK_AI", "false").lower() == "true"
    MOCK_META: bool = os.getenv("MOCK_META", "false").lower() == "true"
    MOCK_CMS: bool = os.getenv("MOCK_CMS", "false").lower() == "true"
    MOCK_ANALYTICS: bool = os.getenv("MOCK_ANALYTICS", "false").lower() == "true"
    MOCK_IMAGE_GEN: bool = os.getenv("MOCK_IMAGE_GEN", "false").lower() == "true"
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # AI Research
    AI_RESEARCH_PROVIDER: str = os.getenv("AI_RESEARCH_PROVIDER", "perplexity") # perplexity or openai
    AI_RESEARCH_API_KEY: str = os.getenv("AI_RESEARCH_API_KEY", "")
    AI_RESEARCH_MODEL: str = os.getenv("AI_RESEARCH_MODEL", "sonar-pro")

    # Image generation
    IMAGE_PROVIDER: str = os.getenv("IMAGE_PROVIDER", "").strip()
    REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")
    REPLICATE_FLUX_MODEL: str = os.getenv("REPLICATE_FLUX_MODEL", "black-forest-labs/flux-schnell")
    
    # Meta Graph API
    META_PAGE_ID: str = os.getenv("META_PAGE_ID", "")
    META_PAGE_ACCESS_TOKEN: str = os.getenv("META_PAGE_ACCESS_TOKEN", "")
    
    # WordPress CMS
    WP_API_URL: str = os.getenv("WP_API_URL", "")
    WP_USERNAME: str = os.getenv("WP_USERNAME", "")
    WP_APP_PASSWORD: str = os.getenv("WP_APP_PASSWORD", "")
    
    # Google Analytics 4
    GA4_PROPERTY_ID: str = os.getenv("GA4_PROPERTY_ID", "")
    GOOGLE_APPLICATION_CREDENTIALS_JSON: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "")

    # Directories
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"
    STATIC_DIR: Path = BACKEND_DIR / "static"
    TEMPLATE_DIR: Path = BACKEND_DIR / "templates"
    BRAND_DIR: Path = UPLOAD_DIR / "brand"

# Tạo các thư mục nếu chưa tồn tại
Settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
Settings.STATIC_DIR.mkdir(parents=True, exist_ok=True)
Settings.TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
Settings.BRAND_DIR.mkdir(parents=True, exist_ok=True)
(Settings.BRAND_DIR / "products").mkdir(parents=True, exist_ok=True)

settings = Settings()
