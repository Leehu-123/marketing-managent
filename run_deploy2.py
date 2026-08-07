import paramiko
import sys

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

commands = [
    # Backup
    "cp -a /var/www/dafaglass /var/www/dafaglass_backup_$(date +%F_%H%M%S)",
    
    # Unzip backend silently
    "unzip -o -q /root/backend_deploy.zip -d /var/www/dafaglass/",
    
    # Create client_automation and unzip silently
    "mkdir -p /var/www/client_automation",
    "unzip -o -q /root/client_automation_deploy.zip -d /var/www/client_automation/",
    
    # Backend dependencies
    "bash -c 'cd /var/www/dafaglass && source venv/bin/activate && pip install -r requirements.txt > /tmp/pip_backend.log 2>&1'",
    
    # Fix MOCK_AI in .env if needed
    "python3 -c \"import os; p='/var/www/dafaglass/.env'; content = open(p).read() if os.path.exists(p) else ''; content = content.replace('MOCK_AI=true', 'MOCK_AI=false').replace('MOCK_AI=True', 'MOCK_AI=false'); open(p, 'w').write(content)\"",
    
    # Client automation setup
    "bash -c 'cd /var/www/client_automation && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt > /tmp/pip_client.log 2>&1 && playwright install chromium > /tmp/pw1.log 2>&1 && playwright install-deps > /tmp/pw2.log 2>&1'",
    
    # Adjust path in seeding.py
    "python3 -c \"import sys; p='/var/www/dafaglass/app/api/v1/seeding.py'; c=open(p).read(); c=c.replace('client_dir = os.path.join(project_root, \\\"client_automation\\\")', 'client_dir = \\\"/var/www/client_automation\\\"'); open(p, 'w').write(c)\"",
    
    # Kill uvicorn (it will be restarted)
    "pkill -f uvicorn || echo 'uvicorn not running'"
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting for deployment execution...")
    client.connect(hostname=host, username=user, password=password, timeout=10)
    for cmd in commands:
        print(f"--- Running: {cmd[:50]}... ---")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        # Wait for the command to finish
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        
        if out:
            print(out)
        if err:
            print(f"STDERR: {err}")
        
        if exit_status != 0:
            print(f"Command failed with exit status {exit_status}")
finally:
    client.close()
