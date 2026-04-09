# Algorithm
Given a player profile 
Player1{
    Name:
    Height:
    Weight
    rushn_Yrds
    tds:
    pos:
}

filter database by player position to get players to compare to 

Normalize data on a 0-1 range
normalized = (value - min) / (max - min)


Group Categories 
physical_score = average(height, weight)
production_score = average(yards, tds)
context_score = average(level, games)


Weighted Score // Scores are just placeholder, users should be able to define the weights
final_score =
(physical * 0.35) +
(production * 0.35) +
(context * 0.25)

In case of missing data we skip/ignore it, and reduce confidence score

Add a check for context:
Im gonna make a function that takes in the player state as paramerter and returns the state competition for college football


Recency weight 
weight = 1 / (current_year - player_year + 1)

compute feature similarity 
similarity = 1 - |Player A - Player B|--- 
Example:
Player A
Height: 1 - |0.5 - 0.4| = 0.9
Weight: 1 - |0.375 - 0.5| = 0.875
Physical Score = (0.9 + 0.875)/2 = 0.887



Yards: 1 - |0.70 - 0.77| = 0.93
TDs: 1 - |0.60 - 0.50| = 0.90
Production Score = (0.93 + 0.90)/2 = 0.915

Competition: same → 1.0
Games: 11 vs 12 → ~0.92
Context Score = (1.0 + 0.92)/2 = 0.96

Final Score =
(0.887 × 0.35) +
(0.915 × 0.35) +
(0.96 × 0.25)


compute for all players in same position in historical database and return top 5 or top 3 matches
basically iterate on entire historical database and compare, will definitely need sime thought into optimization
