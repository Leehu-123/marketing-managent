import paramiko

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

commands = [
    "ps -f -p 1272422,1204846,93622,1209670,1272425",
    "ls -l /var/www"
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=user, password=password, timeout=10)
    for cmd in commands:
        print(f"--- {cmd} ---")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8'))
        err = stderr.read().decode('utf-8')
        if err:
            print("STDERR:", err)
finally:
    client.close()
