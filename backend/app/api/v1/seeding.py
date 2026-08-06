from fastapi import APIRouter, Depends, HTTPException, status
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
                            status="pending"
                        )
                        db.add(task)
                else:
                    task = SeedingTask(
                        campaign_id=campaign.id,
                        target_url=url,
                        status="pending"
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
    return db.query(SeedingCampaign).offset(skip).limit(limit).all()

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
    for field, value in update_data.items():
        setattr(campaign, field, value)
        
    # Re-generate tasks if target_urls changed or campaign was failed/completed
    if ("target_urls" in update_data or "account_ids" in update_data) or campaign.status in ["failed", "completed"]:
        # Xoá toàn bộ task cũ để chạy lại từ đầu
        db.query(SeedingTask).filter(SeedingTask.campaign_id == campaign.id).delete()
        campaign.status = "pending"
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
                            status="pending"
                        )
                        db.add(task)
                else:
                    task = SeedingTask(
                        campaign_id=campaign.id,
                        target_url=url,
                        status="pending"
                    )
                    db.add(task)
        except Exception:
            pass
            
    db.commit()
    db.refresh(campaign)
    return campaign

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

    return {"status": "success"}

# --- Tool Control Endpoints ---
from pydantic import BaseModel
class ToolStartRequest(BaseModel):
    platform: str = "facebook"
    show_browser: bool = False

@router.post("/tool/start")
def start_tool(req: ToolStartRequest):
    global client_tool_process
    
    if client_tool_process is not None:
        if client_tool_process.poll() is None:
            return {"status": "running", "message": "Tool đang chạy rồi!"}
            
    import platform
    
    # Xác định đường dẫn tuỳ theo hệ điều hành (Windows vs Linux)
    if platform.system() == "Windows":
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
        client_dir = os.path.join(project_root, "client_automation")
        python_exe = os.path.join(client_dir, "venv", "Scripts", "python.exe")
    else:
        # Trên VPS (Linux)
        client_dir = "/var/www/client_automation"
        python_exe = os.path.join(client_dir, "venv", "bin", "python")
    
    main_script = os.path.join(client_dir, "main.py")
    
    if not os.path.exists(python_exe):
        return {"status": "error", "message": f"Chưa cài đặt Python env cho Client Tool tại: {python_exe}"}
        
    cmd = [python_exe, main_script, "--platform", req.platform]
    if req.show_browser:
        cmd.append("--show-browser")
        
    try:
        # Popen without waiting
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        client_tool_process = subprocess.Popen(
            cmd,
            cwd=client_dir,
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE if req.show_browser else 0
        )
        return {"status": "success", "message": "Đã khởi động Tool Automation!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/tool/stop")
def stop_tool():
    global client_tool_process
    if client_tool_process and client_tool_process.poll() is None:
        client_tool_process.terminate()
        client_tool_process = None
        return {"status": "success", "message": "Đã dừng Tool."}
    return {"status": "idle", "message": "Tool không chạy."}

@router.get("/tool/status")
def get_tool_status():
    global client_tool_process
    if client_tool_process and client_tool_process.poll() is None:
        return {"status": "running"}
    return {"status": "idle"}


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
            acc = db.query(SeedingAccount).filter(
                SeedingAccount.platform == platform,
                SeedingAccount.status == "active"
            ).order_by(SeedingAccount.id).first()
        
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

