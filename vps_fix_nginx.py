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
    print(out)

# 1. Update marketing-management Nginx config
nginx_conf = """server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:3006;
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

sftp = ssh.open_sftp()
with sftp.file('/etc/nginx/sites-available/marketing-management', 'w') as f:
    f.write(nginx_conf)
sftp.close()

# Update dafaglass config if present
run_cmd("sed -i 's/127.0.0.1:8000/127.0.0.1:3006/g' /etc/nginx/sites-available/dafaglass || true")
run_cmd("ln -sf /etc/nginx/sites-available/marketing-management /etc/nginx/sites-enabled/default")
run_cmd("nginx -t && systemctl reload nginx")

# Test curl to container 3006 directly
run_cmd("curl -s http://127.0.0.1:3006/seeding/campaigns | grep -i 'reply'")
run_cmd("curl -s http://127.0.0.1:3006/seeding/campaigns | grep -i 'POST_GROUP'")

ssh.close()
