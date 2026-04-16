# Hashmark Recruiting Assistant: How to Run

## 1. Install backend and frontend dependancies:

From the ```frontend/``` directory run: ```npm i```
From the ```backend/app/``` directory run: ```pip install -r requirements.txt```

## 2. Create the database and insert data for historical comparisons:

From the ```backend/data/``` directory, ensure that ```mac_players_dataframe.csv``` is there and run: ```python create_database.py```

## 3. To run the application locally:

From the ```frontend/``` directory run: ```npm run main```