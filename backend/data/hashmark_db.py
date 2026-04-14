"""
hashmark_db.py
--------------
Database layer for the Hashmark football scouting application.

Schema summary
--------------
  positions            – QB, RB, WR, etc. (user-extensible)
  players              – recruits + historical players
  stats                – stat definitions tied to a position
  player_stats         – per-player stat values
  player_evaluations   – physical/contextual evaluation of a recruit
  player_comparisons   – generated comparison scores from an evaluation
  archetypes           – user-defined role templates (optional position, optional stat rule)
  stat_rules           – minimum value thresholds for a stat
  schemes              – named lineups (shortlists) with up to 11 slots
  scheme_positions     – each slot in a scheme (standard position OR archetype)
  scheme_assignments   – recruit assigned to a scheme slot
  log_activity         – audit log of user / system actions
"""

import sqlite3
import pandas as pd
from contextlib import contextmanager
from datetime import datetime

DB_NAME = "hashmark_players.db"


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db():
    """Create all tables if they do not already exist."""
    with get_conn() as conn:
        conn.executescript("""
        -- ----------------------------------------------------------------
        -- Core lookup tables
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS positions (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT    NOT NULL UNIQUE
        );

        -- ----------------------------------------------------------------
        -- Stat definitions
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS stats (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            position_id INTEGER,                          -- NULL = universal stat
            FOREIGN KEY (position_id) REFERENCES positions(id)
        );

        -- ----------------------------------------------------------------
        -- Stat rules  (used by archetypes to gate eligibility)
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS stat_rules (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_id       INTEGER NOT NULL,
            minimum_value REAL    NOT NULL,
            FOREIGN KEY (stat_id) REFERENCES stats(id)
        );

        -- ----------------------------------------------------------------
        -- Archetypes  (user-defined roles: e.g. "Slot Receiver", "Pass Rusher")
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS archetypes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT    NOT NULL,
            position_id  INTEGER,           -- optional position constraint
            notes        TEXT,
            stat_rule_id INTEGER,           -- optional eligibility rule
            FOREIGN KEY (position_id)  REFERENCES positions(id),
            FOREIGN KEY (stat_rule_id) REFERENCES stat_rules(id)
        );

        -- ----------------------------------------------------------------
        -- Players
        --   is_recruit   : 1 = active recruit being scouted
        --                  0 = historical player (used for analysis only)
        --   evaluation_id: FK to player_evaluations; NULL until first eval
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS players (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT    NOT NULL,
            team_name           TEXT,
            position_id         INTEGER,
            is_recruit          INTEGER NOT NULL DEFAULT 1  CHECK(is_recruit IN (0,1)),
            notes               TEXT,
            evaluation_id       INTEGER,          -- set after first evaluation is created
            -- Physical
            height              REAL,             -- inches
            weight              REAL,             -- lbs
            -- School / recruitment context
            school_name         TEXT,
            state_code          TEXT,             -- 2-letter state abbreviation, e.g. "OH"
            recruit_type        TEXT CHECK(recruit_type IN ('high_school', 'college', 'transfer') OR recruit_type IS NULL),
            school_strength     TEXT CHECK(school_strength IN ('elite', 'strong', 'average', 'weak') OR school_strength IS NULL),
            transfer_conference TEXT,             -- only relevant when recruit_type = 'transfer'
            -- Playing history
            play_year           INTEGER,          -- year the player played (e.g. 2024)
            frequency_player    TEXT CHECK(frequency_player IN ('starter', 'backup', 'bench') OR frequency_player IS NULL),
            FOREIGN KEY (position_id)   REFERENCES positions(id),
            FOREIGN KEY (evaluation_id) REFERENCES player_evaluations(id)
                DEFERRABLE INITIALLY DEFERRED
        );

        -- ----------------------------------------------------------------
        -- Per-player stat values
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS player_stats (
            player_id INTEGER NOT NULL,
            stat_id   INTEGER NOT NULL,
            value     REAL,
            PRIMARY KEY (player_id, stat_id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (stat_id)   REFERENCES stats(id)
        );

        -- ----------------------------------------------------------------
        -- Player evaluations  (physical + contextual snapshot)
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS player_evaluations (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id           INTEGER NOT NULL,
            height              REAL,       -- inches or cm, caller's choice
            weight              REAL,       -- lbs or kg, caller's choice
            context_multiplier  REAL,       -- e.g. 1.43 for strong competition context
            confidence          REAL,       -- 0.0 – 100.0
            physical_score      REAL,       -- composite physical score (0.0 – 1.0)
            production_score    REAL,       -- stat-based production score (0.0 – 1.0)
            context_score       REAL,       -- contextual/situational score (0.0 – 1.0)
            evaluated_at        TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );

        -- ----------------------------------------------------------------
        -- Player comparisons  (generated from an evaluation)
        --   Stores the breakdown that feeds the final composite score.
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS player_comparisons (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id       INTEGER NOT NULL UNIQUE,   -- one comparison per eval
            final_score         REAL,
            confidence          REAL,
            recency_weight      REAL,
            physical_score      REAL,   -- composite of height/weight sub-scores
            physical_height     REAL,
            physical_weight     REAL,
            production_score    REAL,
            production_stats_used   INTEGER,
            production_stats_missing INTEGER,
            context_score       REAL,
            context_recruit     REAL,
            context_comp        REAL,
            generated_at        TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (evaluation_id) REFERENCES player_evaluations(id)
        );

        -- ----------------------------------------------------------------
        -- Schemes  (shortlists / potential lineups, up to 11 slots)
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS schemes (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name    TEXT,
            color   TEXT
        );

        -- ----------------------------------------------------------------
        -- Scheme positions  (each slot in a scheme)
        --   Exactly one of position_id or archetype_id must be set.
        --   slot_number: 1-11
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS scheme_positions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_id    INTEGER NOT NULL,
            position_id  INTEGER,           -- standard position slot
            archetype_id INTEGER,           -- OR archetype slot
            slot_number  INTEGER NOT NULL CHECK(slot_number BETWEEN 1 AND 11),
            FOREIGN KEY (scheme_id)    REFERENCES schemes(id),
            FOREIGN KEY (position_id)  REFERENCES positions(id),
            FOREIGN KEY (archetype_id) REFERENCES archetypes(id),
            CHECK (
                (position_id IS NOT NULL AND archetype_id IS NULL) OR
                (position_id IS NULL     AND archetype_id IS NOT NULL)
            )
        );

        -- ----------------------------------------------------------------
        -- Scheme assignments  (recruit → slot; only recruits allowed)
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS scheme_assignments (
            scheme_position_id INTEGER PRIMARY KEY,
            player_id          INTEGER NOT NULL,
            FOREIGN KEY (scheme_position_id) REFERENCES scheme_positions(id),
            FOREIGN KEY (player_id)          REFERENCES players(id)
        );

        -- ----------------------------------------------------------------
        -- Activity log
        -- ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS log_activity (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_name  TEXT NOT NULL,
            activity_notes TEXT,
            activity_time  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """)

    # ------------------------------------------------------------------
    # Migration: add new score columns to player_evaluations if this is
    # an existing database created before these fields were introduced.
    # ALTER TABLE ADD COLUMN is a no-op-safe operation in SQLite when the
    # column does not yet exist; we catch the OperationalError for safety.
    # ------------------------------------------------------------------
    _migrate_player_evaluations()
    _migrate_schemes()


def _migrate_player_evaluations():
    """Add physical_score / production_score / context_score to player_evaluations
    if they are not already present (safe to call on every startup)."""
    new_columns = [
        ("physical_score",   "REAL"),
        ("production_score", "REAL"),
        ("context_score",    "REAL"),
    ]
    with get_conn() as conn:
        existing = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(player_evaluations)"
            ).fetchall()
        }
        for col_name, col_type in new_columns:
            if col_name not in existing:
                conn.execute(
                    f"ALTER TABLE player_evaluations ADD COLUMN {col_name} {col_type}"
                )
                conn.execute(
                    "INSERT INTO log_activity (activity_name, activity_notes) VALUES (?, ?)",
                    ("migrate_schema", f"Added column player_evaluations.{col_name}"),
                )


def _migrate_schemes():
    """Add color to schemes if it is not already present."""
    with get_conn() as conn:
        existing = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(schemes)"
            ).fetchall()
        }
        if "color" not in existing:
            conn.execute("ALTER TABLE schemes ADD COLUMN color TEXT")
            conn.execute(
                "INSERT INTO log_activity (activity_name, activity_notes) VALUES (?, ?)",
                ("migrate_schema", "Added column schemes.color"),
            )


# ---------------------------------------------------------------------------
# Logging utility (used internally and exposed for manual logging)
# ---------------------------------------------------------------------------

def _log_conn(conn, activity_name: str, notes: str = None):
    """Write a log entry using an already-open connection (no locking)."""
    conn.execute(
        "INSERT INTO log_activity (activity_name, activity_notes) VALUES (?, ?)",
        (activity_name, notes),
    )


def log(activity_name: str, notes: str = None):
    """Append a row to log_activity (opens its own connection — use outside transactions)."""
    with get_conn() as conn:
        _log_conn(conn, activity_name, notes)


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

def insert_position(name: str) -> int:
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO positions (name) VALUES (?)", (name,))
        _log_conn(conn, "insert_position", f"name={name}")
        return cur.lastrowid


def get_position_id(name: str) -> int | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM positions WHERE name = ?", (name,)
        ).fetchone()
        return row[0] if row else None


def get_or_create_position(name: str) -> int:
    pos_id = get_position_id(name)
    if pos_id:
        return pos_id
    return insert_position(name)


def delete_position(position_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))
    log("delete_position", f"id={position_id}")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def insert_stat(name: str, position_id: int = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO stats (name, position_id) VALUES (?, ?)",
            (name, position_id),
        )
        _log_conn(conn, "insert_stat", f"name={name}, position_id={position_id}")
        return cur.lastrowid


def get_stat_id(stat_name: str, position_id: int = None) -> int | None:
    with get_conn() as conn:
        if position_id is not None:
            row = conn.execute(
                "SELECT id FROM stats WHERE name = ? AND position_id = ?",
                (stat_name, position_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id FROM stats WHERE name = ?", (stat_name,)
            ).fetchone()
        return row[0] if row else None


def update_stat(stat_id: int, name: str = None, position_id: int = None):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE stats
            SET name        = COALESCE(?, name),
                position_id = COALESCE(?, position_id)
            WHERE id = ?
            """,
            (name, position_id, stat_id),
        )
    log("update_stat", f"id={stat_id}")


# ---------------------------------------------------------------------------
# Stat rules
# ---------------------------------------------------------------------------

def insert_stat_rule(stat_id: int, minimum_value: float) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO stat_rules (stat_id, minimum_value) VALUES (?, ?)",
            (stat_id, minimum_value),
        )
        _log_conn(conn, "insert_stat_rule", f"stat_id={stat_id}, min={minimum_value}")
        return cur.lastrowid


def get_stat_rules_df() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT sr.id, s.name AS stat_name, sr.minimum_value
            FROM stat_rules sr
            JOIN stats s ON s.id = sr.stat_id
            """,
            conn,
        )


# ---------------------------------------------------------------------------
# Archetypes
# ---------------------------------------------------------------------------

def insert_archetype(
    title: str,
    position_id: int = None,
    notes: str = None,
    stat_rule_id: int = None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO archetypes (title, position_id, notes, stat_rule_id)
            VALUES (?, ?, ?, ?)
            """,
            (title, position_id, notes, stat_rule_id),
        )
        _log_conn(conn, "insert_archetype", f"title={title}")
        return cur.lastrowid


def update_archetype(
    archetype_id: int,
    title: str = None,
    position_id: int = None,
    notes: str = None,
    stat_rule_id: int = None,
):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE archetypes
            SET title        = COALESCE(?, title),
                position_id  = COALESCE(?, position_id),
                notes        = COALESCE(?, notes),
                stat_rule_id = COALESCE(?, stat_rule_id)
            WHERE id = ?
            """,
            (title, position_id, notes, stat_rule_id, archetype_id),
        )
    log("update_archetype", f"id={archetype_id}")


def delete_archetype(archetype_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM archetypes WHERE id = ?", (archetype_id,))
    log("delete_archetype", f"id={archetype_id}")


def get_archetypes_df() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT a.id, a.title, p.name AS position, a.notes,
                   sr.minimum_value AS stat_rule_min,
                   s.name           AS stat_rule_stat
            FROM archetypes a
            LEFT JOIN positions  p  ON p.id  = a.position_id
            LEFT JOIN stat_rules sr ON sr.id = a.stat_rule_id
            LEFT JOIN stats      s  ON s.id  = sr.stat_id
            ORDER BY a.title
            """,
            conn,
        )


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------

_RECRUIT_TYPES     = {"high_school", "college", "transfer"}
_SCHOOL_STRENGTHS  = {"elite", "strong", "average", "weak"}
_FREQ_TYPES        = {"starter", "backup", "bench"}


def _validate_player_enums(recruit_type, school_strength, frequency_player):
    if recruit_type is not None and recruit_type not in _RECRUIT_TYPES:
        raise ValueError(f"recruit_type must be one of {_RECRUIT_TYPES}, got {recruit_type!r}")
    if school_strength is not None and school_strength not in _SCHOOL_STRENGTHS:
        raise ValueError(f"school_strength must be one of {_SCHOOL_STRENGTHS}, got {school_strength!r}")
    if frequency_player is not None and frequency_player not in _FREQ_TYPES:
        raise ValueError(f"frequency_player must be one of {_FREQ_TYPES}, got {frequency_player!r}")


def insert_player(
    name: str,
    team_name: str = None,
    position_id: int = None,
    is_recruit: bool = True,
    notes: str = None,
    # Physical
    height: float = None,
    weight: float = None,
    # School / recruitment context
    school_name: str = None,
    state_code: str = None,
    recruit_type: str = None,          # 'high_school' | 'college' | 'transfer'
    school_strength: str = None,       # 'elite' | 'strong' | 'average' | 'weak'
    transfer_conference: str = None,
    # Playing history
    play_year: int = None,
    frequency_player: str = None,      # 'starter' | 'backup' | 'bench'
) -> int:
    _validate_player_enums(recruit_type, school_strength, frequency_player)
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO players (
                name, team_name, position_id, is_recruit, notes,
                height, weight,
                school_name, state_code, recruit_type, school_strength,
                transfer_conference, play_year, frequency_player
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name, team_name, position_id, int(is_recruit), notes,
                height, weight,
                school_name, state_code, recruit_type, school_strength,
                transfer_conference, play_year, frequency_player,
            ),
        )
        _log_conn(conn, "insert_player", f"name={name}, is_recruit={is_recruit}")
        return cur.lastrowid


def bulk_insert_players(players: list[tuple]):
    """
    Each tuple: (name, team_name, position_id, is_recruit, notes,
                 height, weight, school_name, state_code, recruit_type,
                 school_strength, transfer_conference, play_year, frequency_player)
    All fields after `name` are optional — pad missing tail values with None.
    """
    def _get(p, i, default=None):
        return p[i] if len(p) > i else default

    rows = []
    for p in players:
        recruit_type    = _get(p, 9)
        school_strength = _get(p, 10)
        freq            = _get(p, 13)
        _validate_player_enums(recruit_type, school_strength, freq)
        rows.append((
            p[0],               # name
            _get(p, 1),         # team_name
            _get(p, 2),         # position_id
            int(_get(p, 3, 1)), # is_recruit
            _get(p, 4),         # notes
            _get(p, 5),         # height
            _get(p, 6),         # weight
            _get(p, 7),         # school_name
            _get(p, 8),         # state_code
            recruit_type,
            school_strength,
            _get(p, 11),        # transfer_conference
            _get(p, 12),        # play_year
            freq,               # frequency_player
        ))

    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO players (
                name, team_name, position_id, is_recruit, notes,
                height, weight, school_name, state_code, recruit_type,
                school_strength, transfer_conference, play_year, frequency_player
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    log("bulk_insert_players", f"count={len(rows)}")


def update_player(
    player_id: int,
    name: str = None,
    team_name: str = None,
    position_id: int = None,
    is_recruit: bool = None,
    notes: str = None,
    evaluation_id: int = None,
    # Physical
    height: float = None,
    weight: float = None,
    # School / recruitment context
    school_name: str = None,
    state_code: str = None,
    recruit_type: str = None,
    school_strength: str = None,
    transfer_conference: str = None,
    # Playing history
    play_year: int = None,
    frequency_player: str = None,
):
    _validate_player_enums(recruit_type, school_strength, frequency_player)
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE players
            SET name                = COALESCE(?, name),
                team_name           = COALESCE(?, team_name),
                position_id         = COALESCE(?, position_id),
                is_recruit          = COALESCE(?, is_recruit),
                notes               = COALESCE(?, notes),
                evaluation_id       = COALESCE(?, evaluation_id),
                height              = COALESCE(?, height),
                weight              = COALESCE(?, weight),
                school_name         = COALESCE(?, school_name),
                state_code          = COALESCE(?, state_code),
                recruit_type        = COALESCE(?, recruit_type),
                school_strength     = COALESCE(?, school_strength),
                transfer_conference = COALESCE(?, transfer_conference),
                play_year           = COALESCE(?, play_year),
                frequency_player    = COALESCE(?, frequency_player)
            WHERE id = ?
            """,
            (
                name,
                team_name,
                position_id,
                int(is_recruit) if is_recruit is not None else None,
                notes,
                evaluation_id,
                height,
                weight,
                school_name,
                state_code,
                recruit_type,
                school_strength,
                transfer_conference,
                play_year,
                frequency_player,
                player_id,
            ),
        )
    log("update_player", f"id={player_id}")


def delete_player(player_id: int):
    with get_conn() as conn:
        conn.execute(
            """
            DELETE FROM scheme_assignments
            WHERE player_id = ?
            """,
            (player_id,),
        )
        conn.execute(
            """
            DELETE FROM player_comparisons
            WHERE evaluation_id IN (
                SELECT id FROM player_evaluations WHERE player_id = ?
            )
            """,
            (player_id,),
        )
        conn.execute(
            "DELETE FROM player_stats WHERE player_id = ?",
            (player_id,),
        )
        conn.execute(
            "DELETE FROM player_evaluations WHERE player_id = ?",
            (player_id,),
        )
        conn.execute("DELETE FROM players WHERE id = ?", (player_id,))
    log("delete_player", f"id={player_id}")


def get_recruits_df() -> pd.DataFrame:
    """Return all players flagged as active recruits."""
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT p.id, p.name, p.team_name, pos.name AS position,
                   p.height, p.weight,
                   p.school_name, p.state_code, p.recruit_type,
                   p.school_strength, p.transfer_conference,
                   p.play_year, p.frequency_player,
                   p.notes
            FROM players p
            LEFT JOIN positions pos ON pos.id = p.position_id
            WHERE p.is_recruit = 1
            ORDER BY p.name
            """,
            conn,
        )


def get_historical_players_df() -> pd.DataFrame:
    """Return all historical (non-recruit) players."""
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT p.id, p.name, p.team_name, pos.name AS position,
                   p.height, p.weight,
                   p.school_name, p.state_code, p.recruit_type,
                   p.school_strength, p.transfer_conference,
                   p.play_year, p.frequency_player,
                   p.notes
            FROM players p
            LEFT JOIN positions pos ON pos.id = p.position_id
            WHERE p.is_recruit = 0
            ORDER BY p.name
            """,
            conn,
        )


# ---------------------------------------------------------------------------
# Player stats
# ---------------------------------------------------------------------------

def insert_player_stat(player_id: int, stat_id: int, value: float):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO player_stats (player_id, stat_id, value)
            VALUES (?, ?, ?)
            """,
            (player_id, stat_id, value),
        )


def get_all_players_with_stats() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT p.id          AS player_id,
                   p.name        AS player_name,
                   p.team_name,
                   p.is_recruit,
                   s.name        AS stat_name,
                   ps.value
            FROM players p
            LEFT JOIN player_stats ps ON ps.player_id = p.id
            LEFT JOIN stats        s  ON s.id         = ps.stat_id
            ORDER BY p.name
            """,
            conn,
        )


def get_players_stats_pivot() -> pd.DataFrame:
    df = get_all_players_with_stats()
    pivot = df.pivot_table(
        index=["player_id", "player_name", "team_name", "is_recruit"],
        columns="stat_name",
        values="value",
        dropna=False,   # keep players whose team_name (or other index) is NULL
    ).reset_index()
    pivot.columns.name = None   # remove the "stat_name" axis label for cleaner output
    return pivot


def get_players_with_stats_by_position(position_name: str) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT p.name  AS player_name,
                   p.is_recruit,
                   s.name  AS stat_name,
                   ps.value
            FROM players p
            JOIN positions     pos ON pos.id = p.position_id
            LEFT JOIN player_stats ps ON ps.player_id = p.id
            LEFT JOIN stats        s  ON s.id         = ps.stat_id
            WHERE pos.name = ?
            """,
            conn,
            params=(position_name,),
        )


# ---------------------------------------------------------------------------
# Player evaluations
# ---------------------------------------------------------------------------

def insert_player_evaluation(
    player_id: int,
    height: float = None,
    weight: float = None,
    context_multiplier: float = None,
    confidence: float = None,
    physical_score: float = None,
    production_score: float = None,
    context_score: float = None,
) -> int:
    """
    Create a new evaluation record and update the player's evaluation_id pointer.

    Args:
        player_id:          ID of the player being evaluated.
        height:             Height in inches (or cm — caller's choice).
        weight:             Weight in lbs (or kg — caller's choice).
        context_multiplier: Competition-context multiplier, e.g. 1.43.
        confidence:         Overall confidence in the evaluation (0.0 – 100.0).
        physical_score:     Composite physical score derived from height/weight
                            comparisons (0.0 – 1.0).
        production_score:   Stat-based production score (0.0 – 1.0).
        context_score:      Contextual/situational score (0.0 – 1.0).

    Returns:
        The newly created evaluation id.
    """
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO player_evaluations
                (player_id, height, weight, context_multiplier, confidence,
                 physical_score, production_score, context_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (player_id, height, weight, context_multiplier, confidence,
             physical_score, production_score, context_score),
        )
        eval_id = cur.lastrowid
        # Point the player to their latest evaluation
        conn.execute(
            "UPDATE players SET evaluation_id = ? WHERE id = ?",
            (eval_id, player_id),
        )
    log("insert_player_evaluation", f"player_id={player_id}, eval_id={eval_id}")
    return eval_id


def update_player_evaluation(
    evaluation_id: int,
    height: float = None,
    weight: float = None,
    context_multiplier: float = None,
    confidence: float = None,
    physical_score: float = None,
    production_score: float = None,
    context_score: float = None,
):
    """
    Partially update an existing evaluation.  Only non-None arguments are written;
    omitted arguments leave the stored value unchanged.

    Args:
        evaluation_id:      ID of the evaluation to update.
        height:             Updated height value.
        weight:             Updated weight value.
        context_multiplier: Updated competition-context multiplier.
        confidence:         Updated confidence (0.0 – 100.0).
        physical_score:     Updated composite physical score (0.0 – 1.0).
        production_score:   Updated stat-based production score (0.0 – 1.0).
        context_score:      Updated contextual/situational score (0.0 – 1.0).
    """
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE player_evaluations
            SET height             = COALESCE(?, height),
                weight             = COALESCE(?, weight),
                context_multiplier = COALESCE(?, context_multiplier),
                confidence         = COALESCE(?, confidence),
                physical_score     = COALESCE(?, physical_score),
                production_score   = COALESCE(?, production_score),
                context_score      = COALESCE(?, context_score)
            WHERE id = ?
            """,
            (height, weight, context_multiplier, confidence,
             physical_score, production_score, context_score,
             evaluation_id),
        )
    log("update_player_evaluation", f"id={evaluation_id}")


def get_evaluation(evaluation_id: int) -> dict | None:
    """
    Fetch a single evaluation by id.

    Returns a dict whose keys mirror the player_evaluations columns
    (including physical_score, production_score, context_score),
    or None if no matching row exists.
    """
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM player_evaluations WHERE id = ?", (evaluation_id,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


def get_evaluations_df() -> pd.DataFrame:
    """
    Return all evaluations joined to player names, ordered newest-first.
    Includes physical_score, production_score, and context_score columns.
    """
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT pe.*, p.name AS player_name
            FROM player_evaluations pe
            JOIN players p ON p.id = pe.player_id
            ORDER BY pe.evaluated_at DESC
            """,
            conn,
        )


# ---------------------------------------------------------------------------
# Player comparisons
# ---------------------------------------------------------------------------

def insert_player_comparison(
    evaluation_id: int,
    final_score: float,
    confidence: float,
    recency_weight: float,
    physical_score: float,
    physical_height: float,
    physical_weight: float,
    production_score: float,
    production_stats_used: int,
    production_stats_missing: int,
    context_score: float,
    context_recruit: float,
    context_comp: float,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT OR REPLACE INTO player_comparisons (
                evaluation_id, final_score, confidence, recency_weight,
                physical_score, physical_height, physical_weight,
                production_score, production_stats_used, production_stats_missing,
                context_score, context_recruit, context_comp
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                evaluation_id, final_score, confidence, recency_weight,
                physical_score, physical_height, physical_weight,
                production_score, production_stats_used, production_stats_missing,
                context_score, context_recruit, context_comp,
            ),
        )
        _log_conn(conn, "insert_player_comparison", f"eval_id={evaluation_id}, final={final_score:.4f}")
        return cur.lastrowid


def get_comparison_for_evaluation(evaluation_id: int) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT pc.*, p.name AS player_name
            FROM player_comparisons pc
            JOIN player_evaluations pe ON pe.id = pc.evaluation_id
            JOIN players            p  ON p.id  = pe.player_id
            WHERE pc.evaluation_id = ?
            """,
            conn,
            params=(evaluation_id,),
        )


def get_all_comparisons_df() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT pc.*, p.name AS player_name, pe.evaluated_at
            FROM player_comparisons pc
            JOIN player_evaluations pe ON pe.id = pc.evaluation_id
            JOIN players            p  ON p.id  = pe.player_id
            ORDER BY pc.final_score DESC
            """,
            conn,
        )


# ---------------------------------------------------------------------------
# Schemes (shortlists)
# ---------------------------------------------------------------------------

def insert_scheme(user_id: int, name: str, color: str = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO schemes (user_id, name, color) VALUES (?, ?, ?)",
            (user_id, name, color),
        )
        _log_conn(conn, "insert_scheme", f"name={name}, user_id={user_id}, color={color}")
        return cur.lastrowid


def delete_scheme(scheme_id: int):
    with get_conn() as conn:
        conn.execute(
            """
            DELETE FROM scheme_assignments
            WHERE scheme_position_id IN (
                SELECT id FROM scheme_positions WHERE scheme_id = ?
            )
            """,
            (scheme_id,),
        )
        conn.execute(
            "DELETE FROM scheme_positions WHERE scheme_id = ?",
            (scheme_id,),
        )
        conn.execute("DELETE FROM schemes WHERE id = ?", (scheme_id,))
    log("delete_scheme", f"id={scheme_id}")


def insert_scheme_position(
    scheme_id: int,
    slot_number: int,
    position_id: int = None,
    archetype_id: int = None,
) -> int:
    """
    Add a slot to a scheme.  Exactly one of position_id / archetype_id must be set.
    slot_number must be 1-11.
    """
    if not (1 <= slot_number <= 11):
        raise ValueError("slot_number must be between 1 and 11.")
    if (position_id is None) == (archetype_id is None):
        raise ValueError("Exactly one of position_id or archetype_id must be provided.")

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO scheme_positions
                (scheme_id, position_id, archetype_id, slot_number)
            VALUES (?, ?, ?, ?)
            """,
            (scheme_id, position_id, archetype_id, slot_number),
        )
        return cur.lastrowid


def assign_recruit_to_scheme_position(scheme_position_id: int, player_id: int):
    """Assign a recruit to a scheme slot. Raises if the player is not a recruit."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT is_recruit FROM players WHERE id = ?", (player_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"No player found with id={player_id}.")
        if row[0] != 1:
            raise ValueError(
                f"Player id={player_id} is a historical player and cannot be assigned to a scheme."
            )
        conn.execute(
            """
            INSERT OR REPLACE INTO scheme_assignments (scheme_position_id, player_id)
            VALUES (?, ?)
            """,
            (scheme_position_id, player_id),
        )
    log("assign_recruit_to_scheme_position",
        f"slot={scheme_position_id}, player={player_id}")


def remove_recruit_from_scheme_position(scheme_position_id: int):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM scheme_assignments WHERE scheme_position_id = ?",
            (scheme_position_id,),
        )
    log("remove_recruit_from_scheme_position", f"slot={scheme_position_id}")


def get_scheme_lineup(scheme_id: int) -> pd.DataFrame:
    """
    Returns the full lineup for a scheme, including unfilled slots.
    Slots backed by an archetype show the archetype title instead of a position name.
    """
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT
                sp.slot_number,
                COALESCE(pos.name, arc.title) AS slot_label,
                CASE WHEN arc.id IS NOT NULL THEN 'archetype' ELSE 'position' END AS slot_type,
                p.name                         AS player_name,
                p.team_name,
                CASE WHEN p.id IS NULL THEN 'OPEN' ELSE 'FILLED' END AS status
            FROM scheme_positions sp
            LEFT JOIN positions          pos ON pos.id = sp.position_id
            LEFT JOIN archetypes         arc ON arc.id = sp.archetype_id
            LEFT JOIN scheme_assignments sa  ON sa.scheme_position_id = sp.id
            LEFT JOIN players            p   ON p.id  = sa.player_id
            WHERE sp.scheme_id = ?
            ORDER BY sp.slot_number
            """,
            conn,
            params=(scheme_id,),
        )


def get_all_schemes_df() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM schemes ORDER BY name", conn)


# ---------------------------------------------------------------------------
# Activity log queries
# ---------------------------------------------------------------------------

def get_recent_activity(limit: int = 50) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT * FROM log_activity
            ORDER BY activity_time DESC
            LIMIT ?
            """,
            conn,
            params=(limit,),
        )


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def get_table_df(table_name: str) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)


def custom_query_df(query: str, params=None) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(query, conn, params=params or ())


# ---------------------------------------------------------------------------
# Example / smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()

    # --- Positions ---
    qb_id = get_or_create_position("QB")
    rb_id = get_or_create_position("RB")
    wr_id = get_or_create_position("WR")
    ol_id = get_or_create_position("OL")

    # --- Stats ---
    pass_yds_id = insert_stat("passing_yards", position_id=qb_id)
    rush_yds_id = insert_stat("rushing_yards", position_id=rb_id)

    # --- Stat rule + archetype ---
    rule_id = insert_stat_rule(pass_yds_id, minimum_value=3000.0)
    arch_id = insert_archetype(
        title="Pocket Passer",
        position_id=qb_id,
        notes="Classic drop-back QB; must hit 3000+ passing yards.",
        stat_rule_id=rule_id,
    )

    # --- Players ---
    brady_id = insert_player(
        "Tom Brady", position_id=qb_id, is_recruit=False,
        notes="Historical reference player.",
        height=76.0, weight=225.0,
        school_name="Michigan", state_code="MI",
        recruit_type="college", school_strength="elite",
        play_year=2000, frequency_player="starter",
    )
    mahomes_id = insert_player(
        "Patrick Mahomes", position_id=qb_id, is_recruit=True,
        height=74.0, weight=227.0,
        school_name="Texas Tech", state_code="TX",
        recruit_type="college", school_strength="strong",
        play_year=2024, frequency_player="starter",
    )

    # Columns: name, team, pos_id, is_recruit, notes,
    #          height, weight, school_name, state_code, recruit_type,
    #          school_strength, transfer_conference, play_year, frequency_player
    bulk_insert_players([
        ("Derrick Henry",       "Falcons", rb_id, True, None,
         71.0, 247.0, "Alabama",   "AL", "college",  "elite",   None,   2024, "starter"),
        ("Christian McCaffrey", None,      rb_id, True, None,
         71.0, 205.0, "Stanford",  "CA", "college",  "elite",   None,   2024, "starter"),
        ("Justin Jefferson",    None,      wr_id, True, "Elite route runner.",
         73.0, 195.0, "LSU",       "LA", "college",  "elite",   None,   2024, "starter"),
        ("Tyreek Hill",         None,      wr_id, True, None,
         70.0, 185.0, "West Ala.", "AL", "transfer", "average", "SWAC", 2024, "starter"),
    ])

    # --- Player stats ---
    insert_player_stat(brady_id,   pass_yds_id, 4500.0)
    insert_player_stat(mahomes_id, pass_yds_id, 5250.0)

    # --- Evaluation + comparison for Mahomes (now includes score fields) ---
    eval_id = insert_player_evaluation(
        mahomes_id,
        height=74.0,              # inches
        weight=227.0,             # lbs
        context_multiplier=1.43,
        confidence=100.0,
        physical_score=0.5417,
        production_score=0.0,
        context_score=0.2778,
    )

    insert_player_comparison(
        evaluation_id=eval_id,
        final_score=0.1365,
        confidence=100.0,
        recency_weight=0.5,
        physical_score=0.5417,
        physical_height=0.5,
        physical_weight=0.5833,
        production_score=0.0,
        production_stats_used=0,
        production_stats_missing=0,
        context_score=0.2778,
        context_recruit=1.43,
        context_comp=1.3,
    )

    # --- Scheme with mixed position / archetype slots ---
    scheme_id = insert_scheme(1, "Spread Offense")

    sp_qb    = insert_scheme_position(scheme_id, 1, position_id=qb_id)
    sp_arch  = insert_scheme_position(scheme_id, 2, archetype_id=arch_id)
    sp_rb    = insert_scheme_position(scheme_id, 3, position_id=rb_id)

    assign_recruit_to_scheme_position(sp_qb, mahomes_id)

    # --- Verify outputs ---
    print("\n=== Scheme Lineup ===")
    print(get_scheme_lineup(scheme_id).to_string(index=False))

    print("\n=== Recruits ===")
    print(get_recruits_df().to_string(index=False))

    print("\n=== Historical Players ===")
    print(get_historical_players_df().to_string(index=False))

    print("\n=== Comparisons ===")
    print(get_all_comparisons_df().to_string(index=False))

    print("\n=== Archetypes ===")
    print(get_archetypes_df().to_string(index=False))

    print("\n=== Evaluations (with score fields) ===")
    print(get_evaluations_df().to_string(index=False))

    print("\n=== Recent Activity Log ===")
    print(get_recent_activity(10).to_string(index=False))

    print("\n✓ All tests passed.")
