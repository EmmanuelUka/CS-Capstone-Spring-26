import hashmark_db as hdb
import pandas as pd
import math

# ---------------------------------------------------------------------------
# Position → stat column mapping
# ---------------------------------------------------------------------------

POSITION_STATS: dict[str, list[str]] = {
    "QB": [
        "stat_passing_YDS", "stat_passing_TD", "stat_passing_PCT",
        "stat_passing_YPA", "stat_passing_INT", "stat_rushing_YDS",
        "stat_rushing_TD",
    ],
    "WR": [
        "stat_receiving_YDS", "stat_receiving_TD", "stat_receiving_REC",
        "stat_receiving_YPR", "stat_receiving_LONG",
    ],
    "TE": [
        "stat_receiving_YDS", "stat_receiving_TD", "stat_receiving_REC",
        "stat_receiving_YPR",
    ],
    "RB": [
        "stat_rushing_YDS", "stat_rushing_TD", "stat_rushing_CAR",
        "stat_rushing_YPC", "stat_rushing_LONG",
        "stat_receiving_REC", "stat_receiving_YDS",
    ],
    "FB": [
        "stat_rushing_YDS", "stat_rushing_TD", "stat_rushing_CAR",
        "stat_receiving_REC",
    ],
    "OL": [],
    "OT": [],
    "LS": [],
    "PK": [
        "stat_kicking_FGM", "stat_kicking_FGA", "stat_kicking_PCT",
        "stat_kicking_LONG", "stat_kicking_PTS", "stat_kicking_XPM",
    ],
    "DL": [
        "stat_defensive_SACKS", "stat_defensive_TOT", "stat_defensive_SOLO",
        "stat_defensive_TFL", "stat_defensive_QB_HUR",
    ],
    "DT": [
        "stat_defensive_SACKS", "stat_defensive_TOT", "stat_defensive_SOLO",
        "stat_defensive_TFL",
    ],
    "DE": [
        "stat_defensive_SACKS", "stat_defensive_TOT", "stat_defensive_SOLO",
        "stat_defensive_TFL", "stat_defensive_QB_HUR",
    ],
    "LB": [
        "stat_defensive_TOT", "stat_defensive_SOLO", "stat_defensive_TFL",
        "stat_defensive_SACKS", "stat_defensive_PD", "stat_defensive_TD",
    ],
    "CB": [
        "stat_interceptions_INT", "stat_interceptions_YDS",
        "stat_defensive_PD", "stat_defensive_SOLO", "stat_defensive_TOT",
    ],
    "S": [
        "stat_interceptions_INT", "stat_interceptions_YDS",
        "stat_defensive_PD", "stat_defensive_TOT", "stat_defensive_SOLO",
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _float(v):
    """Return float or None — treats NaN/NA as None."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _int(v):
    f = _float(v)
    return int(f) if f is not None else None


def _str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s and s.lower() not in ("nan", "none", "") else None


# ---------------------------------------------------------------------------
# Main import
# ---------------------------------------------------------------------------

def load_csv(path: str = "mac_players_dataframe.csv"):
    df = pd.read_csv(path, low_memory=False)
    print(f"Loaded {len(df)} rows from '{path}'")

    # ------------------------------------------------------------------
    # Build all insert data in memory first
    # ------------------------------------------------------------------

    # These will be populated as we encounter new positions/stats in the data.
    position_names: dict[str, None] = {}         # ordered set of positions seen
    stat_keys: dict[tuple[str, str], None] = {}  # (stat_name, pos_name) seen with real data

    # player_rows  : list of dicts for the players table
    # player_stats : list of (player_index, stat_name, pos_name, value)
    player_rows  = []
    player_stats = []
    skipped      = 0

    for _, row in df.iterrows():
        pos_name = _str(row.get("position")) or _str(row.get("bio_position"))
        if not pos_name:
            skipped += 1
            continue

        position_names[pos_name] = None  # record that this position exists in data

        player_rows.append({
            "name"       : _str(row.get("player")) or "Unknown",
            "team_name"  : _str(row.get("team")),
            "pos_name"   : pos_name,
            "height"     : _float(row.get("bio_height")),
            "weight"     : _float(row.get("bio_weight")),
            "school_name": _str(row.get("team")),
            "state_code" : _str(row.get("bio_homeState")),
            "play_year"  : _int(row.get("season")),
        })

        player_idx = len(player_rows) - 1

        # Only collect stats that have an actual value in this row
        for col in POSITION_STATS.get(pos_name, []):
            if col not in df.columns:
                continue
            val = _float(row.get(col))
            if val is None:
                continue
            stat_keys[(col, pos_name)] = None  # mark this stat as needed
            player_stats.append((player_idx, col, pos_name, val))

    print(f"Parsed {len(player_rows)} players, {len(player_stats)} stat values "
          f"({skipped} rows skipped — no position).")
    print(f"Unique positions in data : {len(position_names)}")
    print(f"Unique (stat, position) pairs with data: {len(stat_keys)}")

    # ------------------------------------------------------------------
    # Single transaction — write everything at once
    # ------------------------------------------------------------------

    with hdb.get_conn() as conn:

        # 1. Upsert only the positions that actually appear in the data
        pos_id: dict[str, int] = {}
        for pos_name in position_names:
            row_db = conn.execute(
                "SELECT id FROM positions WHERE name = ?", (pos_name,)
            ).fetchone()
            if row_db:
                pos_id[pos_name] = row_db[0]
            else:
                cur = conn.execute(
                    "INSERT INTO positions (name) VALUES (?)", (pos_name,)
                )
                pos_id[pos_name] = cur.lastrowid

        # 2. Upsert only the (stat, position) pairs that have real data
        stat_id: dict[tuple[str, str], int] = {}
        for (stat_name, p_name) in stat_keys:
            pid = pos_id[p_name]
            row_db = conn.execute(
                "SELECT id FROM stats WHERE name = ? AND position_id = ?",
                (stat_name, pid),
            ).fetchone()
            if row_db:
                stat_id[(stat_name, p_name)] = row_db[0]
            else:
                cur = conn.execute(
                    "INSERT INTO stats (name, position_id) VALUES (?, ?)",
                    (stat_name, pid),
                )
                stat_id[(stat_name, p_name)] = cur.lastrowid

        # 3. Insert all players, capture their new IDs in order
        player_ids = []
        for p in player_rows:
            cur = conn.execute(
                """
                INSERT INTO players (
                    name, team_name, position_id, is_recruit,
                    height, weight, school_name, state_code, play_year
                ) VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?)
                """,
                (
                    p["name"], p["team_name"], pos_id[p["pos_name"]],
                    p["height"], p["weight"],
                    p["school_name"], p["state_code"], p["play_year"],
                ),
            )
            player_ids.append(cur.lastrowid)

        # 4. Insert all stat values in one executemany call
        stat_rows = [
            (player_ids[pidx], stat_id[(sname, pname)], val)
            for pidx, sname, pname, val in player_stats
        ]
        conn.executemany(
            "INSERT OR REPLACE INTO player_stats (player_id, stat_id, value) VALUES (?, ?, ?)",
            stat_rows,
        )

        # 5. Single log entry for the whole import
        conn.execute(
            "INSERT INTO log_activity (activity_name, activity_notes) VALUES (?, ?)",
            ("bulk_import_csv", f"file={path}, players={len(player_ids)}, stats={len(stat_rows)}"),
        )

    print(f"Committed — {len(player_ids)} players, {len(stat_rows)} stat rows.")


if __name__ == '__main__':
    hdb.init_db()
    load_csv("mac_players_dataframe.csv")

    import hashmark_tests
    hashmark_tests.print_db_state("hashmark_players.db")