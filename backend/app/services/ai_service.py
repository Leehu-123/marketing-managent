import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.core.config import settings

from app.core.database import SessionLocal
from app.models.setting import AISetting
from app.models.brand import BrandProfile

def get_active_ai_client():
    if settings.MOCK_AI:
        return None
    db = SessionLocal()
    try:
        setting = db.query(AISetting).filter(AISetting.is_active == True).first()
        if not setting or not setting.api_key:
            return None
            
        if setting.provider_name in ["OpenAI", "9Router"]:
            from openai import OpenAI
            client_args = {"api_key": setting.api_key}
            if hasattr(setting, 'base_url') and setting.base_url:
                client_args["base_url"] = setting.base_url
            model_name = getattr(setting, 'model_name', None) or settings.OPENAI_MODEL
            return {"provider": setting.provider_name, "client": OpenAI(**client_args), "model": model_name}
        elif setting.provider_name == "Gemini":
            import google.generativeai as genai
            genai.configure(api_key=setting.api_key)
            model_name = getattr(setting, 'model_name', None) or 'gemini-1.5-flash'
            return {"provider": "Gemini", "client": genai.GenerativeModel(model_name), "model": model_name}
            
        return None
    except Exception:
        return None
    finally:
        db.close()

def get_active_image_client():
    if settings.MOCK_AI:
        return None
    db = SessionLocal()
    try:
        setting = db.query(AISetting).filter(AISetting.is_active == True, AISetting.provider_name.like('%(Image)%')).first()
        if not setting or not setting.api_key:
            # Fallback to normal text active client if it supports image (e.g. OpenAI)
            setting = db.query(AISetting).filter(AISetting.is_active == True).first()
            if not setting or not setting.api_key:
                return None
                
        return {"provider": setting.provider_name, "api_key": setting.api_key, "base_url": setting.base_url, "model": setting.model_name}
    except Exception:
        return None
    finally:
        db.close()

def get_active_research_client():
    if settings.MOCK_AI:
        return None
    db = SessionLocal()
    try:
        setting = db.query(AISetting).filter(AISetting.is_active == True, AISetting.provider_name.like('%(Research)%')).first()
        if not setting or not setting.api_key:
            # Fallback to normal text active client
            setting = db.query(AISetting).filter(AISetting.is_active == True, ~AISetting.provider_name.like('%(Image)%'), ~AISetting.provider_name.like('%(Research)%')).first()
            if not setting or not setting.api_key:
                return None
                
        provider = setting.provider_name.replace(" (Research)", "")
        if provider in ["OpenAI", "9Router", "Perplexity"]:
            from openai import OpenAI
            client_args = {"api_key": setting.api_key}
            if hasattr(setting, 'base_url') and setting.base_url:
                client_args["base_url"] = setting.base_url
            elif provider == "Perplexity":
                client_args["base_url"] = "https://api.perplexity.ai"
                
            model_name = getattr(setting, 'model_name', None) or ("sonar-pro" if provider == "Perplexity" else settings.OPENAI_MODEL)
            return {"provider": provider, "client": OpenAI(**client_args), "model": model_name}
        elif provider == "Gemini":
            import google.generativeai as genai
            genai.configure(api_key=setting.api_key)
            model_name = getattr(setting, 'model_name', None) or 'gemini-1.5-pro'
            return {"provider": "Gemini", "client": genai.GenerativeModel(model_name), "model": model_name}
            
        return None
    except Exception:
        return None
    finally:
        db.close()

def _get_brand_context() -> str:
    db = SessionLocal()
    try:
        profile = db.query(BrandProfile).first()
        if not profile:
            return ""
        
        parts = []
        if profile.tone_of_voice:
            parts.append(f"- Tone of Voice (Giọng văn): {profile.tone_of_voice}")
        if profile.target_audience:
            parts.append(f"- Target Audience (Khách hàng mục tiêu): {profile.target_audience}")
        if profile.core_values:
            parts.append(f"- Core Values (Giá trị cốt lõi): {profile.core_values}")
        if profile.product_knowledge:
            parts.append(f"- Product Knowledge (Kiến thức Sản phẩm/Dịch vụ): {profile.product_knowledge}")
            
        if profile.hotline:
            parts.append(f"- Hotline/Zalo: {profile.hotline}")
        if profile.email:
            parts.append(f"- Email: {profile.email}")
        if profile.website:
            parts.append(f"- Website: {profile.website}")
        if profile.address:
            parts.append(f"- Địa chỉ: {profile.address}")
            
        if not parts:
            return ""
            
        context = "Thông tin Hồ sơ Thương hiệu (Brand Profile) cần tuân thủ tuyệt đối:\n" + "\n".join(parts) + "\n"
        context += "\nLƯU Ý ĐẶC BIỆT: Bắt buộc lồng ghép khéo léo thông tin liên hệ (Hotline, Email, Website, Địa chỉ) vào đoạn Call to Action (CTA) ở cuối bài viết.\n"
        return context
    except Exception:
        return ""
    finally:
        db.close()

def _get_product_descriptions(focus_products: str) -> str:
    if not focus_products:
        return ""
    
    products_dir = settings.BRAND_DIR / "products"
    if not products_dir.exists():
        return ""
        
    products = [p.strip() for p in focus_products.split(",") if p.strip()]
    if not products:
        return ""
        
    import re
    import unicodedata
    
    def slugify(text):
        slug = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', slug).strip('-').lower()
        return slug

    product_descriptions = []
    
    for prod in products:
        prod_slug = slugify(prod)
        if not prod_slug:
            continue
            
        for folder in products_dir.iterdir():
            if folder.is_dir():
                # Compare slug
                if prod_slug in folder.name or folder.name in prod_slug:
                    desc_file = folder / "description.txt"
                    if desc_file.exists():
                        try:
                            with desc_file.open("r", encoding="utf-8") as f:
                                desc = f.read().strip()
                                if desc:
                                    product_descriptions.append(f"--- Thông số/Mô tả sản phẩm '{prod}': ---\n{desc}")
                        except:
                            pass
                    break
                    
    if product_descriptions:
        return "\n\nTHÔNG TIN THAM KHẢO VỀ SẢN PHẨM TRỌNG TÂM (Sử dụng các thông tin này để viết bài chính xác hơn):\n" + "\n\n".join(product_descriptions) + "\n"
    return ""

def _safe_product_slug_static(focus_products: str) -> str:
    import re
    import unicodedata
    first = (focus_products or "").split(",")[0].strip() or "kinh-cuong-luc"
    slug = unicodedata.normalize('NFKD', first).encode('ASCII', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9]+', '-', slug).strip('-').lower()
class AIService:
    @staticmethod
    def generate_completion(prompt: str) -> str:
        """
        Gửi 1 prompt text cơ bản và lấy text response (dùng chung cho các tính năng sinh text nhỏ như tạo prompt ảnh).
        """
        ai_cfg = get_active_ai_client()
        if not ai_cfg:
            print("[AI_SERVICE] Cannot find active text AI client.")
            return ""
            
        provider = ai_cfg["provider"]
        client = ai_cfg["client"]
        model = ai_cfg["model"]
        
        try:
            if provider in ["OpenAI", "9Router"]:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=150
                )
                return response.choices[0].message.content.strip()
            elif provider == "Gemini":
                response = client.generate_content(prompt)
                return response.text.strip()
            else:
                print(f"[AI_SERVICE] Provider {provider} not supported for simple completion.")
                return ""
        except Exception as e:
            print(f"[AI_SERVICE] Error generating completion: {str(e)}")
            return ""

    @staticmethod
    def generate_image(prompt: str) -> str:
        """
        Gửi prompt lấy URL ảnh tạo bởi AI (Replicate FLUX, OpenAI DALL-E, etc.)
        """
        if settings.MOCK_AI:
            return f"https://image.pollinations.ai/prompt/{prompt}"
            
        img_cfg = get_active_image_client()
        if not img_cfg:
            # Fallback to pollinations if no API key configured
            import urllib.parse
            return f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
            
        provider = img_cfg["provider"]
        api_key = img_cfg["api_key"]
        
        try:
            import httpx
            if "Replicate" in provider:
                # Use Replicate API
                url = img_cfg["base_url"] or "https://api.replicate.com/v1/predictions"
                model_name = img_cfg["model"] or "black-forest-labs/flux-schnell"
                
                # Flux API on Replicate: POST to predictions with model version or model name
                # Actually, standard prediction API:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Prefer": "wait"
                }
                data = {
                    "input": {
                        "prompt": prompt,
                        "go_fast": True,
                        "megapixels": "1",
                        "num_outputs": 1,
                        "aspect_ratio": "9:16",
                        "output_format": "webp"
                    }
                }
                # For flux-schnell official endpoint
                if "models/black-forest-labs/flux-schnell/predictions" not in url:
                    url = "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions"
                    
                resp = httpx.post(url, headers=headers, json=data, timeout=60.0)
                if resp.status_code in [200, 201]:
                    res_json = resp.json()
                    if "output" in res_json and res_json["output"]:
                        return res_json["output"][0]
            elif "OpenAI" in provider:
                # Use OpenAI DALL-E 3
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1792",
                    quality="standard",
                    n=1,
                )
                return response.data[0].url
        except Exception as e:
            print(f"[AI_SERVICE] Image Generation Error: {e}")
            
        # Fallback
        import urllib.parse
        return f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"

    @staticmethod
    def generate_content_plan(
        core_theme: str, 
        month_year: str, 
        focus_products: str = "", 
        keywords: str = "",
        web_freq: int = 3,
        fanpage_freq: int = 4,
        web_content_pillars: str = None,
        fanpage_content_pillars: str = None
    ) -> List[Dict[str, Any]]:
        """
        Sinh ra danh sách kế hoạch nội dung (Content Plan) dự kiến trong tháng.
        Định dạng trả về: List của dict chứa {title, platform, format, scheduled_days_offset}
        """
        if settings.MOCK_AI:
            return AIService._mock_content_plan(core_theme, month_year, focus_products, keywords, web_freq, fanpage_freq, web_content_pillars, fanpage_content_pillars)
        
        return AIService._real_openai_content_plan(core_theme, month_year, focus_products, keywords, web_freq, fanpage_freq, web_content_pillars, fanpage_content_pillars)

    @staticmethod
    def generate_post_content(
        title: str, 
        platform: str, 
        format_type: str, 
        focus_products: str = "", 
        keywords: str = ""
    ) -> Dict[str, Any]:
        """
        Sinh nội dung chi tiết cho bài đăng:
        - Nếu Web: Sinh nội dung SEO (body H1, H2, H3), meta_title, meta_description, CTA.
        - Nếu Fanpage: Sinh nội dung ngắn, hashtag, prompt thiết kế ảnh.
        """
        if settings.MOCK_AI:
            return AIService._mock_post_content(title, platform, format_type, focus_products, keywords)
        
        return AIService._real_openai_post_content(title, platform, format_type, focus_products, keywords)

    @staticmethod
    def generate_video_research(campaign_name: str, core_theme: str, platform: str) -> str:
        """
        Thực hiện research thị trường, phân tích trend, hooks, formats và pain points để chuẩn bị làm kịch bản video.
        """
        if settings.MOCK_AI:
            return f"**Báo cáo Research Giả lập cho chiến dịch: {campaign_name}**\n\n1. Trending Hooks: 'Bạn có biết...', 'Sự thật về...'\n2. Formats: POV, Hướng dẫn nhanh.\n3. Pain points: Khách hàng sợ kính vỡ, khó vệ sinh.\n4. Keywords: #DAFA #KinhOpBep #NoiThat"
            
        provider_info = get_active_research_client()
        if not provider_info:
            raise Exception("No active AI Research client found")
            
        import datetime
        current_month = datetime.datetime.now().month
        
        prompt = f"""
        Thực hiện nghiên cứu thị trường và xu hướng mới nhất cho chủ đề: "{core_theme}" (Chiến dịch: {campaign_name}). Nền tảng đích: {platform}.

        Yêu cầu kết quả (Markdown format):
        Hãy trả lời đầy đủ 3 phần sau đây, lấy dữ liệu thực tế tại Việt Nam:

        1. Tìm các video TikTok Việt Nam đang viral trong tuần này có nội dung về: {core_theme}.
        - Cho biết chủ đề cụ thể và lý do người xem phản ứng mạnh.
        
        2. Những 'nỗi đau' nào của đối tượng mục tiêu liên quan đến {core_theme} đang được thảo luận nhiều nhất gần đây?
        - Tìm trên các diễn đàn, group Facebook, Reddit Việt Nam, TikTok comment.
        - Phải cho ví dụ câu chuyện cụ thể, không viết lý thuyết chung chung.

        3. Trong tháng {current_month}/2026, những vấn đề nào liên quan đến kinh tế, văn hóa, xã hội đang được bàn tán nhiều nhất trên mạng xã hội Việt Nam?
        - Cho ví dụ cụ thể về tình huống hoặc câu chuyện người ta đang chia sẻ, không cần format video.
        
        Sau khi phân tích 3 phần trên, hãy tổng hợp lại thành 5-10 ý tưởng nội dung có khả năng viral cao. 
        Với mỗi ý tưởng, CHỈ CẦN trình bày theo format sau:
        - **[Tên ý tưởng]**: [Mô tả nội dung ý tưởng. Ví dụ: hãy tìm cách để trở thành steve job Việt Nam -> Đây là chủ đề đang được bàn tán sôi động vài ngày hôm nay ở Việt Nam, do nó là nội dung của đề thi văn trong cuộc thi THPT...]
        """
        try:
            content = ""
            if provider_info["provider"] in ["OpenAI", "9Router", "Perplexity"]:
                client = provider_info["client"]
                model_name = provider_info.get("model")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert market researcher and social media trend analyst. Return a highly professional, actionable research report."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                content = response.choices[0].message.content.strip()
            elif provider_info["provider"] == "Gemini":
                client = provider_info["client"]
                response = client.generate_content("You are an expert market researcher and social media trend analyst. Return a highly professional, actionable research report in markdown.\n\n" + prompt)
                content = response.text.strip()
                
            return content
        except Exception as e:
            print(f"[AI ERROR] Lỗi khi chạy AI Research: {e}")
            raise Exception(f"Lỗi khi chạy AI Research: {e}")

    @staticmethod
    def generate_video_plan(
        campaign_name: str,
        month_year: str,
        objective: str,
        total_posts: int,
        content_proportions: List[Dict[str, Any]],
        vibe: str,
        platform: str,
        channel_info: Dict[str, str] = None
    ) -> List[Dict[str, Any]]:
        """
        Sinh kế hoạch Video theo tháng cho 1 kênh cụ thể.
        """
        if settings.MOCK_AI:
            plans = []
            for i in range(total_posts):
                day = (i * (28 // max(total_posts, 1))) + 1
                prop_name = content_proportions[i % len(content_proportions)]["name"] if content_proportions else "General"
                plans.append({
                    "title": f"[{prop_name}] Video Mock #{i+1} - {campaign_name}",
                    "content_line": prop_name,
                    "vibe": vibe,
                    "target_platforms": json.dumps([platform]),
                    "optimal_post_time": f"{month_year}-{day:02d}T19:00:00",
                    "trending_audio": "Trending sound mock",
                    "trending_hashtags": json.dumps(["#DAFAglass", f"#{platform.lower()}"]),
                    "ai_prompt": f"Viết kịch bản video {platform} về chủ đề {prop_name}",
                    "status": "Draft"
                })
            return plans
            
        provider_info = get_active_ai_client()
        if not provider_info:
            raise Exception("No active AI client found")
            
        lower_vibe = vibe.lower()
        is_kol = any(w in lower_vibe for w in ["kol", "hài", "giải trí", "cá nhân", "drama", "trend", "vlog"])
        if is_kol:
            brand_context = "KHÔNG SỬ DỤNG BẤT KỲ THÔNG TIN NÀO VỀ SẢN PHẨM HOẶC THƯƠNG HIỆU DAFA GLASS CHO KÊNH NÀY. Tập trung 100% vào việc sáng tạo nội dung giải trí/KOL để thu hút view và xây dựng kênh."
        else:
            brand_context = _get_brand_context()
        
        # Handle both dict and Pydantic objects
        props = []
        for p in content_proportions:
            if isinstance(p, dict):
                props.append(f"{p.get('percentage', 0)}% {p.get('name', 'General')}")
            else:
                props.append(f"{getattr(p, 'percentage', 0)}% {getattr(p, 'name', 'General')}")
        proportions_str = ", ".join(props)
        
        channel_guide = ""
        if channel_info:
            channel_guide = f"""
            Thông tin định hướng kênh:
            - Đối tượng người xem: {channel_info.get('target_audience', 'Không có')}
            - Độ dài & Định dạng: {channel_info.get('format_length', 'Không có')}
            - Giọng điệu (Tone of voice): {channel_info.get('tone_of_voice', 'Không có')}
            - Thông điệp chính: {channel_info.get('key_message', 'Không có')}
            """
            
        research_context = ""
        if channel_info and channel_info.get("research_data"):
            research_context = f"""
            DỮ LIỆU RESEARCH THỊ TRƯỜNG & TRENDING (Sử dụng dữ liệu này để lên ý tưởng):
            {channel_info.get("research_data")}
            """
        
        prompt = f"""
        Bạn là một chuyên gia Video Content Strategist.
        {brand_context}
        {channel_guide}
        {research_context}
        
        Hãy tạo một kế hoạch video chi tiết trong tháng {month_year} cho kênh {platform}.
        - Tên chiến dịch: {campaign_name}
        - Mục tiêu: {objective}
        - Phong cách (Vibe) của kênh: {vibe}
        - Tổng số lượng video cần sản xuất: {total_posts} video
        - Tỷ trọng các tuyến nội dung: {proportions_str}
        
        LƯU Ý CỰC KỲ QUAN TRỌNG: 
        - Đây là kênh mang phong cách '{vibe}'.
        - NẾU ĐÂY LÀ KÊNH KOL HOẶC KÊNH GIẢI TRÍ, TUYỆT ĐỐI KHÔNG VIẾT VỀ SẢN PHẨM KÍNH HOẶC ÉP BUỘC NHẮC TỚI DAFA GLASS vào các video không thuộc tuyến bán hàng.
        - TẬP TRUNG 100% VÀO SÁNG TẠO NỘI DUNG THEO ĐÚNG VIBE '{vibe}' ĐỂ HÚT VIEW.
        - CHỈ đưa sản phẩm vào nếu đó là video thuộc tuyến nội dung bán hàng / quảng cáo.
        
        RẤT QUAN TRỌNG: 
        1. Bạn phải sinh ĐÚNG CHÍNH XÁC {total_posts} object trong mảng JSON (không thừa không thiếu).
        2. Tên video (title) phải thật NGẮN GỌN (tối đa 10-15 chữ), chỉ tập trung vào chủ đề chính của video.
        3. Hãy phân bổ các ngày đăng hợp lý trong tháng.
        4. TRƯỜNG "ai_prompt": BẮT BUỘC phải trích xuất các ý tưởng, Hook, và Trend hay nhất từ "DỮ LIỆU RESEARCH THỊ TRƯỜNG & TRENDING" (nếu có) để tạo thành một Prompt cực kỳ chi tiết cho việc viết kịch bản ở bước tiếp theo. Đừng để trống hoặc viết chung chung!
        
        Yêu cầu trả về cấu trúc JSON hợp lệ dưới dạng một mảng (Array) chứa các object như sau, KHÔNG thêm bất kỳ giải thích nào bên ngoài JSON:
        [
          {{
            "title": "Tiêu đề video hấp dẫn",
            "content_line": "Tuyến nội dung tương ứng (VD: Hài hước, Review...)",
            "vibe": "{vibe}",
            "target_platforms": "[\"{platform}\"]",
            "optimal_post_time": "2026-06-15T19:00:00",
            "trending_audio": "Tên bài nhạc trending gợi ý",
            "trending_hashtags": "[\"#hashtag1\", \"#hashtag2\"]",
            "ai_prompt": "Prompt chi tiết cho AI viết kịch bản, CHẮC CHẮN PHẢI sử dụng Trend và Hook từ dữ liệu Research",
            "status": "Draft"
          }}
        ]
        """
        try:
            content = ""
            if provider_info["provider"] in ["OpenAI", "9Router", "Perplexity"]:
                client = provider_info["client"]
                model_name = provider_info.get("model") or settings.OPENAI_MODEL
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You output only valid JSON arrays without markdown block syntax."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                content = response.choices[0].message.content.strip()
            elif provider_info["provider"] == "Gemini":
                client = provider_info["client"]
                response = client.generate_content("You output only valid JSON arrays without markdown block syntax.\n\n" + prompt)
                content = response.text.strip()
                
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            parsed = json.loads(content.strip())
            if isinstance(parsed, dict):
                # Search for any list inside the dict
                for key, value in parsed.items():
                    if isinstance(value, list):
                        parsed = value
                        break
                if isinstance(parsed, dict):
                    # If still a dict, maybe wrap it in a list
                    parsed = [parsed]
            return parsed
        except Exception as e:
            print(f"[AI ERROR] Lỗi khi sinh Video Plan: {e}")
            raise Exception(f"Lỗi khi sinh Video Plan: {e}")

    # --- MOCK LOGIC ---
    @staticmethod
    def _mock_content_plan(core_theme: str, month_year: str, focus_products: str, keywords: str, web_freq: int = 3, fanpage_freq: int = 4, web_content_pillars: str = None, fanpage_content_pillars: str = None) -> List[Dict[str, Any]]:
        print("[MOCK AI] Đang tạo kế hoạch nội dung giả lập cho chủ đề:", core_theme)
        
        # Mẫu bài đăng dựa trên sản phẩm trọng tâm
        products = [p.strip() for p in focus_products.split(",") if p.strip()] if focus_products else ["Kính ốp bếp", "Vách kính tắm", "Cửa kính thủy lực DAFA"]
        product_1 = products[0]
        product_2 = products[1] if len(products) > 1 else products[0]
        
        plans = []
        
        # Web plans
        web_pillars = []
        if web_content_pillars:
            try:
                web_pillars = json.loads(web_content_pillars)
            except:
                pass
                
        if web_pillars:
            pillar_posts = []
            for pillar in web_pillars:
                count = max(1, round(web_freq * pillar.get("weight", 0) / 100))
                pillar_posts.append({"name": pillar["name"], "count": count})
                
            current_total = sum(p["count"] for p in pillar_posts)
            while current_total > web_freq and pillar_posts:
                pillar_posts[-1]["count"] = max(1, pillar_posts[-1]["count"] - 1)
                current_total = sum(p["count"] for p in pillar_posts)
            while current_total < web_freq and pillar_posts:
                pillar_posts[0]["count"] += 1
                current_total = sum(p["count"] for p in pillar_posts)
                
            web_count = 0
            for pp in pillar_posts:
                for _ in range(pp["count"]):
                    if web_count < web_freq:
                        day = (web_count * (28 // max(web_freq, 1))) + 1
                        plans.append({
                            "title": f"[{pp['name']}] Cẩm nang {product_1} cho kiến trúc",
                            "platform": "Web",
                            "format": "Long article",
                            "content_pillar": pp["name"],
                            "scheduled_days_offset": min(day, 28)
                        })
                        web_count += 1
        else:
            for i in range(web_freq):
                day = (i * (28 // max(web_freq, 1))) + 1
                plans.append({
                    "title": f"[{i+1}/{web_freq}] Cẩm nang {product_1} cho kiến trúc DAFA",
                    "platform": "Web",
                    "format": "Long article",
                    "content_pillar": "Kiến thức / Hướng dẫn",
                    "scheduled_days_offset": min(day, 28)
                })
                
        # Fanpage plans
        fanpage_pillars = []
        if fanpage_content_pillars:
            try:
                fanpage_pillars = json.loads(fanpage_content_pillars)
            except:
                pass
                
        if fanpage_pillars:
            pillar_posts = []
            for pillar in fanpage_pillars:
                count = max(1, round(fanpage_freq * pillar.get("weight", 0) / 100))
                pillar_posts.append({"name": pillar["name"], "count": count})
                
            current_total = sum(p["count"] for p in pillar_posts)
            while current_total > fanpage_freq and pillar_posts:
                pillar_posts[-1]["count"] = max(1, pillar_posts[-1]["count"] - 1)
                current_total = sum(p["count"] for p in pillar_posts)
            while current_total < fanpage_freq and pillar_posts:
                pillar_posts[0]["count"] += 1
                current_total = sum(p["count"] for p in pillar_posts)
                
            fanpage_count = 0
            for pp in pillar_posts:
                for _ in range(pp["count"]):
                    if fanpage_count < fanpage_freq:
                        day = (fanpage_count * (28 // max(fanpage_freq, 1))) + 3
                        plans.append({
                            "title": f"[{pp['name']}] Top mẫu {product_2} từ DAFA Glass",
                            "platform": "Fanpage",
                            "format": "Image post",
                            "content_pillar": pp["name"],
                            "scheduled_days_offset": min(day, 28)
                        })
                        fanpage_count += 1
        else:
            for i in range(fanpage_freq):
                day = (i * (28 // max(fanpage_freq, 1))) + 3
                plans.append({
                    "title": f"[{i+1}/{fanpage_freq}] Top mẫu {product_2} siêu sang từ DAFA Glass",
                    "platform": "Fanpage",
                    "format": "Image post",
                    "content_pillar": "Sản phẩm / Bán hàng",
                    "scheduled_days_offset": min(day, 28)
                })

        return plans

    @staticmethod
    def generate_video_script(title: str, content_line: str, platform: str, ai_prompt: str = None, vibe: str = "Chuyên nghiệp") -> List[Dict[str, Any]]:
        if settings.MOCK_AI:
            return [
                {"scene_order": 1, "setting": "Studio", "frame_type": "Hook", "voiceover": f"Bạn đã biết {title}?", "on_screen_text": "SỰ THẬT LÀ...", "visuals": "Quay cận cảnh", "audio": "Nhạc kịch tính", "transition": "Zoom in"},
                {"scene_order": 2, "setting": "Ngoài trời", "frame_type": "Body", "voiceover": f"Đây là nội dung {content_line}.", "on_screen_text": "TÍNH NĂNG NỔI BẬT", "visuals": "Sử dụng sản phẩm", "audio": "Nhạc vui tươi", "transition": "Fade out"}
            ]
        
        provider_info = get_active_ai_client()
        if not provider_info:
            raise Exception("No active AI client")
            
        lower_vibe = vibe.lower()
        is_kol = any(w in lower_vibe for w in ["kol", "hài", "giải trí", "cá nhân", "drama", "trend", "vlog"])
        if is_kol:
            brand_context = "KHÔNG SỬ DỤNG BẤT KỲ THÔNG TIN NÀO VỀ SẢN PHẨM HOẶC THƯƠNG HIỆU DAFA GLASS CHO KÊNH NÀY. Tập trung 100% vào việc sáng tạo nội dung giải trí/KOL để thu hút view và xây dựng kênh. TRONG PHẦN CTA TUYỆT ĐỐI KHÔNG BÁN HÀNG, CHỈ KÊU GỌI FOLLOW/TƯƠNG TÁC KÊNH."
        else:
            brand_context = _get_brand_context()
            
        prompt_instruction = f"Prompt tùy chỉnh từ người dùng: {ai_prompt}" if ai_prompt else ""
            
        prompt = f"""
        Bạn là một chuyên gia Video Content Strategist và Script Writer.
        {brand_context}
        
        Tạo kịch bản video ngắn (TikTok/Reels/Shorts) cho:
        Tiêu đề: {title}
        Tuyến nội dung: {content_line}
        Nền tảng: {platform}
        
        {prompt_instruction}
        
        Trả về DUY NHẤT mảng JSON chứa các phân cảnh (scene). Mỗi object có:
        scene_order (int), setting (string), frame_type (string: Hook/Body/CTA), voiceover (string), on_screen_text (string), visuals (string), audio (string), transition (string).
        """
        try:
            content = ""
            client = provider_info["client"]
            if provider_info["provider"] in ["OpenAI", "9Router"]:
                model_name = provider_info.get("model") or settings.OPENAI_MODEL
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You output only valid JSON arrays without markdown block syntax."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                content = response.choices[0].message.content.strip()
            elif provider_info["provider"] == "Gemini":
                response = client.generate_content("You output only valid JSON arrays without markdown block syntax.\n\n" + prompt)
                content = response.text.strip()
                
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content.strip())
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    if isinstance(v, list):
                        parsed = v
                        break
                if isinstance(parsed, dict):
                    parsed = [parsed]
            return parsed
        except Exception as e:
            print(f"[AI ERROR] Lỗi khi sinh Video Script: {e}")
            raise Exception(f"Lỗi khi sinh Video Script: {e}")

    @staticmethod
    def _mock_post_content(title: str, platform: str, format_type: str, focus_products: str, keywords: str) -> Dict[str, Any]:
        print(f"[MOCK AI] Đang sinh nội dung bài viết cho [{platform}] - Tiêu đề: {title}")
        
        if platform.lower() == "web":
            # Tạo bài viết SEO giả lập với Image Slots
            body_html = f"""<h1>{title}</h1>
<p>Trong kiến trúc hiện đại, kính cường lực đã trở thành vật liệu không thể thiếu để kiến tạo không gian sống mở, sang trọng và tràn ngập ánh sáng tự nhiên. Đối với thương hiệu <strong>DAFA glass</strong>, chúng tôi tự hào mang đến các giải pháp kính kiến trúc và kính trang trí chất lượng vượt trội.</p>

<!-- IMAGE_SLOT_1 -->
<!-- IMAGE_SLOT_PROMPT_1: Ảnh chụp toàn cảnh không gian phòng khách hiện đại lắp đặt vách kính cường lực DAFA Glass, ánh sáng tự nhiên tràn ngập, tông màu trắng sang trọng -->

<h2>Ưu điểm nổi bật của dòng sản phẩm DAFA Glass</h2>
<p>Các sản phẩm của chúng tôi, đặc biệt là dòng kính cường lực và gương trang trí, sở hữu độ bền cơ học gấp 4-5 lần kính thường. Nhờ công nghệ tôi nhiệt tiên tiến, kính có khả năng chống va đập mạnh, chống sốc nhiệt tối đa, mang lại sự an toàn tuyệt đối cho người sử dụng.</p>

<!-- IMAGE_SLOT_2 -->
<!-- IMAGE_SLOT_PROMPT_2: Ảnh cận cảnh quy trình sản xuất kính cường lực trong nhà máy, công nhân đang kiểm tra chất lượng bề mặt kính, ánh sáng công nghiệp, chuyên nghiệp -->

<h2>Lợi ích khi lắp đặt thiết bị kính cao cấp DAFA</h2>
<ul>
  <li>Tính thẩm mỹ cao: Bề mặt kính nhẵn bóng, dễ vệ sinh, tạo hiệu ứng mở rộng không gian cực tốt.</li>
  <li>Độ bền vượt thời gian: Không bị ố mốc, xước xát nhờ lớp phủ nano cao cấp.</li>
  <li>Thi công nhanh chóng: Đội ngũ kỹ thuật lành nghề của DAFA glass cam kết bàn giao đúng tiến độ.</li>
</ul>

<!-- IMAGE_SLOT_3 -->
<!-- IMAGE_SLOT_PROMPT_3: Ảnh before-after so sánh phòng tắm trước và sau khi lắp vách kính cường lực DAFA, không gian sáng sủa hơn hẳn, thiết kế hiện đại -->

<h2>Lời kết và liên hệ báo giá</h2>
<p>Nếu bạn đang có nhu cầu tân trang không gian gia đình bằng các mẫu kính bếp, vách tắm kính hay gương decor sang trọng, hãy liên hệ ngay với <strong>DAFA glass</strong> để được tư vấn miễn phí và nhận ưu đãi tốt nhất tháng này!</p>"""

            headings = {
                "H1": title,
                "H2": ["Ưu điểm nổi bật của dòng sản phẩm DAFA Glass", "Lợi ích khi lắp đặt thiết bị kính cao cấp DAFA", "Lời kết và liên hệ báo giá"]
            }

            return {
                "title": title,
                "body": body_html,
                "meta_title": f"{title[:50]} | DAFA Glass Kính Cường Lực",
                "meta_description": f"Tìm hiểu ngay {title.lower()} tại DAFA glass. Đơn vị chuyên thi công kính cường lực, kính bếp, vách tắm kính chất lượng cao, an toàn số 1.",
                "headings_structure": json.dumps(headings, ensure_ascii=False),
                "image_prompt": f"Ảnh chụp thực tế góc thi công kính sang trọng của DAFA Glass, ánh sáng tự nhiên tươi sáng, độ nét cao.",
                "utm_source": "website"
            }
        else:
            # Tạo bài đăng Facebook giả lập
            hashtags = "#DAFAglass #kinhcuongluc #vachkinhtam #kinhopeb #noithathiendai #kinhkientruc"
            fb_body = f"""✨ {title} ✨

🏡 Bạn muốn nâng tầm không gian sống trở nên sang trọng, hiện đại và tràn ngập ánh sáng? Kính cường lực DAFA chính là câu trả lời hoàn hảo!

👉 Tại sao nên chọn DAFA Glass?
✔ Kính cường lực siêu bền, chịu lực tốt, an toàn tuyệt đối.
✔ Thiết kế may đo riêng biệt phù hợp từng góc nhà (Kính ốp bếp, vách kính tắm, gương trang trí...).
✔ Dịch vụ thi công lắp đặt trọn gói chuyên nghiệp, bảo hành uy tín.

📞 Inbox ngay cho Fanpage hoặc gọi Hotline để nhận báo giá ưu đãi độc quyền hôm nay!
---
{hashtags}"""
            
            image_prompt = f"Thiết kế poster marketing hình vuông 1:1, chủ đề '{title}'. Góc trái có logo DAFA Glass nhỏ, hiển thị hình ảnh nội thất lắp đặt kính sang trọng, tông màu xanh ngọc và trắng hiện đại, chữ text nổi bật: 'An Toàn - Sang Trọng - Bền Bỉ'."
            
            return {
                "title": title,
                "body": fb_body,
                "image_prompt": image_prompt,
                "utm_source": "facebook"
            }

    # --- REAL OPENAI LOGIC ---
    @staticmethod
    @staticmethod
    def _real_openai_content_plan(core_theme: str, month_year: str, focus_products: str, keywords: str, web_freq: int = 3, fanpage_freq: int = 4, web_content_pillars: str = None, fanpage_content_pillars: str = None) -> List[Dict[str, Any]]:
        provider_info = get_active_ai_client()
        if not provider_info:
            print("[AI ERROR] AI chưa được cấu hình. Chuyển sang dùng Mock.")
            return AIService._mock_content_plan(core_theme, month_year, focus_products, keywords, web_freq, fanpage_freq, web_content_pillars, fanpage_content_pillars)

        # Xây dựng hướng dẫn content pillars nếu có
        pillars_instruction = ""
        
        web_instr = ""
        if web_content_pillars:
            try:
                pillars = json.loads(web_content_pillars)
                if pillars:
                    web_instr = "Web Content Pillars (Tỷ trọng %):\n" + "\n".join([f"- {p['name']}: {p['weight']}%" for p in pillars])
            except:
                pass
                
        fanpage_instr = ""
        if fanpage_content_pillars:
            try:
                pillars = json.loads(fanpage_content_pillars)
                if pillars:
                    fanpage_instr = "Fanpage Content Pillars (Tỷ trọng %):\n" + "\n".join([f"- {p['name']}: {p['weight']}%" for p in pillars])
            except:
                pass
                
        if web_instr or fanpage_instr:
            pillars_instruction = "\nPhân bổ bài viết theo các tuyến nội dung với tỷ trọng sau:\n" + web_instr + "\n" + fanpage_instr + "\nĐảm bảo số lượng bài ở mỗi tuyến phản ánh đúng tỷ trọng đã cho trên từng kênh."

        brand_context = _get_brand_context()
        product_context = _get_product_descriptions(focus_products)

        prompt = f"""
        Bạn là một chuyên gia Content Strategist.
        {brand_context}
        {product_context}
        Hãy tạo một kế hoạch nội dung marketing chi tiết trong tháng {month_year} dựa trên các thông tin sau:
        - Chủ đề cốt lõi của tháng: {core_theme}
        - Sản phẩm trọng tâm: {focus_products}
        - Từ khóa chủ đạo: {keywords}

        Kế hoạch phải bao gồm chính xác {web_freq + fanpage_freq} bài viết, trong đó có:
        - {web_freq} bài viết Website SEO dài (platform: "Web")
        - {fanpage_freq} bài viết Facebook Fanpage ngắn (platform: "Fanpage")
        
        Hãy sắp xếp lịch đăng (scheduled_days_offset từ 1 đến 28) rải rác đan xen trong tháng.

        Yêu cầu trả về cấu trúc JSON hợp lệ dưới dạng một mảng (Array) chứa các object như sau, KHÔNG thêm bất kỳ giải thích nào bên ngoài JSON:
        [
          {{
            "title": "Tiêu đề bài viết dự kiến",
            "platform": "Web" hoặc "Fanpage",
            "format": "Long article" (cho Web) hoặc "Image post"/"Video" (cho Fanpage),
            "content_pillar": "Tuyến nội dung tương ứng (VD: Kiến thức, Sản phẩm, Giải trí, Thương hiệu, v.v.)",
            "target_keywords": "3-5 từ khóa SEO mục tiêu cho bài Web, ngăn cách bằng dấu phẩy (Để trống nếu là Fanpage)",
            "scheduled_days_offset": số nguyên từ 1 đến 28
          }}
        ]
        {pillars_instruction}
        """
        try:
            content = ""
            if provider_info["provider"] in ["OpenAI", "9Router"]:
                client = provider_info["client"]
                model_name = provider_info.get("model") or settings.OPENAI_MODEL
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON arrays without markdown block syntax."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                content = response.choices[0].message.content.strip()
            elif provider_info["provider"] == "Gemini":
                client = provider_info["client"]
                full_prompt = "You are a helpful assistant that outputs only valid JSON arrays without markdown block syntax.\n\n" + prompt
                response = client.generate_content(full_prompt)
                content = response.text.strip()
                
            # Xử lý trường hợp bọc JSON trong ```json ... ```
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            return json.loads(content)
        except Exception as e:
            print(f"[AI ERROR] Lỗi khi gọi AI API: {e}. Sử dụng Mock thay thế.")
            return AIService._mock_content_plan(core_theme, month_year, focus_products, keywords, web_freq, fanpage_freq, web_content_pillars, fanpage_content_pillars)

    @staticmethod
    def _real_openai_post_content(title: str, platform: str, format_type: str, focus_products: str, keywords: str) -> Dict[str, Any]:
        provider_info = get_active_ai_client()
        if not provider_info:
            print("[AI ERROR] AI không khả dụng. Sử dụng Mock.")
            return AIService._mock_post_content(title, platform, format_type, focus_products, keywords)

        brand_context = _get_brand_context()
        product_context = _get_product_descriptions(focus_products)

        if platform.lower() == "web":
            # Gửi prompt viết bài SEO Web
            prompt = f"""
            Hãy viết một bài viết chuẩn SEO chi tiết (Long article) bằng HTML dựa trên tiêu đề kế hoạch: "{title}"
            Sản phẩm liên quan: {focus_products}
            Từ khóa chủ đạo cần SEO: {keywords}
            {brand_context}
            {product_context}

            Yêu cầu:
            - Viết theo cấu trúc HTML chuẩn (dùng thẻ <h1>, <h2>, <h3>, <p>, <ul>, <li>). CHỈ trả về phần nội dung HTML bên trong thẻ <body> (không trả về <html>, <head>).
            - Nội dung chuyên sâu, văn phong phù hợp với thương hiệu.
            - Phân bổ từ khóa tự nhiên.
            - Ở các vị trí cần chèn ảnh minh họa, hãy chèn chính xác chuỗi sau: <!-- IMAGE_SLOT_N --> và ngay bên dưới nó chèn <!-- IMAGE_SLOT_PROMPT_N: mô tả chi tiết hình ảnh cần thiết kế cho đoạn này --> (N là số thứ tự 1, 2, 3...).
            - Viết kèm một đoạn text ngắn làm Headline, Subheadline (Mô tả ngắn) và CTA để in đè lên ảnh đại diện bài viết. Chú ý CTA phải phù hợp với bài viết trên website (VD: Đọc chi tiết, Tìm hiểu ngay, Nhận báo giá).
            - Xử lý Internal/External Link: Tự động gắn các External link ra các trang uy tín (như Wikipedia) cho các khái niệm thuật ngữ nếu cần. Với các sản phẩm cốt lõi hoặc từ khóa chính, hãy tạo sẵn Placeholder Internal Link theo định dạng: `<a href="[CHUYEN_TRANG_SAN_PHAM]">từ khóa</a>` để quản trị viên dễ dàng điền link sau.

            Hãy trả về một định dạng JSON duy nhất, KHÔNG chứa markdown block:
            {{
              "title": "{title}",
              "body": "Nội dung HTML ở đây...",
              "meta_title": "Meta Title chuẩn SEO ở đây",
              "meta_description": "Meta Description chuẩn SEO ở đây",
              "headings_structure": "{{\\"H1\\": \\"{title}\\", \\"H2\\": [\\"Ý 1\\", \\"Ý 2\\"]}}",
              "image_prompt": "Prompt gợi ý thiết kế ảnh đi kèm bài viết SEO này",
              "headline": "Tiêu đề ngắn in trên ảnh (tối đa 6 từ)",
              "subheadline": "Mô tả ngắn in trên ảnh (tối đa 12 từ)",
              "cta": "Call to action ngắn gọn in trên ảnh (tối đa 5 từ)",
              "utm_source": "website"
            }}
            """
        else:
            # Gửi prompt viết bài Facebook Fanpage
            prompt = f"""
            Hãy viết một bài đăng Facebook Fanpage ngắn gọn, hấp dẫn bằng tiếng Việt dựa trên tiêu đề kế hoạch: "{title}"
            Sản phẩm liên quan: {focus_products}
            {brand_context}
            {product_context}

            Yêu cầu:
            - Giọng văn sinh động, bắt trend, sử dụng các biểu tượng cảm xúc (emoji) phù hợp.
            - Có các hashtag thương hiệu và ngành phù hợp.
            - Viết kèm một "Prompt gợi ý thiết kế ảnh" chi tiết để designer hoặc AI tạo ảnh minh họa phù hợp cho bài viết này.
            - Viết kèm Headline, Subheadline (Mô tả) và CTA để in đè lên ảnh thiết kế đăng Facebook. Chú ý CTA phải phù hợp với kênh Fanpage (VD: Nhắn tin ngay, Inbox tư vấn, Đặt lịch khảo sát).

            Hãy trả về một định dạng JSON duy nhất, KHÔNG chứa markdown block:
            {{
              "title": "{title}",
              "body": "Nội dung bài đăng Facebook ở đây...",
              "image_prompt": "Mô tả chi tiết prompt gợi ý thiết kế ảnh ở đây...",
              "headline": "Tiêu đề cực ngắn in trên ảnh (tối đa 6 từ)",
              "subheadline": "Mô tả đánh trúng tâm lý in trên ảnh (tối đa 12 từ)",
              "cta": "Call to action in trên ảnh (tối đa 5 từ)",
              "utm_source": "facebook"
            }}
            """

        try:
            content = ""
            if provider_info["provider"] in ["OpenAI", "9Router"]:
                client = provider_info["client"]
                model_name = provider_info.get("model") or settings.OPENAI_MODEL
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON objects without markdown block syntax."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                content = response.choices[0].message.content.strip()
            elif provider_info["provider"] == "Gemini":
                client = provider_info["client"]
                full_prompt = "You are a helpful assistant that outputs only valid JSON objects without markdown block syntax.\n\n" + prompt
                response = client.generate_content(full_prompt)
                content = response.text.strip()
                
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            return json.loads(content)
        except Exception as e:
            print(f"[AI ERROR] Lỗi khi gọi OpenAI API để viết bài: {e}. Sử dụng Mock.")
            return AIService._mock_post_content(title, platform, format_type, focus_products, keywords)

    @staticmethod
    def generate_insights(campaign_name: str, month_year: str, focus_products: str, metrics_summary: str) -> str:
        """
        Dùng AI để phân tích dữ liệu hiệu quả thật của chiến dịch và trả về nhận xét.
        """
        provider_info = get_active_ai_client()
        if not provider_info or settings.MOCK_AI:
            print("[AI ERROR] AI không khả dụng hoặc MOCK mode được bật. Trả về insight mẫu.")
            return f"### 📊 BÁO CÁO PHÂN TÍCH HIỆU QUẢ - THÁNG {month_year} (AI Generated)\n\n#### 1. Chủ đề hiệu quả nhất:\n- Các bài viết xoay quanh sản phẩm **\"{focus_products.split(',')[0] if focus_products else 'DAFA'}\"** đạt lượng truy cập tốt.\n\n#### 2. Điểm cần cải thiện:\n- Tỷ lệ thoát trên bài viết hướng dẫn cao.\n\n#### 3. Đề xuất:\n- Tối ưu SEO và thử nghiệm định dạng video ngắn."

        prompt = f"""
        Bạn là chuyên gia phân tích dữ liệu Marketing. Dưới đây là số liệu thực tế của chiến dịch "{campaign_name}" trong tháng {month_year}.
        Sản phẩm trọng tâm của chiến dịch: {focus_products}

        {metrics_summary}

        Dựa trên số liệu này, hãy viết một bản báo cáo tóm tắt bằng tiếng Việt với cấu trúc sau:
        ### 📊 BÁO CÁO PHÂN TÍCH HIỆU QUẢ - THÁNG {month_year}
        
        #### 1. Đánh giá chung & Điểm sáng:
        (Phân tích các bài viết có views/reach/engagement cao nhất, tìm ra nguyên nhân thành công dựa trên chủ đề hoặc nền tảng)
        
        #### 2. Điểm cần cải thiện:
        (Phân tích các bài viết có hiệu quả thấp hoặc bounce rate cao, chỉ ra vấn đề về CTA, hình ảnh hoặc nội dung)
        
        #### 3. Đề xuất hành động tháng sau:
        (Đưa ra 2-3 đề xuất cụ thể để cái thiện hiệu quả cho kế hoạch nội dung tiếp theo)

        Trả về kết quả dưới dạng Markdown sạch, mạch lạc. Không cần mở bài/kết bài thừa.
        """

        try:
            content = ""
            if provider_info["provider"] in ["OpenAI", "9Router"]:
                client = provider_info["client"]
                model_name = provider_info.get("model") or settings.OPENAI_MODEL
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a professional marketing data analyst."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                content = response.choices[0].message.content.strip()
            elif provider_info["provider"] == "Gemini":
                client = provider_info["client"]
                full_prompt = "You are a professional marketing data analyst.\n\n" + prompt
                response = client.generate_content(full_prompt)
                content = response.text.strip()
                
            return content
        except Exception as e:
            print(f"[AI ERROR] Lỗi khi phân tích số liệu: {e}")
            return f"### 📊 BÁO CÁO PHÂN TÍCH HIỆU QUẢ - THÁNG {month_year}\n\nHiện tại hệ thống AI đang quá tải và không thể phân tích số liệu tự động. Lỗi: {e}"


