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

print("[1/3] Đang nâng cấp package 9router qua npm...")
run_cmd('npm install -g 9router@latest')

print("[2/3] Đang khởi động lại dịch vụ 9router...")
run_cmd('systemctl restart 9router')

print("[3/3] Kiểm tra phiên bản mới và trạng thái dịch vụ...")
run_cmd('npm list -g --depth=0')
run_cmd('systemctl status 9router')

ssh.close()
