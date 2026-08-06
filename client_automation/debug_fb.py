import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        page = await context.new_page()
        print("start")
        await page.goto("https://www.facebook.com/dafaglass/posts/pfbid0YUw3SD5LsRnV4t58GJLuCau9MfzfdEsVSS2opZdjsZFUp75jwqebjaT1H9tvyEZal", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        
        with open("debug_out.txt", "w", encoding="utf-8") as f:
            f.write("HTML contenteditable:\n")
            els = await page.query_selector_all("div[contenteditable='true']")
            for el in els:
                html = await el.evaluate("el => el.outerHTML")
                f.write(html + "\n")
                
            f.write("HTML role textbox:\n")
            els = await page.query_selector_all("div[role='textbox']")
            for el in els:
                html = await el.evaluate("el => el.outerHTML")
                f.write(html + "\n")
            
        await browser.close()

asyncio.run(main())
