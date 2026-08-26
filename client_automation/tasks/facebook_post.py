# ============================================================
# Facebook Post Task
# Luồng xử lý: Đăng bài vào Hội nhóm Facebook
# ============================================================

import asyncio
from typing import Dict
from playwright.async_api import BrowserContext, Page
from browser_manager import random_delay
from api_client import APIClient
from config import FB_MBASIC_URL, BACKEND_URL


async def execute_post_task(context: BrowserContext, task: Dict, api: APIClient, dry_run: bool = False) -> Dict:
    """
    Thực thi 1 task Đăng bài vào Hội nhóm Facebook (dùng mbasic.facebook.com).
    
    Luồng:
    1. Mở trang Group (mbasic URL)
    2. Gọi AI sinh nội dung bài viết theo chỉ thị
    3. Điền nội dung vào form đăng bài
    4. Nhấn "Đăng" và báo cáo kết quả
    
    Args:
        context: Playwright BrowserContext (đã inject cookies + proxy)
        task: TaskWithDetails dict từ API
        api: APIClient instance
        dry_run: True = chỉ giả lập, không thực sự đăng bài
    
    Returns:
        {"status": "success"|"failed", "content": str, "error": str}
    """
    page: Page = await context.new_page()
    result = {"status": "failed", "content": "", "error": ""}
    
    try:
        target_url = task["target_url"]
        ai_instructions = task.get("ai_instructions", "Viết bài đăng hội nhóm tự nhiên, hữu ích.")
        
        # --- Bước 1: Chuyển URL sang dạng mbasic ---
        mbasic_url = convert_to_mbasic_group_url(target_url)
        print(f"    📄 Truy cập Group: {mbasic_url}")
        
        await page.goto(mbasic_url, wait_until="domcontentloaded")
        await random_delay(2, 5)
        
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
            
            generated_post = api.generate_content(
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
        
        post_success = await submit_post(page, generated_post, media_urls=media_urls)
        
        if post_success:
            result["status"] = "success"
            print(f"    ✅ Đăng bài thành công!")
        else:
            result["error"] = "Không tìm thấy form đăng bài hoặc không thể gửi"
            
    except Exception as e:
        result["error"] = str(e)
        print(f"    ❌ Lỗi: {e}")
    finally:
        await page.close()
    
    return result


def convert_to_mbasic_group_url(url: str) -> str:
    """Chuyển URL Group Facebook sang dạng mbasic."""
    url = url.strip()
    replacements = [
        ("https://www.facebook.com", FB_MBASIC_URL),
        ("http://www.facebook.com", FB_MBASIC_URL),
        ("https://facebook.com", FB_MBASIC_URL),
        ("http://facebook.com", FB_MBASIC_URL),
        ("https://m.facebook.com", FB_MBASIC_URL),
        ("https://web.facebook.com", FB_MBASIC_URL),
    ]
    for old, new in replacements:
        if url.startswith(old):
            url = url.replace(old, new, 1)
            break
    
    if not url.startswith("http"):
        url = f"{FB_MBASIC_URL}/{url.lstrip('/')}"
    
    return url


async def scrape_group_info(page: Page) -> str:
    """Scrape tên và mô tả Group từ mbasic."""
    selectors = [
        "h1",
        "h3 > a",
        "title",
        "#m-group-header-info strong",
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
    
    # Fallback
    try:
        title = await page.title()
        return title
    except Exception:
        return "Group Facebook"


async def submit_post(page: Page, post_content: str, media_urls: list = None) -> bool:
    """Tìm form đăng bài trong Group trên mbasic hoặc Desktop FB và đăng."""
    
    # ----------------------------------------------------
    # Cách 1: Thử tìm theo cấu trúc mbasic / mobile HTML
    # ----------------------------------------------------
    write_selectors = [
        "textarea[name='xc_message']",
        "textarea[name='message']", 
        "textarea",
        "a[href*='composer']",
        "a[href*='publish']",
    ]
    
    post_input = None
    
    # Thử tìm textarea trực tiếp
    for selector in write_selectors[:3]:
        try:
            el = await page.query_selector(selector)
            if el:
                tag = await el.evaluate("el => el.tagName")
                if tag.lower() == "textarea":
                    post_input = el
                    break
        except Exception:
            continue
    
    # Nếu không tìm thấy textarea, thử click vào link composer (mbasic)
    if not post_input:
        for selector in write_selectors[3:]:
            try:
                link = await page.query_selector(selector)
                if link:
                    await link.click()
                    await random_delay(2, 4)
                    for ts in ["textarea[name='xc_message']", "textarea[name='message']", "textarea"]:
                        el = await page.query_selector(ts)
                        if el:
                            post_input = el
                            break
                    if post_input:
                        break
            except Exception:
                continue
    
    # Nếu tìm thấy textarea mbasic -> xử lý theo luồng mbasic
    if post_input:
        print("    📝 Tìm thấy form đăng bài mbasic HTML")
        await post_input.click()
        await random_delay(1, 2)
        
        # Gõ từng đoạn
        import random
        chunk_size = 12
        for i in range(0, len(post_content), chunk_size):
            chunk = post_content[i:i+chunk_size]
            await post_input.type(chunk, delay=random.uniform(20, 60))
            await asyncio.sleep(random.uniform(0.02, 0.1))
        
        # Upload media nếu có
        if media_urls:
            print(f"    📎 Đang đính kèm {len(media_urls)} file media...")
            media_selectors = [
                "input[type='file'][name='file1']",
                "input[type='file'][accept*='image']",
                "input[type='file'][accept*='video']",
                "input[type='file']",
            ]
            for media_url in media_urls:
                try:
                    import httpx
                    import tempfile
                    import os
                    if media_url.startswith("/"):
                        from config import BACKEND_URL
                        full_url = f"{BACKEND_URL}{media_url}"
                    else:
                        full_url = media_url
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(full_url)
                        if resp.status_code == 200:
                            ext = os.path.splitext(media_url)[1] or ".jpg"
                            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                            tmp_file.write(resp.content)
                            tmp_file.close()
                            for sel in media_selectors:
                                file_input = await page.query_selector(sel)
                                if file_input:
                                    await file_input.set_input_files(tmp_file.name)
                                    await random_delay(2, 4)
                                    print(f"    ✅ Đã đính kèm: {media_url}")
                                    break
                            try:
                                os.unlink(tmp_file.name)
                            except Exception:
                                pass
                except Exception as e:
                    print(f"    ⚠️ Không thể đính kèm media {media_url}: {e}")
        
        await random_delay(2, 4)
        
        submit_selectors = [
            "input[type='submit'][name='view_post']",
            "input[type='submit'][value*='Đăng']",
            "input[type='submit'][value*='Post']",
            "button[type='submit']",
            "input[type='submit']",
        ]
        for selector in submit_selectors:
            try:
                submit_btn = await page.query_selector(selector)
                if submit_btn:
                    await submit_btn.click()
                    await random_delay(4, 7)
                    return True
            except Exception:
                continue
        return False

    # ----------------------------------------------------
    # Cách 2: Thử theo giao diện Desktop Facebook (React SPA)
    # ----------------------------------------------------
    print("    🖥️ Không thấy form mbasic, thử theo giao diện Desktop Facebook...")
    desktop_open_selectors = [
        "div[role='button'] span:has-text('Bạn viết gì đi')",
        "div[role='button'] span:has-text('Viết gì đó')",
        "div[role='button'] span:has-text('Write something')",
        "div[role='button'] span:has-text('Tạo bài viết')",
        "div[role='button'] span:has-text('Create a post')",
        "div[role='main'] div[role='button'][tabindex='0']",
    ]
    
    opened_dialog = False
    for sel in desktop_open_selectors:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await random_delay(2, 4)
                opened_dialog = True
                break
        except Exception:
            continue
            
    # Tìm vùng nhập trong Dialog hoặc trang Desktop
    search_root = page
    dialogs = await page.query_selector_all("div[role='dialog']")
    if dialogs:
        for dialog in reversed(dialogs):
            box = await dialog.bounding_box()
            if box and box['width'] > 200 and box['height'] > 200:
                search_root = dialog
                break
                
    desktop_input_selectors = [
        "div[role='textbox'][contenteditable='true']",
        "div[contenteditable='true'][aria-label*='Bạn đang nghĩ gì']",
        "div[contenteditable='true'][aria-label*='Write something']",
        "div[contenteditable='true'][aria-label*='Tạo bài viết']",
    ]
    
    desktop_input = None
    for sel in desktop_input_selectors:
        try:
            el = await search_root.query_selector(sel)
            if el:
                desktop_input = el
                break
        except Exception:
            continue
            
    if not desktop_input:
        return False
        
    print("    📝 Đã tìm thấy ô soạn thảo Desktop")
    await desktop_input.click()
    await random_delay(1, 2)
    
    # Gõ nội dung bằng paste clipboard event hoặc insert_text
    try:
        await page.evaluate('''([el, text]) => {
            const dataTransfer = new DataTransfer();
            dataTransfer.setData('text/plain', text);
            el.focus();
            el.dispatchEvent(new ClipboardEvent('paste', {
                clipboardData: dataTransfer,
                bubbles: true,
                cancelable: true
            }));
        }''', [desktop_input, post_content])
    except Exception:
        try:
            await page.keyboard.insert_text(post_content)
        except Exception:
            await desktop_input.type(post_content, delay=30)
            
    await random_delay(2, 4)
    
    # Xử lý upload media desktop
    if media_urls:
        print(f"    📎 Đang đính kèm file media trên desktop...")
        for media_url in media_urls:
            try:
                import httpx, tempfile, os
                full_url = f"{BACKEND_URL}{media_url}" if media_url.startswith("/") else media_url
                async with httpx.AsyncClient() as client:
                    resp = await client.get(full_url)
                    if resp.status_code == 200:
                        ext = os.path.splitext(media_url)[1] or ".jpg"
                        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                        tmp_file.write(resp.content)
                        tmp_file.close()
                        file_inputs = await search_root.query_selector_all("input[type='file']")
                        if not file_inputs:
                            file_inputs = await page.query_selector_all("input[type='file']")
                        for fi in file_inputs:
                            await fi.set_input_files(tmp_file.name)
                            await random_delay(2, 4)
                            break
                        try:
                            os.unlink(tmp_file.name)
                        except Exception:
                            pass
            except Exception as e:
                print(f"    ⚠️ Lỗi đính kèm media: {e}")
                
    await random_delay(2, 4)
    
    # Click nút Đăng / Post desktop
    desktop_submit_selectors = [
        "div[aria-label='Đăng']",
        "div[aria-label='Post']",
        "div[role='button']:has-text('Đăng')",
        "div[role='button']:has-text('Post')",
    ]
    for sel in desktop_submit_selectors:
        try:
            btn = await search_root.query_selector(sel)
            if btn:
                await btn.click()
                await random_delay(4, 7)
                return True
        except Exception:
            continue
            
    return False
