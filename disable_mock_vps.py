import paramiko

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=host, username=user, password=password)

# Replace MOCK_*=True with MOCK_*=False in .env
commands = [
    "sed -i 's/MOCK_ANALYTICS=true/MOCK_ANALYTICS=false/gI' /var/www/dafaglass/.env",
    "sed -i 's/MOCK_META=true/MOCK_META=false/gI' /var/www/dafaglass/.env",
    "systemctl restart dafaglass"
]

for cmd in commands:
    client.exec_command(cmd)

client.close()
print("Disabled MOCK on VPS.")
