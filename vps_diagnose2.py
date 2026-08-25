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
    err = stderr.read().decode('utf-8', errors='ignore')
    print(out)
    if err:
        print(f'STDERR: {err}')

# Which container is running?
run_cmd('docker ps')

# Check both containers
run_cmd('curl -s "http://127.0.0.1:3006/api/v1/seeding/tasks/fetch?platform=facebook&limit=5"')
run_cmd('curl -s "http://127.0.0.1:3007/api/v1/seeding/tasks/fetch?platform=facebook&limit=5"')

# Check campaign status via API
run_cmd('curl -s "http://127.0.0.1:3006/api/v1/seeding/campaigns" -H "Authorization: Bearer test"')
run_cmd('curl -s "http://127.0.0.1:3007/api/v1/seeding/campaigns" -H "Authorization: Bearer test"')

# Check tool status
run_cmd('curl -s "http://127.0.0.1:3006/api/v1/seeding/tool/status"')
run_cmd('curl -s "http://127.0.0.1:3007/api/v1/seeding/tool/status"')

# Check if the web interface is dakifa or dafa_glass
run_cmd('curl -s http://127.0.0.1:3006/ -o /dev/null -w "%{http_code} %{redirect_url}"')
run_cmd('curl -s http://127.0.0.1:3007/ -o /dev/null -w "%{http_code} %{redirect_url}"')

# Check what Nginx proxies to  
run_cmd('cat /etc/nginx/sites-enabled/default 2>/dev/null || cat /etc/nginx/conf.d/*.conf 2>/dev/null || cat /etc/nginx/nginx.conf')

ssh.close()
