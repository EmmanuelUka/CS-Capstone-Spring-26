import json
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

API_KEY = os.getenv(
    "CFBD_API_KEY",
    "0q5yclRoF68+1bcVGqlIR8wsGbGXKPTz9AX+UfgYMkt1D4NyjaU67TD3gIsbEvFp",
)

ROSTER_URL = "https://api.collegefootballdata.com/roster"
STATS_URL = "https://api.collegefootballdata.com/stats/player/season"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
}

MAC_TEAMS = {
    "Akron",
    "Ball State",
    "Bowling Green",
    "Buffalo",
    "Central Michigan",
    "Eastern Michigan",
    "Kent State",
    "Miami (OH)",
    "Northern Illinois",
    "Ohio",
    "Toledo",
    "Western Michigan",
    "UMass",
}

CURRENT_YEAR = datetime.now().year
YEARS = range(CURRENT_YEAR - 15, CURRENT_YEAR)

RAW_STATS_FILE = Path("mac_player_stats_raw.json")
PIVOTED_STATS_FILE = Path("mac_player_stats_pivoted.json")
MERGED_FILE = Path("mac_players_bio_and_stats_15_years.json")
DATAFRAME_PICKLE = Path("mac_players_dataframe.pkl")
DATAFRAME_CSV = Path("mac_players_dataframe.csv")


def make_player_key(season, player_id, team):
    return f"{season}|{player_id}|{team}"


def get_or_create_player_record(merged, season, player_id, player_name, team):
    key = make_player_key(season, player_id, team)
    if key not in merged:
        merged[key] = {
            "season": season,
            "playerId": player_id,
            "player": player_name,
            "team": team,
            "position": None,
            "conference": "MAC",
            "bio": {},
            "stats": {},
        }
    return merged[key]


def fetch_json(url, params):
    response = requests.get(url, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_mac_rosters(merged):
    print("Pulling FBS rosters and filtering to MAC...")
    for year in YEARS:
        print(f"Roster: {year}")
        rows = fetch_json(
            ROSTER_URL,
            {
                "year": year,
                "classification": "fbs",
            },
        )

        mac_rows = [row for row in rows if row.get("team") in MAC_TEAMS]
        print(f"  Returned: {len(rows)} total, {len(mac_rows)} MAC")

        for row in mac_rows:
            player_id = str(row.get("id", "")).strip()
            first = str(row.get("firstName", "")).strip()
            last = str(row.get("lastName", "")).strip()
            full_name = f"{first} {last}".strip()
            team = row.get("team", "")
            position = row.get("position")

            record = get_or_create_player_record(merged, year, player_id, full_name, team)
            record["position"] = record["position"] or position
            record["bio"] = {
                "firstName": row.get("firstName"),
                "lastName": row.get("lastName"),
                "height": row.get("height"),
                "weight": row.get("weight"),
                "jersey": row.get("jersey"),
                "position": row.get("position"),
                "homeCity": row.get("homeCity"),
                "homeState": row.get("homeState"),
                "homeCountry": row.get("homeCountry"),
                "homeLatitude": row.get("homeLatitude"),
                "homeLongitude": row.get("homeLongitude"),
                "homeCountyFIPS": row.get("homeCountyFIPS"),
                "recruitIds": row.get("recruitIds", []),
            }

        time.sleep(0.25)


def fetch_mac_player_stats(merged):
    print("\nPulling MAC player season stats...")
    raw_stats = []
    pivoted_stats = {}

    for year in YEARS:
        print(f"Stats: {year}")
        rows = fetch_json(
            STATS_URL,
            {
                "year": year,
                "conference": "MAC",
            },
        )
        print(f"  Returned: {len(rows)} rows")

        for row in rows:
            row["year"] = year
            raw_stats.append(row)

            season = row.get("season", year)
            player_id = str(row.get("playerId", "")).strip()
            player_name = row.get("player", "")
            team = row.get("team", "")
            position = row.get("position")
            category = row.get("category", "unknown")
            stat_type = row.get("statType", "unknown")
            stat_value = row.get("stat")

            record = get_or_create_player_record(merged, season, player_id, player_name, team)
            record["position"] = record["position"] or position
            record["conference"] = row.get("conference", "MAC")

            if category not in record["stats"]:
                record["stats"][category] = {}
            record["stats"][category][stat_type] = stat_value

            pivot_key = make_player_key(season, player_id, team)
            if pivot_key not in pivoted_stats:
                pivoted_stats[pivot_key] = {
                    "season": season,
                    "playerId": player_id,
                    "player": player_name,
                    "position": position,
                    "team": team,
                    "conference": row.get("conference", "MAC"),
                    "stats": {},
                }

            if category not in pivoted_stats[pivot_key]["stats"]:
                pivoted_stats[pivot_key]["stats"][category] = {}
            pivoted_stats[pivot_key]["stats"][category][stat_type] = stat_value

        time.sleep(0.25)

    return raw_stats, list(pivoted_stats.values())


def make_stat_column(category, stat_type):
    category_part = str(category).strip().replace(" ", "_")
    stat_part = str(stat_type).strip().replace(" ", "_")
    return f"stat_{category_part}_{stat_part}"


def flatten_record(record):
    flattened = {
        "season": record.get("season"),
        "playerId": record.get("playerId"),
        "player": record.get("player"),
        "team": record.get("team"),
        "position": record.get("position"),
        "conference": record.get("conference"),
    }

    bio = record.get("bio") or {}
    for key, value in bio.items():
        if key == "recruitIds":
            flattened["bio_recruitIds"] = "|".join(str(item) for item in value)
            flattened["bio_recruitIds_count"] = len(value)
            continue
        flattened[f"bio_{key}"] = value

    stats = record.get("stats") or {}
    for category, stat_block in stats.items():
        if not isinstance(stat_block, dict):
            continue
        for stat_type, value in stat_block.items():
            flattened[make_stat_column(category, stat_type)] = value

    return flattened


def convert_numeric_columns(df):
    skip_columns = {
        "playerId",
        "player",
        "team",
        "position",
        "conference",
        "bio_firstName",
        "bio_lastName",
        "bio_position",
        "bio_homeCity",
        "bio_homeState",
        "bio_homeCountry",
        "bio_homeCountyFIPS",
        "bio_recruitIds",
    }

    for column in df.columns:
        if column in skip_columns:
            continue
        converted = pd.to_numeric(df[column], errors="coerce")
        if converted.notna().sum() == df[column].notna().sum():
            df[column] = converted

    return df


def build_dataframe(merged_records):
    rows = [flatten_record(record) for record in merged_records]
    df = pd.DataFrame(rows)
    df = convert_numeric_columns(df)
    return df.sort_values(["season", "team", "player"], kind="stable").reset_index(drop=True)


def write_json(path, payload):
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2)


def main():
    if not API_KEY:
        raise RuntimeError("Missing API key. Set CFBD_API_KEY in your environment.")

    merged = {}

    fetch_mac_rosters(merged)
    raw_stats, pivoted_stats = fetch_mac_player_stats(merged)

    merged_records = list(merged.values())
    df = build_dataframe(merged_records)

    write_json(RAW_STATS_FILE, raw_stats)
    write_json(PIVOTED_STATS_FILE, pivoted_stats)
    write_json(MERGED_FILE, merged_records)
    df.to_pickle(DATAFRAME_PICKLE)
    df.to_csv(DATAFRAME_CSV, index=False)

    print("\nFinished.")
    print(f"Saved raw stats: {RAW_STATS_FILE}")
    print(f"Saved pivoted stats: {PIVOTED_STATS_FILE}")
    print(f"Saved merged records: {MERGED_FILE}")
    print(f"Saved DataFrame pickle: {DATAFRAME_PICKLE}")
    print(f"Saved DataFrame csv: {DATAFRAME_CSV}")
    print(f"DataFrame shape: {df.shape}")


if __name__ == "__main__":
    main()
