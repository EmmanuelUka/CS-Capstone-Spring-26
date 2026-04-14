"""
hashmark_tests.py
-----------------
Test cases for every public function in hashmark_db.py, plus a
print_db_state() utility that prints a full human-readable snapshot
of the current database.

Run with:
    python hashmark_tests.py
"""

import os
import sys
import traceback
import sqlite3
import pandas as pd

# ---------------------------------------------------------------------------
# Point at a throw-away test DB so tests never touch production data
# ---------------------------------------------------------------------------
import hashmark_db as db

TEST_DB = "hashmark_test.db"
db.DB_NAME = TEST_DB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS  = "\033[92m✓\033[0m"
FAIL  = "\033[91m✗\033[0m"
HEAD  = "\033[1;94m"
RESET = "\033[0m"
SEP   = "─" * 60

_results: list[tuple[str, bool, str]] = []


def run_test(name: str, fn):
    """Run fn(); record pass/fail; never abort the suite."""
    try:
        fn()
        _results.append((name, True, ""))
        print(f"  {PASS}  {name}")
    except Exception as exc:
        msg = traceback.format_exc(limit=3)
        _results.append((name, False, msg))
        print(f"  {FAIL}  {name}")
        print(f"       {exc}")


def section(title: str):
    print(f"\n{HEAD}{SEP}")
    print(f"  {title}")
    print(f"{SEP}{RESET}")


def assert_eq(label, actual, expected):
    assert actual == expected, f"{label}: expected {expected!r}, got {actual!r}"


def assert_true(label, value):
    assert value, f"{label} was falsy"


def assert_raises(exc_type, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
        raise AssertionError(f"Expected {exc_type.__name__} but no exception was raised.")
    except exc_type:
        pass


def fresh_db():
    """Wipe and re-initialise the test DB between test groups."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    db.init_db()


# ===========================================================================
# TEST GROUPS
# ===========================================================================

# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------
def test_init_db():
    section("init_db")

    def t_creates_tables():
        fresh_db()
        conn = sqlite3.connect(TEST_DB)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        expected = {
            "positions", "stats", "stat_rules", "archetypes",
            "players", "player_stats", "player_evaluations",
            "player_comparisons", "schemes", "scheme_positions",
            "scheme_assignments", "log_activity",
        }
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"

    def t_idempotent():
        db.init_db()   # second call must not raise
        db.init_db()

    run_test("creates all 12 tables", t_creates_tables)
    run_test("calling init_db twice is safe", t_idempotent)


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------
def test_positions():
    section("Positions")
    fresh_db()

    def t_insert():
        pid = db.insert_position("QB")
        assert_true("insert returns int id", isinstance(pid, int) and pid > 0)

    def t_get_position_id():
        pid = db.get_position_id("QB")
        assert_true("get_position_id returns int", isinstance(pid, int))

    def t_get_position_id_missing():
        assert_eq("missing position returns None", db.get_position_id("ZZ"), None)

    def t_get_or_create_existing():
        pid1 = db.get_or_create_position("QB")
        pid2 = db.get_or_create_position("QB")
        assert_eq("same id on second call", pid1, pid2)

    def t_get_or_create_new():
        pid = db.get_or_create_position("RB")
        assert_true("new position gets an id", pid > 0)

    def t_delete_position():
        pid = db.insert_position("TEMP")
        db.delete_position(pid)
        assert_eq("deleted position not found", db.get_position_id("TEMP"), None)

    run_test("insert_position returns valid id", t_insert)
    run_test("get_position_id finds existing", t_get_position_id)
    run_test("get_position_id returns None for unknown", t_get_position_id_missing)
    run_test("get_or_create_position is idempotent", t_get_or_create_existing)
    run_test("get_or_create_position creates new", t_get_or_create_new)
    run_test("delete_position removes row", t_delete_position)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
def test_stats():
    section("Stats")
    fresh_db()
    qb_id = db.get_or_create_position("QB")

    def t_insert_with_position():
        sid = db.insert_stat("passing_yards", position_id=qb_id)
        assert_true("stat id > 0", sid > 0)

    def t_insert_universal():
        sid = db.insert_stat("games_played")
        assert_true("universal stat id > 0", sid > 0)

    def t_get_stat_id_with_position():
        db.insert_stat("touchdowns", position_id=qb_id)
        sid = db.get_stat_id("touchdowns", position_id=qb_id)
        assert_true("found by name + position", sid is not None)

    def t_get_stat_id_without_position():
        sid = db.get_stat_id("games_played")
        assert_true("found by name alone", sid is not None)

    def t_get_stat_id_missing():
        assert_eq("missing stat returns None", db.get_stat_id("interceptions"), None)

    def t_update_stat():
        sid = db.insert_stat("old_name")
        db.update_stat(sid, name="new_name")
        new_sid = db.get_stat_id("new_name")
        assert_eq("stat renamed successfully", new_sid, sid)

    run_test("insert_stat with position", t_insert_with_position)
    run_test("insert_stat universal (no position)", t_insert_universal)
    run_test("get_stat_id with position_id", t_get_stat_id_with_position)
    run_test("get_stat_id without position_id", t_get_stat_id_without_position)
    run_test("get_stat_id returns None for unknown", t_get_stat_id_missing)
    run_test("update_stat renames the stat", t_update_stat)


# ---------------------------------------------------------------------------
# Stat rules
# ---------------------------------------------------------------------------
def test_stat_rules():
    section("Stat Rules")
    fresh_db()
    qb_id  = db.get_or_create_position("QB")
    sid    = db.insert_stat("passing_yards", position_id=qb_id)

    def t_insert():
        rid = db.insert_stat_rule(sid, 3000.0)
        assert_true("rule id > 0", rid > 0)

    def t_get_stat_rules_df():
        db.insert_stat_rule(sid, 3000.0)
        df = db.get_stat_rules_df()
        assert_true("returns DataFrame", isinstance(df, pd.DataFrame))
        assert_true("has rows", len(df) > 0)
        assert_true("has stat_name column", "stat_name" in df.columns)
        assert_true("has minimum_value column", "minimum_value" in df.columns)

    run_test("insert_stat_rule returns valid id", t_insert)
    run_test("get_stat_rules_df returns correct shape", t_get_stat_rules_df)


# ---------------------------------------------------------------------------
# Archetypes
# ---------------------------------------------------------------------------
def test_archetypes():
    section("Archetypes")
    fresh_db()
    qb_id = db.get_or_create_position("QB")
    sid   = db.insert_stat("passing_yards", position_id=qb_id)
    rid   = db.insert_stat_rule(sid, 3000.0)

    def t_insert_full():
        aid = db.insert_archetype("Pocket Passer", position_id=qb_id,
                                  notes="Classic QB", stat_rule_id=rid)
        assert_true("archetype id > 0", aid > 0)

    def t_insert_minimal():
        aid = db.insert_archetype("Generic Role")
        assert_true("minimal archetype id > 0", aid > 0)

    def t_get_archetypes_df():
        df = db.get_archetypes_df()
        assert_true("returns DataFrame", isinstance(df, pd.DataFrame))
        assert_true("has title column", "title" in df.columns)

    def t_update_archetype():
        aid = db.insert_archetype("Old Title")
        db.update_archetype(aid, title="New Title", notes="Updated notes")
        df = db.get_archetypes_df()
        titles = df["title"].tolist()
        assert_true("title was updated", "New Title" in titles)
        assert_true("old title gone", "Old Title" not in titles)

    def t_delete_archetype():
        aid = db.insert_archetype("To Delete")
        db.delete_archetype(aid)
        df = db.get_archetypes_df()
        assert_true("deleted archetype not in df", "To Delete" not in df["title"].tolist())

    run_test("insert_archetype with all fields", t_insert_full)
    run_test("insert_archetype minimal (title only)", t_insert_minimal)
    run_test("get_archetypes_df returns DataFrame", t_get_archetypes_df)
    run_test("update_archetype changes title and notes", t_update_archetype)
    run_test("delete_archetype removes row", t_delete_archetype)


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------
def test_players():
    section("Players")
    fresh_db()
    qb_id = db.get_or_create_position("QB")
    rb_id = db.get_or_create_position("RB")

    def t_insert_recruit_all_fields():
        pid = db.insert_player(
            "Patrick Mahomes", position_id=qb_id, is_recruit=True,
            notes="Elite arm talent.",
            height=74.0, weight=227.0,
            school_name="Texas Tech", state_code="TX",
            recruit_type="college", school_strength="strong",
            play_year=2024, frequency_player="starter",
        )
        assert_true("recruit id > 0", pid > 0)
        row = db.custom_query_df("SELECT * FROM players WHERE id = ?", (pid,))
        assert_eq("height stored",           row.iloc[0]["height"],           74.0)
        assert_eq("weight stored",           row.iloc[0]["weight"],           227.0)
        assert_eq("school_name stored",      row.iloc[0]["school_name"],      "Texas Tech")
        assert_eq("state_code stored",       row.iloc[0]["state_code"],       "TX")
        assert_eq("recruit_type stored",     row.iloc[0]["recruit_type"],     "college")
        assert_eq("school_strength stored",  row.iloc[0]["school_strength"],  "strong")
        assert_eq("play_year stored",        row.iloc[0]["play_year"],        2024)
        assert_eq("frequency_player stored", row.iloc[0]["frequency_player"], "starter")

    def t_insert_recruit_minimal():
        pid = db.insert_player("Backup Bob", position_id=qb_id, is_recruit=True)
        assert_true("minimal recruit id > 0", pid > 0)
        row = db.custom_query_df("SELECT height, school_name FROM players WHERE id = ?", (pid,))
        assert_eq("height is None when omitted", row.iloc[0]["height"], None)
        assert_eq("school_name is None when omitted", row.iloc[0]["school_name"], None)

    def t_insert_historical():
        pid = db.insert_player(
            "Joe Montana", position_id=qb_id, is_recruit=False,
            height=76.0, weight=200.0,
            school_name="Notre Dame", state_code="PA",
            recruit_type="college", school_strength="elite",
            play_year=1989, frequency_player="starter",
        )
        assert_true("historical id > 0", pid > 0)

    def t_insert_transfer_with_conference():
        pid = db.insert_player(
            "Transfer Tommy", position_id=qb_id, is_recruit=True,
            recruit_type="transfer", school_strength="average",
            transfer_conference="Big 12", play_year=2024,
            frequency_player="backup",
        )
        row = db.custom_query_df("SELECT transfer_conference FROM players WHERE id = ?", (pid,))
        assert_eq("transfer_conference stored", row.iloc[0]["transfer_conference"], "Big 12")

    def t_insert_high_school_recruit():
        pid = db.insert_player(
            "HS Star", position_id=qb_id, is_recruit=True,
            school_name="Central High", state_code="OH",
            recruit_type="high_school", school_strength="weak",
            play_year=2024, frequency_player="starter",
        )
        row = db.custom_query_df("SELECT recruit_type, school_strength FROM players WHERE id = ?", (pid,))
        assert_eq("recruit_type high_school", row.iloc[0]["recruit_type"], "high_school")
        assert_eq("school_strength weak",     row.iloc[0]["school_strength"], "weak")

    def t_insert_invalid_recruit_type():
        assert_raises(ValueError, db.insert_player, "Bad Type",
                      position_id=qb_id, recruit_type="pro")

    def t_insert_invalid_school_strength():
        assert_raises(ValueError, db.insert_player, "Bad Strength",
                      position_id=qb_id, school_strength="legendary")

    def t_insert_invalid_frequency_player():
        assert_raises(ValueError, db.insert_player, "Bad Freq",
                      position_id=qb_id, frequency_player="superstar")

    def t_bulk_insert_with_new_fields():
        before = len(db.get_recruits_df())
        # Columns: name, team, pos_id, is_recruit, notes,
        #          height, weight, school_name, state_code, recruit_type,
        #          school_strength, transfer_conference, play_year, frequency_player
        db.bulk_insert_players([
            ("Derrick Henry",       "Falcons", rb_id, True, None,
             71.0, 247.0, "Alabama",  "AL", "college",  "elite",   None, 2024, "starter"),
            ("Christian McCaffrey", None,      rb_id, True, "Dual threat",
             71.0, 205.0, "Stanford", "CA", "college",  "elite",   None, 2024, "starter"),
        ])
        after = len(db.get_recruits_df())
        assert_eq("two recruits added via bulk", after, before + 2)

    def t_bulk_insert_short_tuples_still_work():
        # Old-style short tuples (name only) must still work
        before = len(db.get_recruits_df())
        db.bulk_insert_players([("Short Tuple QB",)])
        after = len(db.get_recruits_df())
        assert_eq("short tuple inserted as recruit", after, before + 1)

    def t_bulk_insert_invalid_enum_raises():
        assert_raises(ValueError, db.bulk_insert_players, [
            ("Bad Bulk", None, rb_id, True, None,
             None, None, None, None, "invalid_type", None, None, None, None),
        ])

    def t_get_recruits_df_new_columns():
        db.insert_player("Mahomes2", position_id=qb_id, is_recruit=True,
                         height=74.0, school_name="Texas Tech", state_code="TX",
                         recruit_type="college", school_strength="strong",
                         play_year=2024, frequency_player="starter")
        df = db.get_recruits_df()
        expected_cols = {
            "name", "height", "weight", "school_name", "state_code",
            "recruit_type", "school_strength", "transfer_conference",
            "play_year", "frequency_player",
        }
        assert_true("all new columns present", expected_cols.issubset(set(df.columns)))

    def t_get_recruits_excludes_historical():
        db.insert_player("Joe Montana", position_id=qb_id, is_recruit=False)
        df = db.get_recruits_df()
        assert_true("Montana NOT in recruits", "Joe Montana" not in df["name"].tolist())

    def t_get_historical_df_new_columns():
        db.insert_player("Old Legend", position_id=qb_id, is_recruit=False,
                         height=75.0, school_name="Notre Dame", state_code="IN",
                         recruit_type="college", school_strength="elite",
                         play_year=1985, frequency_player="starter")
        df = db.get_historical_players_df()
        assert_true("historical has school_name col", "school_name" in df.columns)
        assert_true("Old Legend in historical", "Old Legend" in df["name"].tolist())

    def t_update_player_physical_fields():
        pid = db.insert_player("Update Me", position_id=qb_id, height=70.0, weight=200.0)
        db.update_player(pid, height=74.0, weight=215.0)
        row = db.custom_query_df("SELECT height, weight FROM players WHERE id = ?", (pid,))
        assert_eq("height updated",  row.iloc[0]["height"],  74.0)
        assert_eq("weight updated",  row.iloc[0]["weight"],  215.0)

    def t_update_player_school_fields():
        pid = db.insert_player("School Update", position_id=qb_id,
                               school_name="Old U", state_code="OH")
        db.update_player(pid, school_name="New U", state_code="CA",
                         recruit_type="transfer", school_strength="strong",
                         transfer_conference="ACC", play_year=2025,
                         frequency_player="backup")
        row = db.custom_query_df("SELECT * FROM players WHERE id = ?", (pid,))
        assert_eq("school_name updated",       row.iloc[0]["school_name"],         "New U")
        assert_eq("state_code updated",        row.iloc[0]["state_code"],          "CA")
        assert_eq("recruit_type updated",      row.iloc[0]["recruit_type"],        "transfer")
        assert_eq("school_strength updated",   row.iloc[0]["school_strength"],     "strong")
        assert_eq("transfer_conf updated",     row.iloc[0]["transfer_conference"], "ACC")
        assert_eq("play_year updated",         row.iloc[0]["play_year"],           2025)
        assert_eq("frequency_player updated",  row.iloc[0]["frequency_player"],    "backup")

    def t_update_player_convert_to_historical():
        pid = db.insert_player("Convert Me", position_id=qb_id, is_recruit=True)
        db.update_player(pid, is_recruit=False)
        row = db.custom_query_df("SELECT is_recruit FROM players WHERE id = ?", (pid,))
        assert_eq("is_recruit flipped to 0", row.iloc[0]["is_recruit"], 0)

    def t_update_player_invalid_enum_raises():
        pid = db.insert_player("Enum Guard", position_id=qb_id)
        assert_raises(ValueError, db.update_player, pid, frequency_player="legend")

    def t_delete_player():
        pid = db.insert_player("Delete Me", position_id=qb_id)
        db.delete_player(pid)
        row = db.custom_query_df("SELECT id FROM players WHERE id = ?", (pid,))
        assert_eq("player deleted", len(row), 0)

    run_test("insert_player recruit with all new fields",       t_insert_recruit_all_fields)
    run_test("insert_player recruit minimal (no new fields)",   t_insert_recruit_minimal)
    run_test("insert_player historical with new fields",        t_insert_historical)
    run_test("insert_player transfer with conference",          t_insert_transfer_with_conference)
    run_test("insert_player high_school recruit",               t_insert_high_school_recruit)
    run_test("insert_player rejects invalid recruit_type",      t_insert_invalid_recruit_type)
    run_test("insert_player rejects invalid school_strength",   t_insert_invalid_school_strength)
    run_test("insert_player rejects invalid frequency_player",  t_insert_invalid_frequency_player)
    run_test("bulk_insert_players with new fields",             t_bulk_insert_with_new_fields)
    run_test("bulk_insert_players short tuples still work",     t_bulk_insert_short_tuples_still_work)
    run_test("bulk_insert_players invalid enum raises",         t_bulk_insert_invalid_enum_raises)
    run_test("get_recruits_df includes all new columns",        t_get_recruits_df_new_columns)
    run_test("get_recruits_df excludes historical",             t_get_recruits_excludes_historical)
    run_test("get_historical_players_df includes new columns",  t_get_historical_df_new_columns)
    run_test("update_player updates physical fields",           t_update_player_physical_fields)
    run_test("update_player updates all school/context fields", t_update_player_school_fields)
    run_test("update_player convert recruit to historical",     t_update_player_convert_to_historical)
    run_test("update_player rejects invalid enum",              t_update_player_invalid_enum_raises)
    run_test("delete_player removes row",                       t_delete_player)


# ---------------------------------------------------------------------------
# Player stats
# ---------------------------------------------------------------------------
def test_player_stats():
    section("Player Stats")
    fresh_db()
    qb_id  = db.get_or_create_position("QB")
    rb_id  = db.get_or_create_position("RB")
    sid_p  = db.insert_stat("passing_yards", position_id=qb_id)
    sid_r  = db.insert_stat("rushing_yards", position_id=rb_id)
    p1     = db.insert_player("Mahomes", position_id=qb_id)
    p2     = db.insert_player("Henry",   position_id=rb_id)

    def t_insert_player_stat():
        db.insert_player_stat(p1, sid_p, 5250.0)
        df = db.get_all_players_with_stats()
        row = df[(df["player_id"] == p1) & (df["stat_name"] == "passing_yards")]
        assert_eq("stat value stored", row.iloc[0]["value"], 5250.0)

    def t_upsert_player_stat():
        db.insert_player_stat(p1, sid_p, 5250.0)
        db.insert_player_stat(p1, sid_p, 6000.0)   # should update
        df = db.get_all_players_with_stats()
        row = df[(df["player_id"] == p1) & (df["stat_name"] == "passing_yards")]
        assert_eq("upsert updates value", row.iloc[0]["value"], 6000.0)

    def t_get_all_players_with_stats():
        db.insert_player_stat(p2, sid_r, 1800.0)
        df = db.get_all_players_with_stats()
        assert_true("returns DataFrame", isinstance(df, pd.DataFrame))
        assert_true("has value column", "value" in df.columns)

    def t_get_players_stats_pivot():
        db.insert_player_stat(p1, sid_p, 5250.0)  # ensure at least one stat value exists
        pivot = db.get_players_stats_pivot()
        assert_true("pivot is DataFrame", isinstance(pivot, pd.DataFrame))
        assert_true("passing_yards column present", "passing_yards" in pivot.columns)

    def t_get_players_with_stats_by_position():
        df = db.get_players_with_stats_by_position("QB")
        names = df["player_name"].tolist()
        assert_true("QB player present", "Mahomes" in names)

    run_test("insert_player_stat stores value", t_insert_player_stat)
    run_test("insert_player_stat upserts on conflict", t_upsert_player_stat)
    run_test("get_all_players_with_stats returns data", t_get_all_players_with_stats)
    run_test("get_players_stats_pivot pivots correctly", t_get_players_stats_pivot)
    run_test("get_players_with_stats_by_position filters by position", t_get_players_with_stats_by_position)


# ---------------------------------------------------------------------------
# Player evaluations
# ---------------------------------------------------------------------------
def test_player_evaluations():
    section("Player Evaluations")
    fresh_db()
    qb_id = db.get_or_create_position("QB")
    pid   = db.insert_player("Recruit A", position_id=qb_id, is_recruit=True)

    def t_insert_evaluation():
        eid = db.insert_player_evaluation(pid, height=74.0, weight=220.0,
                                          context_multiplier=1.3, confidence=95.0)
        assert_true("eval id > 0", eid > 0)

    def t_evaluation_updates_player_fk():
        eid = db.insert_player_evaluation(pid, height=74.0, weight=220.0)
        row = db.custom_query_df("SELECT evaluation_id FROM players WHERE id = ?", (pid,))
        assert_eq("player.evaluation_id updated", row.iloc[0]["evaluation_id"], eid)

    def t_update_player_evaluation():
        eid = db.insert_player_evaluation(pid, height=72.0, weight=210.0)
        db.update_player_evaluation(eid, height=74.0, confidence=88.0)
        df  = db.custom_query_df("SELECT height, confidence FROM player_evaluations WHERE id = ?", (eid,))
        assert_eq("height updated", df.iloc[0]["height"], 74.0)
        assert_eq("confidence updated", df.iloc[0]["confidence"], 88.0)

    def t_get_evaluations_df():
        db.insert_player_evaluation(pid, height=74.0, weight=220.0)
        df = db.get_evaluations_df()
        assert_true("returns DataFrame", isinstance(df, pd.DataFrame))
        assert_true("has player_name column", "player_name" in df.columns)

    def t_get_evaluation_dict():
        eid = db.insert_player_evaluation(pid, height=73.0, weight=215.0,
                                          context_multiplier=1.1, confidence=80.0)
        result = db.get_evaluation(eid)
        assert_true("returns dict", isinstance(result, dict))
        assert_eq("height matches", result["height"], 73.0)

    run_test("insert_player_evaluation returns id", t_insert_evaluation)
    run_test("insert_player_evaluation updates player FK", t_evaluation_updates_player_fk)
    run_test("update_player_evaluation changes fields", t_update_player_evaluation)
    run_test("get_evaluations_df returns DataFrame", t_get_evaluations_df)
    run_test("get_evaluation returns dict", t_get_evaluation_dict)


# ---------------------------------------------------------------------------
# Player comparisons
# ---------------------------------------------------------------------------
def test_player_comparisons():
    section("Player Comparisons")
    fresh_db()
    qb_id = db.get_or_create_position("QB")
    pid   = db.insert_player("Recruit B", position_id=qb_id, is_recruit=True)
    eid   = db.insert_player_evaluation(pid, height=74.0, weight=225.0,
                                        context_multiplier=1.43, confidence=100.0)

    _COMP = dict(
        evaluation_id=eid,
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

    def t_insert_comparison():
        cid = db.insert_player_comparison(**_COMP)
        assert_true("comparison id > 0", cid > 0)

    def t_get_comparison_for_evaluation():
        db.insert_player_comparison(**_COMP)
        df = db.get_comparison_for_evaluation(eid)
        assert_true("returns DataFrame", isinstance(df, pd.DataFrame))
        assert_eq("final_score matches", round(df.iloc[0]["final_score"], 4), 0.1365)

    def t_get_all_comparisons_df():
        db.insert_player_comparison(**_COMP)
        df = db.get_all_comparisons_df()
        assert_true("returns DataFrame", isinstance(df, pd.DataFrame))
        assert_true("has player_name", "player_name" in df.columns)

    def t_upsert_comparison():
        db.insert_player_comparison(**_COMP)
        updated = {**_COMP, "final_score": 0.9999}
        db.insert_player_comparison(**updated)   # INSERT OR REPLACE
        df = db.get_comparison_for_evaluation(eid)
        assert_eq("final_score updated", round(df.iloc[0]["final_score"], 4), 0.9999)

    run_test("insert_player_comparison returns id", t_insert_comparison)
    run_test("get_comparison_for_evaluation returns correct row", t_get_comparison_for_evaluation)
    run_test("get_all_comparisons_df returns data", t_get_all_comparisons_df)
    run_test("insert_player_comparison upserts on conflict", t_upsert_comparison)


# ---------------------------------------------------------------------------
# Schemes
# ---------------------------------------------------------------------------
def test_schemes():
    section("Schemes")
    fresh_db()
    qb_id = db.get_or_create_position("QB")
    rb_id = db.get_or_create_position("RB")
    wr_id = db.get_or_create_position("WR")
    sid   = db.insert_stat("passing_yards", position_id=qb_id)
    rid   = db.insert_stat_rule(sid, 3000.0)
    arc_id= db.insert_archetype("Pocket Passer", position_id=qb_id, stat_rule_id=rid)

    recruit_id  = db.insert_player("Sam Recruit",  position_id=qb_id, is_recruit=True)
    historic_id = db.insert_player("Old Legend",   position_id=qb_id, is_recruit=False)

    def t_insert_scheme():
        scid = db.insert_scheme(user_id=1, name="4-3 Defense")
        assert_true("scheme id > 0", scid > 0)

    def t_get_all_schemes_df():
        db.insert_scheme(1, "Test Scheme")
        df = db.get_all_schemes_df()
        assert_true("returns DataFrame", isinstance(df, pd.DataFrame))
        assert_true("has name column", "name" in df.columns)

    def t_insert_scheme_position_by_position():
        scid = db.insert_scheme(1, "Spread")
        sp   = db.insert_scheme_position(scid, slot_number=1, position_id=qb_id)
        assert_true("sp id > 0", sp > 0)

    def t_insert_scheme_position_by_archetype():
        scid = db.insert_scheme(1, "Arch Scheme")
        sp   = db.insert_scheme_position(scid, slot_number=1, archetype_id=arc_id)
        assert_true("archetype slot id > 0", sp > 0)

    def t_insert_scheme_position_invalid_slot():
        scid = db.insert_scheme(1, "Bad Slot")
        assert_raises(ValueError, db.insert_scheme_position, scid, 12, position_id=qb_id)

    def t_insert_scheme_position_needs_one_of():
        scid = db.insert_scheme(1, "Bad Slot 2")
        assert_raises(ValueError, db.insert_scheme_position, scid, 1)  # neither given
        assert_raises(ValueError, db.insert_scheme_position, scid, 1,  # both given
                      position_id=qb_id, archetype_id=arc_id)

    def t_assign_recruit():
        scid = db.insert_scheme(1, "Recruit Scheme")
        sp   = db.insert_scheme_position(scid, 1, position_id=qb_id)
        db.assign_recruit_to_scheme_position(sp, recruit_id)
        df = db.get_scheme_lineup(scid)
        assert_eq("slot is FILLED", df.iloc[0]["status"], "FILLED")
        assert_eq("correct player", df.iloc[0]["player_name"], "Sam Recruit")

    def t_assign_historical_raises():
        scid = db.insert_scheme(1, "Hist Scheme")
        sp   = db.insert_scheme_position(scid, 1, position_id=qb_id)
        assert_raises(ValueError, db.assign_recruit_to_scheme_position, sp, historic_id)

    def t_remove_recruit_from_slot():
        scid = db.insert_scheme(1, "Remove Scheme")
        sp   = db.insert_scheme_position(scid, 1, position_id=qb_id)
        db.assign_recruit_to_scheme_position(sp, recruit_id)
        db.remove_recruit_from_scheme_position(sp)
        df = db.get_scheme_lineup(scid)
        assert_eq("slot is OPEN again", df.iloc[0]["status"], "OPEN")

    def t_get_scheme_lineup_open_slots():
        scid = db.insert_scheme(1, "Partial Lineup")
        db.insert_scheme_position(scid, 1, position_id=qb_id)
        db.insert_scheme_position(scid, 2, position_id=rb_id)
        db.insert_scheme_position(scid, 3, archetype_id=arc_id)
        df = db.get_scheme_lineup(scid)
        assert_eq("three slots returned", len(df), 3)
        assert_eq("all open", list(df["status"]), ["OPEN", "OPEN", "OPEN"])
        assert_eq("slot 3 is archetype type", df.iloc[2]["slot_type"], "archetype")

    def t_delete_scheme():
        scid = db.insert_scheme(1, "To Delete")
        db.delete_scheme(scid)
        df = db.get_all_schemes_df()
        assert_true("deleted scheme gone", "To Delete" not in df["name"].tolist())

    run_test("insert_scheme returns id", t_insert_scheme)
    run_test("get_all_schemes_df returns DataFrame", t_get_all_schemes_df)
    run_test("insert_scheme_position by position_id", t_insert_scheme_position_by_position)
    run_test("insert_scheme_position by archetype_id", t_insert_scheme_position_by_archetype)
    run_test("insert_scheme_position rejects slot > 11", t_insert_scheme_position_invalid_slot)
    run_test("insert_scheme_position requires exactly one of position/archetype", t_insert_scheme_position_needs_one_of)
    run_test("assign_recruit_to_scheme_position fills slot", t_assign_recruit)
    run_test("assign historical player raises ValueError", t_assign_historical_raises)
    run_test("remove_recruit_from_scheme_position empties slot", t_remove_recruit_from_slot)
    run_test("get_scheme_lineup shows open + archetype slots", t_get_scheme_lineup_open_slots)
    run_test("delete_scheme removes row", t_delete_scheme)


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------
def test_activity_log():
    section("Activity Log")
    fresh_db()

    def t_manual_log():
        db.log("manual_event", "notes here")
        df = db.get_recent_activity(1)
        assert_eq("activity_name stored", df.iloc[0]["activity_name"], "manual_event")
        assert_eq("notes stored", df.iloc[0]["activity_notes"], "notes here")

    def t_log_no_notes():
        db.log("no_notes_event")
        df = db.get_recent_activity(5)
        names = df["activity_name"].tolist()
        assert_true("event logged without notes", "no_notes_event" in names)

    def t_mutating_functions_auto_log():
        before = len(db.get_recent_activity(100))
        db.insert_position("TEST_POS")
        after = len(db.get_recent_activity(100))
        assert_true("insert_position wrote to log", after > before)

    def t_get_recent_activity_limit():
        for i in range(10):
            db.log(f"event_{i}")
        df = db.get_recent_activity(3)
        assert_eq("limit respected", len(df), 3)

    run_test("log() stores activity_name and notes", t_manual_log)
    run_test("log() works without notes", t_log_no_notes)
    run_test("mutating functions auto-write to log", t_mutating_functions_auto_log)
    run_test("get_recent_activity respects limit", t_get_recent_activity_limit)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
def test_generic_helpers():
    section("Generic Helpers")
    fresh_db()
    db.get_or_create_position("QB")

    def t_get_table_df():
        df = db.get_table_df("positions")
        assert_true("returns DataFrame", isinstance(df, pd.DataFrame))
        assert_true("has id column", "id" in df.columns)

    def t_custom_query_df_no_params():
        df = db.custom_query_df("SELECT * FROM positions")
        assert_true("returns DataFrame", isinstance(df, pd.DataFrame))

    def t_custom_query_df_with_params():
        df = db.custom_query_df("SELECT * FROM positions WHERE name = ?", ("QB",))
        assert_eq("one row", len(df), 1)
        assert_eq("name matches", df.iloc[0]["name"], "QB")

    run_test("get_table_df returns full table", t_get_table_df)
    run_test("custom_query_df without params", t_custom_query_df_no_params)
    run_test("custom_query_df with params", t_custom_query_df_with_params)


# ===========================================================================
# DATABASE STATE PRINTER
# ===========================================================================

def _header(title: str):
    width = 70
    bar   = "═" * width
    print(f"\n╔{bar}╗")
    print(f"║  {title:<{width - 2}}║")
    print(f"╚{bar}╝")


def _subheader(title: str):
    print(f"\n  ┌─ {title} {'─' * max(0, 60 - len(title))}┐")


def _print_df(df: pd.DataFrame, indent: int = 4):
    if df is None or df.empty:
        print(" " * indent + "(no rows)")
        return
    lines = df.to_string(index=False).splitlines()
    for line in lines:
        print(" " * indent + line)


def print_db_state(db_path: str = None):
    """
    Print a complete, human-readable snapshot of the current database.

    Parameters
    ----------
    db_path : str, optional
        Path to the SQLite file.  Defaults to db.DB_NAME.
    """
    if db_path:
        db.DB_NAME = db_path

    _header(f"HASHMARK DATABASE STATE  ·  {db.DB_NAME}")

    # ── Positions ────────────────────────────────────────────────────────────
    _subheader("POSITIONS")
    _print_df(db.get_table_df("positions"))

    # ── Stats ─────────────────────────────────────────────────────────────────
    _subheader("STATS")
    with db.get_conn() as conn:
        stats_df = pd.read_sql_query(
            """
            SELECT s.id, s.name, p.name AS position
            FROM stats s
            LEFT JOIN positions p ON p.id = s.position_id
            ORDER BY s.id
            """, conn)
    _print_df(stats_df)

    # ── Stat Rules ────────────────────────────────────────────────────────────
    _subheader("STAT RULES")
    _print_df(db.get_stat_rules_df())

    # ── Archetypes ────────────────────────────────────────────────────────────
    _subheader("ARCHETYPES")
    _print_df(db.get_archetypes_df())

    # ── Recruits ──────────────────────────────────────────────────────────────
    _subheader("RECRUITS  (is_recruit = 1)")
    _print_df(db.get_recruits_df())

    # ── Historical Players ────────────────────────────────────────────────────
    _subheader("HISTORICAL PLAYERS  (is_recruit = 0)")
    _print_df(db.get_historical_players_df())

    # ── Player Stats (pivot) ──────────────────────────────────────────────────
    # _subheader("PLAYER STATS  (pivoted)")
    # pivot = db.get_players_stats_pivot()
    # _print_df(pivot)

    # ── Evaluations ───────────────────────────────────────────────────────────
    _subheader("PLAYER EVALUATIONS")
    _print_df(db.get_evaluations_df())

    # ── Comparisons ───────────────────────────────────────────────────────────
    _subheader("PLAYER COMPARISONS  (ranked by final_score)")
    _print_df(db.get_all_comparisons_df())

    # ── Schemes ───────────────────────────────────────────────────────────────
    _subheader("SCHEMES")
    schemes = db.get_all_schemes_df()
    _print_df(schemes)

    if not schemes.empty:
        for _, row in schemes.iterrows():
            scid = int(row["id"])
            name = row["name"]
            _subheader(f"SCHEME LINEUP · '{name}'  (id={scid})")
            _print_df(db.get_scheme_lineup(scid))

    # ── Activity Log ──────────────────────────────────────────────────────────
    _subheader("RECENT ACTIVITY  (last 20 entries)")
    _print_df(db.get_recent_activity(20))

    print(f"\n{'═' * 72}\n")


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def run_all_tests():
    print(f"\n{HEAD}{'═'*60}")
    print("  HASHMARK DB  –  FULL TEST SUITE")
    print(f"{'═'*60}{RESET}")
    print(f"  Test database: {TEST_DB}\n")

    test_init_db()
    test_positions()
    test_stats()
    test_stat_rules()
    test_archetypes()
    test_players()
    test_player_stats()
    test_player_evaluations()
    test_player_comparisons()
    test_schemes()
    test_activity_log()
    test_generic_helpers()

    # Summary
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    total  = len(_results)

    print(f"\n{HEAD}{'═'*60}")
    print(f"  RESULTS:  {passed}/{total} passed   {failed} failed")
    print(f"{'═'*60}{RESET}\n")

    if failed:
        print("FAILURES:")
        for name, ok, tb in _results:
            if not ok:
                print(f"\n  {FAIL}  {name}")
                print(tb)

    # Cleanup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    return failed == 0


if __name__ == "__main__":
    all_passed = run_all_tests()

    # ── Demo: print state of the production (or provided) DB ─────────────────
    prod_db = sys.argv[1] if len(sys.argv) > 1 else "hashmark_players.db"
    if os.path.exists(prod_db):
        db.DB_NAME = prod_db
        print_db_state(prod_db)
    else:
        print(f"(No database found at '{prod_db}' – skipping state print.)\n"
              f"Tip: pass your DB path as an argument:  python hashmark_tests.py myfile.db\n")

    sys.exit(0 if all_passed else 1)