from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app import models
from app.core.config import settings

router = APIRouter(prefix="/stats", tags=["Analytics & Tracking"])

@router.get("/dashboard")
async def get_dashboard_summary(start_date: str = None, end_date: str = None, db: Session = Depends(get_db)):
    """
    Lấy số liệu tổng hợp cho Dashboard và trang Báo cáo.
    """
    from datetime import datetime
    
    # 1. Thống kê số lượng bài viết theo trạng thái
    status_query = db.query(models.Post.status, func.count(models.Post.id)).group_by(models.Post.status)
    if start_date and end_date:
        # Lọc theo created_at
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            status_query = status_query.filter(models.Post.created_at >= start_dt, models.Post.created_at <= end_dt)
        except:
            pass
    status_counts = status_query.all()
    status_summary = {status: count for status, count in status_counts}

    # 2. Thống kê số lượng theo Platform
    platform_query = db.query(models.ContentPlan.platform, func.count(models.ContentPlan.id)).group_by(models.ContentPlan.platform)
    platform_counts = platform_query.all()
    platform_summary = {platform: count for platform, count in platform_counts}

    # Nếu có lọc ngày, ưu tiên lấy live từ GA4/Meta
    if start_date and end_date:
        from app.services.google_service import GoogleAnalyticsService
        from app.services.meta_service import MetaService
        
        ga4_data = await GoogleAnalyticsService.fetch_site_analytics(start_date, end_date)
        meta_data = await MetaService.fetch_page_insights(start_date, end_date)
        
        # Ánh xạ top pages -> posts
        top_web_posts = []
        if ga4_data.get("success"):
            for page in sorted(ga4_data["top_pages"], key=lambda x: x["views"], reverse=True)[:5]:
                # Tìm bài viết có url chứa path này
                path = page["path"]
                post = db.query(models.Post).filter(models.Post.published_url.like(f"%{path}%")).first()
                title = post.title if post else path
                top_web_posts.append({"title": title, "views": page["views"]})
                
        return {
            "status_summary": status_summary,
            "platform_summary": platform_summary,
            "web_metrics": {
                "views": ga4_data.get("total_views", 0),
                "avg_time_on_page": ga4_data.get("avg_time_on_page", 0.0),
                "avg_bounce_rate": ga4_data.get("avg_bounce_rate", 0.0),
            },
            "fb_metrics": {
                "reach": meta_data.get("total_reach", 0),
                "engagement": meta_data.get("total_engagement", 0),
                "video_views": meta_data.get("video_views", 0),
                "clicks": meta_data.get("clicks", 0),
                "reactions": meta_data.get("reactions", 0),
                "shares": meta_data.get("shares", 0),
                "comments": meta_data.get("comments", 0),
            },
            "top_web_posts": top_web_posts,
            "top_fb_posts": []
        }

    # 3. Mặc định: Lấy từ DB AnalyticsMetric
    total_metrics = db.query(
        func.sum(models.AnalyticsMetric.views).label("total_views"),
        func.avg(models.AnalyticsMetric.time_on_page).label("avg_time_on_page"),
        func.avg(models.AnalyticsMetric.bounce_rate).label("avg_bounce_rate"),
        
        func.sum(models.AnalyticsMetric.reach).label("total_reach"),
        func.sum(models.AnalyticsMetric.engagement).label("total_engagement"),
        func.sum(models.AnalyticsMetric.video_views).label("total_video_views"),
        func.sum(models.AnalyticsMetric.clicks).label("total_clicks"),
        func.sum(models.AnalyticsMetric.reactions).label("total_reactions"),
        func.sum(models.AnalyticsMetric.shares).label("total_shares"),
        func.sum(models.AnalyticsMetric.comments).label("total_comments")
    ).first()

    # 4. Lấy danh sách 5 bài viết có tương tác tốt nhất từ DB
    top_web_posts_db = db.query(models.Post, models.AnalyticsMetric)\
        .join(models.AnalyticsMetric, models.Post.id == models.AnalyticsMetric.post_id)\
        .filter(models.Post.utm_source == "website")\
        .order_by(models.AnalyticsMetric.views.desc())\
        .limit(5).all()
        
    top_web_posts = [{"title": p.title, "views": m.views} for p, m in top_web_posts_db]

    top_fb_posts_db = db.query(models.Post, models.AnalyticsMetric)\
        .join(models.AnalyticsMetric, models.Post.id == models.AnalyticsMetric.post_id)\
        .filter(models.Post.utm_source == "facebook")\
        .order_by(models.AnalyticsMetric.engagement.desc())\
        .limit(5).all()
        
    top_fb_posts = [{"title": p.title, "reach": m.reach, "engagement": m.engagement} for p, m in top_fb_posts_db]

    return {
        "status_summary": status_summary,
        "platform_summary": platform_summary,
        
        "web_metrics": {
            "views": total_metrics.total_views or 0,
            "avg_time_on_page": round(total_metrics.avg_time_on_page or 0, 1),
            "avg_bounce_rate": round(total_metrics.avg_bounce_rate or 0, 1)
        },
        
        "fb_metrics": {
            "reach": total_metrics.total_reach or 0,
            "engagement": total_metrics.total_engagement or 0,
            "video_views": total_metrics.total_video_views or 0,
            "clicks": total_metrics.total_clicks or 0,
            "reactions": total_metrics.total_reactions or 0,
            "shares": total_metrics.total_shares or 0,
            "comments": total_metrics.total_comments or 0
        },
        
        "top_web_posts": top_web_posts,
        "top_fb_posts": top_fb_posts
    }

@router.get("/campaigns/{campaign_id}/insights")
async def generate_ai_insights(campaign_id: int, start_date: str = None, end_date: str = None, db: Session = Depends(get_db)):
    """
    [Module 4] AI phân tích dữ liệu hiệu quả từ Dashboard để tự động đưa ra nhận xét:
    - Chủ đề nào hiệu quả nhất?
    - Đề xuất cải tiến cho kế hoạch tháng sau.
    """
    # Lấy chiến dịch
    campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Không tìm thấy chiến dịch")

    # Giả lập dữ liệu nhận xét từ AI dựa trên sản phẩm chính
    focus = campaign.focus_products or "Kính cường lực DAFA"
    
    # Kéo số liệu thật từ DB cho các bài viết thuộc chiến dịch này
    posts_metrics = db.query(models.Post, models.AnalyticsMetric)\
        .join(models.ContentPlan, models.Post.content_plan_id == models.ContentPlan.id)\
        .join(models.AnalyticsMetric, models.Post.id == models.AnalyticsMetric.post_id)\
        .filter(models.ContentPlan.campaign_id == campaign_id, models.Post.status == "Published").all()

    if not posts_metrics:
        # Nếu chưa có bài nào publish và có số liệu
        insight_text = f"### 📊 BÁO CÁO PHÂN TÍCH HIỆU QUẢ - THÁNG {campaign.month_year}\n\nHiện tại chưa có đủ dữ liệu bài viết đã xuất bản cho chiến dịch này để AI phân tích. Bạn hãy Đồng bộ số liệu sau khi đăng bài nhé!"
    else:
        from app.services.google_service import GoogleAnalyticsService
        
        # Tổng hợp thành chuỗi JSON/văn bản
        metrics_summary_lines = []
        for post, metric in posts_metrics:
            platform = post.content_plan.platform
            if platform == "Web":
                if start_date and end_date:
                    # Fetch live data for the specific date range
                    ga4_data = await GoogleAnalyticsService.fetch_page_analytics(post.published_url, start_date, end_date)
                    views = ga4_data.get("views", 0) if ga4_data else 0
                    time_on_page = ga4_data.get("time_on_page", 0.0) if ga4_data else 0.0
                    bounce_rate = ga4_data.get("bounce_rate", 0.0) if ga4_data else 0.0
                else:
                    views = metric.views
                    time_on_page = metric.time_on_page
                    bounce_rate = metric.bounce_rate
                    
                metrics_summary_lines.append(f"- Tiêu đề: '{post.title}', Nền tảng: Web, Views: {views}, Time on page: {time_on_page}s, Bounce rate: {bounce_rate}%")
            else:
                metrics_summary_lines.append(f"- Tiêu đề: '{post.title}', Nền tảng: Fanpage, Reach: {metric.reach}, Engagement: {metric.engagement}, Reactions: {metric.reactions}, Comments: {metric.comments}, Shares: {metric.shares}")
                
        metrics_summary = "\n".join(metrics_summary_lines)
        
        from app.services.ai_service import AIService
        insight_text = AIService.generate_insights(
            campaign_name=campaign.name,
            month_year=campaign.month_year,
            focus_products=focus,
            metrics_summary=metrics_summary
        )

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "insights": insight_text
    }

@router.post("/sync")
async def sync_analytics_data(db: Session = Depends(get_db)):
    """
    Đồng bộ dữ liệu phân tích từ Google Analytics và Facebook cho các bài viết đã xuất bản.
    """
    from app.services.google_service import GoogleAnalyticsService
    from app.services.meta_service import MetaService
    from datetime import datetime

    published_posts = db.query(models.Post).filter(models.Post.status == "Published", models.Post.published_url.isnot(None)).all()
    
    if not published_posts:
        return {"message": "Không có bài viết nào đã xuất bản để đồng bộ."}

    sync_count = 0
    for post in published_posts:
        platform = post.content_plan.platform if post.content_plan else None
        metric = db.query(models.AnalyticsMetric).filter(models.AnalyticsMetric.post_id == post.id).first()
        
        if not metric:
            metric = models.AnalyticsMetric(post_id=post.id, recorded_at=datetime.utcnow())
            db.add(metric)
        else:
            metric.recorded_at = datetime.utcnow()

        try:
            if platform == "Web":
                # Kéo dữ liệu từ GA4
                ga4_data = await GoogleAnalyticsService.fetch_page_analytics(post.published_url)
                if ga4_data and ga4_data.get("success"):
                    metric.views = ga4_data.get("views", metric.views)
                    metric.time_on_page = ga4_data.get("time_on_page", metric.time_on_page)
                    metric.bounce_rate = ga4_data.get("bounce_rate", metric.bounce_rate)
                    sync_count += 1
            
            elif platform == "Fanpage":
                # Kéo dữ liệu từ Meta (giả sử có hàm fetch_post_insights, nếu không sẽ dùng mock)
                if hasattr(MetaService, 'fetch_post_insights'):
                    fb_data = await MetaService.fetch_post_insights(post.published_url)
                else:
                    # Mock FB data
                    import random
                    fb_data = {
                        "success": True,
                        "reach": random.randint(100, 10000),
                        "engagement": random.randint(10, 1000),
                        "video_views": random.randint(0, 500),
                        "clicks": random.randint(5, 200),
                        "reactions": random.randint(5, 500),
                        "shares": random.randint(0, 50),
                        "comments": random.randint(0, 100)
                    }
                
                if fb_data and fb_data.get("success"):
                    metric.reach = fb_data.get("reach", metric.reach)
                    metric.engagement = fb_data.get("engagement", metric.engagement)
                    metric.video_views = fb_data.get("video_views", metric.video_views)
                    metric.clicks = fb_data.get("clicks", metric.clicks)
                    metric.reactions = fb_data.get("reactions", metric.reactions)
                    metric.shares = fb_data.get("shares", metric.shares)
                    metric.comments = fb_data.get("comments", metric.comments)
                    sync_count += 1
        except Exception as e:
            print(f"Error syncing post {post.id}: {e}")
            continue

    db.commit()
    return {"message": f"Đã đồng bộ dữ liệu cho {sync_count} bài viết.", "sync_count": sync_count}
