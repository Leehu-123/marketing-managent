"""
Script migration: Thêm cột content_pillars vào bảng campaigns.
Chạy: python run_migration.py
"""
import sqlite3
import os

# Tìm DB file
db_paths = ["dafa_glass.db", "dafa_saas.db"]

for db_path in db_paths:
    if not os.path.exists(db_path):
        print(f"[SKIP] {db_path} không tồn tại")
        continue
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Kiểm tra xem cột đã tồn tại chưa
    cols = [c[1] for c in cursor.execute("PRAGMA table_info(campaigns)").fetchall()]
    
    if "content_pillars" in cols:
        print(f"[OK] {db_path}: Cột 'content_pillars' đã tồn tại.")
    else:
        cursor.execute("ALTER TABLE campaigns ADD COLUMN content_pillars TEXT DEFAULT NULL")
        conn.commit()
        print(f"[DONE] {db_path}: Đã thêm cột 'content_pillars' thành công.")
    
    # Hiển thị cấu trúc bảng hiện tại
    cols = [c[1] for c in cursor.execute("PRAGMA table_info(campaigns)").fetchall()]
    print(f"  Các cột hiện tại: {cols}")
    
    conn.close()

# Tạo thư mục brand
brand_dir = os.path.join("uploads", "brand", "products")
os.makedirs(brand_dir, exist_ok=True)
print(f"\n[DONE] Đã tạo thư mục: {brand_dir}")
