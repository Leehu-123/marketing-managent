import sqlite3
import os

db_paths = ["dafa_glass.db", "dafa_saas.db"]

for db_path in db_paths:
    if not os.path.exists(db_path):
        continue
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE seeding_accounts ADD COLUMN two_fa_secret TEXT DEFAULT NULL")
        conn.commit()
        print(f"[OK] Đã thêm cột two_fa_secret vào {db_path}")
    except Exception as e:
        print(f"[SKIP] {db_path}: {e}")
        
    conn.close()
