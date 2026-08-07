import sqlite3

def upgrade():
    conn = sqlite3.connect("d:/Antigrapvity/Marketing manager/backend/dafa_glass.db")
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE seeding_campaigns ADD COLUMN account_ids TEXT")
        print("Successfully added account_ids column to seeding_campaigns")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column account_ids already exists")
        else:
            print(f"Error: {e}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade()
