#!/usr/bin/env bash
set -e

echo "========================================================================="
echo "   DAFA GLASS MARKETING MANAGEMENT - CHẠY APP TRÊN LOCAL (TESTING)"
echo "========================================================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/backend"

# 1. Check .env
if [ ! -f .env ]; then
    echo "[INFO] Khởi tạo file .env từ .env.example..."
    cp .env.example .env
fi

# 2. Check virtualenv
if [ ! -d "venv" ]; then
    echo "[INFO] Tạo môi trường ảo venv..."
    python3 -m venv venv || python -m venv venv
fi

# 3. Activate venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# 4. Install dependencies
echo "[INFO] Cài đặt dependencies..."
pip install -r requirements.txt

echo ""
echo "========================================================================="
echo "  🚀 SERVER ĐÃ SẴN SÀNG CHẠY TẠI: http://localhost:8000"
echo "  🔑 TÀI KHOẢN MẶC ĐỊNH: admin / dafa123"
echo "  📌 Nhấn Ctrl+C để dừng server khi test xong."
echo "========================================================================="
echo ""

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
