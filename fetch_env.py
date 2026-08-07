import paramiko

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=host, username=user, password=password)

sftp = client.open_sftp()
sftp.get('/var/www/dafaglass/.env', 'vps_env.txt')
sftp.close()
client.close()
print("Downloaded .env")
