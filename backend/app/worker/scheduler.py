"""
APScheduler Background Task Scheduler
=======================================
Periodically checks for approved posts whose scheduled time has passed,
then publishes them to the appropriate platform (WordPress or Facebook).
"""

import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.models.content_plan import ContentPlan
from app.models.post import Post
from app.models.video_content import VideoDistribution
from app.models.lead import Lead
from app.services.cms_service import CMSService
from app.services.meta_service import MetaService
from app.services.tiktok_service import TikTokService
from app.services.youtube_service import YouTubeService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# Module-level scheduler instance
_scheduler: AsyncIOScheduler | None = None


async def _publish_due_posts():
    """
    Core scheduled job: find all posts with status='Approved' whose
    content_plan.scheduled_at <= now, and publish them to the correct platform.
    """
    db = SessionLocal()
    now = datetime.now()

    try:
        # Query for posts that are approved and past their scheduled time
        due_posts = (
            db.query(Post)
            .join(ContentPlan, Post.content_plan_id == ContentPlan.id)
            .filter(
                Post.status == "Approved",
                ContentPlan.scheduled_at <= now,
            )
            .all()
        )

        if not due_posts:
            return

        logger.info(f"[SCHEDULER] Found {len(due_posts)} post(s) due for publishing.")

        for post in due_posts:
            content_plan = post.content_plan
            platform = content_plan.platform  # "Web" or "Fanpage"
            post_format = content_plan.format  # "Long article", "Image post", "Video"

            logger.info(
                f"[SCHEDULER] Publishing post #{post.id} "
                f"('{post.title[:40]}') to {platform} [{post_format}]"
            )

            try:
                result = None

                # ----- WORDPRESS (Web) -----
                if platform == "Web":
                    result = await CMSService.publish_post(
                        title=post.title,
                        body=post.body or "",
                        meta_title=post.meta_title,
                        meta_description=post.meta_description,
                        media_url=post.media_url,
                    )

                # ----- FACEBOOK FANPAGE -----
                elif platform == "Fanpage":
                    result = await MetaService.publish_post(
                        title=post.title,
                        body=post.body or "",
                        post_format=post_format,
                        media_url=post.media_url,
                    )

                else:
                    logger.warning(
                        f"[SCHEDULER] Unknown platform '{platform}' for post #{post.id}. Skipping."
                    )
                    continue

                # ----- Update post status based on result -----
                if result and result.get("success"):
                    post.status = "Published"
                    post.published_at = datetime.now()
                    post.published_url = result.get("url", "")
                    logger.info(
                        f"[SCHEDULER] [OK] Post #{post.id} published successfully: {post.published_url}"
                    )
                else:
                    post.status = "Failed"
                    error_msg = result.get("error", "Unknown error") if result else "No result returned"
                    logger.error(
                        f"[SCHEDULER] [FAILED] Post #{post.id} failed to publish: {error_msg}"
                    )

            except Exception as exc:
                post.status = "Failed"
                logger.error(
                    f"[SCHEDULER] [FAILED] Exception while publishing post #{post.id}: {exc}",
                    exc_info=True,
                )

            # Commit after each post so partial successes are saved
            db.commit()

    except Exception as exc:
        logger.error(f"[SCHEDULER] Critical error in publish job: {exc}", exc_info=True)
        db.rollback()
    finally:
        db.close()


async def _publish_due_videos():
    """Find VideoDistributions with status='Scheduled' or 'Pending' and scheduled_at <= now"""
    db = SessionLocal()
    now = datetime.now()
    try:
        due_videos = db.query(VideoDistribution).filter(
            VideoDistribution.status.in_(["Pending", "Scheduled"]),
            VideoDistribution.scheduled_at <= now,
            VideoDistribution.retry_count < 5
        ).all()
        
        for dist in due_videos:
            logger.info(f"[SCHEDULER] Publishing VideoDistribution #{dist.id} to {dist.platform}")
            try:
                # Use processed URL or fallback to source URL
                video_url = dist.processed_video_url or (dist.video_content.source_video_url if dist.video_content else None)
                if not video_url:
                    raise Exception("No video URL found for distribution")
                    
                post_id = None
                if dist.platform == "TikTok":
                    post_id = TikTokService.upload_video(video_url, dist.caption)
                elif dist.platform == "YouTube":
                    post_id = YouTubeService.upload_short(video_url, {"title": dist.title, "description": dist.description})
                else: # Facebook
                    post_id = f"fb_video_{dist.id}"
                
                dist.platform_post_id = post_id
                dist.status = "Published"
                dist.published_at = datetime.now()
            except Exception as e:
                dist.status = "Failed"
                dist.last_error = str(e)
                dist.retry_count += 1
                logger.error(f"[SCHEDULER] Failed to publish VideoDistribution #{dist.id}: {e}")
            
            db.commit()
    except Exception as exc:
        logger.error(f"[SCHEDULER] Error in _publish_due_videos: {exc}")
    finally:
        db.close()

async def _create_daily_seeding_tasks():
    """Tạo batch seeding tasks cho các chiến dịch có lịch đăng hàng ngày."""
    db = SessionLocal()
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    today_str = now.strftime("%Y-%m-%d")
    
    try:
        from app.models.seeding_campaign import SeedingCampaign
        from app.models.seeding_task import SeedingTask
        from app.models.seeding_account import SeedingAccount
        import json
        
        # Tìm các campaign có lịch đăng hàng ngày
        daily_campaigns = db.query(SeedingCampaign).filter(
            SeedingCampaign.is_daily_repeat == True,
            SeedingCampaign.daily_schedule_time != None,
            SeedingCampaign.status.in_(["pending", "running", "completed"])
        ).all()
        
        for campaign in daily_campaigns:
            schedule_time = campaign.daily_schedule_time  # VD: "08:30"
            if not schedule_time:
                continue
                
            # Chỉ chạy nếu đúng giờ (trong khoảng 1 phút)
            if current_time != schedule_time:
                continue
            
            # Kiểm tra đã tạo task hôm nay chưa (tránh trùng lặp)
            existing_today = db.query(SeedingTask).filter(
                SeedingTask.campaign_id == campaign.id,
                SeedingTask.created_at >= datetime.strptime(today_str, "%Y-%m-%d")
            ).first()
            
            if existing_today:
                continue  # Đã tạo hôm nay rồi
            
            # Tạo tasks mới
            urls = []
            if campaign.target_urls:
                try:
                    urls = json.loads(campaign.target_urls)
                except Exception:
                    continue
            
            acc_ids = []
            if campaign.account_ids:
                try:
                    acc_ids = json.loads(campaign.account_ids)
                except Exception:
                    pass
            
            for url in urls:
                if acc_ids:
                    for acc_id in acc_ids:
                        task = SeedingTask(
                            campaign_id=campaign.id,
                            account_id=acc_id,
                            target_url=url,
                            task_type=campaign.campaign_type,
                            media_urls=campaign.media_urls,
                            status="pending"
                        )
                        db.add(task)
                else:
                    task = SeedingTask(
                        campaign_id=campaign.id,
                        target_url=url,
                        task_type=campaign.campaign_type,
                        media_urls=campaign.media_urls,
                        status="pending"
                    )
                    db.add(task)
            
            campaign.status = "pending"  # Reset để tool có thể pick up
            logger.info(f"[SCHEDULER] Created daily seeding tasks for campaign #{campaign.id} '{campaign.name}'")
        
        db.commit()
    except Exception as exc:
        logger.error(f"[SCHEDULER] Error in _create_daily_seeding_tasks: {exc}")
        db.rollback()
    finally:
        db.close()


# ============================================================
# Stale Task Recovery & Tool Health Check
# ============================================================

STALE_TASK_TIMEOUT_MINUTES = 15
MAX_TASK_RETRIES = 3
MAX_TOOL_AUTO_RESTARTS = 3

# Tool tracking state (shared with seeding.py via import)
tool_crash_info = {
    "last_crash_at": None,
    "auto_restart_count": 0,
    "tool_started_at": None,
}


async def _recover_stale_seeding_tasks():
    """
    Quét và phục hồi các seeding tasks bị kẹt ở trạng thái 'in_progress' quá lâu.
    - Tasks in_progress > STALE_TASK_TIMEOUT_MINUTES phút → reset về 'pending'
    - Nếu retry_count >= MAX_TASK_RETRIES → đánh dấu 'failed'
    """
    from app.models.seeding_campaign import SeedingCampaign
    from app.models.seeding_task import SeedingTask

    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=STALE_TASK_TIMEOUT_MINUTES)

        # Tìm tasks in_progress đã quá thời gian chờ
        stale_tasks = db.query(SeedingTask).filter(
            SeedingTask.status == "in_progress",
            SeedingTask.created_at <= cutoff
        ).all()

        if not stale_tasks:
            return

        recovered = 0
        marked_failed = 0

        for task in stale_tasks:
            if task.retry_count >= MAX_TASK_RETRIES:
                task.status = "failed"
                task.error_message = f"Timeout — task không hoàn thành sau {MAX_TASK_RETRIES} lần thử. Có thể tool bị crash hoặc Facebook chặn."
                task.executed_at = datetime.utcnow()
                marked_failed += 1
            else:
                task.status = "pending"
                task.retry_count = (task.retry_count or 0) + 1
                task.error_message = None
                recovered += 1

        db.commit()

        if recovered > 0 or marked_failed > 0:
            logger.info(
                f"[SCHEDULER] Stale task recovery: {recovered} reset to pending, "
                f"{marked_failed} marked as failed"
            )

        # Kiểm tra và cập nhật trạng thái campaign nếu tất cả tasks đã hoàn thành
        campaign_ids = set(t.campaign_id for t in stale_tasks)
        for cid in campaign_ids:
            total = db.query(SeedingTask).filter(SeedingTask.campaign_id == cid).count()
            finished = db.query(SeedingTask).filter(
                SeedingTask.campaign_id == cid,
                SeedingTask.status.in_(["success", "failed"])
            ).count()
            if total > 0 and finished == total:
                camp = db.query(SeedingCampaign).filter(SeedingCampaign.id == cid).first()
                if camp and camp.status == "running":
                    all_failed = db.query(SeedingTask).filter(
                        SeedingTask.campaign_id == cid,
                        SeedingTask.status == "failed"
                    ).count()
                    camp.status = "failed" if all_failed == total else "completed"
                    logger.info(f"[SCHEDULER] Campaign #{cid} auto-completed → {camp.status}")
                    db.commit()

    except Exception as exc:
        logger.error(f"[SCHEDULER] Error in _recover_stale_seeding_tasks: {exc}")
        db.rollback()
    finally:
        db.close()


async def _check_tool_health():
    """
    Giám sát process của client automation tool.
    Nếu tool đã crash (process exited) và vẫn còn campaigns active → tự động restart.
    Giới hạn MAX_TOOL_AUTO_RESTARTS lần restart liên tiếp.
    """
    from app.api.v1.seeding import client_tool_process, start_tool_internal

    if client_tool_process is None:
        return  # Tool chưa từng được start, bỏ qua

    if client_tool_process.poll() is None:
        # Tool đang chạy bình thường — reset counter
        if tool_crash_info["auto_restart_count"] > 0:
            tool_crash_info["auto_restart_count"] = 0
        return

    # Tool đã exit (crash hoặc tự kết thúc)
    tool_crash_info["last_crash_at"] = datetime.utcnow().isoformat()
    logger.warning(f"[SCHEDULER] Client tool process exited (code={client_tool_process.returncode})")

    # Kiểm tra còn campaigns active không
    from app.models.seeding_campaign import SeedingCampaign
    db = SessionLocal()
    try:
        active = db.query(SeedingCampaign).filter(
            SeedingCampaign.status.in_(["pending", "running"])
        ).count()

        if active == 0:
            logger.info("[SCHEDULER] No active campaigns — tool restart skipped")
            return

        if tool_crash_info["auto_restart_count"] >= MAX_TOOL_AUTO_RESTARTS:
            logger.error(
                f"[SCHEDULER] Tool đã crash {MAX_TOOL_AUTO_RESTARTS} lần liên tiếp — "
                f"dừng auto-restart. Cần kiểm tra thủ công."
            )
            return

        # Auto-restart
        tool_crash_info["auto_restart_count"] += 1
        logger.info(
            f"[SCHEDULER] Auto-restarting tool (attempt {tool_crash_info['auto_restart_count']}"
            f"/{MAX_TOOL_AUTO_RESTARTS})"
        )
        start_tool_internal(platform="facebook")

    except Exception as exc:
        logger.error(f"[SCHEDULER] Error in _check_tool_health: {exc}")
    finally:
        db.close()


def start_scheduler() -> AsyncIOScheduler:
    """
    Create and start the APScheduler instance.
    Should be called from FastAPI's lifespan startup event.

    Returns:
        The running AsyncIOScheduler instance.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("[SCHEDULER] Scheduler is already running. Skipping start.")
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _publish_due_posts,
        trigger=IntervalTrigger(seconds=60),
        id="publish_due_posts",
        name="Publish approved posts on schedule",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )
    _scheduler.add_job(
        _publish_due_videos,
        trigger=IntervalTrigger(seconds=60),
        id="publish_due_videos",
        name="Publish scheduled videos",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _create_daily_seeding_tasks,
        trigger=IntervalTrigger(seconds=60),
        id="create_daily_seeding_tasks",
        name="Create daily seeding tasks on schedule",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _recover_stale_seeding_tasks,
        trigger=IntervalTrigger(seconds=300),  # Mỗi 5 phút
        id="recover_stale_seeding_tasks",
        name="Recover stale in_progress seeding tasks",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _check_tool_health,
        trigger=IntervalTrigger(seconds=120),  # Mỗi 2 phút
        id="check_tool_health",
        name="Check client automation tool health",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()

    logger.info("[SCHEDULER] [OK] Background scheduler started (interval=60s).")
    print("[SCHEDULER] [OK] Background scheduler started - checking for due posts every 60 seconds.")

    return _scheduler


def stop_scheduler():
    """
    Gracefully shut down the scheduler.
    Should be called from FastAPI's lifespan shutdown event.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] [STOPPED] Background scheduler stopped.")
        print("[SCHEDULER] [STOPPED] Background scheduler stopped.")
    else:
        logger.info("[SCHEDULER] Scheduler was not running. Nothing to stop.")

    _scheduler = None


def get_scheduler() -> AsyncIOScheduler | None:
    """Return the current scheduler instance (or None if not started)."""
    return _scheduler
