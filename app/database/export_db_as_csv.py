import sqlite3
import pandas as pd

def export_to_csv(db_name="recruits.db", export_path="recruits_export.csv"):
    """
    Export recruits table to a CSV file.

    Args:
        db_name (str): Path to SQLite database.
        export_path (str): Output CSV file path.

    Returns:
        pandas.DataFrame: DataFrame containing exported data.
    """

    # Connect to database
    conn = sqlite3.connect(db_name)

    try:
        # Load table into DataFrame
        df = pd.read_sql_query("SELECT * FROM recruits", conn)

        # Force integer columns to pandas nullable integer type
        if "grad_year" in df.columns:
            df["grad_year"] = df["grad_year"].astype("Int64")

        if "star_rating" in df.columns:
            df["star_rating"] = df["star_rating"].astype("Int64")

        # Export to CSV
        df.to_csv(export_path, index=False)

        print(f"Data successfully exported to '{export_path}'.")
        return df

    finally:
        conn.close()

if __name__ == '__main__':
    df = export_to_csv(
        db_name="hashmark.db",
        export_path="export.csv"
    )

    print(df.head())