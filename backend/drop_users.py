import sqlite3

conn = sqlite3.connect('dafa_glass.db')
cursor = conn.cursor()

try:
    cursor.execute("DROP TABLE users")
    conn.commit()
    print("Table 'users' dropped successfully.")
except Exception as e:
    print(f"Error dropping table: {e}")

conn.close()
