import paramiko
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('45.117.177.80', username='root', password='Y3pKPk3C4rH4EWe1')

def run_cmd(cmd):
    print(f'=== CMD: {cmd} ===')
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    print(out)
    if err:
        print(f'STDERR: {err}')

# ============================================================
# Fix 1: Update Nginx to proxy to port 3007 (dafa_glass_backend = the seeding app)
# ============================================================
print("[1/4] Cập nhật Nginx proxy -> port 3007...")
nginx_conf = """server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:3007;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
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
"""

# Write nginx config
stdin, stdout, stderr = ssh.exec_command("cat > /etc/nginx/sites-enabled/default << 'NGINX_EOF'\n" + nginx_conf + "NGINX_EOF")
stdout.read()

# Test and reload nginx
run_cmd('nginx -t && systemctl reload nginx')

# ============================================================
# Fix 2: Stop the tool first (it's in a broken loop)
# ============================================================
print("[2/4] Dừng tool đang chạy lỗi...")
run_cmd('curl -s -X POST http://127.0.0.1:3007/api/v1/seeding/tool/stop')

# ============================================================
# Fix 3: Check campaigns and tasks status
# ============================================================
print("[3/4] Kiểm tra campaigns và tasks status...")
run_cmd('curl -s "http://127.0.0.1:3007/api/v1/seeding/tasks/fetch?platform=facebook&limit=5" | python3 -m json.tool 2>/dev/null || curl -s "http://127.0.0.1:3007/api/v1/seeding/tasks/fetch?platform=facebook&limit=5"')

# ============================================================
# Fix 4: Verify Nginx proxies correctly now
# ============================================================
print("[4/4] Kiểm tra Nginx proxy đã chính xác...")
run_cmd('curl -s "http://127.0.0.1/api/v1/seeding/tool/status"')

ssh.close()
