import sqlite3
conn = sqlite3.connect("db/database.sqlite")
cursor = conn.cursor()

cursor.execute("SELECT typeof(job_id) FROM matches LIMIT 1")
rows = cursor.fetchall()
for row in rows:
    print(row)

conn.close()
