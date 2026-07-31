from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas

router = APIRouter(prefix="/plans", tags=["Content Plans"])

@router.put("/{id}", response_model=schemas.ContentPlanResponse)
def update_content_plan(id: int, plan: schemas.ContentPlanUpdate, db: Session = Depends(get_db)):
    """
    Cập nhật thông tin chi tiết của một kế hoạch nội dung (ví dụ: đổi ngày giờ đăng, đổi tiêu đề).
    """
    db_plan = db.query(models.ContentPlan).filter(models.ContentPlan.id == id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy kế hoạch nội dung")
    
    # Chỉ cho sửa nếu trạng thái khác Approved (hoặc cho sửa nhưng cần review lại)
    # Tuy nhiên trong SaaS nội bộ, cứ cho admin chỉnh sửa linh hoạt.
    update_data = plan.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_plan, key, value)
        
    db.commit()
    db.refresh(db_plan)
    return db_plan

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content_plan(id: int, db: Session = Depends(get_db)):
    """
    Xóa một kế hoạch nội dung khỏi danh sách.
    """
    db_plan = db.query(models.ContentPlan).filter(models.ContentPlan.id == id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy kế hoạch nội dung")
        
    db.delete(db_plan)
    db.commit()
    return None
