import paramiko
import sys

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=user, password=password, timeout=10)
    stdin, stdout, stderr = client.exec_command("pkill -9 -f 'pip install'")
    print(stdout.read().decode('utf-8'))
finally:
    client.close()
