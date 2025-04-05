from pdfminer.high_level import extract_text
import sqlite3
import pandas as pd
import os

DB_PATH = "db/database.sqlite"
CV_FOLDER = "data/cvs"
JOB_CSV = "data/job_description.csv"

def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        job_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        summary TEXT,
        embedding BLOB
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        candidate_id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        phone TEXT,
        education TEXT,
        experience TEXT,
        skills TEXT,
        certifications TEXT,
        achievements TEXT,
        tech_stack TEXT,
        resume_text TEXT,
        embedding BLOB
    )
    """)

    conn.commit()
    conn.close()

def extract_fields(text):
    fields = {
        "name": "", "email": "", "phone": "",
        "education": "", "experience": "", "skills": "",
        "certifications": "", "achievements": "", "tech_stack": ""
    }

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sections = {
        "education": ["education"],
        "experience": ["work experience", "professional experience"],
        "skills": ["skills", "technical skills"],
        "certifications": ["certifications"],
        "achievements": ["achievements", "accomplishments"],
        "tech_stack": ["tech stack", "technology stack", "tools"]
    }

    current_section = None
    buffer = []

    for line in lines:
        lower = line.lower()

        # Extract name/email/phone as exact fields
        if "name:" in lower:
            fields["name"] = line.split(":", 1)[-1].strip()
        elif "email:" in lower:
            fields["email"] = line.split(":", 1)[-1].strip()
        elif "phone:" in lower:
            fields["phone"] = line.split(":", 1)[-1].strip()

        # Check if this line starts a known section
        matched_section = None
        for key, keywords in sections.items():
            for keyword in keywords:
                if lower.startswith(keyword):
                    matched_section = key
                    break

        if matched_section:
            # If we're switching to a new section, save the old one
            if current_section and buffer:
                fields[current_section] = " ".join(buffer).strip()
                buffer = []
            current_section = matched_section
        elif current_section:
            buffer.append(line)

    # Save the final section at the end
    if current_section and buffer:
        fields[current_section] = " ".join(buffer).strip()

    return fields


def ingest_resumes():
    conn = sqlite3.connect(DB_PATH)
    for file in os.listdir(CV_FOLDER):
        if file.endswith(".pdf"):
            path = os.path.join(CV_FOLDER, file)
            cid = file.replace(".pdf", "")
            text = extract_text(path)
            data = extract_fields(text)
            conn.execute("""
            INSERT OR REPLACE INTO candidates (
                candidate_id, name, email, phone,
                education, experience, skills, certifications,
                achievements, tech_stack, resume_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cid, data["name"], data["email"], data["phone"],
                data["education"], data["experience"], data["skills"],
                data["certifications"], data["achievements"],
                data["tech_stack"], text
            ))
    conn.commit()
    conn.close()

def ingest_jobs():
    df = pd.read_csv(JOB_CSV, encoding='ISO-8859-1')
    conn = sqlite3.connect(DB_PATH)
    for _, row in df.iterrows():
        conn.execute("INSERT INTO jobs (title, description) VALUES (?, ?)",
                     (row["Job Title"], row["Job Description"]))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Creating tables...")
    create_tables()
    print("Ingesting resumes from PDFs...")
    ingest_resumes()
    print("Ingesting job descriptions from CSV...")
    ingest_jobs()
    print("✅ Done! Data inserted into db/database.sqlite")
