import streamlit as st
import sqlite3
import pandas as pd
import os
import tempfile
from PyPDF2 import PdfReader
import json
import uuid
import re
import ollama
import subprocess

DB_PATH = "db/database.sqlite"

# ──────────────────────────────────────────────
# Cached DB fetch
# ──────────────────────────────────────────────
@st.cache_data
def get_jobs():
    conn = sqlite3.connect(DB_PATH)
    jobs_df = pd.read_sql_query("SELECT job_id, title FROM jobs", conn)
    conn.close()
    return jobs_df

@st.cache_data
def get_matches_for_job(job_id):
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT m.similarity_score, c.name, c.email, c.skills, c.resume_text, j.title
    FROM matches m
    JOIN candidates c ON m.candidate_id = c.candidate_id
    JOIN jobs j ON m.job_id = j.job_id
    WHERE m.job_id = ?
    ORDER BY m.similarity_score DESC
    """
    df = pd.read_sql_query(query, conn, params=(job_id,))
    conn.close()
    return df

# ──────────────────────────────────────────────
# Resume Upload Logic
# ──────────────────────────────────────────────
def process_uploaded_resume(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        reader = PdfReader(tmp_path)
        full_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except Exception as e:
        st.error(f"❌ PDF text extraction failed: {e}")
        return

    name = uploaded_file.name.split(".")[0]
    email = find_first_email(full_text)
    skills = extract_section(full_text, "Skills")
    resume_text = full_text.strip()
    embedding = get_embedding_ollama(resume_text)

    if embedding:
        insert_resume(name, email, skills, resume_text, embedding)
        st.success(f"✅ {uploaded_file.name} ingested!")

def find_first_email(text):
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+", text)
    return match.group(0) if match else "unknown@email.com"

def extract_section(text, header):
    lines = text.splitlines()
    section = []
    capture = False
    for line in lines:
        if header.lower() in line.lower():
            capture = True
            continue
        if capture:
            if line.strip() == "" or any(h in line.lower() for h in ["education", "work", "certifications", "experience"]):
                break
            section.append(line.strip())
    return ", ".join(section)

def get_embedding_ollama(text):
    try:
        response = ollama.embeddings(model="nomic-embed-text", prompt=text)
        return json.dumps(response["embedding"])
    except Exception as e:
        st.error(f"❌ Embedding failed: {e}")
        return None

def generate_candidate_id(name):
    return f"C{str(uuid.uuid4())[:8].upper()}"

def insert_resume(name, email, skills, resume_text, embedding):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO candidates (candidate_id, name, email, skills, resume_text, embedding)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        generate_candidate_id(name),
        name,
        email,
        skills,
        resume_text,
        embedding
    ))
    conn.commit()
    conn.close()

def send_email(to_email, subject, body):
    st.success(f"📨 Email sent to {to_email} (simulated)")

st.set_page_config(page_title="AI Resume Matcher", page_icon="🧠", layout="wide")
st.title("🧠 AI Resume Matcher")
st.markdown("Upload resumes, match them to jobs, and contact top candidates instantly.")

# Upload Resumes
with st.sidebar.expander("📤 Upload New Resumes"):
    uploaded_files = st.file_uploader("Upload PDF resumes", type="pdf", accept_multiple_files=True)
    if uploaded_files:
        if st.button("🚀 Process Resumes"):
            for file in uploaded_files:
                process_uploaded_resume(file)

# Upload JDs
with st.sidebar.expander("📝 Upload New Job Descriptions"):
    jd_file = st.file_uploader("Upload CSV file", type="csv", key="job_csv")
    if jd_file is not None:
        jd_df = pd.read_csv(jd_file)
        st.success(f"✅ Loaded {len(jd_df)} job descriptions.")
        if st.button("➕ Insert into DB"):
            conn = sqlite3.connect(DB_PATH)
            for _, row in jd_df.iterrows():
                title = row.get("title") or row.get("Title") or "Untitled"
                description = row.get("description") or row.get("Description") or ""
                embedding = get_embedding_ollama(description)
                conn.execute(
                    "INSERT INTO jobs (title, description, embedding) VALUES (?, ?, ?)",
                    (title, description, embedding)
                )
            conn.commit()
            conn.close()
            st.success("📥 Job descriptions inserted with embeddings!")

# Trigger original scripts
st.sidebar.header("⚙️ Trigger Pipeline Phases")
if st.sidebar.button("Run ingest_data.py"):
    result = subprocess.run(["python", "ingest_data.py"], capture_output=True, text=True)
    st.sidebar.code(result.stdout)
    if result.stderr:
        st.sidebar.error(result.stderr)

if st.sidebar.button("Run embed_data.py"):
    result = subprocess.run(["python", "embed_data.py"], capture_output=True, text=True)
    st.sidebar.code(result.stdout)
    if result.stderr:
        st.sidebar.error(result.stderr)

if st.sidebar.button("Run match_candidates.py"):
    result = subprocess.run(["python", "match_candidates.py"], capture_output=True, text=True)
    st.sidebar.code(result.stdout)
    if result.stderr:
        st.sidebar.error(result.stderr)

if st.sidebar.button("Run send_invites.py"):
    result = subprocess.run(["python", "send_invites.py"], capture_output=True, text=True)
    st.sidebar.code(result.stdout)
    if result.stderr:
        st.sidebar.error(result.stderr)

# Threshold Filter
threshold = st.sidebar.slider("🔍 Minimum Match Score", 0.0, 1.0, 0.70, 0.01)

# Job selection
jobs_df = get_jobs()
job_title = st.selectbox("Select a Job to View Matches", jobs_df["title"].tolist())
selected_job_id = int(jobs_df[jobs_df["title"] == job_title]["job_id"].values[0])

# Display candidates
matches_df = get_matches_for_job(selected_job_id)
matches_df = matches_df[matches_df["similarity_score"] >= threshold]

st.markdown(f"### 🎯 Top Candidates for: {job_title}")

if not matches_df.empty:
    for idx, row in matches_df.iterrows():
        with st.expander(f"{row['name']} — Score: {row['similarity_score']:.2f}"):
            st.markdown(f"**📧 Email:** {row['email']}")
            st.markdown(f"**🧠 Skills:** {row['skills']}")
            col1, col2 = st.columns(2)

            with col1:
                if st.button(f"📩 Send Email to {row['name']}", key=f"send_{idx}"):
                    subject = f"Interview Invitation: {row['title']}"
                    body = f"""
Hi {row['name']},

You've been shortlisted for the role of {row['title']}.

Please reply with your availability for an interview.

Match Score: {row['similarity_score']:.2f}

Best,  
Recruitment Team
"""
                    send_email(row['email'], subject, body)

            with col2:
                if st.button("🔍 View Resume", key=f"resume_{idx}"):
                    st.text_area("📄 Resume Content", row['resume_text'], height=300)

    # CSV download
    csv = matches_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Match List as CSV", data=csv, file_name=f"{job_title}_matches.csv", mime="text/csv")
else:
    st.warning("⚠️ No matches found above threshold. Try lowering the score.")