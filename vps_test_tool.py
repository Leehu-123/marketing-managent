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

run_cmd('curl -X POST http://127.0.0.1:3006/api/v1/seeding/tool/start -H "Content-Type: application/json" -d "{\\"platform\\": \\"facebook\\", \\"show_browser\\": false}"')
run_cmd('curl http://127.0.0.1:3006/api/v1/seeding/tool/status')
ssh.close()
