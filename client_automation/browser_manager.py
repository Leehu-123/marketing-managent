# ============================================================
# Client Automation Tool - Browser Manager
# Quản lý trình duyệt Playwright với Stealth mode
# ============================================================

import random
import asyncio
from typing import Optional, Dict
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import USER_AGENTS, VIEWPORTS, PAGE_TIMEOUT, ACTION_DELAY_MIN, ACTION_DELAY_MAX


async def random_delay(min_sec: int = None, max_sec: int = None):
    """Delay ngẫu nhiên giữa các hành động - mô phỏng người thật."""
    min_s = min_sec or ACTION_DELAY_MIN
    max_s = max_sec or ACTION_DELAY_MAX
    delay = random.uniform(min_s, max_s)
    await asyncio.sleep(delay)


def parse_proxy(proxy_str: str) -> Optional[Dict]:
    """
    Parse proxy string sang dict cho Playwright.
    Hỗ trợ formats:
    - ip:port
    - ip:port:username:password
    """
    if not proxy_str:
        return None
    
    parts = proxy_str.strip().split(":")
    if len(parts) == 2:
        return {"server": f"http://{parts[0]}:{parts[1]}"}
    elif len(parts) == 4:
        return {
            "server": f"http://{parts[0]}:{parts[1]}",
            "username": parts[2],
            "password": parts[3]
        }
    return None


import json

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
                result.append({
                    "name": c.get("name"),
                    "value": c.get("value"),
                    "domain": c.get("domain", domain),
                    "path": c.get("path", "/")
                })
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
        self.browser: Optional[Browser] = None
    
    async def start(self):
        """Khởi tạo Playwright engine."""
        self.playwright = await async_playwright().start()
    
    async def create_context(self, cookies_str: str = None, proxy_str: str = None) -> BrowserContext:
        """
        Tạo browser context mới với:
        - Proxy (nếu có)
        - User-Agent ngẫu nhiên
        - Viewport ngẫu nhiên
        - Stealth settings
        """
        user_agent = random.choice(USER_AGENTS)
        viewport = random.choice(VIEWPORTS)
        proxy = parse_proxy(proxy_str)
        
        launch_args = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        }
        if proxy:
            launch_args["proxy"] = proxy
        
        self.browser = await self.playwright.chromium.launch(**launch_args)
        
        context = await self.browser.new_context(
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
                await context.add_cookies(cookies)
        
        # Cấu hình timeout mặc định
        context.set_default_timeout(PAGE_TIMEOUT)
        
        return context
    
    async def close_context(self, context: BrowserContext):
        """Đóng browser context."""
        try:
            await context.close()
        except Exception:
            pass
    
    async def stop(self):
        """Đóng toàn bộ Playwright engine."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
