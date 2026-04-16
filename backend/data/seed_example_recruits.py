"""
Seed 50 example recruits across all supported positions.

Usage:
    python backend/data/seed_example_recruits.py
"""

from __future__ import annotations

import hashmark_db as hdb

SEED_NAME_PREFIX = "Example Recruit"

POSITIONS = [
    "QB", "WR", "TE", "RB", "FB", "OL", "OT", "LS",
    "PK", "DL", "DT", "DE", "LB", "CB", "S",
]

POSITION_STATS = {
    "QB": [
        "stat_passing_YDS", "stat_passing_TD", "stat_passing_PCT",
        "stat_passing_YPA", "stat_passing_INT", "stat_rushing_YDS", "stat_rushing_TD",
    ],
    "WR": [
        "stat_receiving_YDS", "stat_receiving_TD", "stat_receiving_REC",
        "stat_receiving_YPR", "stat_receiving_LONG",
    ],
    "TE": [
        "stat_receiving_YDS", "stat_receiving_TD", "stat_receiving_REC", "stat_receiving_YPR",
    ],
    "RB": [
        "stat_rushing_YDS", "stat_rushing_TD", "stat_rushing_CAR", "stat_rushing_YPC",
        "stat_rushing_LONG", "stat_receiving_REC", "stat_receiving_YDS",
    ],
    "FB": [
        "stat_rushing_YDS", "stat_rushing_TD", "stat_rushing_CAR", "stat_receiving_REC",
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
        "stat_defensive_SACKS", "stat_defensive_TOT", "stat_defensive_SOLO", "stat_defensive_TFL",
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

STATE_CODES = [
    "TX", "FL", "CA", "GA", "OH", "MI", "PA", "NC", "AL", "LA",
    "TN", "VA", "AZ", "NJ", "SC", "IN", "OK", "KY", "MO", "WA",
]
RECRUIT_TYPES = ["high_school", "transfer"]


def value_for_stat(stat_name: str, seed: int) -> float:
    """Create deterministic sample stat values."""
    if stat_name.endswith("_YDS"):
        return float(200 + (seed * 37) % 1400)
    if stat_name.endswith("_TD"):
        return float(2 + (seed * 3) % 22)
    if stat_name.endswith("_REC"):
        return float(10 + (seed * 5) % 90)
    if stat_name.endswith("_CAR"):
        return float(25 + (seed * 7) % 220)
    if stat_name.endswith("_YPR"):
        return round(8.0 + (seed % 10) * 0.9, 2)
    if stat_name.endswith("_YPC"):
        return round(3.2 + (seed % 10) * 0.35, 2)
    if stat_name.endswith("_LONG"):
        return float(18 + (seed * 2) % 70)
    if stat_name.endswith("_PCT"):
        return round(48.0 + (seed % 40) * 1.1, 2)
    if stat_name.endswith("_YPA"):
        return round(5.0 + (seed % 16) * 0.35, 2)
    if stat_name.endswith("_INT"):
        return float((seed % 6) + 1)
    if stat_name.endswith("_FGM"):
        return float(8 + (seed * 2) % 20)
    if stat_name.endswith("_FGA"):
        return float(10 + (seed * 2) % 24)
    if stat_name.endswith("_PTS"):
        return float(30 + (seed * 5) % 110)
    if stat_name.endswith("_XPM"):
        return float(12 + (seed * 3) % 35)
    if stat_name.endswith("_SACKS"):
        return float(1 + (seed * 2) % 15)
    if stat_name.endswith("_TOT"):
        return float(20 + (seed * 4) % 90)
    if stat_name.endswith("_SOLO"):
        return float(10 + (seed * 3) % 55)
    if stat_name.endswith("_TFL"):
        return float(2 + (seed * 2) % 20)
    if stat_name.endswith("_QB_HUR"):
        return float(1 + (seed * 2) % 18)
    if stat_name.endswith("_PD"):
        return float(1 + (seed * 2) % 14)
    return float(1 + seed % 10)


def cleanup_previous_seed() -> None:
    existing = hdb.custom_query_df(
        "SELECT id FROM players WHERE name LIKE ?",
        (f"{SEED_NAME_PREFIX} %",),
    )
    if existing is None or existing.empty:
        return

    for player_id in existing["id"].tolist():
        hdb.delete_player(int(player_id))


def seed() -> None:
    cleanup_previous_seed()

    position_ids: dict[str, int] = {
        position: hdb.get_or_create_position(position)
        for position in POSITIONS
    }

    stat_ids: dict[tuple[str, str], int] = {}
    for position, stat_names in POSITION_STATS.items():
        position_id = position_ids[position]
        for stat_name in stat_names:
            stat_id = hdb.get_stat_id(stat_name, position_id)
            if stat_id is None:
                stat_id = hdb.insert_stat(stat_name, position_id)
            stat_ids[(position, stat_name)] = stat_id

    per_position_counts = {position: 3 for position in POSITIONS}
    for position in POSITIONS[:5]:
        per_position_counts[position] += 1

    created = 0
    position_coverage: set[str] = set()
    for pos_index, position in enumerate(POSITIONS):
        for offset in range(per_position_counts[position]):
            created += 1
            seed_index = pos_index * 10 + offset + 1
            recruit_type = RECRUIT_TYPES[seed_index % len(RECRUIT_TYPES)]

            player_id = hdb.insert_player(
                name=f"{SEED_NAME_PREFIX} {created:02d} {position}",
                position_id=position_ids[position],
                is_recruit=True,
                notes=f"{position} prospect with sample baseline + position stats.",
                height=69.0 + float((seed_index + pos_index) % 10),
                weight=175.0 + float((seed_index * 7 + pos_index * 3) % 145),
                school_name=f"Example School {(seed_index % 20) + 1}",
                state_code=STATE_CODES[seed_index % len(STATE_CODES)],
                recruit_type=recruit_type,
                play_year=2027 + (seed_index % 3),
            )

            position_coverage.add(position)
            for stat_name in POSITION_STATS[position]:
                hdb.insert_player_stat(
                    player_id=player_id,
                    stat_id=stat_ids[(position, stat_name)],
                    value=value_for_stat(stat_name, seed_index),
                )

    hdb.log(
        "seed_example_recruits",
        f"seeded={created}, positions={len(position_coverage)}",
    )

    print(f"Database: {hdb.get_db_path()}")
    print(f"Seeded recruits: {created}")
    print(f"Positions represented: {len(position_coverage)} / {len(POSITIONS)}")


if __name__ == "__main__":
    seed()
