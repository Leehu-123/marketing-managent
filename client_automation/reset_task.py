import sqlite3

conn = sqlite3.connect('../backend/dafa_glass.db')
c = conn.cursor()
c.execute("UPDATE seeding_tasks SET status='pending', error_message=NULL WHERE id=6")
conn.commit()
conn.close()
