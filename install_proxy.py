import paramiko
import time

host = '45.117.177.80'
user = 'root'
password = 'Y3pKPk3C4rH4EWe1'

commands = [
    "apt-get update",
    "apt-get install -y squid apache2-utils",
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
        
        # Wait for command to finish
        exit_status = stdout.channel.recv_exit_status() 
        
        out = stdout.read().decode('utf-8', errors='ignore').strip()
        err = stderr.read().decode('utf-8', errors='ignore').strip()
        
        if out: print("OUT:", out)
        if err: print("ERR:", err)
        print("Status:", exit_status)
        print("-" * 40)
finally:
    client.close()
