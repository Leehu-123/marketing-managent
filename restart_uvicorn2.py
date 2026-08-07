import paramiko
import time

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

commands = [
    "pkill -9 -f uvicorn",
    "sleep 2",
    "bash -c 'nohup /var/www/dafaglass/venv/bin/python3 /var/www/dafaglass/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir /var/www/dafaglass > /var/www/dafaglass/uvicorn.log 2>&1 &'",
    "sleep 3",
    "ps -ef | grep uvicorn",
    "tail -n 10 /var/www/dafaglass/uvicorn.log"
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting to kill and restart uvicorn...")
    client.connect(hostname=host, username=user, password=password, timeout=10)
    for cmd in commands:
        print(f"--- Running: {cmd[:50]}... ---")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        if out: print(out)
        if err: print(f"STDERR: {err}")
finally:
    client.close()
