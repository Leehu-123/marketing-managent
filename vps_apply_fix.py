import paramiko
import sys
import time

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

# 1. Stop the currently broken tool
print("[1/5] Dừng tool cũ...")
run_cmd('curl -s -X POST http://127.0.0.1:3007/api/v1/seeding/tool/stop')

# 2. Git pull latest code
print("[2/5] Pull code mới...")
run_cmd('cd /var/www/marketing-management && git pull')

# 3. Rebuild Docker container (since code may have changed in backend too)
print("[3/5] Rebuild Docker container...")
run_cmd('cd /var/www/marketing-management/backend && docker compose up -d --build')

time.sleep(5)

# 4. Verify config.py is updated inside the container
print("[4/5] Kiểm tra config.py trong container...")
run_cmd('docker exec dafa_glass_backend head -10 /app/client_automation/config.py')

# 5. Start tool and test
print("[5/5] Khởi động tool mới...")
run_cmd('curl -s -X POST "http://127.0.0.1:3007/api/v1/seeding/tool/start" -H "Content-Type: application/json" -d \'{"platform": "facebook", "show_browser": false}\'')

time.sleep(5)

# Check logs to confirm tool connects successfully
run_cmd('docker logs --tail 20 dafa_glass_backend 2>&1')

ssh.close()
