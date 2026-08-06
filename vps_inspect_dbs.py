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

inspect_code = """
import sqlite3, os

db_paths = [
    '/var/www/marketing-management/backend/dafa_glass.db',
    '/var/www/dafaglass/dafa_glass.db',
    '/var/www/dafaglass/dafa_saas.db',
    '/root/dafa_glass.db'
]

for p in db_paths:
    if os.path.exists(p):
        size = os.path.getsize(p)
        print(f"\\nDB: {p} (Size: {size} bytes)")
        try:
            conn = sqlite3.connect(p)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"  Tables: {tables}")
            for t in ['users', 'seeding_accounts', 'seeding_campaigns', 'seeding_tasks', 'campaigns', 'posts']:
                if t in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {t}")
                    count = cursor.fetchone()[0]
                    print(f"    Table {t}: {count} rows")
            conn.close()
        except Exception as e:
            print(f"  Error: {e}")
"""

sftp = ssh.open_sftp()
with sftp.file('/root/inspect_dbs.py', 'w') as f:
    f.write(inspect_code)
sftp.close()

run_cmd('python3 /root/inspect_dbs.py')
ssh.close()
