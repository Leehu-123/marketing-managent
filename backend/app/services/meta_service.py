"""
Facebook Meta Graph API Integration Service
=============================================
Handles publishing content to Facebook Fanpage and fetching Insights metrics.
Supports MOCK mode for development and REAL mode for production.
"""

import random
import logging
from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Meta Graph API base URL
META_GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class MetaService:
    """Service class for Facebook Meta Graph API integration."""

    @staticmethod
    async def publish_post(
        title: str,
        body: str,
        post_format: str = "Image post",
        media_url: Optional[str] = None,
        media_urls: Optional[list] = None,
    ) -> dict:
        """
        Publish a post to the configured Facebook Fanpage.
        """
        from app.core.database import SessionLocal
        from app.models.setting import IntegrationSetting
        
        db = SessionLocal()
        try:
            meta_setting = db.query(IntegrationSetting).filter(
                IntegrationSetting.platform == "Fanpage",
                IntegrationSetting.is_active == True
            ).first()
        finally:
            db.close()

        if meta_setting and meta_setting.url and meta_setting.access_token:
            return await MetaService._real_publish(title, body, post_format, media_url, media_urls)

        if settings.MOCK_META:
            return MetaService._mock_publish(title, body, post_format, media_url, media_urls)
        else:
            return await MetaService._real_publish(title, body, post_format, media_url, media_urls)

    @staticmethod
    def _mock_publish(
        title: str,
        body: str,
        post_format: str,
        media_url: Optional[str],
        media_urls: Optional[list] = None,
    ) -> dict:
        """Simulate publishing a post to Facebook Fanpage in MOCK mode."""
        fake_post_id = f"{settings.META_PAGE_ID}_{random.randint(100000000000, 999999999999)}"
        fake_url = f"https://www.facebook.com/{settings.META_PAGE_ID}/posts/{fake_post_id}"

        format_label = post_format.lower()
        logger.info(
            f"[MOCK META] Published {format_label} to Fanpage: "
            f"title='{title[:50]}...', post_id={fake_post_id}"
        )
        all_urls = media_urls if media_urls else ([media_url] if media_url else [])
        if all_urls:
            logger.info(f"[MOCK META] Media attached: {all_urls}")

        print(f"[MOCK META] ✅ Successfully published {format_label} post.")
        print(f"[MOCK META]    Post ID : {fake_post_id}")
        print(f"[MOCK META]    URL     : {fake_url}")

        return {
            "success": True,
            "post_id": fake_post_id,
            "url": fake_url,
            "error": None,
        }

    @staticmethod
    async def _real_publish(
        title: str,
        body: str,
        post_format: str,
        media_url: Optional[str],
        media_urls: Optional[list] = None,
    ) -> dict:
        """Publish a post using the real Meta Graph API."""
        from app.core.database import SessionLocal
        from app.models.setting import IntegrationSetting
        import json
        
        db = SessionLocal()
        try:
            meta_setting = db.query(IntegrationSetting).filter(IntegrationSetting.platform == "Fanpage", IntegrationSetting.is_active == True).first()
            if meta_setting:
                page_id = meta_setting.username
                access_token = meta_setting.access_token
            else:
                page_id = settings.META_PAGE_ID
                access_token = settings.META_PAGE_ACCESS_TOKEN
        finally:
            db.close()

        if not page_id or not access_token:
            error_msg = "META_PAGE_ID or META_PAGE_ACCESS_TOKEN is not configured."
            logger.error(f"[META] {error_msg}")
            return {"success": False, "post_id": None, "url": None, "error": error_msg}

        fanpage_signature = (
            "\n\n------------------\n"
            "DAFA Glass - Kính chuẩn, Nhà sang\n"
            "Website: https://dafaglass.com/\n"
            "Fanpage: https://www.facebook.com/dafaglass\n"
            "Instagram: https://www.instagram.com/dafagroupvn/\n"
            "Tiktok: https://www.tiktok.com/@dafa.glass\n"
            "Youtube: https://www.youtube.com/@Dafaglass\n"
            "Địa chỉ: Lô 32, đường Thủ Dầu Một, Cụm công nghiệp Bắc Duyên Hải, Phường Lào Cai, Tỉnh Lào Cai\n"
            "Số điện thoại: 0588.88.7989"
        )
        message_text = f"{title}\n\n{body}{fanpage_signature}"
        all_urls = media_urls if media_urls and len(media_urls) > 0 else ([media_url] if media_url else [])

        # Tự động nhận diện định dạng thực tế từ phần mở rộng file media
        # Ngăn chặn trường hợp content_plan ghi "Video" nhưng user lại upload ảnh PNG/JPG dẫn đến bị biến thành Reel
        video_extensions = ('.mp4', '.mov', '.avi', '.webm', '.mkv')
        image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
        
        has_video = False
        has_image = False
        check_urls = list(all_urls)
        if media_url and media_url not in check_urls:
            check_urls.append(media_url)
            
        for u in check_urls:
            clean_u = u.lower().split('?')[0].strip()
            if any(clean_u.endswith(ext) for ext in video_extensions):
                has_video = True
            elif any(clean_u.endswith(ext) for ext in image_extensions):
                has_image = True

        effective_format = post_format.lower()
        if has_video:
            effective_format = "video"
        elif has_image:
            effective_format = "image post"
            
        logger.info(f"[META] post_format='{post_format}', media detected -> effective_format='{effective_format}'")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # ----------------------------------------------------------
                # TEXT POST  (Long article / default fallback)
                # ----------------------------------------------------------
                if effective_format in ("long article", "text") and not all_urls:
                    endpoint = f"{META_GRAPH_API_BASE}/me/feed"
                    payload = {
                        "message": message_text,
                        "access_token": access_token,
                    }
                    response = await client.post(endpoint, data=payload)

                # ----------------------------------------------------------
                # IMAGE POST
                # ----------------------------------------------------------
                elif effective_format == "image post" or (has_image and not has_video):
                    if all_urls:
                        fbids = []
                        upload_endpoint = f"{META_GRAPH_API_BASE}/me/photos"
                        for url in all_urls:
                            upload_payload = {
                                "published": "false",
                                "access_token": access_token,
                            }
                            media_fbid = None
                            if url.startswith("http"):
                                upload_payload["url"] = url
                                upload_response = await client.post(upload_endpoint, data=upload_payload)
                                upload_response.raise_for_status()
                                media_fbid = upload_response.json().get("id")
                            else:
                                from app.core.config import settings
                                import os
                                local_path = str(settings.UPLOAD_DIR / url.strip("/").replace("uploads/", ""))
                                if os.path.exists(local_path):
                                    with open(local_path, "rb") as f:
                                        file_content = f.read()
                                    files = {"source": ("image.png", file_content, "image/png")}
                                    upload_response = await client.post(upload_endpoint, data=upload_payload, files=files)
                                    upload_response.raise_for_status()
                                    media_fbid = upload_response.json().get("id")
                                else:
                                    logger.error(f"[META] Image file not found: {local_path}")
                            if media_fbid:
                                fbids.append(media_fbid)

                        # Step 2: Create Feed Post with attached media
                        if fbids:
                            feed_endpoint = f"{META_GRAPH_API_BASE}/me/feed"
                            attached_media = json.dumps([{"media_fbid": fbid} for fbid in fbids])
                            feed_payload = {
                                "message": message_text,
                                "attached_media": attached_media,
                                "access_token": access_token
                            }
                            response = await client.post(feed_endpoint, data=feed_payload)
                        else:
                            return {"success": False, "post_id": None, "url": None, "error": "Failed to upload any photo"}
                    else:
                        endpoint = f"{META_GRAPH_API_BASE}/me/feed"
                        payload = {"message": message_text, "access_token": access_token}
                        response = await client.post(endpoint, data=payload)

                # ----------------------------------------------------------
                # VIDEO POST
                # ----------------------------------------------------------
                elif effective_format == "video" and has_video:
                    endpoint = f"{META_GRAPH_API_BASE}/me/videos"
                    payload = {
                        "description": message_text,
                        "access_token": access_token,
                    }
                    if media_url:
                        if media_url.startswith("http"):
                            payload["file_url"] = media_url
                            response = await client.post(endpoint, data=payload)
                        else:
                            from app.core.config import settings
                            import os
                            local_path = str(settings.UPLOAD_DIR / media_url.strip("/").replace("uploads/", ""))
                            if os.path.exists(local_path):
                                with open(local_path, "rb") as f:
                                    file_content = f.read()
                                files = {"source": ("video.mp4", file_content, "video/mp4")}
                                response = await client.post(endpoint, data=payload, files=files)
                            else:
                                logger.error(f"[META] Video file not found: {local_path}")
                                return {"success": False, "post_id": None, "url": None, "error": f"Video file not found: {media_url}"}
                    else:
                        endpoint = f"{META_GRAPH_API_BASE}/me/feed"
                        payload = {"message": message_text, "access_token": access_token}
                        response = await client.post(endpoint, data=payload)

                # ----------------------------------------------------------
                # UNKNOWN FORMAT – fall back to text
                # ----------------------------------------------------------
                else:
                    logger.warning(
                        f"[META] Unknown post format '{post_format}', falling back to text post."
                    )
                    endpoint = f"{META_GRAPH_API_BASE}/me/feed"
                    payload = {
                        "message": message_text,
                        "access_token": access_token,
                    }
                    response = await client.post(endpoint, data=payload)

                # --- Process response ---
                response.raise_for_status()
                data = response.json()

                post_id = data.get("id") or data.get("post_id", "unknown")
                post_url = f"https://www.facebook.com/{post_id}"

                logger.info(f"[META] ✅ Published successfully. Post ID: {post_id}")
                return {
                    "success": True,
                    "post_id": str(post_id),
                    "url": post_url,
                    "error": None,
                }

        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text
            logger.error(f"[META] HTTP {exc.response.status_code} error: {error_body}")
            return {
                "success": False,
                "post_id": None,
                "url": None,
                "error": f"HTTP {exc.response.status_code}: {error_body}",
            }
        except httpx.RequestError as exc:
            logger.error(f"[META] Request error: {exc}")
            return {
                "success": False,
                "post_id": None,
                "url": None,
                "error": f"Request error: {str(exc)}",
            }
        except Exception as exc:
            logger.error(f"[META] Unexpected error: {exc}")
            return {
                "success": False,
                "post_id": None,
                "url": None,
                "error": f"Unexpected error: {str(exc)}",
            }

    # ------------------------------------------------------------------
    # INSIGHTS
    # ------------------------------------------------------------------

    @staticmethod
    async def fetch_insights(post_id: str) -> dict:
        """
        Fetch Facebook Insights metrics for a given post.

        Args:
            post_id: The Facebook post ID.

        Returns:
            dict with keys: success, reach, engagement, video_views, error
        """
        if settings.MOCK_META:
            return MetaService._mock_fetch_insights(post_id)
        else:
            return await MetaService._real_fetch_insights(post_id)

    @staticmethod
    def _mock_fetch_insights(post_id: str) -> dict:
        """Return simulated Facebook Insights data in MOCK mode."""
        reach = random.randint(200, 50000)
        video_views = random.randint(0, int(reach * 0.6))
        clicks = random.randint(10, int(reach * 0.1))
        reactions = random.randint(5, int(reach * 0.05))
        shares = random.randint(0, int(reactions * 0.2))
        comments = random.randint(0, int(reactions * 0.3))
        engagement = reactions + shares + comments + clicks

        print(f"[MOCK META] 📊 Fetched Insights for post {post_id}")
        print(f"[MOCK META]    Reach       : {reach:,}")
        print(f"[MOCK META]    Engagement  : {engagement:,}")
        print(f"[MOCK META]    Video Views : {video_views:,}")
        print(f"[MOCK META]    Clicks      : {clicks:,}")

        logger.info(
            f"[MOCK META] Insights for {post_id}: "
            f"reach={reach}, engagement={engagement}, video_views={video_views}"
        )

        return {
            "success": True,
            "reach": reach,
            "engagement": engagement,
            "video_views": video_views,
            "clicks": clicks,
            "reactions": reactions,
            "shares": shares,
            "comments": comments,
            "error": None,
        }

    @staticmethod
    async def _real_fetch_insights(post_id: str) -> dict:
        """Fetch real Insights data from Meta Graph API."""
        from app.core.database import SessionLocal
        from app.models.setting import IntegrationSetting
        
        db = SessionLocal()
        try:
            meta_setting = db.query(IntegrationSetting).filter(IntegrationSetting.platform == "Fanpage", IntegrationSetting.is_active == True).first()
            if meta_setting:
                access_token = meta_setting.access_token
            else:
                access_token = settings.META_PAGE_ACCESS_TOKEN
        finally:
            db.close()

        if not access_token:
            error_msg = "META_PAGE_ACCESS_TOKEN is not configured."
            logger.error(f"[META] {error_msg}")
            return {
                "success": False,
                "reach": 0,
                "engagement": 0,
                "video_views": 0,
                "error": error_msg,
            }

        metrics = "post_impressions,post_engaged_users,post_video_views"
        endpoint = f"{META_GRAPH_API_BASE}/{post_id}/insights"
        params = {
            "metric": metrics,
            "access_token": access_token,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()

            # Parse the insights response
            reach = 0
            engagement = 0
            video_views = 0
            clicks = 0
            reactions = 0
            shares = 0
            comments = 0

            for item in data.get("data", []):
                metric_name = item.get("name", "")
                values = item.get("values", [{}])
                value = values[0].get("value", 0) if values else 0

                if metric_name == "post_impressions":
                    reach = value
                elif metric_name == "post_engaged_users":
                    engagement = value
                elif metric_name == "post_video_views":
                    video_views = value

            logger.info(
                f"[META] Insights for {post_id}: "
                f"reach={reach}, engagement={engagement}, video_views={video_views}"
            )

            return {
                "success": True,
                "reach": reach,
                "engagement": engagement,
                "video_views": video_views,
                "clicks": clicks,
                "reactions": reactions,
                "shares": shares,
                "comments": comments,
                "error": None,
            }

        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text
            logger.error(f"[META] Insights HTTP {exc.response.status_code}: {error_body}")
            return {
                "success": False,
                "reach": 0,
                "engagement": 0,
                "video_views": 0,
                "clicks": 0,
                "reactions": 0,
                "shares": 0,
                "comments": 0,
                "error": f"HTTP {exc.response.status_code}: {error_body}",
            }
        except httpx.RequestError as exc:
            logger.error(f"[META] Insights request error: {exc}")
            return {
                "success": False,
                "reach": 0,
                "engagement": 0,
                "video_views": 0,
                "clicks": 0,
                "reactions": 0,
                "shares": 0,
                "comments": 0,
                "error": f"Request error: {str(exc)}",
            }
        except Exception as exc:
            logger.error(f"[META] Insights unexpected error: {exc}")
            return {
                "success": False,
                "reach": 0,
                "engagement": 0,
                "video_views": 0,
                "clicks": 0,
                "reactions": 0,
                "shares": 0,
                "comments": 0,
                "error": f"Unexpected error: {str(exc)}",
            }

    @staticmethod
    async def upload_video_to_facebook(
        file_path: str,
        title: str,
        description: str = "",
        channel_token: Optional[str] = None,
        channel_page_id: Optional[str] = None,
    ) -> dict:
        """
        Upload video trực tiếp lên Facebook Fanpage qua Meta Graph API.
        Hỗ trợ token riêng của VideoChannel hoặc token chung từ IntegrationSetting.
        """
        import os
        from app.core.database import SessionLocal
        from app.models.setting import IntegrationSetting
        from app.services.youtube_service import resolve_local_video_path

        # 1. Resolve Access Token & Page ID
        db = SessionLocal()
        page_id = channel_page_id
        access_token = channel_token
        try:
            if not access_token or not page_id:
                meta_setting = db.query(IntegrationSetting).filter(
                    IntegrationSetting.platform == "Fanpage",
                    IntegrationSetting.is_active == True
                ).first()
                if meta_setting:
                    page_id = page_id or meta_setting.username or settings.META_PAGE_ID
                    access_token = access_token or meta_setting.access_token or settings.META_PAGE_ACCESS_TOKEN
                else:
                    page_id = page_id or settings.META_PAGE_ID
                    access_token = access_token or settings.META_PAGE_ACCESS_TOKEN
        finally:
            db.close()

        if settings.MOCK_META:
            fake_id = f"fb_video_{random.randint(100000000000, 999999999999)}"
            logger.info(f"[MOCK META] Đã giả lập upload video Facebook: {title} -> {fake_id}")
            return {
                "success": True,
                "post_id": fake_id,
                "url": f"https://www.facebook.com/{fake_id}",
                "is_mock": True,
                "error": None
            }

        if not page_id or not access_token:
            return {
                "success": False,
                "post_id": None,
                "url": None,
                "error": "Chưa cấu hình Meta Page ID hoặc Access Token cho Fanpage."
            }

        # 2. Tìm file video vật lý
        resolved_file = resolve_local_video_path(file_path)
        if not resolved_file or not os.path.exists(resolved_file):
            return {
                "success": False,
                "post_id": None,
                "url": None,
                "error": f"Không tìm thấy file video tại: {file_path}"
            }

        # 3. Post lên Graph API /{page_id}/videos
        endpoint = f"{META_GRAPH_API_BASE}/{page_id}/videos"
        msg = f"{title}\n\n{description}" if description else title
        payload = {
            "title": title,
            "description": msg,
            "access_token": access_token
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                with open(resolved_file, "rb") as f:
                    file_content = f.read()
                files = {"source": ("video.mp4", file_content, "video/mp4")}
                resp = await client.post(endpoint, data=payload, files=files)
                resp.raise_for_status()
                data = resp.json()
                video_id = data.get("id") or data.get("post_id")
                return {
                    "success": True,
                    "post_id": str(video_id),
                    "url": f"https://www.facebook.com/{video_id}",
                    "is_mock": False,
                    "error": None
                }
        except httpx.HTTPStatusError as exc:
            err = exc.response.text
            logger.error(f"[META VIDEO] HTTP {exc.response.status_code}: {err}")
            return {"success": False, "post_id": None, "url": None, "error": f"HTTP {exc.response.status_code}: {err}"}
        except Exception as exc:
            logger.error(f"[META VIDEO] Error: {exc}")
            return {"success": False, "post_id": None, "url": None, "error": str(exc)}

