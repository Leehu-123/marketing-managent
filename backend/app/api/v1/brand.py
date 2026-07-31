from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas

router = APIRouter(prefix="/brand", tags=["Brand"])

@router.get("/", response_model=schemas.BrandProfileResponse)
def get_brand_profile(db: Session = Depends(get_db)):
    """
    Lấy thông tin Hồ sơ Thương hiệu.
    Nếu chưa có, tạo mặc định một record trống.
    """
    profile = db.query(models.BrandProfile).first()
    if not profile:
        profile = models.BrandProfile(
            tone_of_voice="Chuyên nghiệp, đáng tin cậy",
            target_audience="Khách hàng cá nhân, chủ thầu xây dựng",
            core_values="Chất lượng cao, an toàn, thẩm mỹ",
            product_knowledge="DAFA Glass chuyên thi công kính cường lực, gương trang trí, kính ốp bếp, vách tắm kính..."
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

@router.put("/", response_model=schemas.BrandProfileResponse)
def update_brand_profile(setting: schemas.BrandProfileUpdate, db: Session = Depends(get_db)):
    """
    Cập nhật Hồ sơ Thương hiệu.
    """
    profile = db.query(models.BrandProfile).first()
    if not profile:
        profile = models.BrandProfile(**setting.model_dump(exclude_unset=True))
        db.add(profile)
    else:
        for var, value in vars(setting).items():
            if value is not None:
                setattr(profile, var, value)
    
    db.commit()
    db.refresh(profile)
    return profile
