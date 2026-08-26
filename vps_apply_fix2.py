import paramiko
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('45.117.177.80', username='root', password='Y3pKPk3C4rH4EWe1')

def run_cmd(cmd, timeout=120):
    print(f'=== CMD: {cmd} ===')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    print(out)
    if err:
        print(f'STDERR: {err}')

# Step 1: Stop old tool
print("=== STEP 1: Stop tool ===")
run_cmd('curl -s -X POST http://127.0.0.1:3007/api/v1/seeding/tool/stop')

# Step 2: Git pull
print("=== STEP 2: Git pull ===")
run_cmd('cd /var/www/marketing-management && git pull')

# Step 3: Update config.py directly on VPS (since volume mount shares client_automation)
print("=== STEP 3: Check updated config.py ===")
run_cmd('head -10 /var/www/marketing-management/client_automation/config.py')

# Step 4: Rebuild container
print("=== STEP 4: Rebuild Docker container ===")
run_cmd('cd /var/www/marketing-management/backend && docker compose up -d --build', timeout=180)

ssh.close()
print("\nDone!")
