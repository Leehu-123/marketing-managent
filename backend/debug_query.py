import sqlite3

conn = sqlite3.connect('dafa_glass.db')
c = conn.cursor()
# Kiểm tra chính xác query mà code đang chạy
c.execute("""
    SELECT provider_name, api_key, base_url, model_name, is_active 
    FROM ai_settings 
    WHERE is_active = 1 
    AND provider_name NOT LIKE '%(Image)%'
    AND provider_name NOT LIKE '%(Research)%'
""")
rows = c.fetchall()
with open("result2.txt", "w", encoding="utf-8") as f:
    for row in rows:
        f.write(str(row) + "\n")
    if not rows:
        f.write("NO ROWS FOUND!\n")
        # Show all active
        c.execute("SELECT provider_name, api_key, is_active FROM ai_settings WHERE is_active = 1")
        for row in c.fetchall():
            f.write(f"Active: {row}\n")
conn.close()
