import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

commands = [
    "htpasswd -b -c /etc/squid/passwd dafa DafaGlass123",
    """cat << 'EOF' > /etc/squid/squid.conf
auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwd
auth_param basic children 5
auth_param basic realm Squid proxy-caching web server
auth_param basic credentialsttl 2 hours
auth_param basic casesensitive off

acl authenticated proxy_auth REQUIRED
http_access allow authenticated
http_access deny all

http_port 3128

# Bỏ qua IPv6 để tránh lỗi kết nối
dns_v4_first on

# Ẩn IP thật qua proxy
forwarded_for delete
request_header_access Via deny all
request_header_access X-Forwarded-For deny all
EOF""",
    "systemctl restart squid",
    "ufw allow 3128/tcp"
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=user, password=password, timeout=10)
    for cmd in commands:
        print(f"Executing: {cmd[:50]}...")
        stdin, stdout, stderr = client.exec_command(cmd)
        
        exit_status = stdout.channel.recv_exit_status() 
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        
        if out: print("OUT:", out[:200])
        if err: print("ERR:", err[:200])
        print("Status:", exit_status)
        print("-" * 40)
finally:
    client.close()
