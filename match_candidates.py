import sqlite3
import json
import math

DB_PATH = "db/database.sqlite"

def cosine_similarity(vec1, vec2):
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def load_embeddings(table_name, key_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT {key_name}, embedding FROM {table_name} WHERE embedding IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()
    data = {}
    for key, embed_json in rows:
        try:
            data[key] = json.loads(embed_json)
        except Exception as e:
            print(f"❌ Failed parsing embedding for {key}: {e}")
    return data
import sqlite3

def save_match(job_id, candidate_id, score):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO matches (job_id, candidate_id, similarity_score)
    VALUES (?, ?, ?)
    """, (job_id, candidate_id, score))
    conn.commit()
    conn.close()

def match_all_jobs(threshold=0.70):
    jobs = load_embeddings("jobs", "job_id")
    candidates = load_embeddings("candidates", "candidate_id")

    for job_id, job_vector in jobs.items():
        print(f"\n🔍 Matches for Job ID {job_id}:")
        scores = []
        for cid, cand_vector in candidates.items():
            sim = cosine_similarity(job_vector, cand_vector)
            scores.append((cid, sim))

        # Sort by similarity
        scores.sort(key=lambda x: x[1], reverse=True)

        for rank, (cid, score) in enumerate(scores[:3], start=1):  # top 3
            match_str = "✅" if score >= threshold else "❌"
            print(f"{match_str} Rank {rank}: {cid} → Score: {score:.4f}")
            if score >= threshold:
                save_match(job_id, cid, score)


if __name__ == "__main__":
    match_all_jobs(threshold=0.70)
