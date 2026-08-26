import sqlite3
import sys

conn = sqlite3.connect('/app/dafa_glass.db')
c = conn.cursor()

# Reset Campaign #4 to pending
c.execute("UPDATE seeding_campaigns SET status = 'pending' WHERE id = 4")
print(f"Updated campaign 4 to pending (rows: {c.rowcount})")

# Reset failed tasks in Campaign #4 to pending
c.execute("UPDATE seeding_tasks SET status = 'pending', error_message = NULL WHERE campaign_id = 4")
print(f"Updated tasks in campaign 4 to pending (rows: {c.rowcount})")

conn.commit()
conn.close()
print("Reset completed successfully!")
