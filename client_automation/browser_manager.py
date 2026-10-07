# ============================================================
# Client Automation Tool - Browser Manager
# Quản lý trình duyệt Playwright với Stealth mode
# ============================================================

import random
import asyncio
import json
from typing import Optional, Dict
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import USER_AGENTS, VIEWPORTS, PAGE_TIMEOUT, ACTION_DELAY_MIN, ACTION_DELAY_MAX


async def random_delay(min_sec: int = None, max_sec: int = None):
    """Delay ngẫu nhiên giữa các hành động - mô phỏng người thật."""
    min_s = min_sec or ACTION_DELAY_MIN
    max_s = max_sec or ACTION_DELAY_MAX
    delay = random.uniform(min_s, max_s)
    await asyncio.sleep(delay)


def parse_proxy(proxy_str: str) -> tuple:
    """
    Parse proxy string sang dict cho Playwright.
    Nếu là SOCKS5 có user/pass, tự động tạo cầu nối HTTP pproxy cục bộ vì Chromium không hỗ trợ socks5 auth.
    Hỗ trợ formats:
    - ip:port
    - ip:port:username:password
    - http://username:password@ip:port
    - socks5://ip:port:username:password
    - socks5://username:password@ip:port
    
    Returns:
        (playwright_proxy_dict, forwarder_process)
    """
    if not proxy_str:
        return None, None
    
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return None, None

    # 1. Trường hợp SOCKS5 có xác thực -> dùng pproxy làm cầu nối sang HTTP local
    if "socks5://" in proxy_str:
        clean = proxy_str.replace("socks5://", "")
        host, port, user, pwd = None, None, None, None
        if "@" in clean:
            auth_part, host_port = clean.split("@", 1)
            if ":" in auth_part and ":" in host_port:
                user, pwd = auth_part.split(":", 1)
                host, port = host_port.split(":", 1)
        else:
            parts = clean.split(":")
            if len(parts) == 4:
                host, port, user, pwd = parts[0], parts[1], parts[2], parts[3]
            elif len(parts) == 2:
                # SOCKS5 không có mật khẩu -> Playwright nhận trực tiếp
                return {"server": f"socks5://{parts[0]}:{parts[1]}"}, None

        if host and port and user and pwd:
            try:
                import subprocess
                import time
                local_port = random.randint(16000, 18000)
                proc = subprocess.Popen([
                    'pproxy',
                    '-l', f'http://127.0.0.1:{local_port}',
                    '-r', f'socks5://{host}:{port}#{user}:{pwd}'
                ], stdin=subprocess.DEVNULL)
                time.sleep(1.2)
                return {"server": f"http://127.0.0.1:{local_port}"}, proc
            except Exception as e:
                print(f"    ⚠️ Không thể khởi động pproxy forwarder: {e}")
                return None, None

    # 2. Xử lý format full URL: http://user:pass@host:port
    if proxy_str.startswith("http://") or proxy_str.startswith("https://"):
        from urllib.parse import urlparse
        try:
            parsed = urlparse(proxy_str)
            if not parsed.hostname or not parsed.port:
                return None, None
            server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
            res = {"server": server}
            if parsed.username:
                res["username"] = parsed.username
            if parsed.password:
                res["password"] = parsed.password
            return res, None
        except Exception:
            return None, None

    # 3. Xử lý format cũ: ip:port hoặc ip:port:user:pass
    parts = proxy_str.split(":")
    if len(parts) == 2:
        return {"server": f"http://{parts[0]}:{parts[1]}"}, None
    elif len(parts) == 4:
        return {
            "server": f"http://{parts[0]}:{parts[1]}",
            "username": parts[2],
            "password": parts[3]
        }, None

    return None, None


def parse_cookies(cookie_str: str, domain: str = ".facebook.com") -> list:
    """
    Parse cookie string sang list of dicts cho Playwright.
    Hỗ trợ 2 định dạng:
    1. Chuỗi JSON (từ Dolphin Anty / Cookie-Editor export)
    2. Chuỗi dạng: key=value; key2=value2
    """
    if not cookie_str:
        return []
    
    cookie_str = cookie_str.strip()
    
    # Nếu là JSON
    if cookie_str.startswith("[") and cookie_str.endswith("]"):
        try:
            cookies = json.loads(cookie_str)
            result = []
            for c in cookies:
                cookie_domain = c.get("domain") or domain
                cookie_name = c.get("name")
                cookie_value = c.get("value")
                if not cookie_name or cookie_value is None:
                    continue
                
                # Bỏ qua cookie từ domain khác nếu đang dùng cho Facebook (tránh lỗi xung đột do user export toàn bộ cookies)
                c_dom = (cookie_domain or "").lower()
                if "facebook.com" in domain or "messenger.com" in domain:
                    if not any(fb_dom in c_dom for fb_dom in ["facebook.com", "messenger.com", "instagram.com"]):
                        continue

                cookie_dict = {
                    "name": cookie_name,
                    "value": str(cookie_value),
                    "domain": cookie_domain,
                    "path": c.get("path", "/")
                }
                
                # Xử lý cờ secure: Chromium bắt buộc secure=True với các cookie có tiền tố __Secure- hoặc __Host-
                if c.get("secure") is not None:
                    cookie_dict["secure"] = bool(c.get("secure"))
                elif cookie_name.startswith("__Secure-") or cookie_name.startswith("__Host-"):
                    cookie_dict["secure"] = True
                
                # Cookie __Host- không được phép có domain trong CDP
                if cookie_name.startswith("__Host-") and "domain" in cookie_dict:
                    del cookie_dict["domain"]
                
                # Xử lý sameSite: CDP chỉ nhận "Strict", "Lax", "None"
                same_site = c.get("sameSite")
                if same_site:
                    same_site_str = str(same_site).lower()
                    if same_site_str in ["strict"]:
                        cookie_dict["sameSite"] = "Strict"
                    elif same_site_str in ["lax"]:
                        cookie_dict["sameSite"] = "Lax"
                    elif same_site_str in ["none", "no_restriction"]:
                        cookie_dict["sameSite"] = "None"

                result.append(cookie_dict)
            return result
        except Exception:
            pass
            
    # Nếu là chuỗi thông thường
    cookies = []
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": domain,
                "path": "/",
            })
    return cookies


class BrowserManager:
    """Quản lý vòng đời trình duyệt cho mỗi tài khoản."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
    
    async def start(self):
        """Khởi tạo Playwright engine."""
        self.playwright = await async_playwright().start()
    
    async def create_context(self, cookies_str: str = None, proxy_str: str = None) -> BrowserContext:
        """
        Tạo browser + context mới với:
        - Proxy (nếu có)
        - User-Agent ngẫu nhiên
        - Viewport ngẫu nhiên
        - Stealth settings
        
        Trả về context. Browser được lưu trong context._browser_ref để đóng sau.
        """
        user_agent = random.choice(USER_AGENTS)
        viewport = random.choice(VIEWPORTS)
        proxy, proxy_proc = parse_proxy(proxy_str)
        
        launch_args = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--no-zygote",
                "--single-process",
                "--disable-setuid-sandbox",
            ]
        }
        if proxy:
            launch_args["proxy"] = proxy
            print(f"    🌐 Kích hoạt Proxy qua: {proxy.get('server')}")
        
        try:
            browser = await self.playwright.chromium.launch(**launch_args)
        except Exception:
            if proxy_proc:
                try:
                    proxy_proc.terminate()
                except Exception:
                    pass
            raise
        
        try:
            context = await browser.new_context(
                user_agent=user_agent,
                viewport=viewport,
                locale="vi-VN",
                timezone_id="Asia/Ho_Chi_Minh",
                java_script_enabled=True,
            )
            
            # Inject stealth scripts để che giấu dấu vết automation
            await context.add_init_script("""
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                
                // Override chrome runtime
                window.chrome = { runtime: {} };
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['vi-VN', 'vi', 'en-US', 'en'],
                });
            """)
            
            # Inject cookies
            if cookies_str:
                cookies = parse_cookies(cookies_str)
                if cookies:
                    try:
                        await context.add_cookies(cookies)
                    except Exception as e:
                        # Fallback: Thêm từng cookie một để bỏ qua cookie lỗi lẻ tẻ
                        for c in cookies:
                            try:
                                await context.add_cookies([c])
                            except Exception:
                                pass
            
            # Cấu hình timeout mặc định
            context.set_default_timeout(PAGE_TIMEOUT)
            
            # Lưu reference browser và proxy forwarder vào context để đóng sau
            context._owner_browser = browser
            context._proxy_proc = proxy_proc
            
            return context
            
        except Exception:
            if proxy_proc:
                try:
                    proxy_proc.terminate()
                except Exception:
                    pass
            # Nếu tạo context thất bại, đóng browser ngay
            try:
                await browser.close()
            except Exception:
                pass
            raise
    
    async def close_context(self, context: BrowserContext):
        """Đóng browser context VÀ browser instance liên kết."""
        try:
            await context.close()
        except Exception:
            pass
        # Đóng browser instance để tránh rò rỉ tiến trình Chromium
        try:
            browser = getattr(context, '_owner_browser', None)
            if browser:
                await browser.close()
        except Exception:
            pass
        # Đóng tiến trình proxy forwarder nếu có
        try:
            proxy_proc = getattr(context, '_proxy_proc', None)
            if proxy_proc:
                proxy_proc.terminate()
        except Exception:
            pass
    
    async def stop(self):
        """Đóng toàn bộ Playwright engine."""
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
