import paramiko

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

commands = [
    "echo '--- OS INFO ---'",
    "cat /etc/os-release | grep PRETTY_NAME",
    "echo '\\n--- MEMORY ---'",
    "free -h",
    "echo '\\n--- DISK ---'",
    "df -h /",
    "echo '\\n--- TOP PROCESSES ---'",
    "top -b -n 1 | head -n 15",
    "echo '\\n--- DOCKER CONTAINERS ---'",
    "docker ps -a || echo 'Docker not installed'",
    "echo '\\n--- LISTENING PORTS ---'",
    "netstat -tulpn | grep LISTEN || ss -tulpn | grep LISTEN"
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=user, password=password, timeout=10)
    for cmd in commands:
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8'))
        err = stderr.read().decode('utf-8')
        if err:
            print("STDERR:", err)
finally:
    client.close()
