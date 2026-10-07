# ============================================================
# Facebook Post Task
# Luồng xử lý: Đăng bài vào Hội nhóm Facebook (Desktop & mbasic fallback)
# ============================================================

import asyncio
import os
import random
from typing import Dict
from playwright.async_api import BrowserContext, Page
from browser_manager import random_delay
from api_client import APIClient


def normalize_group_url(url: str) -> str:
    """Chuẩn hoá URL Group Facebook sang URL desktop chuẩn."""
    url = url.strip()
    replacements = [
        ("https://mbasic.facebook.com", "https://www.facebook.com"),
        ("http://mbasic.facebook.com", "https://www.facebook.com"),
        ("https://m.facebook.com", "https://www.facebook.com"),
        ("http://m.facebook.com", "https://www.facebook.com"),
        ("https://facebook.com", "https://www.facebook.com"),
        ("http://facebook.com", "https://www.facebook.com"),
    ]
    for old, new in replacements:
        if url.startswith(old):
            url = url.replace(old, new, 1)
            break
            
    if not url.startswith("http"):
        url = f"https://www.facebook.com/{url.lstrip('/')}"
        
    return url


async def scrape_group_info(page: Page) -> str:
    """Scrape tên và mô tả Group từ trang Facebook."""
    selectors = [
        "h1",
        "h2",
        "title",
    ]
    for selector in selectors:
        try:
            el = await page.query_selector(selector)
            if el:
                text = await el.inner_text()
                if text and len(text.strip()) > 3:
                    return text.strip()
        except Exception:
            continue
    try:
        return await page.title()
    except Exception:
        return "Group Facebook"


async def execute_post_task(context: BrowserContext, task: Dict, api: APIClient, dry_run: bool = False) -> Dict:
    """
    Thực thi 1 task Đăng bài vào Hội nhóm Facebook.
    
    Luồng:
    1. Mở trang Group Facebook
    2. Gọi AI sinh nội dung bài viết theo chỉ thị (nếu chưa có)
    3. Điền nội dung vào form/dialog đăng bài
    4. Đính kèm media (nếu có)
    5. Nhấn "Đăng" và báo cáo kết quả
    """
    page: Page = await context.new_page()
    result = {"status": "failed", "content": "", "error": ""}
    
    try:
        raw_url = task["target_url"]
        ai_instructions = task.get("ai_instructions", "Viết bài đăng hội nhóm tự nhiên, hữu ích.")
        
        # --- Bước 1: Truy cập trang nhóm ---
        group_url = normalize_group_url(raw_url)
        print(f"    📄 Truy cập Group: {group_url}")
        
        await page.goto(group_url, wait_until="domcontentloaded")
        await random_delay(3, 5)
        
        # --- Bước 2: Kiểm tra đăng nhập ---
        if "login" in page.url.lower() or "checkpoint" in page.url.lower():
            result["error"] = "Cookie hết hạn hoặc tài khoản bị checkpoint"
            return result
        
        # --- Bước 3: Scrape thông tin Group ---
        group_info = await scrape_group_info(page)
        print(f"    📝 Group: {group_info[:60]}...")
        
        # --- Bước 4: Dùng nội dung soạn sẵn hoặc gọi AI sinh ---
        generated_post = task.get("post_content") or task.get("generated_content")
        if not generated_post:
            print(f"    🤖 Đang gọi AI sinh nội dung bài viết...")
            post_prompt = f"Tên Group/Chủ đề: {group_info}\n\nYêu cầu: {ai_instructions}"
            
            generated_post = await api.generate_content(
                post_content=post_prompt,
                instruction=ai_instructions,
                platform=task.get("platform", "facebook"),
                task_type="POST_GROUP"
            )
        
        if not generated_post:
            result["error"] = "AI không trả về nội dung bài viết"
            return result
        
        print(f"    📝 Bài viết AI: {generated_post[:80]}...")
        result["content"] = generated_post
        
        # --- Bước 5: Dry Run check ---
        if dry_run:
            print(f"    🔵 [DRY RUN] Bỏ qua bước đăng bài thực tế.")
            result["status"] = "success"
            return result
        
        # --- Bước 6: Tìm form đăng bài và điền nội dung ---
        media_urls = []
        if task.get("media_urls"):
            import json as json_mod
            try:
                media_urls = json_mod.loads(task["media_urls"]) if isinstance(task["media_urls"], str) else task["media_urls"]
            except Exception:
                media_urls = []
        
        post_res = await submit_post(page, generated_post, media_urls=media_urls, backend_url=api.backend_url)
        
        if isinstance(post_res, dict) and post_res.get("status") == "success":
            result["status"] = "success"
            note = post_res.get("note", "")
            if note:
                result["content"] = f"[{note}] {generated_post}"
            print(f"    ✅ Đăng bài thành công! ({note})")
        elif post_res is True:
            result["status"] = "success"
            print(f"    ✅ Đăng bài thành công!")
        else:
            err_msg = post_res.get("note") if isinstance(post_res, dict) else "Không tìm thấy form đăng bài hoặc không thể gửi"
            result["error"] = err_msg
            print(f"    ❌ Đăng bài không thành công: {err_msg}")
            
    except Exception as e:
        result["error"] = str(e)
        print(f"    ❌ Lỗi: {e}")
    finally:
        try:
            await page.close()
        except Exception:
            pass
    
    return result


async def submit_post(page: Page, post_content: str, media_urls: list = None, backend_url: str = None) -> bool:
    """
    Tìm form đăng bài trong Group trên Facebook Desktop và đăng bài.
    Hỗ trợ đính kèm hình ảnh/video.
    """
    # --- Bước 1: Mở hộp thoại soạn bài viết ---
    triggers = [
        "span:has-text('Bạn viết gì đi')",
        "div[role='button']:has-text('Bạn viết gì đi')",
        "span:has-text('Write something')",
        "div[role='button']:has-text('Write something')",
        "div[role='button']:has-text('Tạo bài viết')",
        "div[role='button']:has-text('Create a post')",
        "div[role='button'][aria-label*='Tạo bài viết']",
        "div[role='button'][aria-label*='Create a post']",
    ]
    
    dialog = None
    for sel in triggers:
        try:
            el = await page.query_selector(sel)
            if el:
                box = await el.bounding_box()
                if box and box['width'] > 0 and box['height'] > 0:
                    await el.click()
                    await random_delay(2, 4)
                    break
        except Exception:
            continue
            
    # Tìm hộp thoại dialog xuất hiện
    dialogs = await page.query_selector_all("div[role='dialog']")
    for d in reversed(dialogs):
        try:
            box = await d.bounding_box()
            if box and box['width'] > 300 and box['height'] > 200:
                dialog = d
                break
        except Exception:
            continue
            
    # Fallback nếu không mở được dialog (giao diện mbasic)
    if not dialog:
        for ts in ["textarea[name='xc_message']", "textarea[name='message']", "textarea"]:
            try:
                inp = await page.query_selector(ts)
                if inp:
                    await inp.fill(post_content)
                    btn = await page.query_selector("input[type='submit'][name='view_post'], input[type='submit'][value*='Đăng'], input[type='submit']")
                    if btn:
                        await btn.click()
                        await random_delay(3, 5)
                        return True
            except Exception:
                pass
        print("    ❌ Không tìm thấy nút mở soạn bài viết trên trang nhóm")
        return False

    # --- Bước 2: Nhập nội dung bài viết vào ô textbox ---
    tb = await dialog.query_selector("div[role='textbox'][contenteditable='true']")
    if not tb:
        tb = await dialog.query_selector("div[role='textbox']")
        
    if not tb:
        print("    ❌ Không tìm thấy ô nhập nội dung trong hộp thoại")
        return False
        
    await tb.click()
    await random_delay(1, 2)
    
    try:
        await page.keyboard.insert_text(post_content)
    except Exception:
        try:
            await page.evaluate('''([el, text]) => {
                const dt = new DataTransfer();
                dt.setData('text/plain', text);
                el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
            }''', [tb, post_content])
        except Exception:
            await tb.type(post_content, delay=30)
            
    await random_delay(2, 3)

    # --- Bước 3: Đính kèm Media (nếu có) ---
    if media_urls:
        print(f"    📎 Đang đính kèm {len(media_urls)} file media...")
        import httpx
        import tempfile
        
        for media_url in media_urls:
            tmp_file_path = None
            try:
                if media_url.startswith("/"):
                    full_url = f"{backend_url or 'http://127.0.0.1:8000'}{media_url}"
                else:
                    full_url = media_url
                    
                async with httpx.AsyncClient() as dl_client:
                    resp = await dl_client.get(full_url, timeout=30.0)
                    if resp.status_code == 200:
                        ext = os.path.splitext(media_url)[1] or ".png"
                        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                        tmp_file.write(resp.content)
                        tmp_file.close()
                        tmp_file_path = tmp_file.name
                    else:
                        print(f"    ⚠️ Không tải được media {media_url}: HTTP {resp.status_code}")
                        continue
                        
                if not tmp_file_path:
                    continue
                    
                # Tìm input[type='file'] trong dialog
                file_input = await dialog.query_selector("input[type='file']")
                if not file_input:
                    # Click nút Ảnh/video để kích hoạt input file
                    photo_btn = await dialog.query_selector("div[aria-label*='Ảnh'], div[aria-label*='Photo'], div[aria-label*='video']")
                    if photo_btn:
                        await photo_btn.click()
                        await random_delay(1, 2)
                        file_input = await dialog.query_selector("input[type='file']")
                        
                if file_input:
                    await file_input.set_input_files(tmp_file_path)
                    await random_delay(3, 5)
                    print(f"    ✅ Đã đính kèm ảnh: {media_url}")
                else:
                    print(f"    ⚠️ Không tìm thấy input upload ảnh")
            except Exception as e:
                print(f"    ⚠️ Lỗi khi đính kèm media {media_url}: {e}")
            finally:
                if tmp_file_path:
                    try:
                        os.unlink(tmp_file_path)
                    except Exception:
                        pass

    # --- Bước 4: Nhấn nút Đăng ---
    post_btn_selectors = [
        "div[aria-label='Đăng']",
        "div[aria-label='Post']",
        "div[role='button']:has-text('Đăng')",
        "div[role='button']:has-text('Post')",
    ]
    
    submit_btn = None
    for p_sel in post_btn_selectors:
        btns = await dialog.query_selector_all(p_sel)
        for b in btns:
            try:
                box = await b.bounding_box()
                if box and box['width'] > 0 and box['height'] > 0:
                    is_disabled = await b.get_attribute('aria-disabled')
                    if is_disabled != 'true':
                        submit_btn = b
                        break
            except Exception:
                continue
        if submit_btn:
            break
            
    if not submit_btn:
        print("    ❌ Không tìm thấy nút Đăng bài (hoặc nút đang bị khoá)")
        return False
        
    await submit_btn.click()
    print("    🚀 Đã nhấn nút Đăng bài, đang chờ phản hồi từ Facebook...")
    await random_delay(5, 7)
    
    # Kiểm tra phản hồi từ Facebook (chờ duyệt hoặc lỗi)
    page_text = ""
    try:
        page_text = await page.evaluate("() => document.body.innerText || ''")
    except Exception:
        pass
        
    page_text_lower = page_text.lower()
    pending_keywords = [
        "chờ phê duyệt", "chờ duyệt", "quản trị viên", "gửi đến quản trị viên",
        "pending approval", "submitted for approval", "admin approval", "đã gửi bài viết"
    ]
    is_pending = any(k in page_text_lower for k in pending_keywords)
    if is_pending:
        print("    ℹ️ Bài viết đã gửi thành công và ĐANG CHỜ QUẢN TRỊ VIÊN DUYỆT.")
        return {"status": "success", "note": "Đang chờ Quản trị viên duyệt"}

    error_keywords = [
        "tạm thời bị chặn", "bị hạn chế", "không thể chia sẻ", "spam",
        "something went wrong", "temporarily blocked"
    ]
    for ek in error_keywords:
        if ek in page_text_lower:
            print(f"    ⚠️ Facebook cảnh báo: {ek}")
            return {"status": "failed", "note": f"Facebook từ chối: {ek}"}
            
    return {"status": "success", "note": "Đã gửi thành công"}
