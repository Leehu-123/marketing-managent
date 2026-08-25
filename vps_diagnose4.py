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

# Test: start tool and check logs
print("[1] Khởi động tool trên port 3007...")
run_cmd('curl -s -X POST "http://127.0.0.1:3007/api/v1/seeding/tool/start" -H "Content-Type: application/json" -d \'{"platform": "facebook", "show_browser": false}\'')

import time
time.sleep(5)

# Check docker logs for tool output
print("[2] Kiểm tra logs container...")
run_cmd('docker logs --tail 30 dafa_glass_backend 2>&1')

# Check if the tool process is running inside the container
print("[3] Kiểm tra config.py trong container...")
run_cmd('docker exec dafa_glass_backend cat /app/client_automation/config.py')

ssh.close()
