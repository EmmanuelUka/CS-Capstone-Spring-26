from flask import Flask, jsonify, redirect, request, session
import playerEval as pe
import test_eval as te


print("\n[TEST 1] High school WR — Texas, elite school")
recruit = pe.Recruit(
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
result = pe.evaluate(recruit, te.career_profiles, top_n=3)
te.print_result(result)