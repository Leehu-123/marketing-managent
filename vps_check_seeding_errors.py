import paramiko
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('45.117.177.80', username='root', password='Y3pKPk3C4rH4EWe1')

def run_cmd(cmd, timeout=60):
    print(f'\n=== CMD: {cmd} ===', flush=True)
    chan = ssh.get_transport().open_session()
    chan.settimeout(timeout)
    chan.exec_command(cmd)
    while True:
        if chan.recv_ready():
            data = chan.recv(8192).decode('utf-8', errors='ignore')
            print(data, end='', flush=True)
        if chan.recv_stderr_ready():
            data = chan.recv_stderr(8192).decode('utf-8', errors='ignore')
            print(f'STDERR: {data}', end='', flush=True)
        if chan.exit_status_ready():
            while chan.recv_ready():
                print(chan.recv(8192).decode('utf-8', errors='ignore'), end='', flush=True)
            while chan.recv_stderr_ready():
                print(chan.recv_stderr(8192).decode('utf-8', errors='ignore'), end='', flush=True)
            break
        time.sleep(0.1)
    print(f'\nExit code: {chan.recv_exit_status()}', flush=True)

# 1. Container status
print("=== STEP 1: Container status ===")
run_cmd('docker ps | grep dafa_glass')

# 2. Docker logs (last 200 lines)
print("=== STEP 2: Docker logs (last 200 lines) ===")
run_cmd('docker logs --tail 200 dafa_glass_backend 2>&1')

# 3. Tool status
print("=== STEP 3: Tool status ===")
run_cmd('curl -s http://127.0.0.1:3007/api/v1/seeding/tool/status')

# 4. Query DB for campaign/task status - write a temp script
db_script = r"""
import sqlite3
conn = sqlite3.connect('/app/dafa_glass.db')
c = conn.cursor()
print('=== CAMPAIGNS ===')
for row in c.execute('SELECT id, name, status, campaign_type FROM seeding_campaigns ORDER BY id DESC LIMIT 20'):
    print(f'  id={row[0]} | name={row[1]} | status={row[2]} | type={row[3]}')
print()
print('=== TASKS BY STATUS ===')
for row in c.execute('SELECT status, COUNT(*) FROM seeding_tasks GROUP BY status'):
    print(f'  {row[0]}: {row[1]}')
print()
print('=== FAILED TASKS (last 20) ===')
for row in c.execute("SELECT id, campaign_id, task_type, status, error_message FROM seeding_tasks WHERE status='failed' ORDER BY id DESC LIMIT 20"):
    print(f'  task_id={row[0]} | camp_id={row[1]} | type={row[2]} | error={row[4][:200] if row[4] else "None"}')
conn.close()
"""
# Write script to container, then run it
run_cmd(f"docker exec dafa_glass_backend bash -c 'cat > /tmp/check_db.py << \"PYEOF\"\n{db_script}\nPYEOF\npython3 /tmp/check_db.py'")

ssh.close()
print("\nDone!", flush=True)
