from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Literal
from collections import defaultdict


CURRENT_YEAR = 2024


# ---------------------------------------------------------------------------
# Position → relevant stat keys (hardcoded; edit as schema evolves)
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
# Context: High School — state talent tier
# ---------------------------------------------------------------------------

HS_STATE_TIERS: dict[str, float] = {
    # Tier 1 — Elite football states
    "Texas":        1.30,
    "Florida":      1.30,
    "California":   1.30,
    "Georgia":      1.30,
    "Ohio":         1.30,
    "Louisiana":    1.30,

    # Tier 2 — Strong recruiting states
    "Alabama":          1.20,
    "Pennsylvania":     1.20,
    "Michigan":         1.20,
    "North Carolina":   1.20,
    "South Carolina":   1.20,
    "Virginia":         1.20,
    "Tennessee":        1.20,
    "Mississippi":      1.20,

    # Tier 3 — Solid football states
    "Illinois":     1.10,
    "Indiana":      1.10,
    "Maryland":     1.10,
    "Kentucky":     1.10,
    "Arizona":      1.10,
    "Missouri":     1.10,
    "Arkansas":     1.10,
    "New Jersey":   1.10,
    "Oklahoma":     1.10,
    "Washington":   1.10,

    # Tier 4 — Average
    "Colorado":     1.00,
    "Nevada":       1.00,
    "Utah":         1.00,
    "Minnesota":    1.00,
    "Wisconsin":    1.00,
    "Iowa":         1.00,
    "Kansas":       1.00,
    "Nebraska":     1.00,
    "Oregon":       1.00,
    "West Virginia": 1.00,

    # Tier 5 — Lower talent density
    "Idaho":             0.90,
    "Montana":           0.90,
    "Wyoming":           0.90,
    "New Mexico":        0.90,
    "North Dakota":      0.90,
    "South Dakota":      0.90,
    "Alaska":            0.90,
    "Hawaii":            0.90,
    "Vermont":           0.90,
    "Maine":             0.90,
    "New Hampshire":     0.90,
    "Rhode Island":      0.90,
    "Delaware":          0.90,

    # Tier 6 — Very low football talent density
    "Connecticut":          0.80,
    "Massachusetts":        0.80,
    "New York":             0.80,
    "District of Columbia": 0.80,
}

# Caller supplies one of these string labels for the HS program strength
HS_SCHOOL_STRENGTH: dict[str, float] = {
    "elite":    1.15,   # top-ranked program in state, consistent playoff contender
    "strong":   1.10,
    "average":  1.00,
    "weak":     0.90,
}


# ---------------------------------------------------------------------------
# Context: Transfer — conference tier + playing time modifier
# ---------------------------------------------------------------------------

TRANSFER_CONFERENCE_TIERS: dict[str, float] = {
    # Tier 1 — Elite
    "SEC":      1.30,
    "Big Ten":  1.30,

    # Tier 2 — Power
    "Big 12":   1.25,
    "ACC":      1.25,

    # Tier 3 — Upper G5
    "AAC":           1.15,
    "Mountain West": 1.15,

    # Tier 4 — Mid G5
    "Sun Belt": 1.05,
    "MAC":      1.05,
    "CUSA":     1.05,

    # Tier 5 — Lower FBS / FCS Power
    "Missouri Valley": 0.95,
    "Big Sky":         0.95,
    "CAA":             0.95,

    # Tier 6 — Lower FCS
    "Southland":   0.85,
    "Ohio Valley": 0.85,
    "Patriot":     0.85,
    "NEC":         0.85,

    # Tier 7 — D2 / NAIA / JUCO
    "D2":   0.75,
    "D3":   0.75,
    "NAIA": 0.75,
    "JUCO": 0.75,
}

TRANSFER_PLAYING_TIME: dict[str, float] = {
    "starter_p5":   1.25,
    "starter_g5":   1.15,
    "backup_p5":    1.05,
    "starter_fcs":  1.05,
    "backup_g5":    0.95,
    "starter_d2":   0.90,
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

RecruitType = Literal["highschool", "transfer"]


@dataclass
class Recruit:

    name:         str
    position:     str
    season:       int
    recruit_type: RecruitType      # "highschool" | "transfer"

    height: Optional[float] = None  # inches
    weight: Optional[float] = None  # lbs

    # High school context
    home_state:         Optional[str] = None  # e.g. "Texas"
    hs_school_strength: Optional[str] = None  # "elite" | "strong" | "average" | "weak"

    # Transfer context
    transfer_conference:   Optional[str] = None  # key in TRANSFER_CONFERENCE_TIERS
    transfer_playing_time: Optional[str] = None  # key in TRANSFER_PLAYING_TIME

    # Dynamic stat dict — only include stats that are actually available
    stats: dict[str, Optional[float]] = field(default_factory=dict)

    def get_stat(self, key: str) -> Optional[float]:
        return self.stats.get(key)


@dataclass
class CareerProfile:
    """
    One historical player with stats averaged across all their year instances.
    Built by build_career_profiles() before calling evaluate().
    """
    player_id:   str
    name:        str
    position:    str
    last_season: int               # most recent year in DB — drives recency weight

    height:     Optional[float] = None
    weight:     Optional[float] = None
    conference: Optional[str]   = None  # most recent season conference
    home_state: Optional[str]   = None

    # Averaged stats across all year instances
    stats: dict[str, Optional[float]] = field(default_factory=dict)

    def get_stat(self, key: str) -> Optional[float]:
        return self.stats.get(key)


# ---------------------------------------------------------------------------
# Output structures
# ---------------------------------------------------------------------------

@dataclass
class PhysicalScore:
    height_sim:     Optional[float]
    weight_sim:     Optional[float]
    score:          float
    fields_used:    int
    fields_missing: int


@dataclass
class ProductionScore:
    stat_similarities: dict[str, float]   # stat_key → similarity 0–1
    score:             float
    fields_used:       int
    fields_missing:    int


@dataclass
class ContextScore:
    """
    High school:  multiplier = state_tier  × school_strength
    Transfer:     multiplier = conf_tier   × playing_time_modifier
    Comparable:   multiplier = conf_tier   (treated as starter with recorded stats)

    score = feature similarity between recruit multiplier and comparable multiplier,
            normalized across the full position pool.
    """
    recruit_multiplier:    Optional[float]
    comparable_multiplier: Optional[float]
    score:                 float
    recruit_type:          RecruitType


@dataclass
class PlayerMatch:
    player_id:      str
    name:           str
    final_score:    float
    confidence:     float         # 0–1; penalized per missing field
    physical:       PhysicalScore
    production:     ProductionScore
    context:        ContextScore
    recency_weight: float


@dataclass
class RecruitProfile:
    """
    The recruit's own physical, production, and context values —
    normalized relative to the comparable pool for this position.
    """
    height:             Optional[float]   # raw inches
    weight:             Optional[float]   # raw lbs
    stats:              dict[str, Optional[float]]   # raw stat values
    context_multiplier: Optional[float]   # state×school or conf×playing_time
    confidence:         float             # fraction of fields that were present


@dataclass
class EvaluationResult:
    recruit_name:    str
    position:        str
    recruit_type:    RecruitType
    recruit_profile: RecruitProfile       # the recruit's own data
    top_matches:     list[PlayerMatch]    # sorted best → worst
    total_compared:  int


# ---------------------------------------------------------------------------
# Context multiplier helpers
# ---------------------------------------------------------------------------

def _hs_context_multiplier(recruit: Recruit) -> Optional[float]:
    """state_tier × school_strength. Example: Texas × elite = 1.30 × 1.15 = 1.495"""
    state  = HS_STATE_TIERS.get(recruit.home_state or "")
    school = HS_SCHOOL_STRENGTH.get(recruit.hs_school_strength or "")
    if state is None and school is None:
        return None
    return (state or 1.0) * (school or 1.0)


def _transfer_context_multiplier(recruit: Recruit) -> Optional[float]:
    """conf_tier × playing_time. Example: MAC starter_g5 = 1.05 × 1.15 = 1.2075"""
    conf    = TRANSFER_CONFERENCE_TIERS.get(recruit.transfer_conference or "")
    playing = TRANSFER_PLAYING_TIME.get(recruit.transfer_playing_time or "")
    if conf is None and playing is None:
        return None
    return (conf or 1.0) * (playing or 1.0)


def _recruit_context_multiplier(recruit: Recruit) -> Optional[float]:
    if recruit.recruit_type == "highschool":
        return _hs_context_multiplier(recruit)
    return _transfer_context_multiplier(recruit)


def _comparable_context_multiplier(comp: CareerProfile) -> Optional[float]:
    """
    Historical DB players are college players — use their conference tier.
    Treated as starters since they have recorded production stats.
    """
    conf_mult = TRANSFER_CONFERENCE_TIERS.get(comp.conference or "")
    if conf_mult is not None:
        return conf_mult

    # Fallback: if conference is unavailable, approximate context with
    # home-state talent tier so context similarity can still contribute.
    state_mult = HS_STATE_TIERS.get(comp.home_state or "")
    if state_mult is not None:
        return state_mult

    # Last-resort neutral context value.
    return 1.0


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_pool(
    values: list[Optional[float]],
) -> tuple[Optional[float], Optional[float]]:
    valid = [v for v in values if v is not None]
    if not valid:
        return None, None
    return min(valid), max(valid)


def _normalize(
    value: Optional[float],
    mn: Optional[float],
    mx: Optional[float],
) -> Optional[float]:
    if value is None or mn is None or mx is None:
        return None
    if mx == mn:
        return 1.0  # all values identical → perfect similarity
    return (value - mn) / (mx - mn)


def _similarity(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """1 - |norm_A - norm_B|. Returns None if either is missing."""
    if a is None or b is None:
        return None
    return max(0.0, 1.0 - abs(a - b))


def _safe_avg(values: list[Optional[float]]) -> tuple[float, int, int]:
    """Returns (average_of_non_none, used_count, missing_count)."""
    valid = [v for v in values if v is not None]
    missing = len(values) - len(valid)
    if not valid:
        return 0.0, 0, missing
    return sum(valid) / len(valid), len(valid), missing


def _confidence(total_fields: int, missing: int) -> float:
    if total_fields == 0:
        return 0.0
    return max(0.0, 1.0 - (missing / total_fields))


# ---------------------------------------------------------------------------
# Normalization map — built once per evaluate() call over entire pool
# ---------------------------------------------------------------------------

def _build_normalization_maps(
    recruit:     Recruit,
    comparables: list[CareerProfile],
    stat_keys:   list[str],
) -> dict[str, tuple[Optional[float], Optional[float]]]:
    """
    Compute (min, max) for every field across recruit + full comparable pool.
    All similarities are therefore relative to this position group.
    """
    norm_map: dict[str, tuple] = {}

    all_keys = ["height", "weight", "_context_multiplier"] + stat_keys

    for key in all_keys:
        if key == "height":
            pool = [recruit.height] + [c.height for c in comparables]
        elif key == "weight":
            pool = [recruit.weight] + [c.weight for c in comparables]
        elif key == "_context_multiplier":
            pool = (
                [_recruit_context_multiplier(recruit)] +
                [_comparable_context_multiplier(c) for c in comparables]
            )
        else:
            pool = [recruit.get_stat(key)] + [c.get_stat(key) for c in comparables]

        norm_map[key] = _normalize_pool(pool)

    return norm_map


def _normalize_entity(
    entity,
    norm_map:   dict,
    is_recruit: bool,
) -> dict[str, Optional[float]]:
    result: dict[str, Optional[float]] = {}
    for key, (mn, mx) in norm_map.items():
        if key == "height":
            val = entity.height
        elif key == "weight":
            val = entity.weight
        elif key == "_context_multiplier":
            val = (
                _recruit_context_multiplier(entity)
                if is_recruit
                else _comparable_context_multiplier(entity)
            )
        else:
            val = entity.get_stat(key)
        result[key] = _normalize(val, mn, mx)
    return result


# ---------------------------------------------------------------------------
# Score evaluators
# ---------------------------------------------------------------------------

def _eval_physical(
    recruit_norm: dict[str, Optional[float]],
    comp_norm:    dict[str, Optional[float]],
) -> PhysicalScore:
    h_sim = _similarity(recruit_norm.get("height"), comp_norm.get("height"))
    w_sim = _similarity(recruit_norm.get("weight"), comp_norm.get("weight"))
    score, used, missing = _safe_avg([h_sim, w_sim])
    return PhysicalScore(
        height_sim=h_sim,
        weight_sim=w_sim,
        score=score,
        fields_used=used,
        fields_missing=missing,
    )


def _eval_production(
    stat_keys:    list[str],
    recruit_norm: dict[str, Optional[float]],
    comp_norm:    dict[str, Optional[float]],
) -> ProductionScore:
    sims: dict[str, float] = {}
    sim_values: list[Optional[float]] = []

    for key in stat_keys:
        sim = _similarity(recruit_norm.get(key), comp_norm.get(key))
        if sim is not None:
            sims[key] = sim
        sim_values.append(sim)

    score, used, missing = _safe_avg(sim_values)
    return ProductionScore(
        stat_similarities=sims,
        score=score,
        fields_used=used,
        fields_missing=missing,
    )


def _eval_context(
    recruit:    Recruit,
    comparable: CareerProfile,
    recruit_norm: dict[str, Optional[float]],
    comp_norm:    dict[str, Optional[float]],
) -> ContextScore:
    r_mult = _recruit_context_multiplier(recruit)
    c_mult = _comparable_context_multiplier(comparable)

    norm_r = recruit_norm.get("_context_multiplier")
    norm_c = comp_norm.get("_context_multiplier")
    sim    = _similarity(norm_r, norm_c)

    return ContextScore(
        recruit_multiplier=r_mult,
        comparable_multiplier=c_mult,
        # If either side has missing context signal after normalization,
        # use a neutral midpoint instead of hard-zeroing the context term.
        score=sim if sim is not None else 0.5,
        recruit_type=recruit.recruit_type,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate(
    recruit:    Recruit,
    db_players: list[CareerProfile],
    weights:    Optional[dict[str, float]] = None,
    top_n:      int = 5,
) -> EvaluationResult:
    """
    Compare a recruit against historical career profiles at the same position.

    Args:
        recruit:    The recruit to evaluate (highschool or transfer).
        db_players: All CareerProfiles from the DB — position filtering is internal.
        weights:    Category weights. Keys: "physical", "production", "context".
                    Must sum to 1.0. Defaults: physical=0.35, production=0.35, context=0.25.
        top_n:      How many top matches to return.

    Returns:
        EvaluationResult with top_matches sorted best → worst by final_score.
    """
    w = weights or {"physical": 0.35, "production": 0.35, "context": 0.30}
    assert abs(sum(w.values()) - 1.0) < 1e-6, "Weights must sum to 1.0"

    pos       = recruit.position.upper()
    stat_keys = POSITION_STATS.get(pos, [])

    comparables = [p for p in db_players if p.position.upper() == pos]
    if not comparables:
        return EvaluationResult(
            recruit_name=recruit.name,
            position=recruit.position,
            recruit_type=recruit.recruit_type,
            recruit_profile=RecruitProfile(
                height=recruit.height,
                weight=recruit.weight,
                stats={k: recruit.get_stat(k) for k in stat_keys},
                context_multiplier=_recruit_context_multiplier(recruit),
                confidence=0.0,
            ),
            top_matches=[],
            total_compared=0,
        )

    norm_map     = _build_normalization_maps(recruit, comparables, stat_keys)
    recruit_norm = _normalize_entity(recruit, norm_map, is_recruit=True)

    matches: list[PlayerMatch] = []

    for comp in comparables:
        comp_norm  = _normalize_entity(comp, norm_map, is_recruit=False)

        physical   = _eval_physical(recruit_norm, comp_norm)
        production = _eval_production(stat_keys, recruit_norm, comp_norm)
        context    = _eval_context(recruit, comp, recruit_norm, comp_norm)

        # Recency: players from more recent seasons are weighted higher
        seasons_ago = max(0, CURRENT_YEAR - comp.last_season)
        recency = 1.0 / (seasons_ago + 1)
        recency = max(0.1, min(1.0, recency))

        final_score = (
            physical.score   * w["physical"] +
            production.score * w["production"] +
            context.score    * w["context"]
        ) * recency

        # Confidence: penalize for each field the eval couldn't use
        context_missing = 0 if context.score > 0.0 else 1
        total_missing = (
            physical.fields_missing +
            production.fields_missing +
            context_missing
        )
        total_fields = (
            (physical.fields_used + physical.fields_missing) +
            (production.fields_used + production.fields_missing) +
            1   # context counts as one composite field
        )
        confidence = _confidence(total_fields, total_missing)

        matches.append(PlayerMatch(
            player_id=comp.player_id,
            name=comp.name,
            final_score=round(final_score, 4),
            confidence=round(confidence, 4),
            physical=physical,
            production=production,
            context=context,
            recency_weight=round(recency, 4),
        ))

    matches.sort(key=lambda m: m.final_score, reverse=True)

    recruit_stat_fields = {k: recruit.get_stat(k) for k in stat_keys}
    recruit_missing = (
        (0 if recruit.height is not None else 1) +
        (0 if recruit.weight is not None else 1) +
        sum(1 for v in recruit_stat_fields.values() if v is None) +
        (0 if _recruit_context_multiplier(recruit) is not None else 1)
    )
    recruit_total = 2 + len(stat_keys) + 1  # height, weight, stats, context
    recruit_profile = RecruitProfile(
        height=recruit.height,
        weight=recruit.weight,
        stats=recruit_stat_fields,
        context_multiplier=_recruit_context_multiplier(recruit),
        confidence=round(_confidence(recruit_total, recruit_missing), 4),
    )

    return EvaluationResult(
        recruit_name=recruit.name,
        position=recruit.position,
        recruit_type=recruit.recruit_type,
        recruit_profile=recruit_profile,
        top_matches=matches[:top_n],
        total_compared=len(matches),
    )


# ---------------------------------------------------------------------------
# Flask helper — aggregate raw DB rows into CareerProfiles
# ---------------------------------------------------------------------------

def build_career_profiles(db_rows: list[dict]) -> list[CareerProfile]:
    """
    Aggregate raw YearInstance rows from the DB into CareerProfiles.

    Each row dict should include at minimum:
        player_id, player, position, season,
        bio_height, bio_weight, conference, bio_homeState,
        stat_* columns

    Stats are averaged across all year instances per player.
    conference and home_state are taken from the most recent season row.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in db_rows:
        grouped[str(row["player_id"])].append(row)

    profiles: list[CareerProfile] = []

    for player_id, rows in grouped.items():
        rows.sort(key=lambda r: r.get("season", 0))
        most_recent = rows[-1]

        all_stat_keys = [k for k in most_recent.keys() if k.startswith("stat_")]

        averaged_stats: dict[str, Optional[float]] = {}
        for key in all_stat_keys:
            values: list[float] = []
            for row in rows:
                v = row.get(key)
                if v is not None and v != "":
                    try:
                        values.append(float(v))
                    except (ValueError, TypeError):
                        pass
            averaged_stats[key] = sum(values) / len(values) if values else None

        def _avg_bio(field_name: str) -> Optional[float]:
            values: list[float] = []
            for row in rows:
                v = row.get(field_name)
                if v is not None and v != "":
                    try:
                        values.append(float(v))
                    except (ValueError, TypeError):
                        pass
            return sum(values) / len(values) if values else None

        profiles.append(CareerProfile(
            player_id=player_id,
            name=most_recent.get("player", ""),
            position=most_recent.get("position", ""),
            last_season=int(most_recent.get("season", CURRENT_YEAR)),
            height=_avg_bio("bio_height"),
            weight=_avg_bio("bio_weight"),
            conference=most_recent.get("conference"),
            home_state=most_recent.get("bio_homeState"),
            stats=averaged_stats,
        ))

    return profiles
