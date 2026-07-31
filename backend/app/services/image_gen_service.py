import base64
import io
import json
import os
import random
import uuid
import httpx
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from app.core.config import settings


class ImageGenService:
    GLASS_TEMPLATE_PROMPTS = {
        "glass_facade_premium": "realistic modern commercial building facade with blue-tinted energy-efficient architectural glass, premium corporate advertising background, daylight reflections, clean composition, empty space on the left for headline, no text, no logo, no watermark, no people close-up",
        "office_partition_clean": "modern office interior with clear glass partitions, bright natural daylight, premium minimalist workspace, clean architectural advertising background, elegant reflections, empty space for product information, no text, no logo, no watermark",
        "residential_glass_railing": "modern villa balcony with clear tempered glass railing, premium residential architecture, natural daylight, elegant glass reflections, clean luxury advertising background, no text, no logo, no watermark",
        "kitchen_backsplash": "modern luxury kitchen with glossy glass backsplash, clean countertop, warm daylight, premium interior design advertising background, no text, no logo, no watermark",
        "shower_glass": "modern bathroom with frameless glass shower enclosure, clean premium interior, natural light, elegant reflections, no text, no logo, no watermark",
        "technical_product_card": "premium clean architectural glass material advertising background, modern construction project mood, soft gradient light, minimal composition, empty space for product card, no text, no logo, no watermark",
    }

    @staticmethod
    def _safe_slug(text: str) -> str:
        import re
        import unicodedata
        text = text or ""
        slug = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
        return re.sub(r'[^a-zA-Z0-9]+', '-', slug).strip('-').lower()

    @staticmethod
    def _font(size: int, bold: bool = False):
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        ]
        for c in candidates:
            if Path(c).exists():
                return ImageFont.truetype(c, size=size)
        return ImageFont.load_default()

    @staticmethod
    def _wrap_text(draw, text: str, font, max_width: int):
        words = (text or "").split()
        lines, line = [], ""
        for word in words:
            test = (line + " " + word).strip()
            if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    @staticmethod
    def _aspect_to_size(aspect_ratio: str) -> str:
        return {"1:1": "1024x1024", "4:5": "1024x1280", "16:9": "1280x720", "9:16": "720x1280"}.get(aspect_ratio or "1:1", "1024x1024")

    @staticmethod
    def _load_product(folder_slug: str = None, search_text: str = "") -> dict:
        products_dir = settings.BRAND_DIR / "products"
        if not products_dir.exists():
            return {}
        selected = None
        if folder_slug:
            candidate = products_dir / ImageGenService._safe_slug(folder_slug)
            if candidate.exists() and candidate.is_dir():
                selected = candidate
        if not selected and search_text:
            haystack = ImageGenService._safe_slug(search_text)
            for folder in products_dir.iterdir():
                if folder.is_dir() and (folder.name in haystack or haystack in folder.name):
                    selected = folder
                    break
        if not selected:
            return {}
        data = {"slug": selected.name, "name": selected.name.replace('-', ' ').title(), "description": "", "images": []}
        desc_file = selected / "description.txt"
        if desc_file.exists():
            try:
                data["description"] = desc_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        json_file = selected / "product.json"
        if json_file.exists():
            try:
                meta = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(meta, dict):
                    data.update(meta)
                    data.setdefault("slug", selected.name)
            except Exception as e:
                print(f"[IMAGE_GEN] Cannot parse product.json for {selected.name}: {e}")
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            data["images"].extend(selected.glob(ext))
        return data
    @staticmethod
    def generate_image_prompt(article_title: str, article_body: str, platform: str, product_descriptions: str = "") -> str:
        """
        AI đọc nội dung bài viết và tạo prompt sinh ảnh.
        Sử dụng Gemini API nếu không ở chế độ mock.
        """
        if settings.MOCK_IMAGE_GEN:
            print("[MOCK IMAGE_GEN] Generating image prompt from article content")
            return f"Professional photo of premium glass products for DAFA Glass company, related to: {article_title}. Modern interior design, high quality, studio lighting, clean background. {product_descriptions}"

        # Real mode: Sử dụng AIService để tạo prompt ảnh từ nội dung bài viết
        try:
            from app.services.ai_service import AIService
            
            prompt = f"""Bạn là một chuyên gia thiết kế đồ họa. Dựa trên nội dung bài viết sau, hãy tạo một prompt tiếng Anh ngắn gọn (dưới 200 từ) để tạo ảnh minh họa chuyên nghiệp.

Tiêu đề: {article_title}
Nội dung tóm tắt: {article_body[:500]}
Nền tảng: {platform}
{'Mô tả sản phẩm cần xuất hiện: ' + product_descriptions if product_descriptions else ''}

Yêu cầu prompt ảnh:
- Phong cách chuyên nghiệp, hiện đại
- Phù hợp thương hiệu DAFA Glass (kính cường lực, kính ốp bếp, vách tắm kính)
- Màu sắc sang trọng, ánh sáng tốt
- KHÔNG có chữ/text trong ảnh

Chỉ trả về prompt tạo ảnh, không giải thích."""

            response_text = AIService.generate_completion(prompt)
            if response_text:
                return response_text.strip()
            else:
                return f"Professional product photography of glass products for DAFA Glass, {article_title}"
        except Exception as e:
            print(f"[IMAGE_GEN] Error generating prompt: {e}")
            return f"Professional photo of premium glass products for DAFA Glass company, related to: {article_title}"

    @staticmethod
    def generate_image(prompt: str, size: str = "1024x1024") -> str:
        """
        Tạo ảnh bằng Gemini Imagen API.
        Trả về đường dẫn file của ảnh đã lưu.
        """
        if settings.MOCK_IMAGE_GEN:
            print(f"[MOCK IMAGE_GEN] Would generate image with prompt: {prompt[:100]}...")
            # Tạo ảnh placeholder
            width, height = 1024, 1024
            img = Image.new('RGB', (width, height), color=(30, 30, 50))
            draw = ImageDraw.Draw(img)
            # Vẽ các element trang trí
            for i in range(5):
                x1 = random.randint(0, width)
                y1 = random.randint(0, height)
                x2 = x1 + random.randint(100, 300)
                y2 = y1 + random.randint(100, 300)
                color = (random.randint(0, 100), random.randint(150, 255), random.randint(150, 255))
                draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
            # Thêm text
            draw.text((width // 4, height // 2 - 20), "[MOCK] AI Generated Image", fill=(200, 200, 200))
            draw.text((width // 4, height // 2 + 10), prompt[:60] + "...", fill=(150, 150, 150))

            file_name = f"ai_gen_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
            file_path = settings.UPLOAD_DIR / file_name
            img.save(str(file_path), 'PNG')
            return f"/uploads/{file_name}"

        # Real mode: Sử dụng Image Gen API từ DB Settings
        try:
            from app.models.setting import AISetting
            from app.core.database import SessionLocal
            import httpx
            
            db = SessionLocal()
            ai_setting = db.query(AISetting).filter(AISetting.provider_name.like("%(Image)"), AISetting.is_active == True).first()
            db.close()
            
            if not ai_setting or not ai_setting.api_key:
                print("[IMAGE_GEN] Falling back to MOCK mode due to missing API Key...")
                raise Exception("Không tìm thấy AI provider tạo ảnh nào đang hoạt động")

            file_name = f"ai_gen_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
            file_path = settings.UPLOAD_DIR / file_name

            if "Replicate FLUX" in ai_setting.provider_name or "Replicate" in ai_setting.provider_name:
                import replicate
                client = replicate.Client(api_token=ai_setting.api_key.strip())
                model_name = ai_setting.model_name or "black-forest-labs/flux-schnell"
                replicate_input = {
                    "prompt": prompt,
                    "aspect_ratio": "1:1",
                    "output_format": "png",
                    "num_outputs": 1,
                }
                # FLUX Schnell hỗ trợ thêm các tham số này; giúp ảnh ổn hơn một chút.
                if "flux-schnell" in model_name:
                    replicate_input.update({"go_fast": True, "num_inference_steps": 4, "output_quality": 95})
                output = client.run(model_name, input=replicate_input)
                first = output[0] if isinstance(output, list) else output
                if hasattr(first, "read"):
                    with open(file_path, "wb") as f:
                        f.write(first.read())
                else:
                    with httpx.Client(timeout=120) as h_client:
                        img_res = h_client.get(str(first))
                        img_res.raise_for_status()
                        with open(file_path, 'wb') as f:
                            f.write(img_res.content)
                return f"/uploads/{file_name}"

            if "Gemini" in ai_setting.provider_name:
                from google import genai
                from google.genai import types
                import io
                from PIL import Image as PILImage
                
                client = genai.Client(api_key=ai_setting.api_key)
                model_name = ai_setting.model_name or 'imagen-3.0-generate-001'
                
                result = client.models.generate_images(
                    model=model_name,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="1:1"
                    )
                )
                
                if result.generated_images:
                    image_bytes = result.generated_images[0].image.image_bytes
                    img = PILImage.open(io.BytesIO(image_bytes))
                    img.save(str(file_path))
                    return f"/uploads/{file_name}"
                else:
                    raise Exception("Không có ảnh nào được tạo từ Gemini")

            elif "OpenAI" in ai_setting.provider_name or "9Router" in ai_setting.provider_name:
                from openai import OpenAI
                client_args = {"api_key": ai_setting.api_key}
                if ai_setting.base_url:
                    client_args["base_url"] = ai_setting.base_url
                client = OpenAI(**client_args)
                
                response = client.images.generate(
                    model=ai_setting.model_name or ("cx/gpt-5.5-image" if "9Router" in ai_setting.provider_name else "dall-e-3"),
                    prompt=prompt,
                    size=size or "1024x1024",
                    quality="high" if "9Router" in ai_setting.provider_name else "standard",
                    n=1,
                )

                if not response.data:
                    raise Exception("Không nhận được dữ liệu ảnh từ provider")

                image_data = response.data[0]

                # 9Router/Codex thường trả ảnh dạng base64 (b64_json) thay vì URL.
                b64_json = getattr(image_data, "b64_json", None)
                if b64_json:
                    import base64
                    with open(file_path, 'wb') as f:
                        f.write(base64.b64decode(b64_json))
                    return f"/uploads/{file_name}"

                # OpenAI/DALL-E hoặc một số provider compatible có thể trả URL.
                image_url = getattr(image_data, "url", None)
                if image_url:
                    with httpx.Client() as h_client:
                        img_res = h_client.get(image_url)
                        img_res.raise_for_status()
                        with open(file_path, 'wb') as f:
                            f.write(img_res.content)
                    return f"/uploads/{file_name}"

                raise Exception("Provider không trả về b64_json hoặc url cho ảnh")

        except Exception as e:
            print(f"[IMAGE_GEN] Error generating image: {e}")
            # Không sinh ảnh giả khi provider lỗi, vì ảnh mock làm người dùng tưởng prompt sai.
            raise Exception(f"Provider tạo ảnh lỗi: {e}")

    @staticmethod
    def overlay_logo(image_path: str, position: str = "top-left", scale: float = 0.10) -> str:
        """
        Chèn logo thương hiệu lên ảnh đã sinh bằng Pillow.
        position: 'top-left', 'top-right', 'bottom-left', 'bottom-right'
        scale: chiều rộng logo theo tỷ lệ chiều rộng ảnh (0.10 = 10%)
        Trả về đường dẫn ảnh đã chèn logo.
        """
        logo_dir = settings.BRAND_DIR
        logo_files = list(logo_dir.glob("logo.*"))

        if not logo_files:
            print("[IMAGE_GEN] No logo file found, skipping overlay")
            return image_path

        logo_path = logo_files[0]

        try:
            # Xác định đường dẫn file thực tế
            if image_path.startswith("/uploads/"):
                actual_image_path = settings.UPLOAD_DIR / image_path.replace("/uploads/", "")
            else:
                actual_image_path = Path(image_path)

            base_img = Image.open(str(actual_image_path)).convert("RGBA")
            logo_img = Image.open(str(logo_path)).convert("RGBA")

            # Scale logo
            logo_width = int(base_img.width * scale)
            logo_height = int(logo_img.height * (logo_width / logo_img.width))
            logo_img = logo_img.resize((logo_width, logo_height), Image.LANCZOS)

            # Tính toán vị trí
            padding = 20
            if position == "top-left":
                pos = (padding, padding)
            elif position == "top-right":
                pos = (base_img.width - logo_width - padding, padding)
            elif position == "bottom-left":
                pos = (padding, base_img.height - logo_height - padding)
            else:  # bottom-right
                pos = (base_img.width - logo_width - padding, base_img.height - logo_height - padding)

            # Composite
            base_img.paste(logo_img, pos, logo_img)

            # Lưu file mới (giữ nguyên file gốc)
            output_name = f"ai_gen_logo_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
            output_path = settings.UPLOAD_DIR / output_name
            base_img.convert("RGB").save(str(output_path), 'PNG')

            return f"/uploads/{output_name}"
        except Exception as e:
            print(f"[IMAGE_GEN] Logo overlay error: {e}")
            return image_path


    @staticmethod
    def _infer_template_from_text(text: str) -> str:
        text_l = (text or "").lower()
        if any(k in text_l for k in ["chủ thầu", "xây dựng", "công trình", "báo giá", "mặt dựng", "facade", "tòa nhà"]):
            return "glass_facade_premium"
        if any(k in text_l for k in ["vách tắm", "phòng tắm", "shower", "bathroom"]):
            return "shower_glass"
        if any(k in text_l for k in ["ốp bếp", "bếp", "kitchen"]):
            return "kitchen_backsplash"
        if any(k in text_l for k in ["lan can", "ban công", "railing", "balcony"]):
            return "residential_glass_railing"
        if any(k in text_l for k in ["văn phòng", "vách ngăn", "partition", "office"]):
            return "office_partition_clean"
        if any(k in text_l for k in ["gương", "mirror", "trang trí"]):
            return "technical_product_card"
        return "glass_facade_premium"

    @staticmethod
    def _clean_flux_prompt(raw_prompt: str, post_title: str = "", post_body: str = "", product_desc: str = "", template_key: str = None) -> str:
        """Chuyển prompt quảng cáo/thiết kế thành prompt nền ảnh FLUX: bám nội dung nhưng không sinh chữ/logo."""
        source = " ".join([post_title or "", raw_prompt or "", product_desc or "", (post_body or "")[:700]])
        final_template = template_key or ImageGenService._infer_template_from_text(source)
        base = ImageGenService.GLASS_TEMPLATE_PROMPTS.get(final_template, ImageGenService.GLASS_TEMPLATE_PROMPTS["glass_facade_premium"])

        keywords = []
        rules = [
            (["vách tắm", "phòng tắm", "shower"], "frameless tempered glass shower enclosure in a modern luxury bathroom"),
            (["kính ốp bếp", "ốp bếp", "bếp", "kitchen"], "glossy glass kitchen backsplash in a modern luxury kitchen"),
            (["gương", "mirror", "trang trí"], "decorative mirror wall in a premium modern interior lobby"),
            (["cường lực", "tempered"], "clear tempered safety glass panels with elegant reflections"),
            (["low-e", "low e", "tiết kiệm năng lượng"], "blue tinted low-e energy efficient architectural glass facade"),
            (["lan can", "ban công", "railing"], "clear tempered glass balcony railing in a modern villa"),
            (["vách kính", "vách ngăn", "văn phòng", "office"], "clean glass office partitions in a premium workspace"),
            (["mặt dựng", "facade", "tòa nhà"], "modern commercial building glass facade"),
            (["chủ thầu", "xây dựng", "công trình"], "premium construction project scene focused on installed architectural glass"),
        ]
        source_l = source.lower()
        for keys, phrase in rules:
            if any(k in source_l for k in keys):
                keywords.append(phrase)
        if not keywords:
            keywords.append("premium architectural glass product application scene")

        prompt = (
            f"{base}. Main subject: {', '.join(list(dict.fromkeys(keywords))[:4])}. "
            "Photorealistic high-end architectural advertising background, sharp glass reflections, natural daylight, clean premium composition, realistic materials, no cartoon, no illustration, no CGI look. "
            "Leave clean empty space for Vietnamese headline and product information to be added later by backend. "
            "Strictly no text, no letters, no logo, no watermark, no signage, no brand mark, no distorted typography. "
            "No close-up faces, no handshake scene, no collage, no split-screen layout."
        )
        return prompt

    @staticmethod
    def compose_ad_image(image_path: str, product: dict = None, headline: str = None, subheadline: str = None, cta: str = None, template_key: str = None) -> str:
        """Ghép background AI + logo + text + product card để tránh AI vẽ sai chữ/logo/sản phẩm."""
        product = product or {}
        try:
            actual_image_path = settings.UPLOAD_DIR / image_path.replace("/uploads/", "") if image_path.startswith("/uploads/") else Path(image_path)
            base = Image.open(str(actual_image_path)).convert("RGBA")
            w, h = base.size
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            panel_w = int(w * 0.48)
            for x in range(panel_w):
                alpha = int(178 * (1 - x / max(panel_w, 1))) + 35
                draw.line([(x, 0), (x, h)], fill=(5, 28, 42, min(alpha, 210)))

            margin = int(w * 0.065)
            y = int(h * 0.20)
            headline_font = ImageGenService._font(max(34, int(w * 0.055)), bold=True)
            sub_font = ImageGenService._font(max(22, int(w * 0.030)), bold=False)
            cta_font = ImageGenService._font(max(22, int(w * 0.030)), bold=True)

            for line in ImageGenService._wrap_text(draw, headline or "Giải pháp kính kiến trúc DAFA", headline_font, panel_w - margin * 2):
                draw.text((margin, y), line, font=headline_font, fill=(255, 255, 255, 255))
                y += int(headline_font.size * 1.15)
            y += 14
            for line in ImageGenService._wrap_text(draw, subheadline or "Sang trọng • An toàn • Bền bỉ", sub_font, panel_w - margin * 2):
                draw.text((margin, y), line, font=sub_font, fill=(210, 244, 255, 255))
                y += int(sub_font.size * 1.35)

            y = min(y + 28, int(h * 0.72))
            cta_text = cta or "Inbox để được tư vấn"
            cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
            cta_w = cta_bbox[2] - cta_bbox[0] + 44
            cta_h = cta_bbox[3] - cta_bbox[1] + 28
            draw.rounded_rectangle([margin, y, margin + cta_w, y + cta_h], radius=cta_h // 2, fill=(0, 174, 239, 235))
            draw.text((margin + 22, y + 12), cta_text, font=cta_font, fill=(255, 255, 255, 255))
            base = Image.alpha_composite(base, overlay)

            product_images = product.get("images") or []
            if product_images:
                prod_img = Image.open(str(product_images[0])).convert("RGBA")
                max_pw, max_ph = int(w * 0.34), int(h * 0.34)
                prod_img.thumbnail((max_pw, max_ph), Image.LANCZOS)
                card_pad = 24
                card_w, card_h = prod_img.width + card_pad * 2, prod_img.height + card_pad * 2
                card_x, card_y = w - card_w - margin, h - card_h - margin
                card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 232))
                cd = ImageDraw.Draw(card)
                cd.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=28, fill=(255, 255, 255, 232), outline=(210, 235, 242, 255), width=2)
                card.alpha_composite(prod_img, (card_pad, card_pad))
                base.alpha_composite(card, (card_x, card_y))

            output_name = f"ai_gen_composed_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
            output_path = settings.UPLOAD_DIR / output_name
            base.convert("RGB").save(str(output_path), "PNG")
            return f"/uploads/{output_name}"
        except Exception as e:
            print(f"[IMAGE_GEN] Compose ad image error: {e}")
            return image_path

    @staticmethod
    def generate_for_post(post_id: int, custom_prompt: str = None, product_slug: str = None, template_key: str = None, headline: str = None, subheadline: str = None, cta: str = None, aspect_ratio: str = "1:1") -> dict:
        """Pipeline: đọc post + product -> FLUX/background -> composer logo/text/product -> lưu media."""
        from app.core.database import SessionLocal
        from app import models
        db = SessionLocal()
        try:
            post = db.query(models.Post).filter(models.Post.id == post_id).first()
            if not post:
                raise Exception(f"Không tìm thấy bài viết ID {post_id}")
            plan = db.query(models.ContentPlan).filter(models.ContentPlan.id == post.content_plan_id).first()
            platform = plan.platform if plan else "Web"

            final_product_slug = product_slug or post.product_slug
            product = ImageGenService._load_product(final_product_slug, f"{post.title} {post.body or ''}")
            product_desc = product.get("description", "")
            final_template = template_key or post.template_key or "glass_facade_premium"
            final_headline = headline or post.headline or post.title
            final_subheadline = subheadline or post.subheadline or "Sang trọng • An toàn • Bền bỉ"
            final_cta = cta or post.cta or "Inbox để được tư vấn"

            raw_source_prompt = custom_prompt or post.background_prompt or post.image_prompt or ""
            if custom_prompt:
                # Khi người dùng đã sửa prompt thủ công thì không ép về template mặc định nữa.
                # Chỉ thêm ràng buộc kỹ thuật để AI không vẽ chữ/logo sai.
                image_prompt = (
                    f"{custom_prompt.strip()}\n\n"
                    "Follow the user prompt exactly. Keep the main subject, scene, product, color, material and composition from the prompt. "
                    "Photorealistic professional image, premium Vietnamese glass/construction brand mood, sharp realistic details. "
                    "Strictly no text, no letters, no logo, no watermark, no poster, no collage, no distorted typography."
                )
            else:
                # Không có prompt thủ công thì mới dùng template để suy luận ảnh nền quảng cáo.
                image_prompt = ImageGenService._clean_flux_prompt(
                    raw_prompt=raw_source_prompt,
                    post_title=post.title,
                    post_body=post.body,
                    product_desc=product_desc,
                    template_key=final_template,
                )

            bg_url = ImageGenService.generate_image(image_prompt, size=ImageGenService._aspect_to_size(aspect_ratio or post.aspect_ratio))
            if not bg_url:
                raise Exception("Tạo ảnh nền thất bại")

            composed_url = ImageGenService.compose_ad_image(bg_url, product=product, headline=final_headline, subheadline=final_subheadline, cta=final_cta, template_key=final_template)
            image_url = ImageGenService.overlay_logo(composed_url, position="top-left", scale=0.10)

            current_urls = []
            if post.media_urls and post.media_urls != "[]":
                try:
                    current_urls = json.loads(post.media_urls)
                    if not isinstance(current_urls, list):
                        current_urls = []
                except Exception:
                    current_urls = []
            current_urls.append(image_url)
            post.media_urls = json.dumps(current_urls, ensure_ascii=False)
            if not post.media_url:
                post.media_url = image_url
            post.product_slug = final_product_slug or product.get("slug")
            post.template_key = final_template
            post.headline = final_headline
            post.subheadline = final_subheadline
            post.cta = final_cta
            post.background_prompt = image_prompt
            post.aspect_ratio = aspect_ratio or post.aspect_ratio or "1:1"
            db.commit()
            return {"image_url": image_url, "background_url": bg_url, "prompt_used": image_prompt, "product_slug": post.product_slug, "template_key": final_template}
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
