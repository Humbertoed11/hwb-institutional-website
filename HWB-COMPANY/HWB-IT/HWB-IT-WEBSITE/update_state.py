import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()

def sync():
    with open("HWB-SESSION-RECOVERY.md", "r") as f:
        content = f.read()
    
    db_url = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
    conn = psycopg2.connect(db_url)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO "SigmaSystemCore" (session_id, state_data)
            VALUES (%s, %s)
            ON CONFLICT (session_id) DO UPDATE SET
            state_data = EXCLUDED.state_data,
            updated_at = CURRENT_TIMESTAMP;
        """, ("05-22-2026-FINAL", Json({"raw_text": content})))
    conn.commit()
    conn.close()
    print("SUCCESS: SigmaSystemCore synchronized with HWB-SESSION-RECOVERY.md")

if __name__ == "__main__":
    sync()
