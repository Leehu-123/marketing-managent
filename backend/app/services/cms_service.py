"""
WordPress CMS REST API Integration Service
============================================
Handles publishing blog posts to a WordPress site via the WP REST API.
Supports MOCK mode for development and REAL mode for production.
"""

import random
import logging
from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class CMSService:
    """Service class for WordPress REST API integration."""

    @staticmethod
    async def publish_post(
        title: str,
        body: str,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        media_url: Optional[str] = None,
    ) -> dict:
        """
        Publish a blog post to the configured WordPress site.

        Args:
            title: The post title.
            body: The HTML content body of the post.
            meta_title: SEO meta title (used in Yoast/RankMath if configured).
            meta_description: SEO meta description.
            media_url: Optional featured image URL.

        Returns:
            dict with keys: success (bool), post_id (int|str), url (str), error (str|None)
        """
        if settings.MOCK_CMS:
            return CMSService._mock_publish(title, body, meta_title, meta_description)
        else:
            return await CMSService._real_publish(
                title, body, meta_title, meta_description, media_url
            )

    @staticmethod
    def _mock_publish(
        title: str,
        body: str,
        meta_title: Optional[str],
        meta_description: Optional[str],
    ) -> dict:
        """Simulate publishing a WordPress post in MOCK mode."""
        fake_post_id = random.randint(1000, 99999)
        # Generate a URL-friendly slug from the title
        slug = title.lower().replace(" ", "-")[:60].rstrip("-")
        fake_url = f"https://dafaglass.com/blog/post-{fake_post_id}"

        print(f"[MOCK CMS] ✅ Successfully published WordPress post.")
        print(f"[MOCK CMS]    Post ID : {fake_post_id}")
        print(f"[MOCK CMS]    Title   : {title[:60]}")
        print(f"[MOCK CMS]    URL     : {fake_url}")

        if meta_title:
            print(f"[MOCK CMS]    Meta    : {meta_title[:60]}")

        logger.info(
            f"[MOCK CMS] Published post '{title[:50]}' -> ID={fake_post_id}, URL={fake_url}"
        )

        return {
            "success": True,
            "post_id": fake_post_id,
            "url": fake_url,
            "error": None,
        }

    @staticmethod
    async def _upload_media_to_wp(client: httpx.AsyncClient, wp_api_url: str, wp_username: str, wp_app_password: str, local_url: str) -> Optional[dict]:
        """
        Tải một file ảnh từ backend (thư mục uploads) lên thư viện Media của WordPress.
        """
        import os
        import mimetypes
        from pathlib import Path
        
        # Xử lý đường dẫn
        relative_path = local_url.strip("/")
        if not relative_path.startswith("uploads/"):
            return None
            
        # Lấy tên file
        filename = relative_path.replace("uploads/", "")
        file_path = settings.UPLOAD_DIR / filename
        
        if not file_path.exists():
            logger.error(f"[CMS] Không tìm thấy file ảnh để upload: {file_path}")
            return None
            
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "image/jpeg"
            
        endpoint = f"{wp_api_url}/wp/v2/media"
        
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()
                
            headers = {
                "Content-Disposition": f'attachment; filename="{file_path.name}"',
                "Content-Type": mime_type
            }
            
            response = await client.post(
                endpoint,
                content=file_content,
                auth=(wp_username, wp_app_password),
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"[CMS] Tải ảnh {file_path.name} lên WP thành công -> ID: {data.get('id')}")
            return {"id": data.get("id"), "source_url": data.get("source_url")}
        except Exception as exc:
            logger.error(f"[CMS] Lỗi tải ảnh {file_path.name} lên WP: {exc}")
            return None

    @staticmethod
    async def _real_publish(
        title: str,
        body: str,
        meta_title: Optional[str],
        meta_description: Optional[str],
        media_url: Optional[str],
    ) -> dict:
        """Publish a post via the real WordPress REST API."""
        from app.core.database import SessionLocal
        from app.models.setting import IntegrationSetting
        
        db = SessionLocal()
        try:
            wp_setting = db.query(IntegrationSetting).filter(IntegrationSetting.platform == "WordPress", IntegrationSetting.is_active == True).first()
            if wp_setting:
                wp_api_url = wp_setting.url
                wp_username = wp_setting.username
                wp_app_password = wp_setting.access_token
            else:
                wp_api_url = settings.WP_API_URL
                wp_username = settings.WP_USERNAME
                wp_app_password = settings.WP_APP_PASSWORD
        finally:
            db.close()


        # Validate configuration
        if not wp_api_url or not wp_username or not wp_app_password:
            error_msg = (
                "WordPress API is not fully configured. "
                "Check WP_API_URL, WP_USERNAME, and WP_APP_PASSWORD in .env"
            )
            logger.error(f"[CMS] {error_msg}")
            return {"success": False, "post_id": None, "url": None, "error": error_msg}

        # Ensure API URL does not have trailing slash
        wp_api_url = wp_api_url.rstrip("/")
        if not wp_api_url.endswith("wp-json"):
            wp_api_url = f"{wp_api_url}/wp-json"
        endpoint = f"{wp_api_url}/wp/v2/posts"

        # Build the post payload
        post_data = {
            "title": title,
            "status": "publish",
        }

        # Include Yoast/RankMath SEO meta if available (via custom fields)
        meta_fields = {}
        if meta_title:
            meta_fields["_yoast_wpseo_title"] = meta_title
        if meta_description:
            meta_fields["_yoast_wpseo_metadesc"] = meta_description
        if meta_fields:
            post_data["meta"] = meta_fields

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                
                # 1. Xử lý Thumbnail (Featured Image)
                if media_url:
                    wp_media = await CMSService._upload_media_to_wp(client, wp_api_url, wp_username, wp_app_password, media_url)
                    if wp_media and wp_media.get("id"):
                        post_data["featured_media"] = wp_media["id"]
                        
                # 2. Xử lý Ảnh nội dung (Inline Images)
                import re
                if body:
                    upload_paths = set(re.findall(r'src=["\'](/?uploads/[^"\']+)["\']', body))
                    for path in upload_paths:
                        wp_media = await CMSService._upload_media_to_wp(client, wp_api_url, wp_username, wp_app_password, path)
                        if wp_media and wp_media.get("source_url"):
                            body = body.replace(path, wp_media["source_url"])
                            
                post_data["content"] = body

                response = await client.post(
                    endpoint,
                    json=post_data,
                    auth=(wp_username, wp_app_password),
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

                post_id = data.get("id", "unknown")
                post_url = data.get("link", f"{wp_api_url}/?p={post_id}")

                logger.info(f"[CMS] ✅ Published post '{title[:50]}' -> ID={post_id}, URL={post_url}")
                return {
                    "success": True,
                    "post_id": post_id,
                    "url": post_url,
                    "error": None,
                }

        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text
            logger.error(f"[CMS] HTTP {exc.response.status_code} error: {error_body}")
            return {
                "success": False,
                "post_id": None,
                "url": None,
                "error": f"HTTP {exc.response.status_code}: {error_body}",
            }
        except httpx.RequestError as exc:
            logger.error(f"[CMS] Request error: {exc}")
            return {
                "success": False,
                "post_id": None,
                "url": None,
                "error": f"Request error: {str(exc)}",
            }
        except Exception as exc:
            logger.error(f"[CMS] Unexpected error: {exc}")
            return {
                "success": False,
                "post_id": None,
                "url": None,
                "error": f"Unexpected error: {str(exc)}",
            }

    # ------------------------------------------------------------------
    # UTILITY: Fetch existing post (for future use)
    # ------------------------------------------------------------------

    @staticmethod
    async def get_post(post_id: int) -> dict:
        """
        Fetch a WordPress post by ID.

        Args:
            post_id: The WordPress post ID.

        Returns:
            dict with keys: success, data (post object), error
        """
        if settings.MOCK_CMS:
            print(f"[MOCK CMS] 📖 Fetched post {post_id} (simulated)")
            logger.info(f"[MOCK CMS] Fetched post {post_id}")
            return {
                "success": True,
                "data": {
                    "id": post_id,
                    "title": {"rendered": f"Mock Post {post_id}"},
                    "link": f"https://dafaglass.com/blog/post-{post_id}",
                    "status": "publish",
                },
                "error": None,
            }

        wp_api_url = settings.WP_API_URL.rstrip("/")
        endpoint = f"{wp_api_url}/wp/v2/posts/{post_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    endpoint,
                    auth=(settings.WP_USERNAME, settings.WP_APP_PASSWORD),
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"[CMS] Fetched post {post_id}: {data.get('title', {}).get('rendered', 'N/A')}")
                return {"success": True, "data": data, "error": None}

        except httpx.HTTPStatusError as exc:
            logger.error(f"[CMS] Fetch post HTTP {exc.response.status_code}: {exc.response.text}")
            return {
                "success": False,
                "data": None,
                "error": f"HTTP {exc.response.status_code}: {exc.response.text}",
            }
        except Exception as exc:
            logger.error(f"[CMS] Fetch post error: {exc}")
            return {"success": False, "data": None, "error": str(exc)}
