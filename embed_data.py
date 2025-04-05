import sqlite3
import requests
import json

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
MODEL_NAME = "mxbai-embed-large"
DB_PATH = "db/database.sqlite"

def get_embedding(text):
    response = requests.post(OLLAMA_EMBED_URL, json={
        "model": MODEL_NAME,
        "prompt": text
    })
    response.raise_for_status()
    return response.json()["embedding"]

def update_candidate_embeddings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT candidate_id, resume_text FROM candidates WHERE embedding IS NULL")

    for cid, text in cursor.fetchall():
        print(f"📌 Embedding resume for: {cid}")
        embedding = get_embedding(text)
        cursor.execute("UPDATE candidates SET embedding = ? WHERE candidate_id = ?",
                       (json.dumps(embedding), cid))

    conn.commit()
    conn.close()

def update_job_embeddings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT job_id, description FROM jobs WHERE embedding IS NULL")

    for jid, text in cursor.fetchall():
        print(f"📌 Embedding job: {jid}")
        embedding = get_embedding(text)
        cursor.execute("UPDATE jobs SET embedding = ? WHERE job_id = ?",
                       (json.dumps(embedding), jid))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_candidate_embeddings()
    update_job_embeddings()
    print("✅ All embeddings saved to SQLite!")
