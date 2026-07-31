import sqlite3
import os

db_path = "f:/Antigrapvity/SEO Website DAFA web/backend/dafa_glass.db"
conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys=off;")
conn.commit()

cursor = conn.cursor()

# 1. Rename old table
cursor.execute("ALTER TABLE content_plans RENAME TO _content_plans_old;")

# 2. Create new table without NOT NULL constraint on campaign_id
cursor.execute("""
CREATE TABLE content_plans (
    id INTEGER NOT NULL, 
    campaign_id INTEGER, 
    title VARCHAR NOT NULL, 
    platform VARCHAR NOT NULL, 
    format VARCHAR NOT NULL, 
    scheduled_at DATETIME NOT NULL, 
    status VARCHAR NOT NULL, 
    created_at DATETIME NOT NULL, 
    content_pillar VARCHAR DEFAULT 'Khác', 
    PRIMARY KEY (id), 
    FOREIGN KEY(campaign_id) REFERENCES campaigns (id)
);
""")

# 3. Copy data
cursor.execute("""
INSERT INTO content_plans (id, campaign_id, title, platform, format, scheduled_at, status, created_at, content_pillar)
SELECT id, campaign_id, title, platform, format, scheduled_at, status, created_at, content_pillar
FROM _content_plans_old;
""")

# 4. Drop old table
cursor.execute("DROP TABLE _content_plans_old;")

# Recreate index
cursor.execute("CREATE INDEX ix_content_plans_id ON content_plans (id);")

conn.commit()
conn.execute("PRAGMA foreign_keys=on;")
conn.close()

print("Migration completed.")
