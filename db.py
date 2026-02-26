import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data") / "jobs.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def _has_column(cur, table: str, col: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols


def init_db():
    """
    Creates tables if missing and migrates older DBs by adding new columns.
    This prevents errors like: sqlite3.OperationalError: no such column: followup_date
    """
    conn = get_conn()
    cur = conn.cursor()

    # 1) Create the applications table (minimal base schema)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT,
        role_title TEXT,
        role_family TEXT,
        jd_text TEXT,
        match_score REAL,
        created_at TEXT
    )
    """)

    # 2) Migrate: add missing columns safely
    # (column_name, type, default_sql_literal)
    migrations = [
        ("job_location", "TEXT", "''"),
        ("work_mode", "TEXT", "'UNKNOWN'"),
        ("relocation_required", "INTEGER", "0"),

        ("status", "TEXT", "'CREATED'"),
        ("followup_date", "TEXT", "''"),
        ("notes", "TEXT", "''"),

        ("resume_docx_path", "TEXT", "''"),
        ("resume_pdf_path", "TEXT", "''"),
        ("cover_letter_path", "TEXT", "''"),

        ("recruiter_msg", "TEXT", "''"),
        ("report_json", "TEXT", "''"),
    ]

    for col, coltype, default in migrations:
        if not _has_column(cur, "applications", col):
            cur.execute(f"ALTER TABLE applications ADD COLUMN {col} {coltype} DEFAULT {default}")

    # 3) Create notifications table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_id INTEGER,
        title TEXT,
        body TEXT,
        due_at TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY(app_id) REFERENCES applications(id)
    )
    """)

    conn.commit()
    conn.close()


def create_notification(conn, app_id: int, title: str, body: str, due_at: str):
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO notifications(app_id, title, body, due_at, is_read, created_at)
      VALUES (?, ?, ?, ?, 0, ?)
    """, (app_id, title, body, due_at, datetime.now().strftime("%Y-%m-%d %H:%M")))


def unread_notification_count() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM notifications WHERE is_read = 0")
    n = cur.fetchone()[0] or 0
    conn.close()
    return int(n)
