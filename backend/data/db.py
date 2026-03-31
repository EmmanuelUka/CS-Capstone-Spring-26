import os
import sqlite3
import hmac
import hashlib
import base64
from datetime import datetime, timezone
from typing import Iterable, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# =========================================================
# Configuration / Constants
# =========================================================

# Path to the SQLite database file.
# It gets placed in the same folder as this Python file.
DB_PATH = os.path.join(os.path.dirname(__file__), "hashmark.db")

# These are the only roles the system should allow.
# Keeping them here makes validation easier everywhere else.
ALLOWED_ROLES = {"SUPER_ADMIN", "ADMIN", "COACH"}


# =========================================================
# Environment Helpers
# =========================================================

def _require_env(name: str) -> str:
    # Used for env vars that absolutely must exist.
    # If one is missing, the system should fail immediately instead of silently running with broken security.
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"{name} must be set (see .env.example)")
    return value.strip()


# =========================================================
# General Utility Helpers
# =========================================================

def _normalize_email(email: str) -> str:
    # Makes email comparisons consistent.
    # This avoids issues like uppercase/lowercase or extra spaces.
    return (email or "").strip().lower()


def _now_iso() -> str:
    # Returns the current UTC time as an ISO string.
    # Used for created_at / updated_at timestamps.
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# Cryptography Helpers
# =========================================================

def _pepper_bytes() -> bytes:
    # Loads the email hash pepper from the environment.
    # This adds a secret value to hashing so hashes are harder to attack even if someone got the database.
    return _require_env("EMAIL_HASH_PEPPER").encode("utf-8")


def _aes_key() -> bytes:
    # Loads the base64-encoded AES key from the environment and converts it into raw bytes for AESGCM use.
    raw_b64 = _require_env("EMAIL_ENC_KEY_B64")
    try:
        key = base64.b64decode(raw_b64)
    except Exception as e:
        raise RuntimeError("EMAIL_ENC_KEY_B64 must be valid base64") from e

    if len(key) != 32:
        raise RuntimeError("EMAIL_ENC_KEY_B64 must decode to exactly 32 bytes")

    return key


def email_hash(email: str) -> bytes:
    # Creates a deterministic secure hash of the email.
    # Deterministic matters because I need the same input email to always hash to the same value for lookups.
    # HMAC is used instead of plain SHA-256 so a secret pepper is involved, which is better for protecting stored emails.
    normalized = _normalize_email(email).encode("utf-8")
    return hmac.new(_pepper_bytes(), normalized, hashlib.sha256).digest()


def encrypt_email(email: str) -> bytes:
    # Encrypts the email before storing it.
    # Hashing is used for lookups, but encryption is used so the real email can still be recovered when needed.
    normalized = _normalize_email(email).encode("utf-8")
    aesgcm = AESGCM(_aes_key())
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, normalized, associated_data=None)
    return nonce + ciphertext


def decrypt_email(blob: bytes) -> str:
    # Decrypts the stored email blob back into a normal string.
    # If the value is missing, invalid, or cannot be decrypted, return "".
    if blob is None:
        return ""

    try:
        data = bytes(blob)
        if len(data) < 13:
            return ""

        # First 12 bytes are the nonce, rest is ciphertext+tag.
        nonce, ciphertext = data[:12], data[12:]
        aesgcm = AESGCM(_aes_key())
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
        return plaintext.decode("utf-8")
    except Exception:
        return ""


# =========================================================
# Database Helpers
# =========================================================

def _connect() -> sqlite3.Connection:
    # Opens a connection to the SQLite database and sets row_factory
    # so rows can be accessed like dictionaries instead of only tuples.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # SQLite "production-ish" pragmas
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA temp_store = MEMORY;")

    return conn


# =========================================================
# Schema / Initialization
# =========================================================

def init_db():
    # Creates the users table if it does not exist yet.
    # This is the main table used by the auth/admin system.
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_hash BLOB NOT NULL UNIQUE,
            email_enc BLOB NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('SUPER_ADMIN','ADMIN','COACH')),
            provider_subject TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    """)

    # Index on provider_subject so subject lookups are faster.
    # This matters when matching a Microsoft login back to a stored user.
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_subject
        ON users(provider_subject)
    """)

    # Makes provider_subject unique, but only when it exists.
    # Multiple NULL values are allowed, which is what I want for users who exist before first successful Microsoft login.
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_users_provider_subject
        ON users(provider_subject)
        WHERE provider_subject IS NOT NULL
    """)

    conn.commit()
    conn.close()


# =========================================================
# User Read Operations
# =========================================================

def get_user_by_email(email: str):
    # Finds a user by email using the deterministic email hash.
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email_hash = ?", (email_hash(email),))
    row = cur.fetchone()
    conn.close()
    return row


def get_user_by_subject(subject: str):
    # Finds a user by the OAuth provider subject.
    # This is useful after Microsoft login when you get the subject from the identity provider instead of using email lookup.
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE provider_subject = ?", (subject,))
    row = cur.fetchone()
    conn.close()
    return row


def get_user_list():
    # Returns a simplified list of users for admin/frontend use.
    # The stored encrypted email is decrypted here so the UI can show it.
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT email_enc, role, created_at
        FROM users
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "email": decrypt_email(row["email_enc"]) or "[unreadable email]",
            "role": row["role"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


# =========================================================
# User Write Operations
# =========================================================

def attach_subject_to_user(email: str, subject: str):
    # After a user successfully logs in with Microsoft, this links their stored account to the Microsoft provider subject.
    # That way future lookups can use provider_subject directly.
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users
        SET provider_subject = ?, updated_at = ?
        WHERE email_hash = ?
        """,
        (subject, _now_iso(), email_hash(email)),
    )
    conn.commit()
    conn.close()


def upsert_user(email: str, role: str, provider_subject: Optional[str] = None):
    # Inserts a new user if they do not exist,otherwise updates the existing user.
    # This is useful when you want one function that handles both "create user" and "update user role" logic.
    email_n = _normalize_email(email)
    role_u = (role or "").strip().upper()

    # Validate role before touching the DB.
    if role_u not in ALLOWED_ROLES:
        raise ValueError("invalid_role")

    now = _now_iso()
    hashed_email = email_hash(email_n)
    encrypted_email = encrypt_email(email_n)

    conn = _connect()
    cur = conn.cursor()

    # Check whether this user already exists.
    cur.execute("SELECT * FROM users WHERE email_hash = ?", (hashed_email,))
    existing = cur.fetchone()

    if existing is None:
        cur.execute(
            """
            INSERT INTO users (
                email_hash,
                email_enc,
                role,
                provider_subject,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (hashed_email, encrypted_email, role_u, provider_subject, now),
        )
    # If the user exists and we are now getting a provider_subject for the first time, attach it while updating role.
    else:
        if provider_subject and not (existing["provider_subject"] or ""):
            cur.execute(
                """
                UPDATE users
                SET role = ?, provider_subject = ?, updated_at = ?
                WHERE email_hash = ?
                """,
                (role_u, provider_subject, now, hashed_email),
            )
        else:
            # Otherwise just update the role.
            cur.execute(
                """
                UPDATE users
                SET role = ?, updated_at = ?
                WHERE email_hash = ?
                """,
                (role_u, now, hashed_email),
            )

    conn.commit()
    conn.close()


def update_user_role(email: str, role: str):
    # Updates the user's role.
    # This is meant for admin actions like promote/demote.
    email_n = _normalize_email(email)
    role_u = (role or "").strip().upper()

    if role_u not in ALLOWED_ROLES:
        raise ValueError("invalid_role")

    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users
        SET role = ?, updated_at = ?
        WHERE email_hash = ?
        """,
        (role_u, _now_iso(), email_hash(email_n)),
    )
    conn.commit()
    conn.close()


def delete_user(email: str):
    # Deletes a user from the system.
    email_n = _normalize_email(email)

    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE email_hash = ?", (email_hash(email_n),))
    conn.commit()
    conn.close()


# =========================================================
# Admin / Role Synchronization
# =========================================================

def sync_super_admins(
        
    # Syncs the SUPER_ADMIN list from config / env into the database.
    #
    # Main idea:
    # - every email in the provided list must become SUPER_ADMIN
    # - if enforce=True, any existing SUPER_ADMIN not in the list
    #   gets demoted

    super_admin_emails: Iterable[str],
    enforce: bool = False,
    demote_to: str = "ADMIN",
):
    emails = {
        _normalize_email(email)
        for email in (super_admin_emails or [])
        if email and email.strip()
    }

    # If nothing was passed in, do nothing.
    if not emails:
        return

    conn = _connect()
    cur = conn.cursor()
    now = _now_iso()

    # Make sure every configured super admin exists and has the right role.
    for email in emails:
        hashed_email = email_hash(email)

        cur.execute("SELECT id FROM users WHERE email_hash = ?", (hashed_email,))
        existing = cur.fetchone()

        # If not in the DB yet, create them as SUPER_ADMIN.
        if existing is None:
            cur.execute(
                """
                INSERT INTO users (email_hash, email_enc, role, created_at)
                VALUES (?, ?, 'SUPER_ADMIN', ?)
                """,
                (hashed_email, encrypt_email(email), now),
            )
        # If already there, force role to SUPER_ADMIN.
        else:
            cur.execute(
                """
                UPDATE users
                SET role = 'SUPER_ADMIN', updated_at = ?
                WHERE email_hash = ?
                """,
                (now, hashed_email),
            )

    # If enforcing, any SUPER_ADMIN not in the approved list should be demoted to the chosen fallback role.
    if enforce:
        demote_to = (demote_to or "ADMIN").strip().upper()
        if demote_to not in {"ADMIN", "COACH"}:
            demote_to = "ADMIN"

        cur.execute("SELECT email_hash FROM users WHERE role = 'SUPER_ADMIN'")
        current_hashes = [bytes(row[0]) for row in cur.fetchall()]
        allowed_hashes = {email_hash(email) for email in emails}

        for hashed_email in current_hashes:
            if hashed_email not in allowed_hashes:
                cur.execute(
                    """
                    UPDATE users
                    SET role = ?, updated_at = ?
                    WHERE email_hash = ?
                    """,
                    (demote_to, now, hashed_email),
                )

    conn.commit()
    conn.close()