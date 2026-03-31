import json
import time
from datetime import datetime

import requests

API_KEY = "0q5yclRoF68+1bcVGqlIR8wsGbGXKPTz9AX+UfgYMkt1D4NyjaU67TD3gIsbEvFp"
URL = "https://api.collegefootballdata.com/stats/player/season"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

CONFERENCE = "MAC"

current_year = datetime.now().year
years = range(current_year - 15, current_year)

raw_stats = []
pivoted_stats = {}

for year in years:
    print(f"Fetching {year}...")

    response = requests.get(
        URL,
        headers=headers,
        params={
            "year": year,
            "conference": CONFERENCE
        },
        timeout=30
    )

    print("Status:", response.status_code)

    if response.status_code != 200:
        print("Error body:", response.text[:500])
        continue

    data = response.json()
    print("Rows returned:", len(data))

    for row in data:
        row["year"] = year
        raw_stats.append(row)

        season = row.get("season", year)
        player_id = row.get("playerId", "")
        player_name = row.get("player", "")
        position = row.get("position", "")
        team = row.get("team", "")
        conference = row.get("conference", "")
        category = row.get("category", "")
        stat_type = row.get("statType", "")
        stat_value = row.get("stat", "")

        key = f"{season}|{player_id}|{team}"

        if key not in pivoted_stats:
            pivoted_stats[key] = {
                "season": season,
                "playerId": player_id,
                "player": player_name,
                "position": position,
                "team": team,
                "conference": conference,
                "stats": {}
            }

        if category not in pivoted_stats[key]["stats"]:
            pivoted_stats[key]["stats"][category] = {}

        pivoted_stats[key]["stats"][category][stat_type] = stat_value

    time.sleep(0.25)

pivoted_list = list(pivoted_stats.values())

with open("mac_player_stats_raw.json", "w", encoding="utf-8") as f:
    json.dump(raw_stats, f, indent=2)

with open("mac_player_stats_pivoted.json", "w", encoding="utf-8") as f:
    json.dump(pivoted_list, f, indent=2)

print()
print(f"Saved {len(raw_stats)} raw stat rows to mac_player_stats_raw.json")
print(f"Saved {len(pivoted_list)} player-season rows to mac_player_stats_pivoted.json")