import asyncio
import sqlite3
import json
from playwright.async_api import async_playwright

def get_cookies():
    conn = sqlite3.connect('../backend/dafa_glass.db')
    c = conn.cursor()
    c.execute("SELECT cookies FROM seeding_accounts WHERE platform='facebook' LIMIT 1")
    row = c.fetchone()
    conn.close()
    if not row:
        return []
    cookie_str = row[0]
    
    if cookie_str.startswith("["):
        cookies = json.loads(cookie_str)
        return [{"name": c.get("name"), "value": c.get("value"), "domain": c.get("domain", ".facebook.com"), "path": c.get("path", "/")} for c in cookies]
    
    cookies = []
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".facebook.com",
                "path": "/",
            })
    return cookies

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        cookies = get_cookies()
        if cookies:
            await context.add_cookies(cookies)
            
        page = await context.new_page()
        print("start")
        url = "https://www.facebook.com/dafaglass/posts/pfbid0YUw3SD5LsRnV4t58GJLuCau9MfzfdEsVSS2opZdjsZFUp75jwqebjaT1H9tvyEZal"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(6000)
        
        search_root = page
        dialogs = await page.query_selector_all("div[role='dialog']")
        if dialogs:
            for dialog in reversed(dialogs):
                box = await dialog.bounding_box()
                if box and box['width'] > 200 and box['height'] > 200:
                    search_root = dialog
                    print("Found dialog!")
                    break
        else:
            print("No dialog found, using page")
            
        with open("debug_out_auth.txt", "w", encoding="utf-8") as f:
            f.write("HTML contenteditable:\n")
            els = await search_root.query_selector_all("div[contenteditable='true']")
            for el in els:
                html = await el.evaluate("el => el.outerHTML")
                f.write(html + "\n")
                
            f.write("HTML role textbox:\n")
            els = await search_root.query_selector_all("div[role='textbox']")
            for el in els:
                html = await el.evaluate("el => el.outerHTML")
                f.write(html + "\n")
                
        # chup man hinh
        await page.screenshot(path="debug_screen.png", full_page=True)
        await browser.close()
        print("done")

asyncio.run(main())
