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

# Step 1: Stop old dafa_glass_backend container (from /var/www/dafaglass)
print("=== STEP 1: Stop & remove conflicting old container ===")
run_cmd('docker stop dafa_glass_backend && docker rm dafa_glass_backend')

# Step 2: Now start the new container from marketing-management
print("=== STEP 2: Start new container ===")
run_cmd('cd /var/www/marketing-management/backend && docker compose up -d')

time.sleep(3)

# Step 3: Verify container is running
print("=== STEP 3: Verify container ===")
run_cmd('docker ps')

# Step 4: Test seeding endpoints
print("=== STEP 4: Test seeding endpoints ===")
run_cmd('curl -s http://127.0.0.1:3007/api/v1/seeding/tool/status')

# Step 5: Start tool and check
print("=== STEP 5: Start tool ===")
run_cmd('curl -s -X POST "http://127.0.0.1:3007/api/v1/seeding/tool/start" -H "Content-Type: application/json" -d \'{"platform": "facebook", "show_browser": false}\'')

time.sleep(8)

# Step 6: Check logs to see if tool connects to backend successfully  
print("=== STEP 6: Check tool connection logs ===")
run_cmd('docker logs --tail 25 dafa_glass_backend 2>&1')

# Step 7: Verify Nginx proxy still works
print("=== STEP 7: Verify Nginx ===")
run_cmd('curl -s http://127.0.0.1/api/v1/seeding/tool/status')

ssh.close()
print("\nAll done!", flush=True)
