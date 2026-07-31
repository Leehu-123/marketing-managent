"""
Google Analytics 4 (GA4) Integration Service
==============================================
Handles fetching analytics data for published web content.
Supports MOCK mode for development and a REAL mode placeholder for production.
"""

import random
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.core.database import SessionLocal
from app import models

logger = logging.getLogger(__name__)


class GoogleAnalyticsService:
    """Service class for Google Analytics 4 integration."""

    @staticmethod
    async def fetch_page_analytics(
        page_url: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """
        Fetch GA4 analytics metrics for a specific page URL.

        Args:
            page_url: The full URL of the published page (e.g., https://dafaglass.com/blog/post-123).
            start_date: Start date for the report in YYYY-MM-DD format. Defaults to 7 days ago.
            end_date: End date for the report in YYYY-MM-DD format. Defaults to today.

        Returns:
            dict with keys: success, views, time_on_page, bounce_rate, error
        """
        if settings.MOCK_ANALYTICS:
            return GoogleAnalyticsService._mock_fetch(page_url, start_date, end_date)
        else:
            return await GoogleAnalyticsService._real_fetch(page_url, start_date, end_date)

    @staticmethod
    def _mock_fetch(
        page_url: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> dict:
        """Return simulated GA4 analytics data in MOCK mode."""
        views = random.randint(50, 5000)
        time_on_page = round(random.uniform(30.0, 300.0), 1)  # seconds
        bounce_rate = round(random.uniform(20.0, 80.0), 1)    # percentage

        # Derive a date range label for logging
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.utcnow().strftime("%Y-%m-%d")

        print(f"[MOCK GA4] 📊 Analytics for: {page_url}")
        print(f"[MOCK GA4]    Period       : {start_date} → {end_date}")
        print(f"[MOCK GA4]    Views        : {views:,}")
        print(f"[MOCK GA4]    Time on Page : {time_on_page}s")
        print(f"[MOCK GA4]    Bounce Rate  : {bounce_rate}%")

        logger.info(
            f"[MOCK GA4] Analytics for {page_url}: "
            f"views={views}, time_on_page={time_on_page}s, bounce_rate={bounce_rate}%"
        )

        return {
            "success": True,
            "views": views,
            "time_on_page": time_on_page,
            "bounce_rate": bounce_rate,
            "period": {"start": start_date, "end": end_date},
            "error": None,
        }

    @staticmethod
    def _mock_dashboard_fetch(start_date: str = None, end_date: str = None) -> dict:
        import random
        return {
            "success": True,
            "total_views": random.randint(5000, 20000),
            "avg_time_on_page": random.uniform(60, 300),
            "avg_bounce_rate": random.uniform(30, 70),
            "top_pages": []
        }
        
    @staticmethod
    async def fetch_site_analytics(start_date: str = None, end_date: str = None) -> dict:
        """
        Lấy số liệu toàn bộ website trong khoảng thời gian.
        """
        if settings.MOCK_ANALYTICS:
            return GoogleAnalyticsService._mock_dashboard_fetch(start_date, end_date)
            
        from app.core.database import SessionLocal
        from app import models
        db = SessionLocal()
        setting = db.query(models.IntegrationSetting).filter(models.IntegrationSetting.platform == "GoogleAnalytics").first()
        if not setting or not setting.is_active or not setting.refresh_token:
            db.close()
            return {
                "success": False,
                "total_views": 0,
                "avg_time_on_page": 0.0,
                "avg_bounce_rate": 0.0,
                "top_pages": [],
                "error": "Google Analytics chưa được cấu hình."
            }
            
        client_id = setting.username
        client_secret = setting.access_token
        refresh_token = setting.refresh_token
        property_id = setting.url
        db.close()

        try:
            from google.oauth2.credentials import Credentials
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
            
            credentials = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret
            )
            
            client = BetaAnalyticsDataClient(credentials=credentials)
            
            request = RunReportRequest(
                property=f"properties/{property_id}",
                dimensions=[Dimension(name="pagePath")],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="averageSessionDuration"),
                    Metric(name="bounceRate")
                ],
                date_ranges=[DateRange(start_date=start_date or "7daysAgo", end_date=end_date or "today")],
            )
            
            response = client.run_report(request)
            
            total_views = 0
            total_time = 0.0
            total_bounce = 0.0
            row_count = 0
            top_pages = []
            
            for row in response.rows:
                path = row.dimension_values[0].value
                views = int(row.metric_values[0].value)
                time = float(row.metric_values[1].value)
                bounce = float(row.metric_values[2].value) * 100
                
                total_views += views
                total_time += time
                total_bounce += bounce
                row_count += 1
                
                top_pages.append({
                    "path": path,
                    "views": views,
                    "time_on_page": time,
                    "bounce_rate": bounce
                })
                
            avg_time = (total_time / row_count) if row_count > 0 else 0.0
            avg_bounce = (total_bounce / row_count) if row_count > 0 else 0.0
            
            return {
                "success": True,
                "total_views": total_views,
                "avg_time_on_page": round(avg_time, 1),
                "avg_bounce_rate": round(avg_bounce, 1),
                "top_pages": top_pages
            }
            
        except Exception as e:
            print(f"[REAL GA4 ERROR] {e}")
            return {
                "success": False,
                "total_views": 0,
                "avg_time_on_page": 0.0,
                "avg_bounce_rate": 0.0,
                "top_pages": [],
                "error": str(e)
            }

    @staticmethod
    async def _real_fetch(
        page_url: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> dict:
        """
        Real GA4 Data API integration using OAuth2.0 credentials.
        """
        db = SessionLocal()
        setting = db.query(models.IntegrationSetting).filter(models.IntegrationSetting.platform == "GoogleAnalytics").first()
        if not setting or not setting.is_active or not setting.refresh_token:
            db.close()
            return {
                "success": False,
                "views": 0,
                "time_on_page": 0.0,
                "bounce_rate": 0.0,
                "period": {"start": start_date, "end": end_date},
                "error": "Google Analytics chưa được cấu hình hoặc chưa đăng nhập."
            }
            
        client_id = setting.username
        client_secret = setting.access_token
        refresh_token = setting.refresh_token
        property_id = setting.url
        db.close()

        try:
            from google.oauth2.credentials import Credentials
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
            import urllib.parse
            
            credentials = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret
            )
            
            client = BetaAnalyticsDataClient(credentials=credentials)
            
            path = urllib.parse.urlparse(page_url).path
            if not path:
                path = "/"
                
            request = RunReportRequest(
                property=f"properties/{property_id}",
                dimensions=[Dimension(name="pagePath")],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="averageSessionDuration"),
                    Metric(name="bounceRate")
                ],
                date_ranges=[DateRange(start_date=start_date or "7daysAgo", end_date=end_date or "today")],
            )
            
            response = client.run_report(request)
            
            views = 0
            time_on_page = 0.0
            bounce_rate = 0.0
            
            for row in response.rows:
                if path in row.dimension_values[0].value:
                    views += int(row.metric_values[0].value)
                    time_on_page = float(row.metric_values[1].value)
                    bounce_rate = float(row.metric_values[2].value) * 100 
                    break
                    
            print(f"[REAL GA4] Fetched analytics for {path}: views={views}")
            
            return {
                "success": True,
                "views": views,
                "time_on_page": round(time_on_page, 1),
                "bounce_rate": round(bounce_rate, 1),
                "period": {"start": start_date, "end": end_date},
                "error": None,
            }
            
        except ImportError:
            return {
                "success": False,
                "views": 0,
                "time_on_page": 0.0,
                "bounce_rate": 0.0,
                "period": {"start": start_date, "end": end_date},
                "error": "Thiếu thư viện google-analytics-data hoặc google-auth-oauthlib."
            }
        except Exception as e:
            logger.error(f"[GA4] Error fetching real analytics data: {e}")
            return {
                "success": False,
                "views": 0,
                "time_on_page": 0.0,
                "bounce_rate": 0.0,
                "period": {"start": start_date, "end": end_date},
                "error": str(e)
            }

    # ------------------------------------------------------------------
    # UTILITY: Batch fetch for multiple URLs
    # ------------------------------------------------------------------

    @staticmethod
    async def fetch_batch_analytics(
        page_urls: list[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        """
        Fetch analytics for multiple page URLs.

        Args:
            page_urls: List of page URLs to fetch analytics for.
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            List of analytics result dicts.
        """
        results = []
        for url in page_urls:
            result = await GoogleAnalyticsService.fetch_page_analytics(
                url, start_date, end_date
            )
            result["page_url"] = url
            results.append(result)

        logger.info(f"[GA4] Batch analytics fetched for {len(page_urls)} URLs.")
        return results
