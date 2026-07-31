from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Cấu hình tham số kết nối đặc thù cho SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Khởi tạo Engine và Session
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args=connect_args,
    echo=False  # Đặt thành True nếu muốn debug câu lệnh SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho các model kế thừa
Base = declarative_base()

# Dependency để inject DB session vào các API endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
