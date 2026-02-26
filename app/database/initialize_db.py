import sqlite3

def initialize_database(db_name="hashmark.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create recruits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recruits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            middle_name TEXT,
            last_name TEXT NOT NULL,
            nickname TEXT,
            gender TEXT,
            birth_date DATE,
            grad_year INTEGER,
            status TEXT,
            star_rating INTEGER CHECK(star_rating BETWEEN 0 AND 5), -- 0 means not rated
            positions TEXT,
            height TEXT,   -- store height as text, so any format should work
            weight REAL    -- store weight in pounds (or kg if you prefer)
        );
    """)

    conn.commit()
    conn.close()
    print(f"Database '{db_name}' initialized with table 'recruits'.")

if __name__ == "__main__":
    initialize_database()