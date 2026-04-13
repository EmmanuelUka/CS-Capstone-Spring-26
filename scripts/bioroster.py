import json
import time
from datetime import datetime
import requests

API_KEY = "0q5yclRoF68+1bcVGqlIR8wsGbGXKPTz9AX+UfgYMkt1D4NyjaU67TD3gIsbEvFp"

ROSTER_URL = "https://api.collegefootballdata.com/roster"
STATS_URL = "https://api.collegefootballdata.com/stats/player/season"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
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
    "UMass"
}

current_year = datetime.now().year
years = range(current_year - 15, current_year)

merged = {}

def make_key(season, player_id, team):
    return f"{season}|{player_id}|{team}"

def get_or_create_record(season, player_id, player_name, team):
    key = make_key(season, player_id, team)
    if key not in merged:
        merged[key] = {
            "season": season,
            "playerId": player_id,
            "player": player_name,
            "team": team,
            "position": None,
            "conference": "MAC",
            "bio": {},
            "stats": {}
        }
    return merged[key]

print("Pulling FBS rosters and filtering to MAC...")
for year in years:
    print(f"Roster: {year}")

    r = requests.get(
        ROSTER_URL,
        headers=HEADERS,
        params={
            "year": year,
            "classification": "fbs"
        },
        timeout=30
    )

    print("  Status:", r.status_code)

    if r.status_code != 200:
        print("  Error:", r.text[:300])
        continue

    data = r.json()
    print("  Rows returned:", len(data))

    mac_rows = [row for row in data if row.get("team") in MAC_TEAMS]
    print("  MAC rows:", len(mac_rows))

    for row in mac_rows:
        player_id = str(row.get("id", "")).strip()
        first = str(row.get("firstName", "")).strip()
        last = str(row.get("lastName", "")).strip()
        full_name = f"{first} {last}".strip()
        team = row.get("team", "")
        position = row.get("position")

        rec = get_or_create_record(year, player_id, full_name, team)
        rec["position"] = rec["position"] or position

        rec["bio"] = {
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
            "recruitIds": row.get("recruitIds", [])
        }

    time.sleep(0.25)

print("\nPulling MAC player season stats...")
for year in years:
    print(f"Stats: {year}")

    r = requests.get(
        STATS_URL,
        headers=HEADERS,
        params={
            "year": year,
            "conference": "MAC"
        },
        timeout=30
    )

    print("  Status:", r.status_code)

    if r.status_code != 200:
        print("  Error:", r.text[:300])
        continue

    data = r.json()
    print("  Rows returned:", len(data))

    for row in data:
        season = row.get("season", year)
        player_id = str(row.get("playerId", "")).strip()
        player_name = row.get("player", "")
        team = row.get("team", "")
        position = row.get("position")
        category = row.get("category", "unknown")
        stat_type = row.get("statType", "unknown")
        stat_value = row.get("stat")

        rec = get_or_create_record(season, player_id, player_name, team)
        rec["position"] = rec["position"] or position
        rec["conference"] = row.get("conference", "MAC")

        if category not in rec["stats"]:
            rec["stats"][category] = {}

        rec["stats"][category][stat_type] = stat_value

    time.sleep(0.25)

merged_list = list(merged.values())

with open("mac_players_bio_and_stats_15_years.json", "w", encoding="utf-8") as f:
    json.dump(merged_list, f, indent=2)

print()
print(f"Saved {len(merged_list)} merged player-season rows")
print("Output: mac_players_bio_and_stats_15_years.json")
print(f"Approx requests used: {len(list(years)) * 2}")