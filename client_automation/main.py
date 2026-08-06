# ============================================================
# Client Automation Tool - Main Entry Point
# Chạy seeding tự động: Comment dạo + Đăng bài hội nhóm
# ============================================================

import asyncio
import argparse
import sys
import time
import random
from typing import List, Dict

# Fix encoding for Windows Console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import print as rprint

from config import (
    BACKEND_URL, MAX_WORKERS, TASKS_PER_POLL, POLL_INTERVAL,
    ACCOUNT_DELAY_MIN, ACCOUNT_DELAY_MAX, TASK_DELAY_MIN, TASK_DELAY_MAX
)
from api_client import APIClient
from browser_manager import BrowserManager, random_delay

console = Console()


def print_banner():
    """Hiển thị banner khi khởi động tool."""
    banner = """
╔═══════════════════════════════════════════════════╗
║        🚀 SEEDING AUTOMATION TOOL v1.0 🚀         ║
║                                                   ║
║    Tự động Comment dạo + Đăng bài Hội nhóm       ║
║    Kết nối: Backend Web Quản Lý                   ║
║                                                   ║
║    ⚠️  Sử dụng có trách nhiệm!                    ║
╚═══════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold cyan", border_style="cyan"))


def display_tasks_table(tasks: List[Dict]):
    """Hiển thị bảng tasks đã fetch được."""
    table = Table(title="📋 Danh sách nhiệm vụ", border_style="dim")
    table.add_column("ID", style="cyan", justify="center", width=6)
    table.add_column("Loại", style="magenta", justify="center", width=12)
    table.add_column("Tài khoản", style="green", width=20)
    table.add_column("URL mục tiêu", style="yellow", width=45)
    table.add_column("Proxy", style="dim", width=15)
    
    for t in tasks:
        task_type = "💬 Comment" if t.get("campaign_type") == "COMMENT" else "📝 Đăng bài"
        username = t.get("account_username", "N/A") or "N/A"
        url = t.get("target_url", "")
        if len(url) > 42:
            url = url[:42] + "..."
        proxy = t.get("account_proxy", "Không") or "Không"
        if len(proxy) > 12:
            proxy = proxy[:12] + "..."
        
        table.add_row(str(t["id"]), task_type, username, url, proxy)
    
    console.print(table)


async def process_task(task: Dict, api: APIClient, browser_mgr: BrowserManager, dry_run: bool = False) -> Dict:
    """Xử lý 1 task: tạo browser context → chạy task → đóng."""
    task_id = task["id"]
    task_type = task.get("campaign_type", "COMMENT")
    username = task.get("account_username", "N/A")
    
    console.print(f"\n  [bold]🔄 Task #{task_id}[/bold] | [{task_type}] | Tài khoản: [cyan]{username}[/cyan]")
    
    # Kiểm tra tài khoản có cookies không
    if not task.get("account_cookies"):
        error_msg = "Tài khoản chưa có Cookies - không thể chạy."
        console.print(f"    [red]❌ {error_msg}[/red]")
        api.report_result(task_id, "failed", error_message=error_msg, account_id=task.get("account_id"))
        return {"status": "failed", "error": error_msg}
    
    # Tạo browser context với proxy + cookies
    context = await browser_mgr.create_context(
        cookies_str=task.get("account_cookies"),
        proxy_str=task.get("account_proxy")
    )
    
    try:
        if task_type == "COMMENT":
            from tasks.facebook_comment import execute_comment_task
            result = await execute_comment_task(context, task, api, dry_run=dry_run)
        elif task_type == "POST_GROUP":
            from tasks.facebook_post import execute_post_task
            result = await execute_post_task(context, task, api, dry_run=dry_run)
        else:
            result = {"status": "failed", "content": "", "error": f"Loại task không hỗ trợ: {task_type}"}
        
        # Báo cáo kết quả về Backend
        api.report_result(
            task_id=task_id,
            status=result["status"],
            generated_content=result.get("content"),
            error_message=result.get("error"),
            account_id=task.get("account_id")
        )
        
        return result
        
    finally:
        await browser_mgr.close_context(context)


async def run_worker(tasks: List[Dict], api: APIClient, headless: bool, dry_run: bool):
    """Worker: xử lý danh sách tasks tuần tự (mỗi worker = 1 trình duyệt)."""
    browser_mgr = BrowserManager(headless=headless)
    await browser_mgr.start()
    
    success_count = 0
    fail_count = 0
    
    try:
        for i, task in enumerate(tasks):
            result = await process_task(task, api, browser_mgr, dry_run=dry_run)
            
            if result.get("status") == "success":
                success_count += 1
            else:
                fail_count += 1
            
            # Delay giữa các task
            if i < len(tasks) - 1:
                delay = random.uniform(TASK_DELAY_MIN, TASK_DELAY_MAX)
                console.print(f"    ⏳ Chờ {delay:.0f}s trước task tiếp theo...")
                await asyncio.sleep(delay)
    finally:
        await browser_mgr.stop()
    
    return {"success": success_count, "failed": fail_count}


async def main_loop(platform: str, workers: int, backend_url: str, headless: bool, dry_run: bool, once: bool):
    """Vòng lặp chính: Poll tasks → Phân bổ → Chạy → Lặp lại."""
    api = APIClient(backend_url)
    
    console.print(f"\n[bold green]⚡ Khởi động Tool Automation[/bold green]")
    console.print(f"  📡 Backend: [cyan]{backend_url}[/cyan]")
    console.print(f"  🌐 Platform: [magenta]{platform}[/magenta]")
    console.print(f"  👷 Workers: [yellow]{workers}[/yellow]")
    console.print(f"  👁️  Headless: {'Có' if headless else '[red]Không (hiện trình duyệt)[/red]'}")
    console.print(f"  🔵 Dry Run: {'[blue]BẬT - không đăng thật[/blue]' if dry_run else 'TẮT - đăng thật!'}")
    console.print()
    
    total_success = 0
    total_failed = 0
    poll_count = 0
    
    while True:
        poll_count += 1
        console.rule(f"[bold]Lần poll #{poll_count}[/bold]")
        
        # Fetch tasks từ Backend
        console.print("  📡 Đang lấy nhiệm vụ từ Backend...")
        tasks = api.fetch_tasks(platform, limit=TASKS_PER_POLL)
        
        if not tasks:
            console.print("  [yellow]📭 Không có nhiệm vụ nào đang chờ.[/yellow]")
            if once:
                break
            console.print(f"  ⏳ Chờ {POLL_INTERVAL}s rồi thử lại...")
            await asyncio.sleep(POLL_INTERVAL)
            continue
        
        console.print(f"  ✅ Nhận được [bold]{len(tasks)}[/bold] nhiệm vụ!")
        display_tasks_table(tasks)
        
        # Phân bổ tasks cho workers
        if workers == 1 or len(tasks) <= 1:
            # Chạy tuần tự
            result = await run_worker(tasks, api, headless, dry_run)
            total_success += result["success"]
            total_failed += result["failed"]
        else:
            # Chia tasks cho nhiều workers
            chunks = [[] for _ in range(min(workers, len(tasks)))]
            for i, task in enumerate(tasks):
                chunks[i % len(chunks)].append(task)
            
            # Chạy song song
            worker_tasks = [
                run_worker(chunk, api, headless, dry_run)
                for chunk in chunks if chunk
            ]
            results = await asyncio.gather(*worker_tasks)
            
            for r in results:
                total_success += r["success"]
                total_failed += r["failed"]
        
        # Hiển thị tổng kết
        console.print(f"\n  📊 [bold]Tổng kết:[/bold] ✅ {total_success} thành công | ❌ {total_failed} thất bại")
        
        if once:
            break
        
        # Delay giữa các lần poll
        delay = random.uniform(ACCOUNT_DELAY_MIN, ACCOUNT_DELAY_MAX)
        console.print(f"  ⏳ Chờ {delay:.0f}s trước lần poll tiếp theo...")
        await asyncio.sleep(delay)
    
    api.close()
    
    console.print(f"\n[bold green]🏁 Hoàn tất! Tổng: ✅ {total_success} thành công | ❌ {total_failed} thất bại[/bold green]\n")


def main():
    parser = argparse.ArgumentParser(
        description="🚀 Seeding Automation Tool - Tự động Comment & Đăng bài Facebook",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--platform", "-p",
        type=str, default="facebook",
        choices=["facebook", "tiktok", "youtube"],
        help="Nền tảng mục tiêu (mặc định: facebook)"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int, default=MAX_WORKERS,
        help=f"Số luồng chạy song song (mặc định: {MAX_WORKERS})"
    )
    parser.add_argument(
        "--backend-url", "-b",
        type=str, default=BACKEND_URL,
        help=f"URL của Backend (mặc định: {BACKEND_URL})"
    )
    parser.add_argument(
        "--headless",
        action="store_true", default=True,
        help="Chạy trình duyệt ẩn (mặc định: True)"
    )
    parser.add_argument(
        "--show-browser",
        action="store_true", default=False,
        help="Hiện trình duyệt để theo dõi (tắt headless)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true", default=False,
        help="Chế độ khô: chỉ giả lập, không đăng comment/bài thật"
    )
    parser.add_argument(
        "--once",
        action="store_true", default=False,
        help="Chỉ chạy 1 lần rồi dừng (không lặp poll)"
    )
    
    args = parser.parse_args()
    
    headless = not args.show_browser
    
    print_banner()
    
    try:
        asyncio.run(main_loop(
            platform=args.platform,
            workers=args.workers,
            backend_url=args.backend_url,
            headless=headless,
            dry_run=args.dry_run,
            once=args.once
        ))
    except KeyboardInterrupt:
        console.print("\n[bold red]⛔ Đã dừng Tool bởi người dùng (Ctrl+C)[/bold red]\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
