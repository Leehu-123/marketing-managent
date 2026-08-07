import paramiko

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

commands = [
    # Backup
    "cp -a /var/www/dafaglass /var/www/dafaglass_backup_$(date +%F_%H%M%S)",
    
    # Unzip backend
    "unzip -o /root/backend_deploy.zip -d /var/www/dafaglass/",
    
    # Create client_automation and unzip
    "mkdir -p /var/www/client_automation",
    "unzip -o /root/client_automation_deploy.zip -d /var/www/client_automation/",
    
    # Backend dependencies
    "bash -c 'cd /var/www/dafaglass && source venv/bin/activate && pip install -r requirements.txt'",
    
    # Fix MOCK_AI in .env if needed
    "python3 -c \"import os; content = open('/var/www/dafaglass/.env').read(); content = content.replace('MOCK_AI=true', 'MOCK_AI=false').replace('MOCK_AI=True', 'MOCK_AI=false'); open('/var/www/dafaglass/.env', 'w').write(content)\"",
    
    # Client automation setup
    "bash -c 'cd /var/www/client_automation && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && playwright install chromium && playwright install-deps'",
    
    # Adjust path in seeding.py
    "python3 -c \"import sys; p='/var/www/dafaglass/app/api/v1/seeding.py'; c=open(p).read(); c=c.replace('client_dir = os.path.join(project_root, \\\"client_automation\\\")', 'client_dir = \\\"/var/www/client_automation\\\"'); open(p, 'w').write(c)\""
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting for deployment execution...")
    client.connect(hostname=host, username=user, password=password, timeout=10)
    for cmd in commands:
        print(f"--- Running: {cmd[:50]}... ---")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        # Wait for the command to finish and print output line by line
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        
        if out:
            print(out)
        if err:
            print(f"STDERR: {err}")
        
        if exit_status != 0:
            print(f"Command failed with exit status {exit_status}")
            break
finally:
    client.close()
