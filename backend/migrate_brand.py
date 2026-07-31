import sqlite3
import os
from pathlib import Path

db_path = Path("f:/Antigrapvity/SEO Website DAFA web/backend/dafa_glass.db")

if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    columns = ["hotline", "email", "website", "address"]
    for col in columns:
        try:
            cursor.execute(f"ALTER TABLE brand_profiles ADD COLUMN {col} VARCHAR;")
            print(f"Added {col}")
        except Exception as e:
            print(f"Error {col}:", e)
            
    conn.commit()
    conn.close()
    print("Migration finished")
else:
    print("DB not found")
