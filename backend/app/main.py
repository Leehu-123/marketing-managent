import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import engine, Base
from app.api.router import api_router
from app.api.web import router as web_router
from app.worker.scheduler import start_scheduler, stop_scheduler
from app.models import *  # Đảm bảo các models được load để tạo bảng

# Tự động tạo cơ sở dữ liệu nếu chưa tồn tại (áp dụng cho SQLite để dev nhanh)
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    # --- STARTUP ---
    start_scheduler()
    
    # Init default admin user
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.core.security import get_password_hash
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            print("Creating default admin user: admin/dafa123")
            admin = User(username="admin", hashed_password=get_password_hash("dafa123"))
            db.add(admin)
            db.commit()
    except Exception as e:
        print("Error initializing admin user:", e)
    finally:
        db.close()
        
    yield
    # --- SHUTDOWN ---
    stop_scheduler()


app = FastAPI(
    title="DAFA Glass Content Automation SaaS",
    description="Hệ thống tự động hóa lập kế hoạch, sản xuất nội dung và tracking hiệu quả đa kênh cho DAFA glass.",
    version="1.0.0",
    lifespan=lifespan,
)

# Cấu hình CORS để cho phép kết nối linh hoạt
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount thư mục tĩnh và upload để có thể truy xuất hình ảnh/video qua URL
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

# Đăng ký các router
app.include_router(api_router)
app.include_router(web_router)

# Endpoint kiểm tra sức khỏe hệ thống
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "database": settings.DATABASE_URL.split(":///")[0]}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
