"""
test_eval.py
------------
Manual test harness for eval_system.py.
Run with: python test_eval.py

Tests four scenarios:
    1. High school WR from Texas (elite school)
    2. Transfer QB from SEC (starter)
    3. High school OL (no production stats — physical only)
    4. Missing data — low confidence scenario
"""

from playerEval import (
    Recruit,
    CareerProfile,
    build_career_profiles,
    evaluate,
    EvaluationResult,
    PlayerMatch,
)


# ---------------------------------------------------------------------------
# Fake DB rows — simulating what build_career_profiles() receives from Flask
# These represent raw YearInstance rows as dicts (one row per season per player)
# ---------------------------------------------------------------------------

RAW_DB_ROWS = [

    # --- WR pool ---

    # Player A: 3 seasons as WR in SEC
    {
        "player_id": "wr_001", "player": "Marcus Hill", "position": "WR",
        "season": 2021, "bio_height": 73.0, "bio_weight": 190.0,
        "conference": "SEC", "bio_homeState": "Georgia",
        "stat_receiving_YDS": 750.0, "stat_receiving_TD": 7.0,
        "stat_receiving_REC": 58.0,  "stat_receiving_YPR": 12.9,
        "stat_receiving_LONG": 54.0,
    },
    {
        "player_id": "wr_001", "player": "Marcus Hill", "position": "WR",
        "season": 2022, "bio_height": 73.0, "bio_weight": 192.0,
        "conference": "SEC", "bio_homeState": "Georgia",
        "stat_receiving_YDS": 900.0, "stat_receiving_TD": 9.0,
        "stat_receiving_REC": 68.0,  "stat_receiving_YPR": 13.2,
        "stat_receiving_LONG": 61.0,
    },
    {
        "player_id": "wr_001", "player": "Marcus Hill", "position": "WR",
        "season": 2023, "bio_height": 73.0, "bio_weight": 192.0,
        "conference": "SEC", "bio_homeState": "Georgia",
        "stat_receiving_YDS": 1100.0, "stat_receiving_TD": 11.0,
        "stat_receiving_REC": 78.0,   "stat_receiving_YPR": 14.1,
        "stat_receiving_LONG": 70.0,
    },

    # Player B: 2 seasons as WR in MAC
    {
        "player_id": "wr_002", "player": "DeShawn Brooks", "position": "WR",
        "season": 2022, "bio_height": 71.0, "bio_weight": 178.0,
        "conference": "MAC", "bio_homeState": "Ohio",
        "stat_receiving_YDS": 620.0, "stat_receiving_TD": 5.0,
        "stat_receiving_REC": 52.0,  "stat_receiving_YPR": 11.9,
        "stat_receiving_LONG": 45.0,
    },
    {
        "player_id": "wr_002", "player": "DeShawn Brooks", "position": "WR",
        "season": 2023, "bio_height": 71.0, "bio_weight": 180.0,
        "conference": "MAC", "bio_homeState": "Ohio",
        "stat_receiving_YDS": 710.0, "stat_receiving_TD": 6.0,
        "stat_receiving_REC": 60.0,  "stat_receiving_YPR": 11.8,
        "stat_receiving_LONG": 48.0,
    },

    # Player C: 1 season WR in Big Ten (older — recency penalty)
    {
        "player_id": "wr_003", "player": "Tyler Owens", "position": "WR",
        "season": 2018, "bio_height": 74.0, "bio_weight": 205.0,
        "conference": "Big Ten", "bio_homeState": "Ohio",
        "stat_receiving_YDS": 980.0, "stat_receiving_TD": 10.0,
        "stat_receiving_REC": 72.0,  "stat_receiving_YPR": 13.6,
        "stat_receiving_LONG": 65.0,
    },

    # --- QB pool ---

    # Player D: 2 seasons QB in Big 12
    {
        "player_id": "qb_001", "player": "Jordan Reeves", "position": "QB",
        "season": 2022, "bio_height": 75.0, "bio_weight": 215.0,
        "conference": "Big 12", "bio_homeState": "Texas",
        "stat_passing_YDS": 3200.0, "stat_passing_TD": 28.0,
        "stat_passing_PCT": 64.5,   "stat_passing_YPA": 8.1,
        "stat_passing_INT": 7.0,    "stat_rushing_YDS": 310.0,
        "stat_rushing_TD": 4.0,
    },
    {
        "player_id": "qb_001", "player": "Jordan Reeves", "position": "QB",
        "season": 2023, "bio_height": 75.0, "bio_weight": 217.0,
        "conference": "Big 12", "bio_homeState": "Texas",
        "stat_passing_YDS": 3600.0, "stat_passing_TD": 32.0,
        "stat_passing_PCT": 66.2,   "stat_passing_YPA": 8.6,
        "stat_passing_INT": 5.0,    "stat_rushing_YDS": 280.0,
        "stat_rushing_TD": 5.0,
    },

    # Player E: 1 season QB in Sun Belt
    {
        "player_id": "qb_002", "player": "Malik James", "position": "QB",
        "season": 2023, "bio_height": 74.0, "bio_weight": 205.0,
        "conference": "Sun Belt", "bio_homeState": "Alabama",
        "stat_passing_YDS": 2400.0, "stat_passing_TD": 18.0,
        "stat_passing_PCT": 60.0,   "stat_passing_YPA": 7.2,
        "stat_passing_INT": 9.0,    "stat_rushing_YDS": 450.0,
        "stat_rushing_TD": 6.0,
    },

    # --- OL pool ---

    # Player F: OL in ACC (no stat fields — physical only)
    {
        "player_id": "ol_001", "player": "Brandon Cole", "position": "OL",
        "season": 2023, "bio_height": 77.0, "bio_weight": 308.0,
        "conference": "ACC", "bio_homeState": "Florida",
    },
    {
        "player_id": "ol_002", "player": "Darius Penn", "position": "OL",
        "season": 2023, "bio_height": 78.0, "bio_weight": 320.0,
        "conference": "SEC", "bio_homeState": "Georgia",
    },
]


# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------

def print_result(result: EvaluationResult) -> None:
    print(f"\n{'=' * 60}")
    print(f"  Recruit:  {result.recruit_name}")
    print(f"  Position: {result.position}   Type: {result.recruit_type}")
    print(f"  Compared against {result.total_compared} historical players")
    print(f"{'=' * 60}")

    if not result.top_matches:
        print("  No comparable players found.\n")
        return

    for rank, match in enumerate(result.top_matches, start=1):
        print(f"\n  #{rank}  {match.name}  (id: {match.player_id})")
        print(f"       Final score:    {match.final_score:.4f}")
        print(f"       Confidence:     {match.confidence:.2%}")
        print(f"       Recency weight: {match.recency_weight:.4f}")
        print(f"       Physical:       {match.physical.score:.4f}"
              f"  (h={match.physical.height_sim}, w={match.physical.weight_sim})")
        print(f"       Production:     {match.production.score:.4f}"
              f"  ({match.production.fields_used} stats used,"
              f" {match.production.fields_missing} missing)")
        print(f"       Context:        {match.context.score:.4f}"
              f"  (recruit={match.context.recruit_multiplier},"
              f" comp={match.context.comparable_multiplier})")
        if match.production.stat_similarities:
            sims = match.production.stat_similarities
            top_stat = max(sims, key=sims.get)
            print(f"       Best stat match: {top_stat} = {sims[top_stat]:.4f}")
    print()


# ---------------------------------------------------------------------------
# Build career profiles once — shared across all tests
# ---------------------------------------------------------------------------

career_profiles = build_career_profiles(RAW_DB_ROWS)


# ---------------------------------------------------------------------------
# Test 1: High school WR — Texas, elite school
# Strong state + elite program should match best against SEC/Big Ten WRs
# ---------------------------------------------------------------------------

def test_hs_wr():
    print("\n[TEST 1] High school WR — Texas, elite school")
    recruit = Recruit(
        name="Jaylen Carter",
        position="WR",
        season=2024,
        recruit_type="highschool",
        home_state="Texas",
        hs_school_strength="elite",
        height=73.5,
        weight=188.0,
        stats={
            "stat_receiving_YDS":  950.0,
            "stat_receiving_TD":   10.0,
            "stat_receiving_REC":  65.0,
            "stat_receiving_YPR":  14.6,
            "stat_receiving_LONG": 68.0,
        },
    )
    result = evaluate(recruit, career_profiles, top_n=3)
    print_result(result)


# ---------------------------------------------------------------------------
# Test 2: Transfer QB — SEC starter
# High conference + starter modifier → expect strong match vs Big 12 QB
# ---------------------------------------------------------------------------

def test_transfer_qb():
    print("\n[TEST 2] Transfer QB — SEC starter")
    recruit = Recruit(
        name="Devon Price",
        position="QB",
        season=2024,
        recruit_type="transfer",
        transfer_conference="SEC",
        transfer_playing_time="starter_p5",
        height=76.0,
        weight=218.0,
        stats={
            "stat_passing_YDS": 3400.0,
            "stat_passing_TD":  30.0,
            "stat_passing_PCT": 65.0,
            "stat_passing_YPA": 8.4,
            "stat_passing_INT": 6.0,
            "stat_rushing_YDS": 290.0,
            "stat_rushing_TD":  4.0,
        },
    )
    result = evaluate(recruit, career_profiles, top_n=3)
    print_result(result)


# ---------------------------------------------------------------------------
# Test 3: High school OL — Florida, strong school
# No production stats — physical score carries everything
# ---------------------------------------------------------------------------

def test_hs_ol():
    print("\n[TEST 3] High school OL — Florida, strong school (no production stats)")
    recruit = Recruit(
        name="Terrell Washington",
        position="OL",
        season=2024,
        recruit_type="highschool",
        home_state="Florida",
        hs_school_strength="strong",
        height=77.5,
        weight=315.0,
        stats={},   # no measurable production stats for OL
    )
    result = evaluate(recruit, career_profiles, top_n=3)
    print_result(result)


# ---------------------------------------------------------------------------
# Test 4: Transfer QB — low data, expect low confidence
# Missing most stats — confidence score should be noticeably reduced
# ---------------------------------------------------------------------------

def test_low_confidence_qb():
    print("\n[TEST 4] Transfer QB — sparse data (low confidence expected)")
    recruit = Recruit(
        name="Unknown Transfer",
        position="QB",
        season=2024,
        recruit_type="transfer",
        transfer_conference="JUCO",
        transfer_playing_time="starter_d2",
        height=74.0,
        weight=None,   # missing
        stats={
            "stat_passing_YDS": 1800.0,
            # most stats missing
        },
    )
    result = evaluate(recruit, career_profiles, top_n=3)
    print_result(result)


# ---------------------------------------------------------------------------
# Test 5: Custom weights — scout prioritizes context heavily
# ---------------------------------------------------------------------------

def test_custom_weights():
    print("\n[TEST 5] Same WR recruit as Test 1 but scout-defined weights")
    print("         weights: physical=0.20, production=0.30, context=0.50")
    recruit = Recruit(
        name="Jaylen Carter",
        position="WR",
        season=2024,
        recruit_type="highschool",
        home_state="Texas",
        hs_school_strength="elite",
        height=73.5,
        weight=188.0,
        stats={
            "stat_receiving_YDS":  950.0,
            "stat_receiving_TD":   10.0,
            "stat_receiving_REC":  65.0,
            "stat_receiving_YPR":  14.6,
            "stat_receiving_LONG": 68.0,
        },
    )
    result = evaluate(
        recruit,
        career_profiles,
        weights={"physical": 0.20, "production": 0.30, "context": 0.50},
        top_n=3,
    )
    print_result(result)


# ---------------------------------------------------------------------------
# Test 6: Position with no comparables in DB
# ---------------------------------------------------------------------------

def test_no_comparables():
    print("\n[TEST 6] Position with no DB comparables (CB)")
    recruit = Recruit(
        name="Some Corner",
        position="CB",
        season=2024,
        recruit_type="highschool",
        home_state="Florida",
        hs_school_strength="average",
        height=71.0,
        weight=175.0,
        stats={"stat_defensive_PD": 8.0, "stat_interceptions_INT": 3.0},
    )
    result = evaluate(recruit, career_profiles, top_n=3)
    print_result(result)


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\nEval system test run")
    print(f"Career profiles built: {len(career_profiles)}")
    for cp in career_profiles:
        print(f"  {cp.player_id:10s}  {cp.name:20s}  {cp.position:4s}  "
              f"last_season={cp.last_season}  "
              f"h={cp.height} w={cp.weight}  conf={cp.conference}")

    test_hs_wr()
    test_transfer_qb()
    test_hs_ol()
    test_low_confidence_qb()
    test_custom_weights()
    test_no_comparables()

    print("All tests complete.\n")