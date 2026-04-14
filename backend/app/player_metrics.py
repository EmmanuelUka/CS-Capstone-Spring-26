"""
player_metrics.py
-----------------
Standalone scoring functions for evaluating a player's raw stats
without any comparison pool. Each function returns a score 0.0 – 1.0
and a breakdown dict explaining how it was computed.

These are independent of eval_system.py — no normalization against
a pool, no similarity math. Just "how does this player score on their own."

Usage:
    from player_metrics import physical_score, production_score, context_score

    phys = physical_score(position="WR", height=73.5, weight=188)
    prod = production_score(position="WR", stats={"stat_receiving_YDS": 950, ...})
    ctx  = context_score(recruit_type="highschool", home_state="Texas",
                         hs_school_strength="elite")
"""

from __future__ import annotations
from typing import Optional


# ---------------------------------------------------------------------------
# Position benchmarks — (poor, average, elite) for each stat
# Used to place a raw value on a 0–1 scale for that position group.
# Adjust these as your data grows — they are the only hardcoded assumptions.
# ---------------------------------------------------------------------------

POSITION_BENCHMARKS: dict[str, dict[str, tuple[float, float, float]]] = {
    "QB": {
        "stat_passing_YDS":  (1000, 2500, 4000),
        "stat_passing_TD":   (5,    20,   40),
        "stat_passing_PCT":  (50,   60,   70),
        "stat_passing_YPA":  (5.0,  7.0,  9.5),
        "stat_passing_INT":  (15,   8,    2),    # inverted — lower is better
        "stat_rushing_YDS":  (0,    200,  600),
        "stat_rushing_TD":   (0,    3,    10),
    },
    "WR": {
        "stat_receiving_YDS": (200,  700,  1400),
        "stat_receiving_TD":  (1,    6,    14),
        "stat_receiving_REC": (15,   50,   100),
        "stat_receiving_YPR": (8,    12,   18),
        "stat_receiving_LONG":(15,   40,   75),
    },
    "TE": {
        "stat_receiving_YDS": (100,  400,  900),
        "stat_receiving_TD":  (1,    5,    12),
        "stat_receiving_REC": (10,   35,   80),
        "stat_receiving_YPR": (7,    11,   16),
    },
    "RB": {
        "stat_rushing_YDS":  (200,  700,  1500),
        "stat_rushing_TD":   (2,    8,    18),
        "stat_rushing_CAR":  (50,   150,  300),
        "stat_rushing_YPC":  (3.0,  4.5,  6.0),
        "stat_rushing_LONG": (10,   30,   65),
        "stat_receiving_REC":(5,    25,   60),
        "stat_receiving_YDS":(30,   200,  600),
    },
    "FB": {
        "stat_rushing_YDS":  (50,   250,  600),
        "stat_rushing_TD":   (1,    4,    10),
        "stat_rushing_CAR":  (20,   70,   150),
        "stat_receiving_REC":(3,    15,   35),
    },
    "PK": {
        "stat_kicking_FGM":  (5,    15,   28),
        "stat_kicking_PCT":  (60,   75,   90),
        "stat_kicking_LONG": (35,   48,   58),
        "stat_kicking_PTS":  (30,   70,   130),
        "stat_kicking_XPM":  (10,   30,   55),
    },
    "DL": {
        "stat_defensive_SACKS":  (0,   4,   14),
        "stat_defensive_TOT":    (10,  35,  70),
        "stat_defensive_SOLO":   (5,   20,  50),
        "stat_defensive_TFL":    (2,   8,   20),
        "stat_defensive_QB_HUR": (0,   6,   18),
    },
    "DT": {
        "stat_defensive_SACKS":  (0,   3,   10),
        "stat_defensive_TOT":    (10,  30,  65),
        "stat_defensive_SOLO":   (5,   18,  45),
        "stat_defensive_TFL":    (2,   7,   18),
    },
    "DE": {
        "stat_defensive_SACKS":  (1,   6,   16),
        "stat_defensive_TOT":    (10,  35,  70),
        "stat_defensive_SOLO":   (5,   20,  50),
        "stat_defensive_TFL":    (3,   10,  22),
        "stat_defensive_QB_HUR": (1,   8,   20),
    },
    "LB": {
        "stat_defensive_TOT":    (20,  60,  110),
        "stat_defensive_SOLO":   (10,  40,  80),
        "stat_defensive_TFL":    (2,   8,   18),
        "stat_defensive_SACKS":  (0,   3,   10),
        "stat_defensive_PD":     (0,   4,   12),
        "stat_defensive_TD":     (0,   1,   4),
    },
    "CB": {
        "stat_interceptions_INT": (0,  2,   8),
        "stat_interceptions_YDS": (0,  40,  150),
        "stat_defensive_PD":      (2,  8,   18),
        "stat_defensive_SOLO":    (10, 35,  65),
        "stat_defensive_TOT":     (15, 45,  80),
    },
    "S": {
        "stat_interceptions_INT": (0,  2,   7),
        "stat_interceptions_YDS": (0,  35,  130),
        "stat_defensive_PD":      (1,  6,   15),
        "stat_defensive_TOT":     (20, 55,  90),
        "stat_defensive_SOLO":    (10, 35,  65),
    },
    "OL": {},
    "OT": {},
    "LS": {},
}

# Physical benchmarks per position (poor, average, elite)
PHYSICAL_BENCHMARKS: dict[str, dict[str, tuple[float, float, float]]] = {
    "QB": {"height": (70, 74, 78),  "weight": (185, 215, 245)},
    "WR": {"height": (68, 72, 76),  "weight": (160, 190, 220)},
    "TE": {"height": (73, 76, 79),  "weight": (220, 250, 275)},
    "RB": {"height": (66, 70, 74),  "weight": (170, 210, 235)},
    "FB": {"height": (69, 72, 75),  "weight": (220, 245, 265)},
    "OL": {"height": (73, 76, 80),  "weight": (270, 305, 340)},
    "OT": {"height": (74, 77, 81),  "weight": (275, 310, 345)},
    "LS": {"height": (71, 74, 77),  "weight": (220, 245, 265)},
    "PK": {"height": (68, 72, 76),  "weight": (160, 190, 215)},
    "DL": {"height": (72, 75, 79),  "weight": (255, 290, 325)},
    "DT": {"height": (71, 74, 78),  "weight": (270, 305, 335)},
    "DE": {"height": (72, 75, 79),  "weight": (240, 270, 305)},
    "LB": {"height": (70, 73, 77),  "weight": (210, 240, 265)},
    "CB": {"height": (68, 71, 75),  "weight": (165, 190, 210)},
    "S":  {"height": (69, 72, 76),  "weight": (185, 205, 225)},
}

# Context multiplier tables (imported logic from eval_system)
HS_STATE_TIERS: dict[str, float] = {
    "Texas": 1.30, "Florida": 1.30, "California": 1.30, "Georgia": 1.30,
    "Ohio": 1.30, "Louisiana": 1.30,
    "Alabama": 1.20, "Pennsylvania": 1.20, "Michigan": 1.20,
    "North Carolina": 1.20, "South Carolina": 1.20, "Virginia": 1.20,
    "Tennessee": 1.20, "Mississippi": 1.20,
    "Illinois": 1.10, "Indiana": 1.10, "Maryland": 1.10, "Kentucky": 1.10,
    "Arizona": 1.10, "Missouri": 1.10, "Arkansas": 1.10, "New Jersey": 1.10,
    "Oklahoma": 1.10, "Washington": 1.10,
    "Colorado": 1.00, "Nevada": 1.00, "Utah": 1.00, "Minnesota": 1.00,
    "Wisconsin": 1.00, "Iowa": 1.00, "Kansas": 1.00, "Nebraska": 1.00,
    "Oregon": 1.00, "West Virginia": 1.00,
    "Idaho": 0.90, "Montana": 0.90, "Wyoming": 0.90, "New Mexico": 0.90,
    "North Dakota": 0.90, "South Dakota": 0.90, "Alaska": 0.90,
    "Hawaii": 0.90, "Vermont": 0.90, "Maine": 0.90, "New Hampshire": 0.90,
    "Rhode Island": 0.90, "Delaware": 0.90,
    "Connecticut": 0.80, "Massachusetts": 0.80, "New York": 0.80,
    "District of Columbia": 0.80,
}

HS_SCHOOL_STRENGTH: dict[str, float] = {
    "elite": 1.15, "strong": 1.10, "average": 1.00, "weak": 0.90,
}

TRANSFER_CONFERENCE_TIERS: dict[str, float] = {
    "SEC": 1.30, "Big Ten": 1.30,
    "Big 12": 1.25, "ACC": 1.25,
    "AAC": 1.15, "Mountain West": 1.15,
    "Sun Belt": 1.05, "MAC": 1.05, "CUSA": 1.05,
    "Missouri Valley": 0.95, "Big Sky": 0.95, "CAA": 0.95,
    "Southland": 0.85, "Ohio Valley": 0.85, "Patriot": 0.85, "NEC": 0.85,
    "D2": 0.75, "D3": 0.75, "NAIA": 0.75, "JUCO": 0.75,
}

TRANSFER_PLAYING_TIME: dict[str, float] = {
    "starter_p5": 1.25, "starter_g5": 1.15, "backup_p5": 1.05,
    "starter_fcs": 1.05, "backup_g5": 0.95, "starter_d2": 0.90,
}

# Min/max multiplier range for normalizing context score to 0–1
_CTX_MIN = 0.80 * 0.90   # weakest HS state × weak school
_CTX_MAX = 1.30 * 1.25   # SEC/Big Ten × starter_p5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _bench_score(value: float, poor: float, average: float, elite: float,
                 inverted: bool = False) -> float:
    """
    Map a raw value onto 0–1 using three-point benchmarks.
    Below poor → 0.0. Above elite → 1.0. Linear between points.
    Set inverted=True for stats where lower is better (e.g. INT thrown).
    """
    if inverted:
        value = poor + elite - value   # flip around midpoint
        poor, elite = elite, poor

    if value <= poor:
        return 0.0
    if value >= elite:
        return 1.0
    if value <= average:
        return 0.5 * (value - poor) / (average - poor)
    return 0.5 + 0.5 * (value - average) / (elite - average)


def _is_inverted(stat_key: str) -> bool:
    """Stats where a lower value is better."""
    return stat_key in {"stat_passing_INT", "stat_fumbles_LOST"}


# ---------------------------------------------------------------------------
# 1. Physical score
# ---------------------------------------------------------------------------

def physical_score(
    position: str,
    height:   Optional[float] = None,   # inches
    weight:   Optional[float] = None,   # lbs
) -> dict:
    """
    Score a player's physical attributes against position benchmarks.

    Returns:
        {
            score:          float 0–1,
            height_score:   float | None,
            weight_score:   float | None,
            breakdown:      { field: score },
            fields_used:    int,
            fields_missing: int,
        }
    """
    pos = position.upper()
    benchmarks = PHYSICAL_BENCHMARKS.get(pos, {})
    breakdown: dict[str, float] = {}
    scores: list[float] = []

    if height is not None and "height" in benchmarks:
        s = _bench_score(height, *benchmarks["height"])
        breakdown["height"] = round(s, 4)
        scores.append(s)

    if weight is not None and "weight" in benchmarks:
        s = _bench_score(weight, *benchmarks["weight"])
        breakdown["weight"] = round(s, 4)
        scores.append(s)

    missing = (1 if height is None else 0) + (1 if weight is None else 0)
    score = sum(scores) / len(scores) if scores else 0.0

    return {
        "score":          round(score, 4),
        "height_score":   breakdown.get("height"),
        "weight_score":   breakdown.get("weight"),
        "breakdown":      breakdown,
        "fields_used":    len(scores),
        "fields_missing": missing,
    }


# ---------------------------------------------------------------------------
# 2. Production score
# ---------------------------------------------------------------------------

def production_score(
    position: str,
    stats:    dict[str, Optional[float]],
) -> dict:
    """
    Score a player's production stats against position benchmarks.

    Args:
        position: position code — QB, WR, RB, etc.
        stats:    dict of stat_* keys → raw float values.
                  Only keys that appear in POSITION_BENCHMARKS for the
                  given position are evaluated; all others are ignored.

    Returns:
        {
            score:          float 0–1,
            breakdown:      { stat_key: score },
            fields_used:    int,
            fields_missing: int,
            best_stat:      (key, score) | None,
            worst_stat:     (key, score) | None,
        }
    """
    pos = position.upper()
    benchmarks = POSITION_BENCHMARKS.get(pos, {})
    breakdown: dict[str, float] = {}
    scores: list[float] = []
    missing = 0

    for key, bench in benchmarks.items():
        val = stats.get(key)
        if val is None:
            missing += 1
            continue
        s = _bench_score(val, *bench, inverted=_is_inverted(key))
        breakdown[key] = round(s, 4)
        scores.append(s)

    score = sum(scores) / len(scores) if scores else 0.0
    best  = max(breakdown.items(), key=lambda x: x[1]) if breakdown else None
    worst = min(breakdown.items(), key=lambda x: x[1]) if breakdown else None

    return {
        "score":          round(score, 4),
        "breakdown":      breakdown,
        "fields_used":    len(scores),
        "fields_missing": missing,
        "best_stat":      best,
        "worst_stat":     worst,
    }


# ---------------------------------------------------------------------------
# 3. Context score
# ---------------------------------------------------------------------------

def context_score(
    recruit_type:          str,                    # "highschool" | "transfer"
    home_state:            Optional[str] = None,   # HS only
    hs_school_strength:    Optional[str] = None,   # HS only
    transfer_conference:   Optional[str] = None,   # transfer only
    transfer_playing_time: Optional[str] = None,   # transfer only
) -> dict:
    """
    Score a player's competition context on a 0–1 scale.

    High school:  multiplier = state_tier × school_strength
    Transfer:     multiplier = conference_tier × playing_time_modifier

    The raw multiplier is normalized against the global min/max range
    so the returned score is always 0–1.

    Returns:
        {
            score:       float 0–1,
            multiplier:  float (raw context multiplier),
            recruit_type: str,
            breakdown:   { component: value },
        }
    """
    breakdown: dict[str, Optional[float]] = {}
    multiplier: Optional[float] = None

    if recruit_type == "highschool":
        state  = HS_STATE_TIERS.get(home_state or "")
        school = HS_SCHOOL_STRENGTH.get(hs_school_strength or "")
        breakdown["state_tier"]      = state
        breakdown["school_strength"] = school
        if state is not None or school is not None:
            multiplier = (state or 1.0) * (school or 1.0)

    elif recruit_type == "transfer":
        conf    = TRANSFER_CONFERENCE_TIERS.get(transfer_conference or "")
        playing = TRANSFER_PLAYING_TIME.get(transfer_playing_time or "")
        breakdown["conference_tier"]   = conf
        breakdown["playing_time_mod"]  = playing
        if conf is not None or playing is not None:
            multiplier = (conf or 1.0) * (playing or 1.0)

    if multiplier is None:
        score = 0.0
    else:
        score = (multiplier - _CTX_MIN) / (_CTX_MAX - _CTX_MIN)
        score = max(0.0, min(1.0, score))

    return {
        "score":        round(score, 4),
        "multiplier":   round(multiplier, 4) if multiplier else None,
        "recruit_type": recruit_type,
        "breakdown":    breakdown,
    }


# ---------------------------------------------------------------------------
# 4. Combined — all three in one call
# ---------------------------------------------------------------------------

def player_score(
    position:              str,
    recruit_type:          str,
    height:                Optional[float] = None,
    weight:                Optional[float] = None,
    stats:                 Optional[dict]  = None,
    home_state:            Optional[str]   = None,
    hs_school_strength:    Optional[str]   = None,
    transfer_conference:   Optional[str]   = None,
    transfer_playing_time: Optional[str]   = None,
    weights:               Optional[dict]  = None,
) -> dict:
    """
    Run all three scoring functions and combine into a single report.

    Args:
        weights: optional dict with keys "physical", "production", "context"
                 must sum to 1.0. Defaults to 0.35 / 0.35 / 0.30.

    Returns:
        {
            overall_score: float 0–1,
            physical:      physical_score() result,
            production:    production_score() result,
            context:       context_score() result,
            weights:       { physical, production, context },
        }
    """
    w = weights or {"physical": 0.35, "production": 0.35, "context": 0.30}
    assert abs(sum(w.values()) - 1.0) < 1e-6, "Weights must sum to 1.0"

    phys = physical_score(position, height, weight)
    prod = production_score(position, stats or {})
    ctx  = context_score(
        recruit_type, home_state, hs_school_strength,
        transfer_conference, transfer_playing_time,
    )

    overall = (
        phys["score"] * w["physical"] +
        prod["score"] * w["production"] +
        ctx["score"]  * w["context"]
    )

    return {
        "overall_score": round(overall, 4),
        "physical":      phys,
        "production":    prod,
        "context":       ctx,
        "weights":       w,
    }


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Physical only ===")
    print(physical_score("WR", height=73.5, weight=188))

    print("\n=== Production only ===")
    print(production_score("WR", stats={
        "stat_receiving_YDS":  950,
        "stat_receiving_TD":   10,
        "stat_receiving_REC":  65,
        "stat_receiving_YPR":  14.6,
        "stat_receiving_LONG": 68,
    }))

    print("\n=== Context only (HS) ===")
    print(context_score("highschool", home_state="Texas", hs_school_strength="elite"))

    print("\n=== Context only (transfer) ===")
    print(context_score("transfer", transfer_conference="SEC",
                         transfer_playing_time="starter_p5"))

    print("\n=== Combined player score ===")
    print(player_score(
        position="WR",
        recruit_type="highschool",
        height=73.5,
        weight=188,
        stats={
            "stat_receiving_YDS":  950,
            "stat_receiving_TD":   10,
            "stat_receiving_REC":  65,
            "stat_receiving_YPR":  14.6,
            "stat_receiving_LONG": 68,
        },
        home_state="Texas",
        hs_school_strength="elite",
    ))