# ============================================================
# Client Automation Tool - Configuration
# ============================================================

# URL của Backend Web Quản Lý
BACKEND_URL = "http://127.0.0.1:8000"

# API Endpoints
API_TASKS_FETCH = "/api/v1/seeding/tasks/fetch"
API_TASK_RESULT = "/api/v1/seeding/tasks/{task_id}/result"
API_GENERATE_CONTENT = "/api/v1/seeding/client/generate-content"

# Số luồng (worker) chạy song song - mỗi worker = 1 trình duyệt
MAX_WORKERS = 2

# Delay giữa các hành động trong trình duyệt (giây) - mô phỏng người thật
ACTION_DELAY_MIN = 3
ACTION_DELAY_MAX = 8

# Delay giữa các tài khoản khác nhau (giây) - tránh bị phát hiện
ACCOUNT_DELAY_MIN = 30
ACCOUNT_DELAY_MAX = 90

# Delay giữa các task liên tiếp cùng 1 tài khoản (giây)
TASK_DELAY_MIN = 10
TASK_DELAY_MAX = 30

# Timeout khi load trang (giây)
PAGE_TIMEOUT = 30000  # milliseconds

# Số task lấy mỗi lần poll
TASKS_PER_POLL = 10

# Thời gian chờ giữa các lần poll khi hết task (giây)
POLL_INTERVAL = 60

# Facebook URL (dùng Desktop UA và web chuẩn)
FB_MBASIC_URL = "https://www.facebook.com"

# User Agent pool - xoay vòng ngẫu nhiên (Dùng Desktop UA)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Viewport sizes - giả lập màn hình máy tính
VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
]
