from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User
from app.core.security import decode_access_token

router = APIRouter(tags=["Web Views"])
templates = Jinja2Templates(directory=str(settings.TEMPLATE_DIR))

def check_cookie_auth(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        return False
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return False
    return True

@router.get("/login", response_class=HTMLResponse)
def view_login(request: Request):
    """
    Trang đăng nhập.
    """
    if check_cookie_auth(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html")

@router.get("/", response_class=HTMLResponse)
def view_dashboard(request: Request):
    """
    Trang chủ Dashboard tổng quan.
    """
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="dashboard.html")

@router.get("/planner", response_class=HTMLResponse)
def view_planner(request: Request):
    """
    Trang Quản lý chiến dịch và Lập kế hoạch nội dung tháng.
    """
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="planner.html")

@router.get("/production", response_class=HTMLResponse)
def view_production(request: Request):
    """
    Trang chi tiết bài viết, chuẩn SEO và Duyệt nội dung.
    """
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="production.html")

@router.get("/analytics", response_class=HTMLResponse)
def view_analytics(request: Request):
    """
    Trang xem báo cáo biểu đồ hiệu quả.
    """
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="analytics.html")

@router.get("/settings", response_class=HTMLResponse)
def view_settings(request: Request):
    """
    Trang quản lý cài đặt hệ thống và API Keys.
    """
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="settings.html")

@router.get("/brand", response_class=HTMLResponse)
def view_brand(request: Request):
    """
    Trang quản lý Hồ sơ Thương hiệu và Sản phẩm.
    """
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="brand.html")

@router.get("/video-planner", response_class=HTMLResponse)
def view_video_planner(request: Request):
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="video_planner.html")

@router.get("/video-script", response_class=HTMLResponse)
def view_video_script(request: Request):
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="video_script.html")

@router.get("/video-studio", response_class=HTMLResponse)
def view_video_studio(request: Request):
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="video_studio.html")

@router.get("/video-channels", response_class=HTMLResponse)
def view_video_channels(request: Request):
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="video_channels.html")

@router.get("/analytics-video", response_class=HTMLResponse)
def view_analytics_video(request: Request):
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="analytics_video.html")

@router.get("/seeding/accounts", response_class=HTMLResponse)
def view_seeding_accounts(request: Request):
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="seeding_accounts.html")

@router.get("/seeding/campaigns", response_class=HTMLResponse)
def view_seeding_campaigns(request: Request):
    if not check_cookie_auth(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="seeding_campaigns.html")
