# ============================================================
# Facebook Comment Task
# Luồng xử lý: Comment dạo trên bài viết Facebook
# ============================================================

import asyncio
from typing import Dict
from playwright.async_api import BrowserContext, Page
from browser_manager import random_delay
from api_client import APIClient
from config import FB_MBASIC_URL


async def execute_comment_task(context: BrowserContext, task: Dict, api: APIClient, dry_run: bool = False) -> Dict:
    """
    Thực thi 1 task Comment trên Facebook (dùng mbasic.facebook.com).
    
    Luồng:
    1. Mở trang bài viết (mbasic URL)
    2. Scrape nội dung bài viết
    3. Gọi AI sinh comment phù hợp
    4. Điền comment vào ô nhập liệu và nhấn gửi
    5. Trả về kết quả
    
    Args:
        context: Playwright BrowserContext (đã inject cookies + proxy)
        task: TaskWithDetails dict từ API
        api: APIClient instance
        dry_run: True = chỉ giả lập, không thực sự đăng comment
    
    Returns:
        {"status": "success"|"failed", "content": str, "error": str}
    """
    page: Page = await context.new_page()
    result = {"status": "failed", "content": "", "error": ""}
    
    try:
        target_url = task["target_url"]
        ai_instructions = task.get("ai_instructions", "Hãy comment tự nhiên, thân thiện.")
        
        # --- Bước 1: Truy cập bài viết ---
        mbasic_url = convert_to_mbasic_url(target_url)
        print(f"    📄 Truy cập: {mbasic_url}")
        
        await page.goto(mbasic_url, wait_until="domcontentloaded")
        await random_delay(3, 6)
        
        # --- Bước 2: Kiểm tra đăng nhập thành công ---
        page_content = await page.content()
        if "login" in page.url.lower() or "checkpoint" in page.url.lower():
            result["error"] = "Cookie hết hạn hoặc tài khoản bị checkpoint"
            return result
        
        # --- Bước 2.5: Xác định search_root (dialog nếu có) ---
        # Facebook Desktop mở bài viết trong dialog popup. Mọi thao tác
        # (scrape, tìm ô comment, submit) phải giới hạn trong dialog để
        # tránh tương tác nhầm với bài viết nền phía sau.
        search_root = page
        dialogs = await page.query_selector_all("div[role='dialog']")
        if dialogs:
            for dialog in reversed(dialogs):
                box = await dialog.bounding_box()
                if box and box['width'] > 200 and box['height'] > 200:
                    search_root = dialog
                    break
        
        # --- Bước 3: Scrape nội dung bài viết (trong search_root) ---
        post_content = await scrape_post_content(search_root)
        if not post_content:
            post_content = "(Không đọc được nội dung bài viết)"
        
        print(f"    📝 Nội dung bài viết: {post_content[:80]}...")
        
        # --- Bước 4: Gọi AI sinh comment ---
        print(f"    🤖 Đang gọi AI sinh comment...")
        generated_comment = api.generate_content(
            post_content=post_content,
            instruction=ai_instructions,
            platform=task.get("platform", "facebook"),
            task_type="COMMENT"
        )
        
        if not generated_comment:
            result["error"] = "AI không trả về nội dung comment"
            return result
        
        print(f"    💬 Comment AI: {generated_comment[:60]}...")
        result["content"] = generated_comment
        
        # --- Bước 5: Dry Run check ---
        if dry_run:
            print(f"    🔵 [DRY RUN] Bỏ qua bước đăng comment thực tế.")
            result["status"] = "success"
            return result
        
        # --- Bước 6: Tìm ô comment và điền nội dung ---
        comment_success = await submit_comment(page, target_url, generated_comment)
        
        if comment_success:
            result["status"] = "success"
            print(f"    ✅ Comment thành công!")
        else:
            result["error"] = "Không tìm thấy ô comment hoặc không thể gửi"
            
    except Exception as e:
        result["error"] = str(e)
        print(f"    ❌ Lỗi: {e}")
    finally:
        await page.close()
    
    return result


def convert_to_mbasic_url(url: str) -> str:
    """Chuyển URL Facebook thường sang dạng mbasic."""
    url = url.strip()
    
    # mbasic không hỗ trợ tốt reels/watch, giữ nguyên URL
    if "/reel/" in url.lower() or "/watch/" in url.lower() or "/videos/" in url.lower():
        return url
        
    # Xử lý các dạng URL Facebook phổ biến
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
    
    # Nếu URL không bắt đầu bằng http, thêm mbasic prefix
    if not url.startswith("http"):
        url = f"{FB_MBASIC_URL}/{url.lstrip('/')}"
    
    return url


async def scrape_post_content(root) -> str:
    """Scrape nội dung bài viết từ root element (Page hoặc Dialog element)."""
    selectors = [
        # Modern Facebook / Desktop React selectors (ưu tiên)
        "div[data-ad-preview='message']",
        "div[dir='auto']",
        "span[dir='auto']",
        # mbasic post content selectors
        "div[data-ft] > div > div > span",
        "div.story_body_container div",
        "div[data-ft] p",
        "#m_story_permalink_view div.story_body_container",
    ]
    
    for selector in selectors:
        try:
            elements = await root.query_selector_all(selector)
            if elements:
                texts = []
                for el in elements[:5]:  # Lấy tối đa 5 phần tử đầu
                    text = await el.inner_text()
                    text = text.strip()
                    if text and len(text) > 10:
                        texts.append(text)
                if texts:
                    return "\n".join(texts)
        except Exception:
            continue
    
    # Fallback: lấy toàn bộ text trong root, cắt ngắn
    try:
        text = await root.inner_text()
        lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 15]
        return "\n".join(lines[:10])
    except Exception:
        return ""


async def submit_comment(page: Page, target_url: str, comment_text: str) -> bool:
    """Thực hiện bình luận vào bài viết.
    
    Khi truy cập link bài viết trên Facebook Desktop, bài viết được mở
    trong một dialog popup. Mọi thao tác (tìm nút mở comment, tìm ô nhập,
    nhấn gửi) phải được giới hạn trong dialog đó để tránh click nhầm vào
    bài viết nền phía sau, khiến dialog bị đóng.
    """
    
    # Xác định search_root: ưu tiên dialog chứa bài viết
    search_root = page
    dialogs = await page.query_selector_all("div[role='dialog']")
    if dialogs:
        # Duyệt từ dialog cuối cùng (mới nhất, nổi trên cùng)
        for dialog in reversed(dialogs):
            # Kiểm tra dialog này có hiển thị và có nội dung đáng kể không
            box = await dialog.bounding_box()
            if box and box['width'] > 200 and box['height'] > 200:
                search_root = dialog
                break
    
    # --- Bước 1: Tìm và click nút mở bình luận (trong search_root) ---
    # Desktop Facebook luôn hiện sẵn ô comment ở dưới cùng, không cần click nút mở.
    # Click nút mở có thể vô tình click vào thẻ <a> dẫn đến đóng dialog hoặc tải lại trang.
    # open_comment_btn_selectors = [ ... ]
    # for btn_sel in open_comment_btn_selectors: ...

    # --- Bước 2: Tìm ô nhập bình luận (trong search_root) ---
    comment_selectors = [
        # Desktop generic (robust nhất)
        "div[role='textbox'][contenteditable='true']",
        # mbasic
        "textarea[name='comment_text']",
        # Desktop React fallback
        "div[contenteditable='true'][aria-label*='comment' i]",
        "div[contenteditable='true'][aria-label*='Comment' i]",
        "div[contenteditable='true'][aria-label*='bình luận' i]",
        "div[contenteditable='true'][aria-label*='Bình luận' i]",
        "div[contenteditable='true'][aria-label*='Viết' i]",
    ]
    
    comment_input = None
    for selector in comment_selectors:
        try:
            inputs = await search_root.query_selector_all(selector)
            for inp in inputs:
                box = await inp.bounding_box()
                if box and box['width'] > 0 and box['height'] > 0:
                    comment_input = inp
                    break
            if comment_input:
                break
        except Exception:
            continue
            
    if not comment_input:
        return False
        
    # --- Bước 3: Focus và nhập nội dung ---
    try:
        await comment_input.scroll_into_view_if_needed()
        await comment_input.click(position={"x": 10, "y": 10})
        await random_delay(1, 2)
    except Exception:
        pass
        
    # Gõ nội dung (ClipboardEvent bypass React Draft.js, fallback keyboard)
    try:
        await page.evaluate('''([el, text]) => {
            const dataTransfer = new DataTransfer();
            dataTransfer.setData('text/plain', text);
            const event = new ClipboardEvent('paste', {
                clipboardData: dataTransfer,
                bubbles: true,
                cancelable: true
            });
            el.dispatchEvent(event);
        }''', [comment_input, comment_text])
    except Exception:
        try:
            await page.keyboard.insert_text(comment_text)
        except Exception:
            await comment_input.fill(comment_text)
            
    await random_delay(2, 4)
    
    # --- Bước 4: Tìm và nhấn nút Submit (trong search_root) ---
    submit_selectors = [
        # mbasic
        "form button[type='submit']",
        # Desktop
        "div[aria-label='Gửi' i]",
        "div[aria-label='Send' i]",
        "div[aria-label='Gửi bình luận' i]",
        "div[role='button'][aria-label*='comment' i]",
    ]
    
    for selector in submit_selectors:
        try:
            submit_btns = await search_root.query_selector_all(selector)
            for submit_btn in submit_btns:
                box = await submit_btn.bounding_box()
                if box and box['width'] > 0 and box['height'] > 0:
                    await submit_btn.click()
                    await random_delay(4, 6)
                    return True
        except Exception:
            continue
            
    # Fallback: Ấn Enter
    try:
        await page.keyboard.press("Enter")
        await random_delay(4, 6)
        return True
    except Exception as e:
        return False


def random_between(a: float, b: float) -> float:
    """Trả về số ngẫu nhiên giữa a và b."""
    import random
    return random.uniform(a, b)
