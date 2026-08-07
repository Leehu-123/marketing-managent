import paramiko
import base64

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

script = """
import sqlite3
conn = sqlite3.connect('/var/www/dafaglass/dafa_glass.db')
cursor = conn.cursor()
try:
    cursor.execute('SELECT id, name FROM campaigns;')
    print("Campaigns:")
    for row in cursor.fetchall():
        print(row)
except Exception as e:
    print("Campaigns Error:", e)
    
try:
    cursor.execute('SELECT id, title FROM content_plans;')
    print("\\nPlans:")
    for row in cursor.fetchall():
        print(row)
except Exception as e:
    print("Plans Error:", e)
"""
encoded_script = base64.b64encode(script.encode('utf-8')).decode('utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=user, password=password, timeout=10)
    cmd = f'echo "{encoded_script}" | base64 -d | python3'
    stdin, stdout, stderr = client.exec_command(cmd)
    
    with open('output_db_campaigns.txt', 'wb') as f:
        f.write(stdout.read())
        f.write(b'\\nSTDERR:\\n')
        f.write(stderr.read())
finally:
    client.close()
