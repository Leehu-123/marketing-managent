from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Any
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.seeding_account import SeedingAccount
from app.models.seeding_campaign import SeedingCampaign
from app.models.seeding_task import SeedingTask
from app.schemas.seeding import (
    SeedingAccountCreate, SeedingAccountUpdate, SeedingAccountResponse,
    SeedingCampaignCreate, SeedingCampaignResponse,
    SeedingTaskCreate, SeedingTaskUpdate, SeedingTaskResponse,
    GenerateContentRequest
)
from app.services.ai_service import generate_seeding_content
import json
import os
import sys
from fastapi import UploadFile, File
from typing import List as TypingList

router = APIRouter()

# --- Accounts ---

@router.post("/accounts", response_model=SeedingAccountResponse)
def create_seeding_account(
    account_in: SeedingAccountCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    account = SeedingAccount(**account_in.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account

@router.get("/accounts", response_model=List[SeedingAccountResponse])
def get_seeding_accounts(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    return db.query(SeedingAccount).offset(skip).limit(limit).all()

@router.put("/accounts/{account_id}", response_model=SeedingAccountResponse)
def update_seeding_account(
    account_id: int,
    account_in: SeedingAccountUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    account = db.query(SeedingAccount).filter(SeedingAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    update_data = account_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)
        
    db.commit()
    db.refresh(account)
    return account

@router.delete("/accounts/{account_id}")
def delete_seeding_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    account = db.query(SeedingAccount).filter(SeedingAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    db.delete(account)
    db.commit()
    return {"message": "Account deleted successfully"}

# --- Campaigns ---
import httpx

@router.post("/accounts/{account_id}/check")
async def check_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    account = db.query(SeedingAccount).filter(SeedingAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    if account.platform.lower() != "facebook":
        return {"status": account.status, "message": "Chỉ hỗ trợ check Facebook lúc này."}
        
    if not account.cookies:
        return {"status": "error", "message": "Tài khoản chưa có Cookies."}

    cookie_str = account.cookies.strip()
    cookie_dict = {}
    if cookie_str.startswith("[") and cookie_str.endswith("]"):
        try:
            cookies = json.loads(cookie_str)
            for c in cookies:
                if "name" in c and "value" in c:
                    cookie_dict[c["name"]] = c["value"]
        except Exception:
            pass
            
    if not cookie_dict:
        for item in account.cookies.split(";"):
            if "=" in item:
                k, v = item.strip().split("=", 1)
                cookie_dict[k] = v
            
    proxies = None
    if account.proxy:
        parts = account.proxy.split(":")
        if len(parts) == 4:
            ip, port, user, pwd = parts
            proxies = f"http://{user}:{pwd}@{ip}:{port}"
        elif len(parts) == 2:
            proxies = f"http://{parts[0]}:{parts[1]}"
            
    try:
        async with httpx.AsyncClient(proxy=proxies, cookies=cookie_dict, timeout=10.0, verify=False, follow_redirects=True) as client:
            resp = await client.get("https://www.facebook.com/", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"})
            final_url = str(resp.url)
            if "login" in final_url or "checkpoint" in final_url:
                account.status = "die"
                msg = "Die hoặc Checkpoint! Bị chuyển hướng sang trang đăng nhập."
            else:
                account.status = "active"
                msg = "Live! Cookie hoạt động tốt."
            db.commit()
            return {"status": account.status, "message": msg}
    except Exception as e:
        account.status = "error"
        db.commit()
        return {"status": "error", "message": f"Lỗi kết nối hoặc Proxy die: {str(e)}"}

@router.post("/campaigns", response_model=SeedingCampaignResponse)
def create_seeding_campaign(
    campaign_in: SeedingCampaignCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    campaign = SeedingCampaign(**campaign_in.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    # Auto generate tasks if target_urls is a valid JSON list
    if campaign.target_urls:
        try:
            urls = json.loads(campaign.target_urls)
            acc_ids = json.loads(campaign.account_ids) if campaign.account_ids else []
            if not isinstance(acc_ids, list):
                acc_ids = []

            for url in urls:
                if acc_ids:
                    for acc_id in acc_ids:
                        task = SeedingTask(
                            campaign_id=campaign.id,
                            account_id=acc_id,
                            target_url=url,
                            status="pending",
                            task_type=campaign.campaign_type,
                            media_urls=campaign.media_urls
                        )
                        db.add(task)
                else:
                    task = SeedingTask(
                        campaign_id=campaign.id,
                        target_url=url,
                        status="pending",
                        task_type=campaign.campaign_type,
                        media_urls=campaign.media_urls
                    )
                    db.add(task)
            db.commit()
        except Exception:
            pass # Skip if invalid JSON

    return campaign

@router.get("/campaigns", response_model=List[SeedingCampaignResponse])
def get_seeding_campaigns(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    campaigns = db.query(SeedingCampaign).order_by(SeedingCampaign.id.desc()).offset(skip).limit(limit).all()
    
    results = []
    for c in campaigns:
        tasks = db.query(SeedingTask).filter(SeedingTask.campaign_id == c.id).all()
        total = len(tasks)
        success = sum(1 for t in tasks if t.status == 'success')
        failed = sum(1 for t in tasks if t.status == 'failed')
        in_progress = sum(1 for t in tasks if t.status == 'in_progress')
        pending = sum(1 for t in tasks if t.status == 'pending')
        pct = round(((success + failed) / total * 100)) if total > 0 else 0
        
        # Tính toán tiến trình cho lần chạy hiện tại (đặc biệt hữu ích cho chiến dịch lặp hàng ngày)
        if c.is_daily_repeat and tasks:
            latest_date = max(t.created_at.date() for t in tasks)
            run_tasks = [t for t in tasks if t.created_at.date() == latest_date]
            cr_total = len(run_tasks)
            cr_success = sum(1 for t in run_tasks if t.status == 'success')
            cr_failed = sum(1 for t in run_tasks if t.status == 'failed')
            cr_in_progress = sum(1 for t in run_tasks if t.status == 'in_progress')
            cr_pending = sum(1 for t in run_tasks if t.status == 'pending')
            cr_pct = round(((cr_success + cr_failed) / cr_total * 100)) if cr_total > 0 else 0
            cr_date = latest_date.strftime("%d/%m/%Y")
        else:
            cr_total = total
            cr_success = success
            cr_failed = failed
            cr_in_progress = in_progress
            cr_pending = pending
            cr_pct = pct
            cr_date = None
        
        c_dict = {col.name: getattr(c, col.name) for col in c.__table__.columns}
        c_dict.update({
            "total_tasks": total,
            "completed_tasks": success,
            "failed_tasks": failed,
            "in_progress_tasks": in_progress,
            "pending_tasks": pending,
            "progress_percent": pct,
            "current_run_total": cr_total,
            "current_run_completed": cr_success,
            "current_run_failed": cr_failed,
            "current_run_in_progress": cr_in_progress,
            "current_run_pending": cr_pending,
            "current_run_percent": cr_pct,
            "current_run_date": cr_date
        })
        results.append(SeedingCampaignResponse(**c_dict))
    return results

@router.get("/campaigns/{campaign_id}/tasks", response_model=List[SeedingTaskResponse])
def get_campaign_tasks(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    campaign = db.query(SeedingCampaign).filter(SeedingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    tasks = db.query(SeedingTask).filter(SeedingTask.campaign_id == campaign_id).all()
    return tasks

from app.schemas.seeding import SeedingCampaignUpdate

@router.put("/campaigns/{campaign_id}", response_model=SeedingCampaignResponse)
def update_seeding_campaign(
    campaign_id: int,
    campaign_in: SeedingCampaignUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    campaign = db.query(SeedingCampaign).filter(SeedingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    update_data = campaign_in.model_dump(exclude_unset=True)
    should_rerun = update_data.pop("rerun", False)
    
    for field, value in update_data.items():
        setattr(campaign, field, value)
        
    # Re-generate tasks if rerun requested or content/targets changed or campaign completed/failed
    content_changed = any(k in update_data for k in ["target_urls", "account_ids", "post_content", "media_urls"])
    if should_rerun or content_changed or campaign.status in ["failed", "completed"]:
        # Xoá toàn bộ task cũ để chạy lại từ đầu với nội dung/tài khoản/media mới
        deleted = db.query(SeedingTask).filter(SeedingTask.campaign_id == campaign.id).delete(synchronize_session=False)
        db.flush()
        print(f"[SEEDING] Deleted {deleted} old tasks for campaign #{campaign.id}")
        campaign.status = "pending"
        try:
            urls = json.loads(campaign.target_urls) if campaign.target_urls else []
            acc_ids = json.loads(campaign.account_ids) if campaign.account_ids else []
            if not isinstance(acc_ids, list):
                acc_ids = []

            for url in urls:
                if acc_ids:
                    for acc_id in acc_ids:
                        task = SeedingTask(
                            campaign_id=campaign.id,
                            account_id=acc_id,
                            target_url=url,
                            status="pending",
                            task_type=campaign.campaign_type,
                            media_urls=campaign.media_urls
                        )
                        db.add(task)
                else:
                    task = SeedingTask(
                        campaign_id=campaign.id,
                        target_url=url,
                        status="pending",
                        task_type=campaign.campaign_type,
                        media_urls=campaign.media_urls
                    )
                    db.add(task)
        except Exception as exc:
            print(f"[SEEDING] Lỗi tái tạo tasks khi update: {exc}")
            pass
            
    db.commit()
    db.refresh(campaign)

    tasks = db.query(SeedingTask).filter(SeedingTask.campaign_id == campaign.id).all()
    total = len(tasks)
    success = sum(1 for t in tasks if t.status == 'success')
    failed = sum(1 for t in tasks if t.status == 'failed')
    in_progress = sum(1 for t in tasks if t.status == 'in_progress')
    pending = sum(1 for t in tasks if t.status == 'pending')
    pct = round(((success + failed) / total * 100)) if total > 0 else 0

    c_dict = {col.name: getattr(campaign, col.name) for col in campaign.__table__.columns}
    c_dict.update({
        "total_tasks": total,
        "completed_tasks": success,
        "failed_tasks": failed,
        "in_progress_tasks": in_progress,
        "pending_tasks": pending,
        "progress_percent": pct,
        "current_run_total": total,
        "current_run_completed": success,
        "current_run_failed": failed,
        "current_run_in_progress": in_progress,
        "current_run_pending": pending,
        "current_run_percent": pct,
        "current_run_date": None
    })
    return SeedingCampaignResponse(**c_dict)

@router.post("/campaigns/{campaign_id}/rerun")
def rerun_seeding_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Tái tạo toàn bộ task và đặt chiến dịch về pending để chạy lại từ đầu."""
    campaign = db.query(SeedingCampaign).filter(SeedingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    db.query(SeedingTask).filter(SeedingTask.campaign_id == campaign.id).delete(synchronize_session=False)
    db.flush()
    
    created_count = 0
    try:
        urls = json.loads(campaign.target_urls) if campaign.target_urls else []
        acc_ids = json.loads(campaign.account_ids) if campaign.account_ids else []
        if not isinstance(acc_ids, list):
            acc_ids = []

        for url in urls:
            if acc_ids:
                for acc_id in acc_ids:
                    task = SeedingTask(
                        campaign_id=campaign.id,
                        account_id=acc_id,
                        target_url=url,
                        status="pending",
                        task_type=campaign.campaign_type,
                        media_urls=campaign.media_urls
                    )
                    db.add(task)
                    created_count += 1
            else:
                task = SeedingTask(
                    campaign_id=campaign.id,
                    target_url=url,
                    status="pending",
                    task_type=campaign.campaign_type,
                    media_urls=campaign.media_urls
                )
                db.add(task)
                created_count += 1
    except Exception as e:
        print(f"[SEEDING] Lỗi tái tạo task khi rerun: {e}")
        
    campaign.status = "pending"
    db.commit()
    
    return {
        "status": "success",
        "message": f"Đã khởi tạo lại {created_count} task cho chiến dịch '{campaign.name}', sẵn sàng chạy!",
        "created_count": created_count
    }

from typing import Optional, List
from pydantic import BaseModel

class ToggleDailyRequest(BaseModel):
    is_daily_repeat: Optional[bool] = None

@router.post("/campaigns/{campaign_id}/toggle-daily")
def toggle_daily_schedule(
    campaign_id: int,
    payload: Optional[ToggleDailyRequest] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Bật hoặc dừng lịch chạy tự động hàng ngày của chiến dịch."""
    campaign = db.query(SeedingCampaign).filter(SeedingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    if payload and payload.is_daily_repeat is not None:
        campaign.is_daily_repeat = payload.is_daily_repeat
    else:
        campaign.is_daily_repeat = not bool(campaign.is_daily_repeat)
        
    db.commit()
    db.refresh(campaign)
    
    status_str = "đang BẬT lặp lại hàng ngày" if campaign.is_daily_repeat else "đã TẠM DỪNG lặp lại hàng ngày"
    return {
        "status": "success",
        "is_daily_repeat": campaign.is_daily_repeat,
        "daily_schedule_time": campaign.daily_schedule_time,
        "message": f"Chiến dịch '{campaign.name}' {status_str}."
    }

@router.delete("/campaigns/{campaign_id}")
def delete_seeding_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    campaign = db.query(SeedingCampaign).filter(SeedingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # Xoá các task liên quan
    db.query(SeedingTask).filter(SeedingTask.campaign_id == campaign_id).delete()
    
    # Xoá campaign
    db.delete(campaign)
    db.commit()
    return {"status": "success", "message": "Đã xoá chiến dịch"}

@router.post("/upload-media")
async def upload_seeding_media(
    files: TypingList[UploadFile] = File(...),
    current_user = Depends(get_current_user)
):
    """Upload ảnh/video cho bài đăng seeding. Trả về danh sách URL."""
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../uploads/seeding")
    os.makedirs(upload_dir, exist_ok=True)
    
    uploaded_urls = []
    for file in files:
        # Tạo tên file unique
        import uuid
        ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(upload_dir, filename)
        
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        
        uploaded_urls.append(f"/uploads/seeding/{filename}")
    
    return {"urls": uploaded_urls}

@router.post("/campaigns/{campaign_id}/generate-replies")
def generate_reply_thread(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Sinh kịch bản hội thoại reply chéo giữa các Via cho chiến dịch REPLY_COMMENT."""
    campaign = db.query(SeedingCampaign).filter(SeedingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Lấy danh sách account tham gia
    acc_ids = []
    if campaign.account_ids:
        try:
            acc_ids = json.loads(campaign.account_ids)
        except Exception:
            pass
    
    accounts = []
    if acc_ids:
        accounts = db.query(SeedingAccount).filter(SeedingAccount.id.in_(acc_ids)).all()
    else:
        accounts = db.query(SeedingAccount).filter(
            SeedingAccount.platform == campaign.platform,
            SeedingAccount.status == "active"
        ).limit(5).all()
    
    if len(accounts) < 2:
        raise HTTPException(status_code=400, detail="Cần ít nhất 2 tài khoản Via để tạo kịch bản reply chéo")
    
    # Lấy danh sách URL mục tiêu
    urls = []
    if campaign.target_urls:
        try:
            urls = json.loads(campaign.target_urls)
        except Exception:
            urls = [campaign.target_urls]
    
    if not urls:
        raise HTTPException(status_code=400, detail="Chiến dịch chưa có URL mục tiêu")
    
    # Xoá tasks cũ nếu campaign đang pending
    if campaign.status in ["pending", "failed"]:
        db.query(SeedingTask).filter(SeedingTask.campaign_id == campaign.id).delete()
    
    # Sinh kịch bản reply cho mỗi URL
    from app.services.ai_service import generate_seeding_content
    
    all_tasks = []
    for url in urls:
        # Bước 1: Via đầu tiên comment gốc
        first_acc = accounts[0]
        comment_content = generate_seeding_content(
            target_content=url,
            instructions=campaign.ai_instructions or "Comment tự nhiên như khách hàng thật",
            platform=campaign.platform,
            task_type="COMMENT"
        )
        
        parent_task = SeedingTask(
            campaign_id=campaign.id,
            account_id=first_acc.id,
            target_url=url,
            task_type="COMMENT",
            generated_content=comment_content,
            status="pending"
        )
        db.add(parent_task)
        db.flush()  # Lấy ID
        all_tasks.append(parent_task)
        
        # Bước 2: Các Via còn lại reply chéo
        prev_content = comment_content
        for i, acc in enumerate(accounts[1:], start=1):
            reply_instruction = f"Trả lời comment trước đó: '{prev_content[:100]}'. {campaign.ai_instructions or 'Hãy reply tự nhiên, thân thiện.'}"
            reply_content = generate_seeding_content(
                target_content=prev_content,
                instructions=reply_instruction,
                platform=campaign.platform,
                task_type="REPLY_COMMENT"
            )
            
            reply_task = SeedingTask(
                campaign_id=campaign.id,
                account_id=acc.id,
                target_url=url,
                task_type="REPLY_COMMENT",
                parent_task_id=parent_task.id,
                generated_content=reply_content,
                status="pending"
            )
            db.add(reply_task)
            all_tasks.append(reply_task)
            prev_content = reply_content
    
    campaign.status = "pending"
    db.commit()
    
    return {
        "status": "success",
        "message": f"Đã sinh {len(all_tasks)} task ({len(urls)} URL × {len(accounts)} Via)",
        "tasks_count": len(all_tasks)
    }

# --- Tasks (For Automation Tool) ---

@router.get("/tasks/pending", response_model=List[SeedingTaskResponse])
def get_pending_tasks(
    platform: str,
    db: Session = Depends(get_db),
    limit: int = 10
):
    # This API might be called by an external worker, maybe without user token
    # Get campaigns for the platform
    campaigns = db.query(SeedingCampaign).filter(
        SeedingCampaign.platform == platform,
        SeedingCampaign.status != "completed"
    ).all()
    
    campaign_ids = [c.id for c in campaigns]
    if not campaign_ids:
        return []
        
    tasks = db.query(SeedingTask).filter(
        SeedingTask.campaign_id.in_(campaign_ids),
        SeedingTask.status == "pending"
    ).limit(limit).all()
    
    return tasks

import os
import subprocess

# --- Biến toàn cục quản lý process Tool ---
client_tool_process = None

@router.post("/tasks/{task_id}/result")
def update_task_result(
    task_id: int,
    result_in: SeedingTaskUpdate,
    db: Session = Depends(get_db)
):
    task = db.query(SeedingTask).filter(SeedingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if result_in.status:
        task.status = result_in.status
    if result_in.error_message:
        task.error_message = result_in.error_message
    if result_in.account_id:
        task.account_id = result_in.account_id
    if result_in.generated_content:
        task.generated_content = result_in.generated_content
    
    # Ghi timestamp thực thi
    from datetime import datetime
    if result_in.status in ["success", "failed"]:
        task.executed_at = datetime.utcnow()
        
    db.commit()
    db.refresh(task)
    
    # --- Check and Update Campaign Status ---
    campaign_id = task.campaign_id
    total_tasks = db.query(SeedingTask).filter(SeedingTask.campaign_id == campaign_id).count()
    finished_tasks = db.query(SeedingTask).filter(
        SeedingTask.campaign_id == campaign_id,
        SeedingTask.status.in_(["success", "failed"])
    ).count()
    
    if total_tasks > 0 and finished_tasks == total_tasks:
        campaign = db.query(SeedingCampaign).filter(SeedingCampaign.id == campaign_id).first()
        if campaign:
            failed_tasks = db.query(SeedingTask).filter(
                SeedingTask.campaign_id == campaign_id,
                SeedingTask.status == "failed"
            ).count()
            
            # Nếu tất cả đều thất bại -> failed, ngược lại -> completed
            if failed_tasks == total_tasks:
                campaign.status = "failed"
            else:
                campaign.status = "completed"
            db.commit()

    # --- Auto-sync sang Google Sheets khi thành công ---
    if task.status == "success":
        try:
            from app.services.google_sheets_service import sync_seeding_task_to_sheets
            sync_seeding_task_to_sheets(task, db)
        except Exception as e:
            print(f"[SHEETS] Lỗi auto-sync Google Sheets: {e}")

    return {"status": "success"}

@router.post("/campaigns/{campaign_id}/export-sheets")
def export_campaign_to_sheets(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Xuất toàn bộ kết quả chiến dịch sang Google Sheets."""
    from app.services.google_sheets_service import get_google_sheets_service
    
    campaign = db.query(SeedingCampaign).filter(SeedingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Không tìm thấy chiến dịch")
    
    sheets_svc = get_google_sheets_service(db)
    if not sheets_svc:
        raise HTTPException(status_code=400, detail="Chưa cấu hình Google Sheets. Vào Cài đặt → Google Sheets để thiết lập.")
    
    try:
        result = sheets_svc.export_campaign(campaign_id, db)
        # Also update summary
        sheets_svc.update_summary_sheet(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xuất Google Sheets: {str(e)}")

@router.post("/export-sheets/summary")
def update_sheets_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cập nhật tab Tổng hợp trên Google Sheets."""
    from app.services.google_sheets_service import get_google_sheets_service
    
    sheets_svc = get_google_sheets_service(db)
    if not sheets_svc:
        raise HTTPException(status_code=400, detail="Chưa cấu hình Google Sheets")
    
    try:
        sheets_svc.update_summary_sheet(db)
        return {"status": "success", "message": "Đã cập nhật bảng Tổng hợp", "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{sheets_svc.spreadsheet_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")

# --- Tool Control Endpoints ---
from pydantic import BaseModel
class ToolStartRequest(BaseModel):
    platform: str = "facebook"
    show_browser: bool = False

@router.post("/tool/start")
def start_tool(req: ToolStartRequest, request: Request):
    global client_tool_process
    
    if client_tool_process is not None:
        if client_tool_process.poll() is None:
            return {"status": "running", "message": "Tool đang chạy rồi!"}
            
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
    
    # Tìm client_automation theo các đường dẫn khả thi
    client_dir_candidates = [
        os.path.join(project_root, "client_automation"),
        "/app/client_automation",
        "/var/www/marketing-management/client_automation",
        "/var/www/client_automation",
    ]
    
    client_dir = None
    for cd in client_dir_candidates:
        if os.path.exists(cd):
            client_dir = cd
            break
            
    if not client_dir:
        client_dir = os.path.join(project_root, "client_automation")
        
    main_script = os.path.join(client_dir, "main.py")
    
    # Danh sách ứng viên Python executable
    python_candidates = [
        os.path.join(client_dir, "venv", "Scripts", "python.exe"),
        os.path.join(client_dir, "venv", "bin", "python"),
        os.path.join(project_root, "venv", "Scripts", "python.exe"),
        os.path.join(project_root, "venv", "bin", "python"),
        sys.executable,
        "/usr/bin/python3",
        "/usr/local/bin/python"
    ]
    
    python_exe = None
    for cand in python_candidates:
        if cand and os.path.exists(cand):
            python_exe = cand
            break
            
    if not python_exe or not os.path.exists(main_script):
        return {"status": "error", "message": f"Chưa tìm thấy môi trường Python phù hợp cho Client Tool tại: {client_dir}"}
        
    # Ưu tiên localhost khi chạy trong container
    backend_url = "http://127.0.0.1:8000"
    cmd = [python_exe, main_script, "--platform", req.platform, "--backend-url", backend_url]
    if req.show_browser:
        cmd.append("--show-browser")
        
    try:
        # Popen without waiting
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        creationflags = subprocess.CREATE_NEW_CONSOLE if (sys.platform == "win32" and req.show_browser) else 0
        
        log_path = os.path.join(client_dir, "tool_log.txt")
        log_file = open(log_path, "a", encoding="utf-8")  # append mode để giữ log cũ
        
        # start_new_session=True tạo process group mới để có thể kill toàn bộ tree
        client_tool_process = subprocess.Popen(
            cmd,
            cwd=client_dir,
            env=env,
            creationflags=creationflags,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=(sys.platform != "win32")
        )
        return {"status": "success", "message": "Đã khởi động Tool Automation!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/tool/stop")
def stop_tool():
    global client_tool_process
    if client_tool_process and client_tool_process.poll() is None:
        pid = client_tool_process.pid
        try:
            # Kill entire process tree (browser + playwright + python)
            import signal
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
            else:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            try:
                client_tool_process.kill()
            except Exception:
                pass
        client_tool_process = None
        return {"status": "success", "message": "Đã dừng Tool."}
    return {"status": "idle", "message": "Tool không chạy."}

@router.get("/tool/status")
def get_tool_status():
    global client_tool_process
    if client_tool_process and client_tool_process.poll() is None:
        return {"status": "running"}
    return {"status": "idle"}

@router.get("/tool/logs")
def get_tool_logs(
    limit: int = 80,
    current_user = Depends(get_current_user)
):
    """Lấy các dòng log mới nhất của Tool Seeding Automation để theo dõi tiến trình trực tiếp."""
    candidates = [
        "/var/www/marketing-management/client_automation/tool_log.txt",
        "/app/client_automation/tool_log.txt",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../client_automation/tool_log.txt"))
    ]
    log_file = None
    for c in candidates:
        if os.path.exists(c):
            log_file = c
            break
            
    if not log_file:
        return {"status": "success", "logs": ["Chưa có dữ liệu nhật ký hoạt động. Vui lòng bấm 'Khởi động Tool' để bắt đầu."]}
        
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return {"status": "success", "logs": lines[-limit:]}
    except Exception as e:
        return {"status": "error", "logs": [f"Lỗi khi đọc file nhật ký: {str(e)}"]}

@router.post("/campaigns/{campaign_id}/run-now")
def run_campaign_now(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Reset các task failed/pending và kích hoạt tool chạy ngay."""
    campaign = db.query(SeedingCampaign).filter(SeedingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Reset task failed về pending
    reset_count = db.query(SeedingTask).filter(
        SeedingTask.campaign_id == campaign_id,
        SeedingTask.status.in_(["failed", "in_progress"])
    ).update({"status": "pending"}, synchronize_session=False)
    
    campaign.status = "pending"
    db.commit()
    
    return {"status": "success", "message": f"Đã reset {reset_count} tasks, chiến dịch sẵn sàng chạy.", "reset_count": reset_count}

# --- AI Integration ---

@router.post("/generate-content")
def generate_content(
    request: GenerateContentRequest,
    current_user = Depends(get_current_user)
):
    content = generate_seeding_content(
        target_content=request.post_content,
        instructions=request.instruction,
        platform="Unknown",
        task_type="COMMENT"
    )
    return {"generated_content": content}

# --- Client Automation Endpoints (No Auth - chạy trên máy khách) ---

from app.schemas.seeding import TaskWithDetails

@router.get("/tasks/fetch", response_model=List[TaskWithDetails])
def fetch_tasks_for_client(
    platform: str,
    db: Session = Depends(get_db),
    limit: int = 10
):
    """Endpoint dành riêng cho Client Automation. Trả về tasks kèm đầy đủ thông tin campaign + account."""
    campaigns = db.query(SeedingCampaign).filter(
        SeedingCampaign.platform == platform,
        SeedingCampaign.status.in_(["pending", "running"])
    ).all()
    
    campaign_ids = [c.id for c in campaigns]
    if not campaign_ids:
        return []
    
    campaign_map = {c.id: c for c in campaigns}
    
    tasks = db.query(SeedingTask).filter(
        SeedingTask.campaign_id.in_(campaign_ids),
        SeedingTask.status == "pending"
    ).limit(limit).all()
    
    # Khóa task sang in_progress để tránh cấp trùng
    for task in tasks:
        task.status = "in_progress"
    if tasks:
        db.commit()
    
    results = []
    for task in tasks:
        camp = campaign_map.get(task.campaign_id)
        if not camp:
            continue
            
        acc = None
        if task.account_id:
            acc = db.query(SeedingAccount).filter(SeedingAccount.id == task.account_id).first()
        
        # Nếu task chưa có account_id, lấy random 1 account active cùng platform
        if not acc:
            import random as rand_mod
            active_accounts = db.query(SeedingAccount).filter(
                SeedingAccount.platform == platform,
                SeedingAccount.status == "active"
            ).all()
            if active_accounts:
                acc = rand_mod.choice(active_accounts)
            
        # Look up parent comment content if this is a reply task
        parent_comment = None
        if task.parent_task_id:
            parent = db.query(SeedingTask).filter(SeedingTask.id == task.parent_task_id).first()
            if parent:
                parent_comment = parent.generated_content
        
        results.append(TaskWithDetails(
            id=task.id,
            campaign_id=task.campaign_id,
            account_id=acc.id if acc else None,
            target_url=task.target_url,
            status=task.status,
            campaign_name=camp.name,
            campaign_type=camp.campaign_type,
            platform=camp.platform,
            ai_instructions=camp.ai_instructions,
            account_username=acc.username if acc else None,
            account_password=acc.password if acc else None,
            account_cookies=acc.cookies if acc else None,
            account_proxy=acc.proxy if acc else None,
            account_two_fa_secret=acc.two_fa_secret if acc else None,
            task_type=task.task_type or camp.campaign_type,
            parent_task_id=task.parent_task_id,
            parent_comment_content=parent_comment,
            media_urls=task.media_urls or camp.media_urls,
            post_content=camp.post_content,
        ))
    
    # Cập nhật campaign sang running nếu có task được fetch
    if results:
        for camp_id in set(r.campaign_id for r in results):
            camp = campaign_map.get(camp_id)
            if camp and camp.status == "pending":
                camp.status = "running"
        db.commit()
    
    return results

@router.post("/client/generate-content")
def client_generate_content(
    request: GenerateContentRequest,
    platform: str = "facebook",
    task_type: str = "COMMENT"
):
    """Endpoint dành cho Client Automation - không cần auth."""
    content = generate_seeding_content(
        target_content=request.post_content,
        instructions=request.instruction,
        platform=platform,
        task_type=task_type
    )
    return {"generated_content": content}

