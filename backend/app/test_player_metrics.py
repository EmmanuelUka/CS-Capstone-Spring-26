"""
test_player_metrics.py
----------------------
Test suite for player_metrics.py with clean printed output.
Run with: python test_player_metrics.py
"""

from player_metrics import physical_score, production_score, context_score, player_score


# ---------------------------------------------------------------------------
# Pretty printer helpers
# ---------------------------------------------------------------------------

def divider(title=""):
    if title:
        pad = (60 - len(title) - 2) // 2
        print(f"\n{'=' * pad} {title} {'=' * pad}")
    else:
        print("=" * 62)

def section(label):
    print(f"\n  -- {label} --")

def row(label, value, indent=4):
    print(f"{' ' * indent}{label:<28}{value}")

def print_physical(result):
    section("Physical")
    row("height score",    f"{result['height_score']:.4f}" if result["height_score"] is not None else "N/A")
    row("weight score",    f"{result['weight_score']:.4f}" if result["weight_score"] is not None else "N/A")
    row("physical score",  f"{result['score']:.4f}")
    row("fields used",     result["fields_used"])
    row("fields missing",  result["fields_missing"])

def print_production(result):
    section("Production")
    for k, v in result["breakdown"].items():
        label = k.replace("stat_", "").replace("_", " ")
        row(label, f"{v:.4f}")
    row("production score",  f"{result['score']:.4f}")
    row("fields used",       result["fields_used"])
    row("fields missing",    result["fields_missing"])
    if result["best_stat"]:
        row("best stat",  f"{result['best_stat'][0].replace('stat_', '')}  ({result['best_stat'][1]:.4f})")
    if result["worst_stat"]:
        row("worst stat", f"{result['worst_stat'][0].replace('stat_', '')}  ({result['worst_stat'][1]:.4f})")

def print_context(result):
    section("Context")
    for k, v in result["breakdown"].items():
        row(k, f"{v:.4f}" if v else "N/A")
    row("raw multiplier", f"{result['multiplier']:.4f}" if result["multiplier"] else "N/A")
    row("context score",  f"{result['score']:.4f}")

def print_combined(result):
    section("Combined")
    w = result["weights"]
    row("weights", f"physical={w['physical']}  production={w['production']}  context={w['context']}")
    row("physical score",   f"{result['physical']['score']:.4f}")
    row("production score", f"{result['production']['score']:.4f}")
    row("context score",    f"{result['context']['score']:.4f}")
    row("overall score",    f"{result['overall_score']:.4f}")


# ---------------------------------------------------------------------------
# Test 1 — WR, high school, elite Texas program
# ---------------------------------------------------------------------------

def test_wr_hs_elite():
    divider("TEST 1 — WR | HS | Texas elite")
    print("  Jaylen Carter · WR · highschool · Texas elite school")

    phys = physical_score("WR", height=73.5, weight=188)
    prod = production_score("WR", stats={
        "stat_receiving_YDS":  950,
        "stat_receiving_TD":   10,
        "stat_receiving_REC":  65,
        "stat_receiving_YPR":  14.6,
        "stat_receiving_LONG": 68,
    })
    ctx = context_score("highschool", home_state="Texas", hs_school_strength="elite")

    print_physical(phys)
    print_production(prod)
    print_context(ctx)


# ---------------------------------------------------------------------------
# Test 2 — QB, transfer, SEC starter
# ---------------------------------------------------------------------------

def test_qb_transfer_sec():
    divider("TEST 2 — QB | Transfer | SEC starter")
    print("  Devon Price · QB · transfer · SEC · starter_p5")

    phys = physical_score("QB", height=76, weight=218)
    prod = production_score("QB", stats={
        "stat_passing_YDS": 3400,
        "stat_passing_TD":  30,
        "stat_passing_PCT": 65.0,
        "stat_passing_YPA": 8.4,
        "stat_passing_INT": 6,
        "stat_rushing_YDS": 290,
        "stat_rushing_TD":  4,
    })
    ctx = context_score("transfer", transfer_conference="SEC",
                        transfer_playing_time="starter_p5")

    print_physical(phys)
    print_production(prod)
    print_context(ctx)


# ---------------------------------------------------------------------------
# Test 3 — OL, high school, average state/school (no production stats)
# ---------------------------------------------------------------------------

def test_ol_hs_average():
    divider("TEST 3 — OL | HS | Average state/school")
    print("  Terrell Washington · OL · highschool · Iowa · average school")

    phys = physical_score("OL", height=77, weight=305)
    prod = production_score("OL", stats={})
    ctx  = context_score("highschool", home_state="Iowa", hs_school_strength="average")

    print_physical(phys)
    print_production(prod)
    print_context(ctx)


# ---------------------------------------------------------------------------
# Test 4 — LB, transfer, MAC backup (weak context)
# ---------------------------------------------------------------------------

def test_lb_transfer_weak():
    divider("TEST 4 — LB | Transfer | MAC backup")
    print("  Marcus Webb · LB · transfer · MAC · backup_g5")

    phys = physical_score("LB", height=73, weight=238)
    prod = production_score("LB", stats={
        "stat_defensive_TOT":   52,
        "stat_defensive_SOLO":  34,
        "stat_defensive_TFL":   6,
        "stat_defensive_SACKS": 2,
        "stat_defensive_PD":    3,
    })
    ctx = context_score("transfer", transfer_conference="MAC",
                        transfer_playing_time="backup_g5")

    print_physical(phys)
    print_production(prod)
    print_context(ctx)


# ---------------------------------------------------------------------------
# Test 5 — CB, missing data
# ---------------------------------------------------------------------------

def test_cb_missing_data():
    divider("TEST 5 — CB | HS | Missing data")
    print("  Unknown CB · highschool · state unknown · one stat available")

    phys = physical_score("CB", height=71, weight=None)
    prod = production_score("CB", stats={
        "stat_defensive_PD": 7,
    })
    ctx  = context_score("highschool", home_state=None, hs_school_strength="average")

    print_physical(phys)
    print_production(prod)
    print_context(ctx)


# ---------------------------------------------------------------------------
# Test 6 — Combined player_score() for elite WR
# ---------------------------------------------------------------------------

def test_combined_elite_wr():
    divider("TEST 6 — Combined score | Elite WR")
    print("  Jaylen Carter · full player_score() call")

    result = player_score(
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
    )
    print_combined(result)


# ---------------------------------------------------------------------------
# Test 7 — Combined with custom weights
# ---------------------------------------------------------------------------

def test_combined_custom_weights():
    divider("TEST 7 — Combined score | Custom weights")
    print("  Same WR — scout sets context=0.50, physical=0.20, production=0.30")

    result = player_score(
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
        weights={"physical": 0.20, "production": 0.30, "context": 0.50},
    )
    print_combined(result)


# ---------------------------------------------------------------------------
# Test 8 — Elite DE, transfer from Big Ten
# ---------------------------------------------------------------------------

def test_de_transfer_big_ten():
    divider("TEST 8 — DE | Transfer | Big Ten starter")
    print("  Darius Knight · DE · transfer · Big Ten · starter_p5")

    phys = physical_score("DE", height=76, weight=268)
    prod = production_score("DE", stats={
        "stat_defensive_SACKS":  11,
        "stat_defensive_TOT":    42,
        "stat_defensive_SOLO":   28,
        "stat_defensive_TFL":    14,
        "stat_defensive_QB_HUR": 16,
    })
    ctx = context_score("transfer", transfer_conference="Big Ten",
                        transfer_playing_time="starter_p5")

    print_physical(phys)
    print_production(prod)
    print_context(ctx)


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    divider()
    print("  Player Metrics — Test Suite")
    divider()

    test_wr_hs_elite()
    test_qb_transfer_sec()
    test_ol_hs_average()
    test_lb_transfer_weak()
    test_cb_missing_data()
    test_combined_elite_wr()
    test_combined_custom_weights()
    test_de_transfer_big_ten()

    print(f"\n{'=' * 62}")
    print("  All tests complete.")
    divider()