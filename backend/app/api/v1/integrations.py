from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
import google_auth_oauthlib.flow
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas

router = APIRouter(prefix="/settings/integrations", tags=["Integration Settings"])

DEFAULT_PLATFORMS = ["WordPress", "Fanpage", "GoogleAnalytics", "YouTube"]

@router.get("/", response_model=List[schemas.IntegrationSettingResponse])
def get_integration_settings(db: Session = Depends(get_db)):
    settings = db.query(models.IntegrationSetting).all()
    existing_platforms = [s.platform for s in settings]
    for platform in DEFAULT_PLATFORMS:
        if platform not in existing_platforms:
            db_setting = models.IntegrationSetting(
                platform=platform,
                url="",
                username="",
                access_token="",
                is_active=False
            )
            db.add(db_setting)
    db.commit()
    return db.query(models.IntegrationSetting).all()

@router.put("/{platform}", response_model=schemas.IntegrationSettingResponse)
def update_integration_setting(platform: str, setting: schemas.IntegrationSettingUpdate, db: Session = Depends(get_db)):
    db_setting = db.query(models.IntegrationSetting).filter(models.IntegrationSetting.platform == platform).first()
    if not db_setting:
        raise HTTPException(status_code=404, detail="Không tìm thấy cấu hình nền tảng này")

    if setting.url is not None:
        db_setting.url = setting.url
    if setting.username is not None:
        db_setting.username = setting.username
    if setting.access_token is not None:
        db_setting.access_token = setting.access_token
    if setting.is_active is not None:
        db_setting.is_active = setting.is_active

    db.commit()
    db.refresh(db_setting)
    return db_setting

@router.post("/google/auth")
def init_google_auth(req: Request, payload: dict, db: Session = Depends(get_db)):
    client_id = payload.get("client_id")
    client_secret = payload.get("client_secret")
    property_id = payload.get("property_id")
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="Thiếu Client ID hoặc Client Secret")
        
    db_setting = db.query(models.IntegrationSetting).filter(models.IntegrationSetting.platform == "GoogleAnalytics").first()
    if not db_setting:
        db_setting = models.IntegrationSetting(platform="GoogleAnalytics")
        db.add(db_setting)
        
    db_setting.username = client_id
    db_setting.access_token = client_secret
    db_setting.url = property_id
    db.commit()

    # Define scopes
    scopes = ["https://www.googleapis.com/auth/analytics.readonly"]
    
    # Check if redirect is http
    base_url_str = str(req.base_url).rstrip("/")
    if base_url_str.startswith("http://") and "localhost" not in base_url_str and "127.0.0.1" not in base_url_str:
        import os
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    else:
        import os
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" # For local development

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    
    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_config(client_config, scopes=scopes)
        redirect_uri = base_url_str + "/api/v1/settings/integrations/google/callback"
        flow.redirect_uri = redirect_uri
        
        auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/google/callback")
def google_auth_callback(req: Request, code: str, db: Session = Depends(get_db)):
    db_setting = db.query(models.IntegrationSetting).filter(models.IntegrationSetting.platform == "GoogleAnalytics").first()
    if not db_setting or not db_setting.username or not db_setting.access_token:
        return RedirectResponse(url="/settings?error=no_client_config")
        
    client_config = {
        "web": {
            "client_id": db_setting.username,
            "client_secret": db_setting.access_token,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    
    base_url_str = str(req.base_url).rstrip("/")
    
    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        flow.redirect_uri = base_url_str + "/api/v1/settings/integrations/google/callback"
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        db_setting.refresh_token = credentials.refresh_token
        db_setting.is_active = True
        db.commit()
        return RedirectResponse(url="/settings?success=google_connected")
    except Exception as e:
        return RedirectResponse(url=f"/settings?error={str(e)}")

# --- YouTube OAuth Integration ---
@router.post("/youtube/auth")
def init_youtube_auth(req: Request, payload: dict, db: Session = Depends(get_db)):
    client_id = payload.get("client_id")
    client_secret = payload.get("client_secret")

    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="Thiếu Client ID hoặc Client Secret")

    db_setting = db.query(models.IntegrationSetting).filter(models.IntegrationSetting.platform == "YouTube").first()
    if not db_setting:
        db_setting = models.IntegrationSetting(platform="YouTube")
        db.add(db_setting)

    db_setting.username = client_id.strip()
    db_setting.access_token = client_secret.strip()
    db.commit()

    scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly"
    ]

    base_url_str = str(req.base_url).rstrip("/")
    if base_url_str.startswith("http://") and "localhost" not in base_url_str and "127.0.0.1" not in base_url_str:
        import os
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    else:
        import os
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    client_config = {
        "web": {
            "client_id": db_setting.username,
            "client_secret": db_setting.access_token,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_config(client_config, scopes=scopes)
        redirect_uri = base_url_str + "/api/v1/settings/integrations/youtube/callback"
        flow.redirect_uri = redirect_uri

        auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/youtube/callback")
def youtube_auth_callback(req: Request, code: str, db: Session = Depends(get_db)):
    db_setting = db.query(models.IntegrationSetting).filter(models.IntegrationSetting.platform == "YouTube").first()
    if not db_setting or not db_setting.username or not db_setting.access_token:
        return RedirectResponse(url="/settings?error=no_youtube_client_config")

    client_config = {
        "web": {
            "client_id": db_setting.username,
            "client_secret": db_setting.access_token,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    base_url_str = str(req.base_url).rstrip("/")

    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=[
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.readonly"
            ]
        )
        flow.redirect_uri = base_url_str + "/api/v1/settings/integrations/youtube/callback"
        flow.fetch_token(code=code)

        credentials = flow.credentials
        db_setting.refresh_token = credentials.refresh_token
        db_setting.is_active = True
        db.commit()
        return RedirectResponse(url="/settings?success=youtube_connected")
    except Exception as e:
        return RedirectResponse(url=f"/settings?error={str(e)}")

# --- Google Sheets Integration ---
from pydantic import BaseModel

class GoogleSheetsConfig(BaseModel):
    spreadsheet_id: str
    credentials_json: str
    auto_sync: bool = True

@router.post("/google-sheets/config")
def save_google_sheets_config(config: GoogleSheetsConfig, db: Session = Depends(get_db)):
    """Lưu cấu hình Google Sheets cho báo cáo Seeding."""
    db_setting = db.query(models.IntegrationSetting).filter(
        models.IntegrationSetting.platform == "GoogleSheets"
    ).first()
    
    if not db_setting:
        db_setting = models.IntegrationSetting(platform="GoogleSheets")
        db.add(db_setting)
    
    db_setting.url = config.spreadsheet_id.strip()
    if config.credentials_json and config.credentials_json != "__KEEP_EXISTING__":
        db_setting.access_token = config.credentials_json.strip()
    db_setting.is_active = config.auto_sync
    db.commit()
    
    return {"status": "success", "message": "Đã lưu cấu hình Google Sheets"}

@router.get("/google-sheets/config")
def get_google_sheets_config(db: Session = Depends(get_db)):
    """Đọc cấu hình Google Sheets hiện tại."""
    db_setting = db.query(models.IntegrationSetting).filter(
        models.IntegrationSetting.platform == "GoogleSheets"
    ).first()
    
    if not db_setting:
        return {
            "spreadsheet_id": "",
            "has_credentials": False,
            "auto_sync": False
        }
    
    return {
        "spreadsheet_id": db_setting.url or "",
        "has_credentials": bool(db_setting.access_token),
        "auto_sync": db_setting.is_active if db_setting.is_active is not None else False
    }

@router.post("/google-sheets/test")
def test_google_sheets_connection(db: Session = Depends(get_db)):
    """Kiểm tra kết nối Google Sheets."""
    from app.services.google_sheets_service import get_google_sheets_service
    
    sheets_service = get_google_sheets_service(db)
    if not sheets_service:
        raise HTTPException(status_code=400, detail="Chưa cấu hình Google Sheets. Vui lòng nhập Spreadsheet ID và Service Account JSON.")
    
    try:
        # Try to read spreadsheet metadata
        result = sheets_service.service.spreadsheets().get(
            spreadsheetId=sheets_service.spreadsheet_id
        ).execute()
        title = result.get('properties', {}).get('title', 'Unknown')
        return {
            "status": "success",
            "message": f"Kết nối thành công! Spreadsheet: {title}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi kết nối: {str(e)}")

@router.post("/google-sheets/sync-history")
def sync_google_sheets_history(clear_existing: bool = False, db: Session = Depends(get_db)):
    """Đồng bộ toàn bộ lịch sử các bài đã đăng thành công (Website, Fanpage, Seeding) vào Google Sheets."""
    from app.services.google_sheets_service import get_google_sheets_service
    
    sheets_service = get_google_sheets_service(db, require_active=False)
    if not sheets_service:
        raise HTTPException(status_code=400, detail="Chưa cấu hình Google Sheets. Vui lòng kiểm tra Spreadsheet ID và Service Account JSON.")
        
    try:
        result = sheets_service.sync_all_history(db, clear_existing_sheets=clear_existing)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi đồng bộ dữ liệu: {str(e)}")

