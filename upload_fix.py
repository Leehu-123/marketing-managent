import paramiko
import os

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'
local_file = r"d:\Antigrapvity\Marketing manager\backend\templates\seeding_campaigns.html"
remote_file = "/var/www/dafaglass/templates/seeding_campaigns.html"

try:
    transport = paramiko.Transport((host, 22))
    transport.connect(username=user, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    print(f"Uploading {local_file} to {remote_file}")
    sftp.put(local_file, remote_file)
    print("Upload successful!")
    
    sftp.close()
    transport.close()
except Exception as e:
    print("Error:", e)
