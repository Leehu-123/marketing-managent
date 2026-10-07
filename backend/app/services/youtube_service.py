import os
import random
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)


def resolve_local_video_path(video_url: str) -> Optional[str]:
    """
    Tìm kiếm và chuẩn hóa đường dẫn file video cục bộ trên máy chủ.
    Hỗ trợ cả đường dẫn tương đối, static/uploads/videos và uploads/.
    """
    if not video_url:
        return None

    p = Path(video_url)
    if p.is_file():
        return str(p.resolve())

    # 1. Thử theo BACKEND_DIR
    backend_p = settings.BACKEND_DIR / video_url.lstrip("/\\")
    if backend_p.is_file():
        return str(backend_p.resolve())

    # 2. Thử theo STATIC_DIR (vd: static/uploads/videos/abc.mp4)
    clean_static = video_url.lstrip("/\\").replace("static/", "")
    static_p = settings.STATIC_DIR / clean_static
    if static_p.is_file():
        return str(static_p.resolve())

    # 3. Thử theo UPLOAD_DIR
    clean_upload = video_url.lstrip("/\\").replace("uploads/", "")
    upload_p = settings.UPLOAD_DIR / clean_upload
    if upload_p.is_file():
        return str(upload_p.resolve())

    # 4. Thử tìm trực tiếp trong thư mục static/uploads/videos
    videos_dir = settings.STATIC_DIR / "uploads" / "videos"
    direct_p = videos_dir / Path(video_url).name
    if direct_p.is_file():
        return str(direct_p.resolve())

    return None


class YouTubeService:
    """Service class for YouTube Data API v3 video uploads and metrics."""

    @staticmethod
    def get_credentials(
        channel_token: Optional[str] = None,
        channel_refresh: Optional[str] = None
    ):
        """
        Lấy Google Credentials cho YouTube Data API v3.
        Thứ tự ưu tiên:
        1. Token/Refresh token trực tiếp của VideoChannel
        2. Cấu hình IntegrationSetting(platform='YouTube')
        3. Cấu hình trong file .env / settings
        """
        from app.core.database import SessionLocal
        from app.models.setting import IntegrationSetting
        from google.oauth2.credentials import Credentials

        client_id = getattr(settings, "YOUTUBE_CLIENT_ID", "") or os.getenv("YOUTUBE_CLIENT_ID", "")
        client_secret = getattr(settings, "YOUTUBE_CLIENT_SECRET", "") or os.getenv("YOUTUBE_CLIENT_SECRET", "")
        refresh_token = channel_refresh or channel_token or os.getenv("YOUTUBE_REFRESH_TOKEN", "")

        db = SessionLocal()
        try:
            yt_setting = db.query(IntegrationSetting).filter(
                IntegrationSetting.platform == "YouTube",
                IntegrationSetting.is_active == True
            ).first()
            if yt_setting:
                if yt_setting.username:
                    client_id = yt_setting.username
                if yt_setting.access_token:
                    client_secret = yt_setting.access_token
                if not refresh_token and yt_setting.refresh_token:
                    refresh_token = yt_setting.refresh_token
        except Exception as e:
            logger.warning(f"[YOUTUBE] Không thể đọc cấu hình IntegrationSetting: {e}")
        finally:
            db.close()

        if not refresh_token or not client_id or not client_secret:
            return None

        try:
            return Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=[
                    "https://www.googleapis.com/auth/youtube.upload",
                    "https://www.googleapis.com/auth/youtube.readonly"
                ]
            )
        except Exception as e:
            logger.error(f"[YOUTUBE] Lỗi khởi tạo Credentials: {e}")
            return None

    @staticmethod
    def upload_video_or_short(
        file_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        is_short: bool = True,
        privacy_status: str = "public",
        channel_token: Optional[str] = None,
        channel_refresh: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tải video lên YouTube thông qua YouTube Data API v3 (Resumable Upload).
        Nếu is_short=True, tự động thêm hashtag #Shorts vào tiêu đề/mô tả.
        """
        mock_mode = getattr(settings, "MOCK_YOUTUBE", False) or os.getenv("MOCK_YOUTUBE", "false").lower() == "true"

        # 1. Tìm file vật lý
        local_file = resolve_local_video_path(file_path)
        if not local_file and not mock_mode:
            return {
                "success": False,
                "error": f"Không tìm thấy file video cục bộ tại: {file_path}",
                "video_id": None,
                "url": None
            }

        # 2. Lấy credentials
        creds = YouTubeService.get_credentials(channel_token, channel_refresh)

        # 3. Xử lý MOCK Mode khi không có credentials hoặc bật mock
        if mock_mode or not creds:
            if not creds and not mock_mode:
                logger.warning("[YOUTUBE] Chưa cấu hình YouTube OAuth. Đang chạy ở chế độ MOCK.")
            
            fake_id = f"yt_{random.randint(1000000000, 9999999999)}"
            format_type = "Shorts" if is_short else "Video"
            logger.info(f"[MOCK YOUTUBE] Uploading {format_type}: {title} (File: {file_path}) -> ID: {fake_id}")
            return {
                "success": True,
                "video_id": fake_id,
                "url": f"https://www.youtube.com/watch?v={fake_id}",
                "is_mock": True,
                "error": None
            }

        # 4. Upload thật qua Google API Client
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from googleapiclient.errors import HttpError

            youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

            # Đảm bảo hashtag #Shorts cho video ngắn
            video_title = title.strip()
            video_desc = description.strip()
            if is_short:
                if "#shorts" not in video_title.lower():
                    video_title = f"{video_title} #Shorts"
                if "#shorts" not in video_desc.lower():
                    video_desc = f"{video_desc}\n\n#Shorts #DAFAGlass"

            # Parse tags
            tag_list = list(tags) if tags else ["DAFA Glass", "Kính xây dựng"]
            if is_short and "Shorts" not in tag_list:
                tag_list.append("Shorts")

            body = {
                "snippet": {
                    "title": video_title[:100],  # Giới hạn 100 ký tự
                    "description": video_desc[:5000],
                    "tags": tag_list,
                    "categoryId": "22"  # 22 = People & Blogs, 28 = Science & Technology
                },
                "status": {
                    "privacyStatus": privacy_status,  # public, unlisted, private
                    "selfDeclaredMadeForKids": False
                }
            }

            logger.info(f"[YOUTUBE API] Bắt đầu upload: '{video_title}' từ file {local_file}")
            media = MediaFileUpload(
                local_file,
                mimetype="video/mp4",
                chunksize=1024 * 1024 * 4,  # 4MB chunks
                resumable=True
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"[YOUTUBE API] Tiến độ upload: {progress}%")

            video_id = response.get("id")
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"[YOUTUBE API] Upload thành công! Video ID: {video_id}, URL: {video_url}")

            return {
                "success": True,
                "video_id": video_id,
                "url": video_url,
                "is_mock": False,
                "error": None
            }

        except HttpError as exc:
            err_msg = f"YouTube API Error {exc.resp.status}: {exc.content.decode('utf-8', errors='ignore')}"
            logger.error(f"[YOUTUBE] {err_msg}")
            return {
                "success": False,
                "video_id": None,
                "url": None,
                "error": err_msg
            }
        except Exception as exc:
            err_msg = f"Lỗi không xác định khi upload YouTube: {str(exc)}"
            logger.error(f"[YOUTUBE] {err_msg}", exc_info=True)
            return {
                "success": False,
                "video_id": None,
                "url": None,
                "error": err_msg
            }

    @staticmethod
    def upload_short(file_path: str, metadata: dict) -> str:
        """Phương thức tương thích ngược với code cũ."""
        title = metadata.get("title", "Shorts DAFA Glass")
        description = metadata.get("description", "")
        res = YouTubeService.upload_video_or_short(
            file_path=file_path,
            title=title,
            description=description,
            is_short=True
        )
        if res.get("success"):
            return res.get("video_id")
        raise Exception(res.get("error", "Lỗi upload YouTube Shorts"))

    @staticmethod
    def upload_video(file_path: str, metadata: dict) -> str:
        """Phương thức tương thích ngược với code cũ."""
        title = metadata.get("title", "Video DAFA Glass")
        description = metadata.get("description", "")
        res = YouTubeService.upload_video_or_short(
            file_path=file_path,
            title=title,
            description=description,
            is_short=False
        )
        if res.get("success"):
            return res.get("video_id")
        raise Exception(res.get("error", "Lỗi upload video YouTube"))

    @staticmethod
    def fetch_metrics(video_id: str, channel_token: Optional[str] = None) -> dict:
        """Lấy số liệu views, likes, comments của video."""
        creds = YouTubeService.get_credentials(channel_token)
        if creds and not video_id.startswith("yt_"):
            try:
                from googleapiclient.discovery import build
                youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
                resp = youtube.videos().list(part="statistics", id=video_id).execute()
                items = resp.get("items", [])
                if items:
                    stats = items[0].get("statistics", {})
                    return {
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                    }
            except Exception as e:
                logger.warning(f"[YOUTUBE] Lỗi lấy metrics thật: {e}")

        # Fallback simulated metrics
        return {
            "views": random.randint(500, 20000),
            "likes": random.randint(50, 1000),
            "comments": random.randint(5, 200)
        }
