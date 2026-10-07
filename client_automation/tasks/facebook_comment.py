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


async def like_post_before_comment(page, search_root):
    """Thả Like bài viết trước khi comment. Hỗ trợ Desktop + mbasic."""
    try:
        # Kiểm tra đã Like chưa
        # Desktop: check aria-label 'Bỏ thích' or 'Unlike'
        already_liked = await page.query_selector("div[role='button'][aria-label*='Bỏ thích' i], div[role='button'][aria-label*='Unlike' i]")
        if not already_liked:
            # mbasic: check link 'Bỏ thích' or 'Unlike'
            already_liked = await page.query_selector("a[href*='/a/like.php']:has-text('Bỏ thích'), a[href*='/nfx/basic/direct_actions/']:has-text('Bỏ thích')")
        
        if already_liked:
            print("    ❤️ Bài viết đã được Like trước đó, bỏ qua.")
            return True
        
        # --- Thử Like trên Desktop ---
        like_button = None
        # Tìm trong search_root trước (dialog nếu có)
        if hasattr(search_root, 'query_selector'):
            like_button = await search_root.query_selector("div[role='button'][aria-label*='Thích' i]:not([aria-label*='Bỏ thích' i])")
            if not like_button:
                like_button = await search_root.query_selector("div[role='button'][aria-label*='Like' i]:not([aria-label*='Unlike' i])")
        
        if like_button:
            box = await like_button.bounding_box()
            if box:
                await like_button.scroll_into_view_if_needed()
                await random_delay(1, 2)
                await like_button.click()
                print("    ❤️ Đã Like bài viết (Desktop mode)!")
                return True
        
        # --- Thử Like trên mbasic ---
        like_link = await page.query_selector("a[href*='/a/like.php']")
        if not like_link:
            # Fallback: tìm link có text 'Thích' trên mbasic
            like_link = await page.query_selector("a[href*='/nfx/basic/direct_actions/']:has-text('Thích')")
        
        if like_link:
            await random_delay(1, 2)
            await like_link.click()
            await page.wait_for_load_state("domcontentloaded")
            print("    ❤️ Đã Like bài viết (mbasic mode)!")
            return True
        
        print("    ⚠️ Không tìm thấy nút Like, bỏ qua.")
        return False
        
    except Exception as e:
        print(f"    ⚠️ Lỗi khi Like bài viết (không ảnh hưởng comment): {e}")
        return False


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
        
        # --- Bước 4: Gọi AI sinh comment (retry tối đa 3 lần) ---
        print(f"    🤖 Đang gọi AI sinh comment...")
        generated_comment = ""
        for attempt in range(3):
            generated_comment = await api.generate_content(
                post_content=post_content,
                instruction=ai_instructions,
                platform=task.get("platform", "facebook"),
                task_type="COMMENT"
            )
            if generated_comment:
                break
            print(f"    ⚠️ AI lần {attempt+1} không trả kết quả, thử lại...")
            await asyncio.sleep(3 + attempt * 2)
        
        if not generated_comment:
            # Fallback: chọn ngẫu nhiên từ danh sách bình luận đa dạng theo ngành kính DAFA Glass
            fallback_pool = [
                "Kính dán an toàn bên mình có những độ dày nào vậy shop? Cho mình xin thêm thông tin với ạ.",
                "Bài viết chia sẻ rất hữu ích, mình đang tìm hiểu kính cho công trình nhà ở.",
                "Sản phẩm kính DAFA trông chất lượng và hoàn thiện chuẩn quá, bên mình có nhận công trình ở khu vực phía Bắc không ạ?",
                "Kính dán an toàn và kính cường lực loại nào phù hợp làm vách kính hơn shop tư vấn giúp mình nhé!",
                "Kính nhìn sang và đẹp quá, cho mình xin thông tin liên hệ và báo giá tham khảo với ạ.",
                "Chất lượng hoàn thiện rất tốt, lưu lại để khi nào hoàn thiện nhà liên hệ bên mình tư vấn.",
                "Kính hộp cách âm cách nhiệt này độ bền ra sao vậy shop, dùng cho nhà hướng nắng nhiều có ổn không?",
            ]
            import random as rand_mod
            seed_val = int(task.get("id") or 0) * 17 + int(task.get("account_id") or 0) * 31
            rand_gen = rand_mod.Random(seed_val)
            generated_comment = rand_gen.choice(fallback_pool)
            print(f"    ⚠️ AI không trả về nội dung, dùng fallback đa dạng: {generated_comment[:50]}...")
        
        print(f"    💬 Comment AI: {generated_comment[:60]}...")
        result["content"] = generated_comment
        
        # --- Bước 5: Dry Run check ---
        if dry_run:
            print(f"    🔵 [DRY RUN] Bỏ qua bước đăng comment thực tế.")
            result["status"] = "success"
            return result
        
        # --- Bước 5.5: Thả Like bài viết trước khi comment ---
        print("    ❤️ Đang thả Like bài viết trước khi comment...")
        await like_post_before_comment(page, search_root)
        await random_delay(2, 4)
        
        # --- Bước 6: Tìm ô comment và điền nội dung ---
        comment_success = await submit_comment(page, target_url, generated_comment)
        
        if comment_success:
            result["status"] = "success"
            print(f"    ✅ Comment thành công!")
        else:
            current_url = page.url.lower()
            if "checkpoint" in current_url:
                result["error"] = "Tài khoản bị Facebook checkpoint (cần xác minh danh tính)"
                print(f"    ⚠️ Tài khoản bị checkpoint: {page.url}")
            elif "login" in current_url:
                result["error"] = "Phiên đăng nhập hết hạn (cookie không còn hiệu lực)"
                print(f"    ⚠️ Phiên đăng nhập hết hạn: {page.url}")
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
    # Thử click "Xem thêm" / "See more" để lấy đầy đủ nội dung bài viết / Reel
    try:
        see_more_selectors = [
            "div[role='button']:has-text('Xem thêm')",
            "div[role='button']:has-text('See more')",
            "span:has-text('Xem thêm')",
            "span:has-text('See more')",
            "a:has-text('Xem thêm')",
        ]
        for sel in see_more_selectors:
            btn = await root.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(0.5)
                break
    except Exception:
        pass

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
    
    # --- Bước 1: Tìm và click nút mở bình luận (nếu là bài Reel / Video) ---
    is_reel = "/reel/" in target_url.lower() or "/watch/" in target_url.lower()
    if is_reel:
        print("    🎬 Phát hiện bài viết dạng Facebook Reel / Video. Đang tìm nút mở bình luận...")
        reel_comment_selectors = [
            "div[role='button'][aria-label='Bình luận']",
            "div[role='button'][aria-label='Comment']",
            "div[role='button'][aria-label*='Bình luận' i]",
            "div[role='button'][aria-label*='Comment' i]",
            "div[aria-label='Bình luận'][role='button']",
            "div[aria-label='Comment'][role='button']",
        ]
        for sel in reel_comment_selectors:
            try:
                btns = await page.query_selector_all(sel)
                clicked = False
                for b in btns:
                    box = await b.bounding_box()
                    if box and box['width'] > 0 and box['height'] > 0:
                        await b.click()
                        print("    🔘 Đã click nút mở bình luận Reel, chờ panel xuất hiện...")
                        await random_delay(2, 4)
                        clicked = True
                        break
                if clicked:
                    break
            except Exception:
                continue

    # --- Bước 2: Tìm ô nhập bình luận (trong search_root) ---
    comment_input = None
    
    # Nếu là bài Reel, đợi skeleton loading hoàn tất để ô textbox xuất hiện
    if is_reel:
        try:
            print("    ⏳ Đang đợi khung bình luận Reel tải xong (skeleton load)...")
            inp = await page.wait_for_selector(
                "div[role='textbox'][contenteditable='true'], div[contenteditable='true'][aria-label*='bình luận' i], div[contenteditable='true'][aria-label*='comment' i]",
                timeout=12000
            )
            if inp:
                box = await inp.bounding_box()
                if box and box['width'] > 0 and box['height'] > 0:
                    comment_input = inp
        except Exception:
            pass

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
    
    if not comment_input:
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
            
    # Nếu chưa tìm thấy và search_root != page, tìm tiếp trên phạm vi page
    if not comment_input and search_root != page:
        for selector in comment_selectors:
            try:
                inputs = await page.query_selector_all(selector)
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


async def execute_reply_task(context: BrowserContext, task: Dict, api: APIClient, dry_run: bool = False) -> Dict:
    """
    Thực thi 1 task Reply Comment trên Facebook.
    
    Luồng:
    1. Mở bài viết gốc
    2. Tìm comment cha (dựa vào parent_comment_content)
    3. Click nút Reply/Trả lời dưới comment đó
    4. Điền nội dung reply (đã được AI sinh sẵn hoặc sinh realtime)
    5. Gửi reply
    """
    page: Page = await context.new_page()
    result = {"status": "failed", "content": "", "error": ""}
    
    try:
        target_url = task["target_url"]
        parent_comment = task.get("parent_comment_content", "")
        generated_content = task.get("generated_content", "")
        ai_instructions = task.get("ai_instructions", "Hãy reply tự nhiên, thân thiện.")
        
        # --- Bước 1: Truy cập bài viết ---
        print(f"    📄 [REPLY] Truy cập: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded")
        await random_delay(3, 6)
        
        # Kiểm tra login
        if "login" in page.url.lower() or "checkpoint" in page.url.lower():
            result["error"] = "Cookie hết hạn hoặc tài khoản bị checkpoint"
            return result
        
        # --- Bước 2: Tìm comment cha ---
        print(f"    🔍 Tìm comment cha: {parent_comment[:50]}...")
        
        # Xác định search_root (dialog nếu có)
        search_root = page
        dialogs = await page.query_selector_all("div[role='dialog']")
        if dialogs:
            for dialog in reversed(dialogs):
                box = await dialog.bounding_box()
                if box and box['width'] > 200 and box['height'] > 200:
                    search_root = dialog
                    break
        
        parent_comment_el = await find_comment_element(search_root, parent_comment)
        
        if not parent_comment_el:
            # Fallback: nếu không tìm thấy comment cha, comment bình thường
            print(f"    ⚠️ Không tìm thấy comment cha, chuyển sang comment thường")
            reply_content = generated_content
            if not reply_content:
                reply_content = await api.generate_content(
                    post_content=parent_comment or target_url,
                    instruction=ai_instructions,
                    platform=task.get("platform", "facebook"),
                    task_type="COMMENT"
                )
            result["content"] = reply_content
            
            if dry_run:
                result["status"] = "success"
                return result
            
            comment_success = await submit_comment(page, target_url, reply_content)
            if comment_success:
                result["status"] = "success"
            else:
                result["error"] = "Không thể gửi comment fallback"
            return result
        
        # --- Bước 3: Click nút Reply ---
        print(f"    💬 Tìm thấy comment cha, đang click Reply...")
        reply_clicked = await click_reply_button(parent_comment_el, page)
        
        if not reply_clicked:
            result["error"] = "Không tìm thấy nút Reply dưới comment"
            return result
        
        await random_delay(1, 3)
        
        # --- Bước 4: Sinh hoặc sử dụng nội dung reply ---
        reply_content = generated_content
        if not reply_content:
            reply_content = await api.generate_content(
                post_content=parent_comment,
                instruction=ai_instructions,
                platform=task.get("platform", "facebook"),
                task_type="REPLY_COMMENT"
            )
        
        if not reply_content:
            result["error"] = "AI không trả về nội dung reply"
            return result
        
        print(f"    💬 Reply: {reply_content[:60]}...")
        result["content"] = reply_content
        
        if dry_run:
            print(f"    🔵 [DRY RUN] Bỏ qua gửi reply thực tế")
            result["status"] = "success"
            return result
        
        # --- Bước 5: Điền reply và gửi ---
        reply_success = await submit_reply(page, search_root, reply_content)
        
        if reply_success:
            result["status"] = "success"
            print(f"    ✅ Reply thành công!")
        else:
            result["error"] = "Không thể gửi reply"
            
    except Exception as e:
        result["error"] = str(e)
        print(f"    ❌ Lỗi reply: {e}")
    finally:
        await page.close()
    
    return result


async def find_comment_element(root, comment_text: str):
    """Tìm element chứa comment có nội dung khớp (hoặc gần khớp) với comment_text."""
    if not comment_text or len(comment_text.strip()) < 5:
        return None
    
    # Lấy tất cả các comment blocks (dùng selector cụ thể, KHÔNG quét toàn bộ div)
    comment_selectors = [
        "div[role='article']",  # Desktop React comment blocks
        "div[data-testid='UFI2Comment/body']",
        "div.UFIComment",
    ]
    
    search_text = comment_text.strip()[:80].lower()  # So sánh 80 ký tự đầu
    
    for selector in comment_selectors:
        try:
            elements = await root.query_selector_all(selector)
            for el in elements:
                try:
                    text = await el.inner_text()
                    if search_text in text.lower():
                        return el
                except Exception:
                    continue
        except Exception:
            continue
    
    # Fallback: dùng page.evaluate để tìm trong JS (KHÔNG kéo ElementHandle)
    try:
        result = await root.evaluate('''
            (searchText) => {
                const divs = document.querySelectorAll('div');
                for (const div of divs) {
                    const text = div.innerText || '';
                    if (text.length < 500 && text.length > 10 && text.toLowerCase().includes(searchText)) {
                        const rect = div.getBoundingClientRect();
                        if (rect.height > 50 && rect.height < 400) {
                            return true;
                        }
                    }
                }
                return false;
            }
        ''', search_text)
        # Nếu tìm thấy, dùng locator chính xác hơn
        if result:
            elements = await root.query_selector_all('div[role="article"], div[data-testid]')
            for el in elements:
                try:
                    text = await el.inner_text()
                    if search_text in text.lower():
                        return el
                except Exception:
                    continue
    except Exception:
        pass
    
    return None


async def click_reply_button(comment_el, page) -> bool:
    """Tìm và click nút Reply/Trả lời bên dưới comment element."""
    reply_selectors = [
        # Desktop Facebook
        "div[role='button'] span",
        "a[role='button']",
        "span[dir='auto']",
    ]
    
    reply_keywords = ["reply", "trả lời", "phản hồi", "respond"]
    
    # Tìm trong comment element và vùng lân cận
    try:
        for selector in reply_selectors:
            buttons = await comment_el.query_selector_all(selector)
            for btn in buttons:
                text = (await btn.inner_text()).strip().lower()
                if any(kw in text for kw in reply_keywords):
                    await btn.click()
                    return True
    except Exception:
        pass
    
    # Fallback: tìm trên toàn trang trong vùng gần comment
    try:
        comment_box = await comment_el.bounding_box()
        if comment_box:
            # Tìm tất cả nút reply trên trang
            all_buttons = await page.query_selector_all("div[role='button'], a[role='button'], span")
            for btn in all_buttons:
                try:
                    text = (await btn.inner_text()).strip().lower()
                    if any(kw in text for kw in reply_keywords):
                        btn_box = await btn.bounding_box()
                        if btn_box:
                            # Chỉ click nếu nút nằm gần comment (cùng vùng Y)
                            y_diff = abs(btn_box['y'] - (comment_box['y'] + comment_box['height']))
                            if y_diff < 100:
                                await btn.click()
                                return True
                except Exception:
                    continue
    except Exception:
        pass
    
    return False


async def submit_reply(page, search_root, reply_text: str) -> bool:
    """Điền nội dung vào ô reply đang active và gửi."""
    # Sau khi click Reply, Facebook mở ô nhập reply (thường là textbox mới focus)
    await random_delay(1, 2)
    
    # Tìm ô nhập đang focus
    reply_selectors = [
        "div[role='textbox'][contenteditable='true']:focus",
        "div[role='textbox'][contenteditable='true']",
        "textarea:focus",
        "textarea[name='comment_text']",  # mbasic
    ]
    
    reply_input = None
    for selector in reply_selectors:
        try:
            inputs = await search_root.query_selector_all(selector)
            for inp in inputs:
                box = await inp.bounding_box()
                if box and box['width'] > 0 and box['height'] > 0:
                    reply_input = inp
                    break
            if reply_input:
                break
        except Exception:
            continue
    
    if not reply_input:
        return False
    
    # Focus và nhập nội dung
    try:
        await reply_input.click(position={"x": 10, "y": 10})
        await random_delay(0.5, 1)
    except Exception:
        pass
    
    # Gõ nội dung bằng clipboard paste
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
        }''', [reply_input, reply_text])
    except Exception:
        # Fallback: gõ từng ký tự
        try:
            await reply_input.type(reply_text, delay=50)
        except Exception:
            return False
    
    await random_delay(1, 2)
    
    # Nhấn Enter để gửi (Facebook Desktop)
    try:
        await page.keyboard.press("Enter")
        await random_delay(2, 4)
        return True
    except Exception:
        pass
    
    # Fallback: tìm nút submit (mbasic)
    submit_selectors = [
        "input[type='submit'][value*='Reply']",
        "input[type='submit'][value*='Trả lời']",
        "input[type='submit']",
    ]
    for sel in submit_selectors:
        try:
            btn = await search_root.query_selector(sel)
            if btn:
                await btn.click()
                await random_delay(2, 4)
                return True
        except Exception:
            continue
    
    return False
