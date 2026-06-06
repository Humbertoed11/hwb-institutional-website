import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
import sys

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def log_event(prompt, explanation, status="SUCCESS"):
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "HEX_InteractionCore" (user_prompt, agent_explanation, status)
                VALUES (%s, %s, %s);
            """, (prompt, explanation, status))
        conn.commit()
        conn.close()
        print(f"Logged to HEX_InteractionCore: {prompt}")
    except Exception as e:
        print(f"Logging failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        log_event(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "SUCCESS")
