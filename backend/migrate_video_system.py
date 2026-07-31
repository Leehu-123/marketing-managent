"""
Migration script for DAFA Glass Video Automation System
Adds all new tables for the 4-module video multi-channel system.
Run: py migrate_video_system.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dafa_glass.db')

MIGRATIONS = [
    # === User role upgrade ===
    """ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'admin'""",
    """ALTER TABLE users ADD COLUMN full_name TEXT""",
    """ALTER TABLE users ADD COLUMN telegram_id TEXT""",

    # === Video Channels ===
    """CREATE TABLE IF NOT EXISTS video_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        channel_type TEXT NOT NULL,
        platform TEXT NOT NULL,
        platform_channel_id TEXT,
        access_token TEXT,
        refresh_token TEXT,
        description TEXT,
        avatar_url TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",

    # === Video Plans ===
    """CREATE TABLE IF NOT EXISTS video_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER REFERENCES campaigns(id),
        channel_id INTEGER REFERENCES video_channels(id),
        title TEXT NOT NULL,
        content_line TEXT NOT NULL,
        vibe TEXT,
        target_platforms TEXT,
        optimal_post_time DATETIME,
        trending_audio TEXT,
        trending_hashtags TEXT,
        status TEXT DEFAULT 'Draft',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",

    # === Video Scripts ===
    """CREATE TABLE IF NOT EXISTS video_scripts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_plan_id INTEGER UNIQUE NOT NULL REFERENCES video_plans(id),
        total_duration_seconds INTEGER,
        hook_description TEXT,
        overall_notes TEXT,
        status TEXT DEFAULT 'Draft',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",

    # === Script Scenes ===
    """CREATE TABLE IF NOT EXISTS script_scenes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_script_id INTEGER NOT NULL REFERENCES video_scripts(id),
        scene_order INTEGER NOT NULL,
        start_time_sec REAL,
        end_time_sec REAL,
        duration_sec REAL,
        frame_type TEXT,
        setting TEXT,
        voiceover TEXT,
        on_screen_text TEXT,
        sound_effect TEXT,
        music_note TEXT,
        transition TEXT,
        editor_note TEXT,
        safe_zone_warning TEXT
    )""",

    # === Video Contents (uploaded originals) ===
    """CREATE TABLE IF NOT EXISTS video_contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_plan_id INTEGER UNIQUE REFERENCES video_plans(id),
        source_video_url TEXT,
        source_video_hash TEXT,
        thumbnail_url TEXT,
        duration_seconds INTEGER,
        resolution TEXT,
        file_size_mb REAL,
        cloud_storage_path TEXT,
        status TEXT DEFAULT 'Uploaded',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",

    # === Video Distributions (per-platform releases) ===
    """CREATE TABLE IF NOT EXISTS video_distributions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_content_id INTEGER NOT NULL REFERENCES video_contents(id),
        channel_id INTEGER REFERENCES video_channels(id),
        platform TEXT NOT NULL,
        post_type TEXT,
        processed_video_url TEXT,
        processed_hash TEXT,
        caption TEXT,
        hashtags TEXT,
        title TEXT,
        description TEXT,
        thumbnail_url TEXT,
        scheduled_at DATETIME,
        published_at DATETIME,
        platform_post_id TEXT,
        platform_post_url TEXT,
        status TEXT DEFAULT 'Pending',
        retry_count INTEGER DEFAULT 0,
        last_error TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",

    # === Video Metrics ===
    """CREATE TABLE IF NOT EXISTS video_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_distribution_id INTEGER NOT NULL REFERENCES video_distributions(id),
        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        saves INTEGER DEFAULT 0,
        avg_watch_time_sec REAL DEFAULT 0.0,
        retention_rate REAL DEFAULT 0.0,
        engagement_rate REAL DEFAULT 0.0,
        reach INTEGER DEFAULT 0,
        impressions INTEGER DEFAULT 0
    )""",

    # === Trend Cache ===
    """CREATE TABLE IF NOT EXISTS trend_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        category TEXT NOT NULL,
        keyword TEXT NOT NULL,
        volume INTEGER,
        growth_rate REAL,
        region TEXT DEFAULT 'VN',
        cached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME
    )""",

    # === Banned Keywords (Policy Checker) ===
    """CREATE TABLE IF NOT EXISTS banned_keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT NOT NULL,
        category TEXT,
        safe_alternative TEXT,
        platform TEXT DEFAULT 'all',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",

    # === Leads (CRM) ===
    """CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        source_post_id TEXT,
        source_platform TEXT,
        full_name TEXT,
        phone TEXT,
        email TEXT,
        message TEXT,
        sentiment TEXT,
        lead_score INTEGER DEFAULT 0,
        quality TEXT DEFAULT 'warm',
        assigned_to INTEGER REFERENCES users(id),
        status TEXT DEFAULT 'New',
        notes TEXT,
        follow_up_at DATETIME,
        closed_at DATETIME,
        closed_value REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",

    # === Lead Activities ===
    """CREATE TABLE IF NOT EXISTS lead_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL REFERENCES leads(id),
        user_id INTEGER REFERENCES users(id),
        activity_type TEXT NOT NULL,
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",

    # === Notifications ===
    """CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT,
        severity TEXT DEFAULT 'info',
        is_read BOOLEAN DEFAULT 0,
        action_url TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
]

# Seed banned keywords for Vietnamese content
SEED_BANNED_KEYWORDS = [
    ("giảm cân", "medical", "hỗ trợ vóc dáng", "all"),
    ("chữa bệnh", "medical", "hỗ trợ sức khỏe", "all"),
    ("cam kết 100%", "spam", "cam kết chất lượng", "all"),
    ("số 1 Việt Nam", "spam", "hàng đầu khu vực", "all"),
    ("rẻ nhất", "spam", "giá cạnh tranh", "all"),
    ("bạo lực", "violence", None, "all"),
    ("đánh nhau", "violence", None, "all"),
    ("kỳ thị", "hate", None, "all"),
    ("phân biệt", "hate", "đa dạng", "all"),
    ("lừa đảo", "spam", "uy tín", "all"),
    ("kiếm tiền online", "spam", None, "TikTok"),
    ("link bio", "spam", None, "TikTok"),
    ("follow để xem thêm", "spam", "xem thêm tại kênh", "TikTok"),
]


def run_migration():
    print(f"[MIGRATE] Connecting to: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    success_count = 0
    skip_count = 0
    error_count = 0

    for i, sql in enumerate(MIGRATIONS, 1):
        try:
            cursor.execute(sql)
            conn.commit()
            action = sql.strip().split()[0:3]
            print(f"  [{i}/{len(MIGRATIONS)}] OK: {' '.join(action)}...")
            success_count += 1
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print(f"  [{i}/{len(MIGRATIONS)}] SKIP (already exists)")
                skip_count += 1
            else:
                print(f"  [{i}/{len(MIGRATIONS)}] ERROR: {e}")
                error_count += 1

    # Seed banned keywords
    print("\n[MIGRATE] Seeding banned keywords...")
    for kw, cat, alt, platform in SEED_BANNED_KEYWORDS:
        try:
            cursor.execute(
                "INSERT INTO banned_keywords (keyword, category, safe_alternative, platform) "
                "SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM banned_keywords WHERE keyword = ?)",
                (kw, cat, alt, platform, kw)
            )
        except Exception as e:
            print(f"  SKIP keyword '{kw}': {e}")
    conn.commit()

    conn.close()
    print(f"\n[MIGRATE] DONE! Success: {success_count}, Skipped: {skip_count}, Errors: {error_count}")


if __name__ == "__main__":
    run_migration()
