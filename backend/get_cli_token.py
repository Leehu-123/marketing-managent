import paramiko
import sys
sys.stdout.reconfigure(encoding="utf-8")

HOST = "45.117.177.80"
USER = "root"
PASSWORD = "Y3pKPk3C4rH4EWe1"

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)
    
    cmd = "cat /root/.9router/cli.json"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    print(stdout.read().decode('utf-8', errors='ignore'))
    ssh.close()
except Exception as e:
    print("Error:", e)
