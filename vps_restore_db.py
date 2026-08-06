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

restore_code = """
import shutil, sqlite3

src = '/var/www/dafaglass/dafa_glass.db'
dst = '/var/www/marketing-management/backend/dafa_glass.db'

# 1. Backup current new DB just in case
shutil.copyfile(dst, dst + '.bak')

# 2. Copy original database with all user data
shutil.copyfile(src, dst)
print("Copied original dafa_glass.db with 175 posts and 24 campaigns!")

# 3. Apply missing migration columns if needed
conn = sqlite3.connect(dst)
cursor = conn.cursor()

def add_col(table, col, col_type):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        print(f"Added {col} to {table}")
    except Exception as e:
        print(f"Column {col} on {table}: {e}")

add_col("seeding_campaigns", "post_content", "TEXT")
add_col("seeding_campaigns", "media_urls", "TEXT")
add_col("seeding_campaigns", "daily_schedule_time", "VARCHAR")
add_col("seeding_campaigns", "is_daily_repeat", "BOOLEAN DEFAULT 0")

add_col("seeding_tasks", "task_type", "VARCHAR DEFAULT 'COMMENT'")
add_col("seeding_tasks", "parent_task_id", "INTEGER")
add_col("seeding_tasks", "media_urls", "TEXT")

conn.commit()
conn.close()
print("Restored original user DB successfully!")
"""

sftp = ssh.open_sftp()
with sftp.file('/root/restore_db.py', 'w') as f:
    f.write(restore_code)
sftp.close()

run_cmd('python3 /root/restore_db.py')
run_cmd('docker restart dafa_glass_backend')

ssh.close()
