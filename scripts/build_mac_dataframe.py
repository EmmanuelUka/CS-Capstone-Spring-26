import json
from pathlib import Path

import pandas as pd

INPUT_FILE = Path("mac_players_bio_and_stats_15_years.json")
OUTPUT_PICKLE = Path("mac_players_dataframe.pkl")
OUTPUT_CSV = Path("mac_players_dataframe.csv")


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


def build_dataframe(records):
    rows = [flatten_record(record) for record in records]
    df = pd.DataFrame(rows)
    df = convert_numeric_columns(df)
    df = df.sort_values(["season", "team", "player"], kind="stable").reset_index(drop=True)
    return df


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        records = json.load(f)

    df = build_dataframe(records)

    df.to_pickle(OUTPUT_PICKLE)
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"Built DataFrame with shape: {df.shape}")
    print(f"Saved pickle: {OUTPUT_PICKLE}")
    print(f"Saved csv: {OUTPUT_CSV}")
    print()
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
