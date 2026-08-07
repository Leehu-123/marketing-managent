import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Đang kết nối VPS...")
    client.connect(hostname=host, username=user, password=password, timeout=10)
    
    print("\n1. Đang kill tiến trình client_automation cũ...")
    client.exec_command("pkill -9 -f client_automation/main.py")
    
    print("\n2. Đang chạy thử client_automation và lấy 50 dòng log đầu tiên...")
    # Run the tool and exit after 1 iteration (using --once if we have it, or just timeout)
    # The client tool polls continuously, so we run it with timeout 15s to get logs.
    cmd = "timeout 30 /var/www/client_automation/venv/bin/python /var/www/client_automation/main.py --platform facebook"
    stdin, stdout, stderr = client.exec_command(cmd)
    
    # Wait for completion or timeout
    stdout.channel.recv_exit_status()
    
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    
    print("\n--- STDOUT ---")
    print(out)
    
    print("\n--- STDERR ---")
    print(err)
        
finally:
    client.close()
