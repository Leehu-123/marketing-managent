from fastapi import APIRouter, Depends
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.plans import router as plans_router
from app.api.v1.posts import router as posts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.settings import router as settings_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.image_gen import router as image_gen_router
from app.api.v1.auth import router as auth_router
from app.api.v1.brand import router as brand_router
from app.api.deps import get_current_user

api_router = APIRouter(prefix="/api/v1")

# Auth router không bị protect để còn đăng nhập được
api_router.include_router(auth_router)

# Protect các router còn lại
protected_dependencies = [Depends(get_current_user)]

api_router.include_router(campaigns_router, dependencies=protected_dependencies)
api_router.include_router(plans_router, dependencies=protected_dependencies)
api_router.include_router(posts_router, dependencies=protected_dependencies)
api_router.include_router(analytics_router, dependencies=protected_dependencies)
api_router.include_router(settings_router, dependencies=protected_dependencies)
api_router.include_router(integrations_router, dependencies=protected_dependencies)
api_router.include_router(image_gen_router, dependencies=protected_dependencies)
api_router.include_router(brand_router, dependencies=protected_dependencies)

# New Video & CRM Routers
from app.api.v1.video_channels import router as video_channels_router
from app.api.v1.video_plans import router as video_plans_router
from app.api.v1.video_scripts import router as video_scripts_router
from app.api.v1.video_contents import router as video_contents_router
from app.api.v1.video_distributions import router as video_distributions_router

from app.api.v1.notifications_api import router as notifications_router

api_router.include_router(video_channels_router, prefix="/video-channels", tags=["video-channels"], dependencies=protected_dependencies)
api_router.include_router(video_plans_router, prefix="/video-plans", tags=["video-plans"])
api_router.include_router(video_scripts_router, prefix="/video-scripts", tags=["video-scripts"], dependencies=protected_dependencies)
api_router.include_router(video_contents_router, prefix="/video-contents", tags=["video-contents"], dependencies=protected_dependencies)
api_router.include_router(video_distributions_router, prefix="/video-distributions", tags=["video-distributions"], dependencies=protected_dependencies)

api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"], dependencies=protected_dependencies)

from app.api.v1.seeding import router as seeding_router
api_router.include_router(seeding_router, prefix="/seeding", tags=["seeding"])
