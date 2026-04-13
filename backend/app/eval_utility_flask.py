# API to interact with the Player Evaluation Function

from flask import Flask, jsonify, redirect, request, session
import playerEval as pe
from playerEval import Recruit

### Open database Connection, get full database context

### TEMP; Just get sample database from te

from test_eval import RAW_DB_ROWS
from test_eval import build_career_profiles

career_profiles = build_career_profiles(RAW_DB_ROWS)

### 

### Ensure that a "Recruit Dictionary" (Passed from the front end) has all the attributes a recruit needs
REQUIRED_KEYS = {
    "name",
    "position",
    "season",
    "recruit_type",
    "home_state",
    "hs_school_strength",
    "height",
    "weight",
    "stats"
}

def validate_player_dict(d):
    missing = REQUIRED_KEYS - d.keys()
    if missing:
        raise ValueError(f"Missing required keys: {missing}")
    return True
###

# Given a dictionary, transform the dictionary into a full recruit object
def createRecruitObject(recruitAttributes: dict):
    if not validate_player_dict(recruitAttributes):
        print("Warning - Recruit Object Does Not Have Necessary Recruit Attributes \n", recruitAttributes)
        return None
    
    return pe.Recruit(
        name=recruitAttributes["name"],
        position=recruitAttributes["position"],
        season=recruitAttributes["season"],
        recruit_type=recruitAttributes["recruit_type"],
        home_state=recruitAttributes["home_state"],
        hs_school_strength=recruitAttributes["hs_school_strength"],
        height=recruitAttributes["height"],
        weight=recruitAttributes["weight"],
        stats=recruitAttributes['stats']
    )


### Run evaluation on full database context
def evaluateRecruit(recruit: dict, weights: dict[str, float] = None, top_n: int = 3):
    recruit_to_evaluate = createRecruitObject(recruit)
    return pe.evaluate(recruit_to_evaluate, career_profiles, weights, top_n)

if __name__ == '__main__':
    print('---RUNING TEST CASES---')
    from test_eval import print_result

    recruit_example = {
        "name": "Jaylen Carter",
        "position": "WR",
        "season": 2024,
        "recruit_type": "highschool",
        "home_state": "Texas",
        "hs_school_strength": "elite",
        "height": 73.5,
        "weight": 188.0,
        "stats": {
            "stat_receiving_YDS":  950.0,
            "stat_receiving_TD":   10.0,
            "stat_receiving_REC":  65.0,
            "stat_receiving_YPR":  14.6,
            "stat_receiving_LONG": 68.0,
        },
    }

    result = evaluateRecruit(recruit_example, None, top_n=3)

    print_result(result)
