import paramiko
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('45.117.177.80', username='root', password='Y3pKPk3C4rH4EWe1')

# Upload the check script
sftp = ssh.open_sftp()
sftp.put(r'd:\Antigravity\Marketing manager\check_db_remote.py', '/tmp/check_db_remote.py')
sftp.close()

# Run it inside the container
stdin, stdout, stderr = ssh.exec_command('docker cp /tmp/check_db_remote.py dafa_glass_backend:/tmp/check_db_remote.py && docker exec dafa_glass_backend python3 /tmp/check_db_remote.py', timeout=30)
out = stdout.read().decode('utf-8', errors='ignore')
err = stderr.read().decode('utf-8', errors='ignore')
print(out)
if err:
    print('STDERR:', err)

ssh.close()
