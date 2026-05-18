import sqlite3
import psycopg2
import os
from datetime import datetime

# Paths
SQLITE_DB = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db"
POSTGRES_URL = "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db"

def sync_outbox():
    try:
        # 1. Get from SQLite
        s_conn = sqlite3.connect(SQLITE_DB)
        s_cur = s_conn.cursor()
        s_cur.execute("SELECT recipient, subject, body FROM PendingOutbox ORDER BY id DESC LIMIT 1")
        row = s_cur.fetchone()
        s_conn.close()
        
        if not row:
            print("No record found in SQLite.")
            return

        recipient, subject, body = row
        print(f"Syncing: {subject}")

        # 2. Push to Postgres (Using the container's internal network name if possible, or just localhost)
        # Try internal docker name first as we are likely running in a similar context
        try:
            p_conn = psycopg2.connect("postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
        except:
            p_conn = psycopg2.connect(POSTGRES_URL)
            
        p_cur = p_conn.cursor()
        p_cur.execute(
            "INSERT INTO \"PendingOutbox\" (recipient, subject, body, status, created_at) VALUES (%s, %s, %s, %s, %s)",
            (recipient, subject, body, 'Pending', datetime.now())
        )
        p_conn.commit()
        p_cur.close()
        p_conn.close()
        print("SUCCESS: Record synced to Postgres.")

    except Exception as e:
        print(f"Sync Error: {e}")

if __name__ == "__main__":
    sync_outbox()
