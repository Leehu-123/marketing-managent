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
            # Drain remaining
            while chan.recv_ready():
                print(chan.recv(4096).decode('utf-8', errors='ignore'), end='', flush=True)
            while chan.recv_stderr_ready():
                print(chan.recv_stderr(4096).decode('utf-8', errors='ignore'), end='', flush=True)
            break
        time.sleep(0.1)
    print(f'\nExit code: {chan.recv_exit_status()}', flush=True)

# Step 1: Stop old tool  
run_cmd('curl -s -X POST http://127.0.0.1:3007/api/v1/seeding/tool/stop')

# Step 2: Git pull
run_cmd('cd /var/www/marketing-management && git stash && git pull')

# Step 3: Verify config.py updated
run_cmd('head -10 /var/www/marketing-management/client_automation/config.py')

# Step 4: Rebuild Docker
run_cmd('cd /var/www/marketing-management/backend && docker compose up -d --build')

ssh.close()
print("\nAll done!", flush=True)
