"""
Idempotent migration: add creative image/post fields used by DAFA AI ad composer.
Run: py migrate_creative_fields.py
"""
import os
import sqlite3

DB_PATHS = ["dafa_glass.db", "dafa_saas.db"]
POST_COLUMNS = {
    "caption": "TEXT DEFAULT NULL",
    "headline": "VARCHAR(180) DEFAULT NULL",
    "subheadline": "VARCHAR(250) DEFAULT NULL",
    "cta": "VARCHAR(180) DEFAULT NULL",
    "benefits_json": "TEXT DEFAULT NULL",
    "background_prompt": "TEXT DEFAULT NULL",
    "template_key": "VARCHAR(80) DEFAULT NULL",
    "product_slug": "VARCHAR(120) DEFAULT NULL",
    "aspect_ratio": "VARCHAR(20) DEFAULT '1:1' NOT NULL",
}

for db_path in DB_PATHS:
    if not os.path.exists(db_path):
        print(f"[SKIP] {db_path} không tồn tại")
        continue
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "posts" not in tables:
        print(f"[SKIP] {db_path}: chưa có bảng posts")
        conn.close()
        continue
    cols = [c[1] for c in cur.execute("PRAGMA table_info(posts)").fetchall()]
    for col, ddl in POST_COLUMNS.items():
        if col in cols:
            print(f"[OK] {db_path}: posts.{col} đã tồn tại")
        else:
            cur.execute(f"ALTER TABLE posts ADD COLUMN {col} {ddl}")
            print(f"[DONE] {db_path}: thêm posts.{col}")
    conn.commit()
    conn.close()

os.makedirs(os.path.join("uploads", "brand", "products"), exist_ok=True)
print("[DONE] Migration creative fields hoàn tất")
