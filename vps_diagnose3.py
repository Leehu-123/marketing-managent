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

# Check docker-compose.yml files for both containers
run_cmd('find /var/www -name "docker-compose.yml" -exec echo "--- FILE: {} ---" \; -exec cat {} \; 2>/dev/null')

# Check Dockerfile locations
run_cmd('find /var/www -name "Dockerfile" -exec echo "--- FILE: {} ---" \; -exec head -5 {} \; 2>/dev/null')

# Check where dakifa-marketing app lives
run_cmd('ls -la /var/www/dakifa-marketing/')

# Check which app has seeding routes
run_cmd('grep -rl "seeding" /var/www/dakifa-marketing/ --include="*.py" | head -10')
run_cmd('grep -rl "seeding" /var/www/marketing-management/backend/ --include="*.py" | head -10')

# Check the old dafa_glass_backend container's docker-compose
run_cmd('docker inspect dakifa_backend --format "{{.Config.WorkingDir}}"')
run_cmd('docker inspect dafa_glass_backend --format "{{.Config.WorkingDir}}"')

# Check tool/status and campaigns on port 3007 (dafa_glass_backend = the working one)
run_cmd('curl -s "http://127.0.0.1:3007/api/v1/seeding/tool/status"')

# Check docker logs on port 3007 container for tool/fetch activity
run_cmd('docker logs --tail 20 dafa_glass_backend 2>&1')

ssh.close()
