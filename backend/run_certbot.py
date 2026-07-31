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
    
    cmd = "certbot --nginx -d warehouse.ldhuy.name.vn --non-interactive --agree-tos -m ldhuy@ldhuy.name.vn"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    print("STDOUT:", stdout.read().decode('utf-8', errors='ignore'))
    print("STDERR:", stderr.read().decode('utf-8', errors='ignore'))
    ssh.close()
except Exception as e:
    print("Error:", e)
