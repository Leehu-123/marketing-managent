# ============================================================
# Client Automation Tool - API Client
# Giao tiếp với Backend Web Quản Lý
# ============================================================

import httpx
from typing import List, Dict, Optional
from config import BACKEND_URL, API_TASKS_FETCH, API_TASK_RESULT, API_GENERATE_CONTENT


class APIClient:
    """Client giao tiếp với Backend Web Quản Lý."""
    
    def __init__(self, backend_url: str = None):
        self.backend_url = backend_url or BACKEND_URL
        self.client = httpx.Client(timeout=30.0)
    
    def fetch_tasks(self, platform: str, limit: int = 10) -> List[Dict]:
        """
        Lấy danh sách tasks pending kèm đầy đủ thông tin campaign + account.
        Trả về list of TaskWithDetails.
        """
        try:
            url = f"{self.backend_url}{API_TASKS_FETCH}"
            resp = self.client.get(url, params={"platform": platform, "limit": limit})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            print(f"[API ERROR] Lỗi khi lấy tasks: {e}")
            return []
    
    def generate_content(self, post_content: str, instruction: str, platform: str = "facebook", task_type: str = "COMMENT") -> str:
        """
        Gọi AI Backend sinh nội dung seeding (comment/bài viết).
        """
        try:
            url = f"{self.backend_url}{API_GENERATE_CONTENT}"
            resp = self.client.post(url, json={
                "post_content": post_content,
                "instruction": instruction
            }, params={"platform": platform, "task_type": task_type})
            resp.raise_for_status()
            data = resp.json()
            return data.get("generated_content", "")
        except httpx.HTTPError as e:
            print(f"[API ERROR] Lỗi khi sinh nội dung AI: {e}")
            return ""
    
    def report_result(self, task_id: int, status: str, generated_content: str = None, error_message: str = None, account_id: int = None) -> bool:
        """
        Báo cáo kết quả thực thi task về Backend.
        status: 'success' hoặc 'failed'
        """
        try:
            url = f"{self.backend_url}{API_TASK_RESULT.format(task_id=task_id)}"
            payload = {"status": status}
            if generated_content:
                payload["generated_content"] = generated_content
            if error_message:
                payload["error_message"] = error_message
            if account_id:
                payload["account_id"] = account_id
                
            resp = self.client.post(url, json=payload)
            resp.raise_for_status()
            return True
        except httpx.HTTPError as e:
            print(f"[API ERROR] Lỗi khi báo cáo kết quả task #{task_id}: {e}")
            return False
    
    def close(self):
        self.client.close()
