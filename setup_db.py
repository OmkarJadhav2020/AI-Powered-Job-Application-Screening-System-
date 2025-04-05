import sqlite3

DB_PATH = "db/database.sqlite"

def create_matches_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        match_id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        candidate_id TEXT,
        similarity_score REAL,
        matched_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
    print("✅ matches table created!")

if __name__ == "__main__":
    create_matches_table()
