import os
import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "hashmark.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(seed_super_admin_email: str | None):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        provider TEXT NOT NULL DEFAULT 'microsoft',
        provider_subject TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS invites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL,
        invited_by_email TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        accepted_at TEXT
    )
    """)

    # Helpful indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_subject ON users(provider_subject)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invites_expires ON invites(expires_at)")

    conn.commit()

    if seed_super_admin_email:
        email = seed_super_admin_email.strip().lower()
        cur.execute("SELECT 1 FROM users WHERE email = ?", (email,))
        if cur.fetchone() is None:
            now = datetime.now(timezone.utc).isoformat()
            cur.execute(
                "INSERT INTO users (email, role, is_active, provider, created_at) VALUES (?, ?, 1, 'microsoft', ?)",
                (email, "SUPER_ADMIN", now)
            )
            conn.commit()

    conn.close()


def get_user_by_email(email: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
    row = cur.fetchone()
    conn.close()
    return row


def get_user_by_subject(subject: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE provider_subject = ?", (subject,))
    row = cur.fetchone()
    conn.close()
    return row


def attach_subject_to_user(email: str, subject: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET provider_subject = ? WHERE email = ?", (subject, email.lower()))
    conn.commit()
    conn.close()


def create_invite(email: str, role: str, invited_by_email: str, ttl_hours: int = 168):
    email = email.lower().strip()
    invited_by_email = invited_by_email.lower().strip()

    now = datetime.now(timezone.utc)
    expires = (now + timedelta(hours=ttl_hours)).isoformat()

    conn = _connect()
    cur = conn.cursor()

    # If user exists, update role and activate them
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    if user:
        cur.execute("UPDATE users SET role = ?, is_active = 1 WHERE email = ?", (role, email))
        conn.commit()
        conn.close()
        return "user_updated"

    # Upsert invite
    cur.execute("SELECT * FROM invites WHERE email = ?", (email,))
    inv = cur.fetchone()
    if inv:
        cur.execute("""
            UPDATE invites
            SET role=?, invited_by_email=?, expires_at=?, created_at=?, accepted_at=NULL
            WHERE email=?
        """, (role, invited_by_email, expires, now.isoformat(), email))
    else:
        cur.execute("""
            INSERT INTO invites (email, role, invited_by_email, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (email, role, invited_by_email, expires, now.isoformat()))

    conn.commit()
    conn.close()
    return "invite_created"


def accept_invite(email: str):
    email = email.lower().strip()
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM invites WHERE email = ?", (email,))
    inv = cur.fetchone()
    if not inv:
        conn.close()
        return None

    expires_at = datetime.fromisoformat(inv["expires_at"])
    now = datetime.now(timezone.utc)
    if expires_at < now:
        conn.close()
        return "expired"

    created = now.isoformat()

    cur.execute("""
        INSERT OR IGNORE INTO users (email, role, is_active, provider, created_at)
        VALUES (?, ?, 1, 'microsoft', ?)
    """, (email, inv["role"], created))

    cur.execute("UPDATE invites SET accepted_at = ? WHERE email = ?", (created, email))

    conn.commit()
    conn.close()
    return "accepted"


def list_users():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT email, role, is_active, provider, provider_subject, created_at
        FROM users
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]