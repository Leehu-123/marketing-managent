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

run_cmd('cat /etc/systemd/system/9router.service')
run_cmd('ls -la /root/.9router/')
run_cmd('npm list -g --depth=0 || true')
run_cmd('pnpm list -g || true')
run_cmd('bun pm ls -g || true')
ssh.close()
