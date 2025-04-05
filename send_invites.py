import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DB_PATH = "db/database.sqlite"

# 🔐 SET YOUR GMAIL
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
YOUR_EMAIL = "yourname@gmail.com"
YOUR_PASSWORD = "your-app-password"

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = YOUR_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(YOUR_EMAIL, YOUR_PASSWORD)
        server.send_message(msg)
        print(f"📩 Sent to {to_email}")

def send_invites(threshold=0.70):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT m.job_id, m.candidate_id, m.similarity_score, c.email, c.name, j.title
        FROM matches m
        JOIN candidates c ON m.candidate_id = c.candidate_id
        JOIN jobs j ON m.job_id = j.job_id
        WHERE m.similarity_score >= ?
    """, (threshold,))

    matches = cursor.fetchall()
    conn.close()

    for job_id, cid, score, email, name, job_title in matches:
        subject = f"Interview Invitation for {job_title}"
        body = f"""
Hi {name},

Congratulations! Based on your resume, you’ve been shortlisted for the position of {job_title} at our company.

Match Score: {score:.2f}

Please reply to this email to confirm your availability for the interview. Here are a few tentative slots:
- Option 1: Tomorrow, 10:00 AM
- Option 2: Day after, 2:00 PM
- Option 3: Next Monday, 11:30 AM

Looking forward to your response.

Best regards,  
Recruitment Team  
"""

        send_email(email, subject, body)

if __name__ == "__main__":
    send_invites(threshold=0.70)
