import paramiko
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('45.117.177.80', username='root', password='Y3pKPk3C4rH4EWe1')

def run_cmd(cmd, timeout=300):
    print(f'\n=== CMD: {cmd} ===', flush=True)
    chan = ssh.get_transport().open_session()
    chan.settimeout(timeout)
    chan.exec_command(cmd)
    while True:
        if chan.recv_ready():
            data = chan.recv(4096).decode('utf-8', errors='ignore')
            print(data, end='', flush=True)
        if chan.recv_stderr_ready():
            data = chan.recv_stderr(4096).decode('utf-8', errors='ignore')
            print(f'STDERR: {data}', end='', flush=True)
        if chan.exit_status_ready():
            while chan.recv_ready():
                print(chan.recv(4096).decode('utf-8', errors='ignore'), end='', flush=True)
            while chan.recv_stderr_ready():
                print(chan.recv_stderr(4096).decode('utf-8', errors='ignore'), end='', flush=True)
            break
        time.sleep(0.1)
    print(f'\nExit code: {chan.recv_exit_status()}', flush=True)

print("=== STEP 1: Git force pull ===")
run_cmd('cd /var/www/marketing-management && git stash && git pull')

print("=== STEP 2: Stop & remove container to ensure clean port bind ===")
run_cmd('cd /var/www/marketing-management/backend && docker compose down')

print("=== STEP 3: Start new container (on port 3007) ===")
run_cmd('cd /var/www/marketing-management/backend && docker compose up -d')

time.sleep(3)

print("=== STEP 4: Verify container ports ===")
run_cmd('docker ps | grep dafa_glass_backend')

print("=== STEP 5: Test seeding tool start ===")
run_cmd('curl -s -X POST "http://127.0.0.1:3007/api/v1/seeding/tool/start" -H "Content-Type: application/json" -d \'{"platform": "facebook", "show_browser": false}\'')

time.sleep(8)

print("=== STEP 6: Check tool connection logs ===")
run_cmd('docker logs --tail 25 dafa_glass_backend 2>&1')

print("=== STEP 7: Verify Nginx ===")
run_cmd('curl -s http://127.0.0.1/api/v1/seeding/tool/status')

ssh.close()
print("\nAll done!", flush=True)
