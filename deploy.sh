#!/usr/bin/env bash
# =========================================================================
#  SCRIPT DEPLOY TỰ ĐỘNG LÊN VPS (CLOUD019347 / 45.117.177.80)
#  Project: DAFA Glass Marketing Management SaaS
# =========================================================================

set -e

# Cấu hình VPS
SERVER_IP="45.117.177.80"
EMAIL="dafagroupvn@gmail.com"
GIT_REPO="https://github.com/Leehu-123/marketing-managent.git"
APP_DIR="/var/www/marketing-management"

echo "========================================================================="
echo "   🚀 BẮT ĐẦU QUÁ TRÌNH DEPLOY MARKETING MANAGEMENT LÊN VPS ($SERVER_IP)"
echo "========================================================================="
echo ""

# 1. Cập nhật hệ thống
echo "[1/6] 🔄 Cập nhật hệ điều hành VPS..."
apt-get update -y && apt-get upgrade -y
apt-get install -y git curl wget ufw software-properties-common ca-certificates gnupg

# 2. Cài đặt Docker & Docker Compose nếu chưa có
echo "[2/6] 🐳 Kiểm tra và cài đặt Docker..."
if ! command -v docker &> /dev/null; then
    echo "Đang cài đặt Docker Engine..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm -f get-docker.sh
    systemctl enable docker
    systemctl start docker
    echo "✅ Cài đặt Docker hoàn tất."
else
    echo "✅ Docker đã được cài đặt."
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Đang cài đặt Docker Compose..."
    apt-get install -y docker-compose-plugin || apt-get install -y docker-compose
fi

# 3. Pull/Clone mã nguồn từ GitHub
echo "[3/6] 📥 Cập nhật mã nguồn từ Git ($GIT_REPO)..."
if [ -d "$APP_DIR/.git" ]; then
    echo "Thư mục đã tồn tại, tiến hành git pull mới nhất..."
    cd "$APP_DIR"
    git fetch --all
    git reset --hard origin/main || git reset --hard origin/master
    git pull
else
    echo "Đang clone dự án mới vào $APP_DIR..."
    mkdir -p /var/www
    git clone "$GIT_REPO" "$APP_DIR"
    cd "$APP_DIR"
fi

# 4. Cấu hình file .env cho Backend
echo "[4/6] ⚙️ Cấu hình môi trường Production (.env)..."
cd "$APP_DIR/backend"
if [ ! -f .env ]; then
    cp .env.example .env
    # Đổi môi trường thành production
    sed -i 's/ENV=development/ENV=production/g' .env
    echo "✅ Đã tạo file .env mới cho môi trường production."
fi

# Tạo thư mục uploads và database file nếu chưa có
mkdir -p uploads uploads/brand/products static
touch dafa_glass.db

# 5. Build và khởi chạy Docker Containers
echo "[5/6] 🏗️ Build và khởi chạy Docker Container..."
if docker compose version &> /dev/null; then
    docker compose down || true
    docker compose up -d --build
else
    docker-compose down || true
    docker-compose up -d --build
fi

# 6. Cài đặt Nginx Reverse Proxy
echo "[6/6] 🌐 Cấu hình Nginx & Firewall..."
apt-get install -y nginx

cat << 'EOF' > /etc/nginx/sites-available/marketing-management
server {
    listen 80;
    server_name _;

    # Tăng giới hạn dung lượng upload cho video/hình ảnh
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:3006;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Hỗ trợ WebSocket / Long Polling nếu có
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /static/ {
        alias /var/www/marketing-management/backend/static/;
        expires 30d;
    }

    location /uploads/ {
        alias /var/www/marketing-management/backend/uploads/;
        expires 30d;
    }
}
EOF

ln -sf /etc/nginx/sites-available/marketing-management /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Cấu hình UFW Firewall
ufw allow 22/tcp || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
ufw allow 8000/tcp || true
ufw --force enable || true

echo ""
echo "========================================================================="
echo " 🎉 TẤT CẢ ĐÃ HOÀN TẤT! ĐÃ DEPLOY THÀNH CÔNG LÊN VPS ($SERVER_IP)"
echo "========================================================================="
echo " 🌐 Địa chỉ truy cập App: http://$SERVER_IP"
echo " 🌐 Hoặc cổng Backend trực tiếp: http://$SERVER_IP:8000"
echo " 🔑 Tài khoản Quản trị mặc định: admin / dafa123"
echo " 📄 Log ứng dụng Docker: docker logs -f dafa_glass_backend"
echo "========================================================================="
