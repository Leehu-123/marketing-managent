import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=host, username=user, password=password)

cmd = """PYTHONPATH=/var/www/dafaglass /var/www/dafaglass/venv/bin/python -c "
import sys, sqlite3; sys.path.append('/var/www/dafaglass')

conn = sqlite3.connect('/var/www/dafaglass/dafa_glass.db')
c = conn.cursor()
c.execute(\\"SELECT id, platform, is_active, url, username, access_token, refresh_token FROM integration_settings\\")
for r in c.fetchall():
    print('SETTING:', r[0], r[1], r[2], r[3], r[4], 'pass_len:', len(r[5]) if r[5] else 0)
conn.close()
" """

stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='ignore'))
print(stderr.read().decode('utf-8', errors='ignore'))

client.close()
