import os
import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "hashmark.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(seed_system_admin_email: str | None, default_org_seat_limit: int = 25):
    """Initialize DB schema.

    This version supports:
      - Organizations (teams)
      - Users (identity)
      - Memberships (role per org)
      - Invites scoped to org
      - Optional system-level admin (seed_system_admin_email)
    """
    conn = _connect()
    cur = conn.cursor()

    # --- New schema ---
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1,
            provider TEXT NOT NULL DEFAULT 'microsoft',
            provider_subject TEXT,
            system_role TEXT, -- e.g. 'SUPER_ADMIN' for Hashmark operators
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            seat_limit INTEGER NOT NULL DEFAULT 25,
            allowed_domains TEXT, -- optional comma-separated domains (lowercase)
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS memberships (
            org_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,         -- 'ADMIN' | 'COACH' | 'SCOUT'
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            PRIMARY KEY (org_id, user_id),
            FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL,
            invited_by_user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            accepted_at TEXT,
            FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE,
            FOREIGN KEY (invited_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (org_id, email)
        )
        """
    )

    # Helpful indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_subject ON users(provider_subject)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_memberships_user ON memberships(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invites_expires ON invites(expires_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invites_email ON invites(email)")

    # --- Migration from old schema (best-effort) ---
    # If an older 'users' table existed with a 'role' column, migrate its roles.
    try:
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]  # type: ignore[index]
        # If we already have the new schema, 'role' won't exist.
        if "role" in cols:
            # Old schema is present; create new tables with suffix and migrate.
            # We can't rename in-place safely here; user can delete db for dev.
            pass
    except Exception:
        pass

    conn.commit()

    # Seed system admin (Hashmark operator)
    if seed_system_admin_email:
        email = seed_system_admin_email.strip().lower()
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                """
                INSERT INTO users (email, is_active, provider, system_role, created_at)
                VALUES (?, 1, 'microsoft', 'SUPER_ADMIN', ?)
                """,
                (email, _utc_now_iso()),
            )
        else:
            cur.execute("UPDATE users SET system_role='SUPER_ADMIN', is_active=1 WHERE email=?", (email,))
        conn.commit()

    conn.close()


# ----------------------------
# Users
# ----------------------------
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


def create_user_if_missing(email: str, provider: str = "microsoft"):
    email = email.lower().strip()
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    u = cur.fetchone()
    if u:
        conn.close()
        return u
    cur.execute(
        """
        INSERT INTO users (email, is_active, provider, created_at)
        VALUES (?, 1, ?, ?)
        """,
        (email, provider, _utc_now_iso()),
    )
    conn.commit()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    u2 = cur.fetchone()
    conn.close()
    return u2


def attach_subject_to_user(email: str, subject: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET provider_subject = ? WHERE email = ?", (subject, email.lower()))
    conn.commit()
    conn.close()


# ----------------------------
# Organizations
# ----------------------------
def create_org(name: str, seat_limit: int = 25, allowed_domains: str | None = None):
    name = (name or "").strip()
    if not name:
        raise ValueError("org name required")
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM organizations WHERE name = ?", (name,))
    existing = cur.fetchone()
    if existing:
        conn.close()
        return existing

    cur.execute(
        """
        INSERT INTO organizations (name, seat_limit, allowed_domains, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (name, int(seat_limit), (allowed_domains or None), _utc_now_iso()),
    )
    conn.commit()
    cur.execute("SELECT * FROM organizations WHERE name = ?", (name,))
    org = cur.fetchone()
    conn.close()
    return org


def get_org(org_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM organizations WHERE id = ?", (int(org_id),))
    row = cur.fetchone()
    conn.close()
    return row


def list_orgs_for_user(user_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT o.id, o.name, o.seat_limit, o.allowed_domains,
               m.role, m.is_active
        FROM memberships m
        JOIN organizations o ON o.id = m.org_id
        WHERE m.user_id = ? AND m.is_active = 1
        ORDER BY o.name ASC
        """,
        (int(user_id),),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_membership(user_id: int, org_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM memberships WHERE user_id=? AND org_id=?",
        (int(user_id), int(org_id)),
    )
    row = cur.fetchone()
    conn.close()
    return row


def upsert_membership(org_id: int, user_id: int, role: str, is_active: int = 1):
    role = role.strip().upper()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM memberships WHERE org_id=? AND user_id=?",
        (int(org_id), int(user_id)),
    )
    existing = cur.fetchone()
    if existing:
        cur.execute(
            "UPDATE memberships SET role=?, is_active=? WHERE org_id=? AND user_id=?",
            (role, int(is_active), int(org_id), int(user_id)),
        )
    else:
        cur.execute(
            """
            INSERT INTO memberships (org_id, user_id, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (int(org_id), int(user_id), role, int(is_active), _utc_now_iso()),
        )
    conn.commit()
    conn.close()


def count_active_members(org_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS c FROM memberships WHERE org_id=? AND is_active=1",
        (int(org_id),),
    )
    c = int(cur.fetchone()["c"])
    conn.close()
    return c


def list_members(org_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.id as user_id, u.email, u.provider_subject, u.is_active as user_active,
               m.role, m.is_active as membership_active, m.created_at
        FROM memberships m
        JOIN users u ON u.id = m.user_id
        WHERE m.org_id = ? AND m.is_active = 1
        ORDER BY m.role ASC, u.email ASC
        """,
        (int(org_id),),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def deactivate_membership(org_id: int, user_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE memberships SET is_active=0 WHERE org_id=? AND user_id=?",
        (int(org_id), int(user_id)),
    )
    conn.commit()
    conn.close()


# ----------------------------
# Invites (scoped to org)
# ----------------------------
def delete_membership(org_id: int, user_id: int):
    """Hard-remove a membership so the user no longer sees the team at all."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM memberships WHERE org_id=? AND user_id=?",
        (int(org_id), int(user_id)),
    )
    conn.commit()
    conn.close()

def create_invite(org_id: int, email: str, role: str, invited_by_user_id: int, ttl_hours: int = 168):
    email = email.lower().strip()
    role = role.strip().upper()

    now = datetime.now(timezone.utc)
    expires = (now + timedelta(hours=ttl_hours)).isoformat()

    conn = _connect()
    cur = conn.cursor()

    # Upsert invite
    cur.execute("SELECT * FROM invites WHERE org_id=? AND email=?", (int(org_id), email))
    inv = cur.fetchone()
    if inv:
        cur.execute(
            """
            UPDATE invites
            SET role=?, invited_by_user_id=?, expires_at=?, created_at=?, accepted_at=NULL
            WHERE org_id=? AND email=?
            """,
            (role, int(invited_by_user_id), expires, now.isoformat(), int(org_id), email),
        )
        conn.commit()
        conn.close()
        return "invite_updated"

    cur.execute(
        """
        INSERT INTO invites (org_id, email, role, invited_by_user_id, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (int(org_id), email, role, int(invited_by_user_id), expires, now.isoformat()),
    )
    conn.commit()
    conn.close()
    return "invite_created"



def has_valid_invite(email: str) -> bool:
    """Return True if there is at least one non-expired, unaccepted invite for this email."""
    email = (email or "").lower().strip()
    if not email:
        return False
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT expires_at FROM invites WHERE email=? AND accepted_at IS NULL",
        (email,),
    )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return False
    now = datetime.now(timezone.utc)
    for r in rows:
        try:
            exp = datetime.fromisoformat(r["expires_at"])
            if exp > now:
                return True
        except Exception:
            continue
    return False

def accept_valid_invites_for_user(email: str, user_id: int):
    """Accepts ALL non-expired invites for this email into memberships.
    Returns number of invites accepted.
    """
    email = email.lower().strip()
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM invites WHERE email=? AND accepted_at IS NULL", (email,))
    invites = cur.fetchall()
    if not invites:
        conn.close()
        return 0

    now = datetime.now(timezone.utc)
    accepted = 0

    for inv in invites:
        expires_at = datetime.fromisoformat(inv["expires_at"])
        if expires_at < now:
            continue

        org_id = int(inv["org_id"])
        role = inv["role"]

        # Create/activate membership
        cur.execute(
            """
            INSERT INTO memberships (org_id, user_id, role, is_active, created_at)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(org_id, user_id) DO UPDATE SET role=excluded.role, is_active=1
            """,
            (org_id, int(user_id), role, now.isoformat()),
        )
        cur.execute(
            "UPDATE invites SET accepted_at=? WHERE id=?",
            (now.isoformat(), int(inv["id"])),
        )
        accepted += 1

    conn.commit()
    conn.close()
    return accepted


def list_orgs_system():
    """System-wide org list (Hashmark operators only)."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, seat_limit, allowed_domains, created_at
        FROM organizations
        ORDER BY name ASC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_org(org_id: int) -> bool:
    """Delete an org and all related data (memberships, invites) via cascade."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
    changed = cur.rowcount > 0
    conn.commit()
    conn.close()
    return changed


def set_team_admin(org_id: int, new_admin_user_id: int):
    """Ensure exactly one ACTIVE ADMIN for the org: demote existing admins to COACH, then set new admin."""
    conn = _connect()
    cur = conn.cursor()

    # Demote all active admins in this org
    cur.execute(
        """
        UPDATE memberships
        SET role = 'COACH'
        WHERE org_id = ? AND is_active = 1 AND role = 'ADMIN'
        """,
        (org_id,),
    )

    # Upsert new admin membership
    now = _utc_now_iso()
    cur.execute(
        """
        INSERT INTO memberships (org_id, user_id, role, is_active, created_at)
        VALUES (?, ?, 'ADMIN', 1, ?)
        ON CONFLICT(org_id, user_id) DO UPDATE SET role='ADMIN', is_active=1
        """,
        (org_id, new_admin_user_id, now),
    )

    conn.commit()
    conn.close()

def list_users_system():
    """System-wide user list (Hashmark operators only)."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, email, is_active, provider, provider_subject, system_role, created_at
        FROM users
        ORDER BY created_at DESC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]