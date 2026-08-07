import paramiko
import os

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'
base_dir = r"d:\Antigrapvity\Marketing manager"

backend_zip = os.path.join(base_dir, "backend_deploy.zip")
client_zip = os.path.join(base_dir, "client_automation_deploy.zip")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting...")
    client.connect(hostname=host, username=user, password=password, timeout=10)
    
    sftp = client.open_sftp()
    print("Uploading backend_deploy.zip...")
    sftp.put(backend_zip, '/root/backend_deploy.zip')
    
    print("Uploading client_automation_deploy.zip...")
    sftp.put(client_zip, '/root/client_automation_deploy.zip')
    
    sftp.close()
    print("Upload completed.")
finally:
    client.close()
