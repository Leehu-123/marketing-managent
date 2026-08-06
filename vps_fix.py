import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('45.117.177.80', username='root', password='Y3pKPk3C4rH4EWe1')

def run_cmd(cmd):
    print(f'=== CMD: {cmd} ===')
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode('utf-8'))
    print(stderr.read().decode('utf-8'))

# 1. Update SQLite DB schema on VPS using alter statements or create_all
py_code = """
import sqlite3
conn = sqlite3.connect('/var/www/marketing-management/backend/dafa_glass.db')
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
print("DB Migration Complete!")
"""

# Write script to VPS and run
sftp = ssh.open_sftp()
with sftp.file('/root/migrate_db.py', 'w') as f:
    f.write(py_code)
sftp.close()

run_cmd('python3 /root/migrate_db.py')
run_cmd('docker restart dafa_glass_backend')
run_cmd('systemctl restart nginx')

ssh.close()
