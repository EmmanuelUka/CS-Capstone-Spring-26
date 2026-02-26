import sqlite3
import csv
from datetime import datetime

#Note: CSV file must be in correct format

def import_from_csv(csv_path, db_name="hashmark.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    with open(csv_path, newline='', encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            # Skip completely empty rows
            if not any(row.values()):
                continue

            # Normalize and convert fields safely
            #First and Last name cannot be null; instead make them empty text
            first_name = row.get("First Name", "").strip() if row.get("First Name", "") != None else ""
            middle_name = row.get("Middle Name", "").strip() if row.get("Middle Name", "") != None else None
            last_name = row.get("Last Name", "").strip() if row.get("Last Name", "") != None else ""
            nickname = row.get("Nickname", "").strip() if row.get("Nickname", "") != None else None
            gender = row.get("Gender", "").strip() if row.get("Gender", "") != None else None

            birth_date = row.get("Birth Date", "").strip() if row.get("Birth Date", "") != None else None
            if birth_date:
                try:
                    # Ensure ISO format (YYYY-MM-DD)
                    birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date().isoformat()
                except ValueError:
                    birth_date = None
            else:
                birth_date = None

            grad_year = row.get("Grad. Year", "").strip() if row.get("Grad. Year", "") != None else None
            grad_year = int(grad_year) if grad_year != None and grad_year.isdigit() else None

            status = row.get("Status", "").strip() if row.get("Status", "") != None else None

            star_rating = row.get("Star Rating", "").strip() if row.get("Star Rating", "") != None else None
            star_rating = int(star_rating) if star_rating != None and star_rating.isdigit() else None

            positions = row.get("Positions", "").strip() if row.get("Positions", "") != None else None

            height = row.get("Height", "").strip() if row.get("Height", "") != None else None
            height = height if height else None

            weight = row.get("Weight", "").strip() if row.get("Weight", "") != None else None
            weight = float(weight) if weight else None

            cursor.execute("""
                INSERT INTO recruits (
                    first_name, middle_name, last_name, nickname,
                    gender, birth_date, grad_year, status,
                    star_rating, positions, height, weight
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                first_name, middle_name, last_name, nickname,
                gender, birth_date, grad_year, status,
                star_rating, positions, height, weight
            ))

    conn.commit()
    conn.close()
    print(f"Data successfully imported from '{csv_path}'.")

if __name__ == '__main__':
    import_from_csv(csv_path="import.csv")