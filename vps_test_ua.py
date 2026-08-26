import paramiko
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('45.117.177.80', username='root', password='Y3pKPk3C4rH4EWe1')

# Test script inside docker container
test_script = r"""
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        # Test 1: Desktop UA
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await ctx.new_page()
        await page.goto("https://mbasic.facebook.com/groups/351495118685805")
        print("Desktop UA redirected to:", page.url)
        print("Desktop UA Title:", await page.title())
        await ctx.close()

        # Test 2: Mobile UA
        ctx_mobile = await browser.new_context(user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto("https://mbasic.facebook.com/groups/351495118685805")
        print("Mobile UA redirected to:", page_mobile.url)
        print("Mobile UA Title:", await page_mobile.title())
        await ctx_mobile.close()

        await browser.close()

asyncio.run(test())
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_ua.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('docker cp /tmp/test_ua.py dafa_glass_backend:/tmp/test_ua.py && docker exec dafa_glass_backend python3 /tmp/test_ua.py', timeout=30)
out = stdout.read().decode('utf-8', errors='ignore')
err = stderr.read().decode('utf-8', errors='ignore')
print("OUTPUT:\n", out)
if err:
    print("STDERR:\n", err)

ssh.close()
