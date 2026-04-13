import sqlite3
import pandas as pd
from contextlib import contextmanager

DB_NAME = "hashmark_players.db"

# ---------------------------
# Connection Helper
# ---------------------------
@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---------------------------
# Initialize Database
# ---------------------------
def init_db():
    with get_conn() as conn:
        cursor = conn.cursor()

        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            team_name TEXT,
            position_id INTEGER,
            FOREIGN KEY (position_id) REFERENCES positions(id)
        );

        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position_id INTEGER,
            FOREIGN KEY (position_id) REFERENCES positions(id)
        );

        CREATE TABLE IF NOT EXISTS player_stats (
            player_id INTEGER,
            stat_id INTEGER,
            value REAL,
            PRIMARY KEY (player_id, stat_id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (stat_id) REFERENCES stats(id)
        );

        CREATE TABLE IF NOT EXISTS schemes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT
        );

        CREATE TABLE IF NOT EXISTS scheme_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_id INTEGER,
            position_id INTEGER,
            slot_number INTEGER,
            FOREIGN KEY (scheme_id) REFERENCES schemes(id),
            FOREIGN KEY (position_id) REFERENCES positions(id)
        );

        CREATE TABLE IF NOT EXISTS scheme_assignments (
            scheme_position_id INTEGER PRIMARY KEY,
            player_id INTEGER,
            FOREIGN KEY (scheme_position_id) REFERENCES scheme_positions(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );
        """)


# ---------------------------
# INSERT FUNCTIONS
# ---------------------------
def insert_position(name):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO positions (name) VALUES (?)", (name,))
        return cursor.lastrowid


def insert_player(name, team_name=None, position_id=None):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO players (name, team_name, position_id) VALUES (?, ?, ?)",
            (name, team_name, position_id),
        )
        return cursor.lastrowid


def insert_stat(name, position_id=None):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO stats (name, position_id) VALUES (?, ?)",
            (name, position_id),
        )
        return cursor.lastrowid


def insert_player_stat(player_id, stat_id, value):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO player_stats (player_id, stat_id, value)
            VALUES (?, ?, ?)
        """, (player_id, stat_id, value))


def insert_scheme(user_id, name):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO schemes (user_id, name) VALUES (?, ?)",
            (user_id, name),
        )
        return cursor.lastrowid


def insert_scheme_position(scheme_id, position_id, slot_number):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scheme_positions (scheme_id, position_id, slot_number)
            VALUES (?, ?, ?)
        """, (scheme_id, position_id, slot_number))
        return cursor.lastrowid


def assign_player_to_scheme_position(scheme_position_id, player_id):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO scheme_assignments (scheme_position_id, player_id)
            VALUES (?, ?)
        """, (scheme_position_id, player_id))


# ---------------------------
# UPDATE FUNCTIONS
# ---------------------------
def update_player(player_id, name=None, team_name=None, position_id=None):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE players
            SET name = COALESCE(?, name),
                team_name = COALESCE(?, team_name),
                position_id = COALESCE(?, position_id)
            WHERE id = ?
        """, (name, team_name, position_id, player_id))


def update_stat(stat_id, name=None, position_id=None):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE stats
            SET name = COALESCE(?, name),
                position_id = COALESCE(?, position_id)
            WHERE id = ?
        """, (name, position_id, stat_id))


# ---------------------------
# DELETE FUNCTIONS
# ---------------------------
def delete_player(player_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM players WHERE id = ?", (player_id,))


def delete_position(position_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))


def delete_scheme(scheme_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM schemes WHERE id = ?", (scheme_id,))


# ---------------------------
# QUERY FUNCTIONS
# ---------------------------
def get_scheme_lineup(scheme_id):
    with get_conn() as conn:
        query = """
        SELECT sp.slot_number, p.name, pos.name AS position
        FROM scheme_positions sp
        JOIN scheme_assignments sa ON sa.scheme_position_id = sp.id
        JOIN players p ON p.id = sa.player_id
        JOIN positions pos ON pos.id = sp.position_id
        WHERE sp.scheme_id = ?
        ORDER BY sp.slot_number;
        """
        return pd.read_sql_query(query, conn, params=(scheme_id,))


def get_table_df(table_name):
    with get_conn() as conn:
        return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)


def custom_query_df(query, params=None):
    with get_conn() as conn:
        return pd.read_sql_query(query, conn, params=params or ())
    
def get_all_players_with_stats():
    with get_conn() as conn:
        query = """
        SELECT 
            p.id AS player_id,
            p.name AS player_name,
            p.team_name AS team_name,
            s.name AS stat_name,
            ps.value
        FROM players p
        LEFT JOIN player_stats ps ON ps.player_id = p.id
        LEFT JOIN stats s ON s.id = ps.stat_id
        ORDER BY p.name;
        """
        return pd.read_sql_query(query, conn)
    
def get_players_stats_pivot():
    df = get_all_players_with_stats()
    pivot = df.pivot_table(
        index=["player_id", "player_name", "team_name"],
        columns="stat_name",
        values="value"
    ).reset_index()
    return pivot

def get_players_with_stats_by_position(position_name):
    with get_conn() as conn:
        query = """
        SELECT 
            p.name AS player_name,
            s.name AS stat_name,
            ps.value
        FROM players p
        JOIN positions pos ON pos.id = p.position_id
        LEFT JOIN player_stats ps ON ps.player_id = p.id
        LEFT JOIN stats s ON s.id = ps.stat_id
        WHERE pos.name = ?
        """
        return pd.read_sql_query(query, conn, params=(position_name,))
    
def get_stat_id(stat_name, position_id=None):
    with get_conn() as conn:
        cursor = conn.cursor()

        if position_id:
            cursor.execute("""
                SELECT id FROM stats
                WHERE name = ? AND position_id = ?
            """, (stat_name, position_id))
        else:
            cursor.execute("""
                SELECT id FROM stats
                WHERE name = ?
            """, (stat_name,))

        result = cursor.fetchone()
        return result[0] if result else None
    
def get_position_id_by_name(position_name):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM positions WHERE name = ?",
            (position_name,)
        )
        result = cursor.fetchone()
        return result[0] if result else None
    
# Create position if it doesn't already exist
def get_or_create_position(position_name):
    with get_conn() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM positions WHERE name = ?",
            (position_name,)
        )
        result = cursor.fetchone()

        if result:
            return result[0]

        cursor.execute(
            "INSERT INTO positions (name) VALUES (?)",
            (position_name,)
        )
        return cursor.lastrowid

# ---------------------------
# BULK INSERT (OPTIONAL)
# ---------------------------
def bulk_insert_players(players):
    """
    players = [(name, team_name, position_id), ...]
    """
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO players (name, team_name, position_id) VALUES (?, ?, ?)",
            players
        )


# ---------------------------
# EXAMPLE USAGE
# ---------------------------
if __name__ == "__main__":
    init_db()

    # These are integers representing the id position. If coaches want to create more niche positions 
    # (sub positions of each type, for example) they will be able to.
    qb_id = insert_position("QB")
    rb_id = insert_position("RB")
    wr_id = insert_position("WR")

    player_id = insert_player("Tom Brady", position_id=qb_id)

    # Bulk Insert New Players Into Database (without stats, probably will not be used often)
    players = [
        ("Patrick Mahomes", None, qb_id),
        ("Derrick Henry", "The Falcons", rb_id),
        ("Christian McCaffrey", None, rb_id),
        ("Justin Jefferson", None, wr_id),
        ("Tyreek Hill", None, wr_id),
    ]
    bulk_insert_players(players)

    stat_id = insert_stat("passing_yards", position_id=qb_id)
    insert_player_stat(player_id, stat_id, 4500)

    print("ID of passing yards stat for Quarter-Backs: ", get_stat_id("passing_yards", qb_id))

    scheme_id = insert_scheme(1, "Offense Scheme")

    sp_id = insert_scheme_position(scheme_id, qb_id, 1)
    assign_player_to_scheme_position(sp_id, player_id)

    df = get_scheme_lineup(scheme_id)
    print(df)

    df = get_all_players_with_stats()
    print(df)

    df = get_players_stats_pivot()
    print(df)

    df = get_players_with_stats_by_position("QB")
    print(df)

    print("Tests Complete")

