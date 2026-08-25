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

# 1. Check docker logs for the tool subprocess
run_cmd('docker logs --tail 60 dakifa_backend 2>&1')

# 2. Check campaign statuses and task statuses in DB
run_cmd('docker exec dakifa_backend python3 -c "from app.core.database import SessionLocal; from app.models.seeding_campaign import SeedingCampaign; from app.models.seeding_task import SeedingTask; db=SessionLocal(); camps=db.query(SeedingCampaign).all(); print(\'CAMPAIGNS:\'); [print(f\'  id={c.id} name={c.name} status={c.status} type={c.campaign_type}\') for c in camps]; tasks=db.query(SeedingTask).all(); print(f\'\\nTASKS ({len(tasks)} total):\'); from collections import Counter; status_counts=Counter(t.status for t in tasks); print(f\'  Status counts: {dict(status_counts)}\'); [print(f\'  id={t.id} campaign_id={t.campaign_id} status={t.status} account_id={t.account_id}\') for t in tasks[:20]]"')

# 3. Check if tool process is running inside docker
run_cmd('docker exec dakifa_backend ps aux')

# 4. Test fetch endpoint directly
run_cmd('curl -s http://127.0.0.1:3006/api/v1/seeding/tasks/fetch?platform=facebook&limit=5')

ssh.close()
