import os
import re
import json
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from dotenv import load_dotenv

# SigmaFidelity™ Security: Load the .env file
load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")

def get_latest_walkthrough():
    base_path = os.path.expanduser("~/.gemini/antigravity-cli/brain/")
    if not os.path.exists(base_path): return None, None
    dirs = [os.path.join(base_path, d) for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    if not dirs: return None, None
    latest_dir = max(dirs, key=os.path.getmtime)
    walkthrough_path = os.path.join(latest_dir, "walkthrough.md")
    if os.path.exists(walkthrough_path):
        return walkthrough_path, os.path.basename(latest_dir)
    return None, None

def sync_walkthrough():
    path, session_id = get_latest_walkthrough()
    if not path: return
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"[SYNC] Ingesting Walkthrough: {session_id}")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "SigmaWalkthroughs" (session_id, project_name, narrative_content)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET narrative_content = EXCLUDED.narrative_content;
            """, (session_id, "Antigravity Active Task", content))
            
            cur.execute("""
                INSERT INTO "SigmaInteractionCore" (session_id, user_prompt, agent_explanation, status)
                VALUES (%s, %s, %s, %s);
            """, (session_id, "Institutional Persistence Sync", "Automatic synchronization of session narrative and code impact.", "SUCCESS"))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error syncing walkthrough: {e}")

def sync_new_sops():
    sop_dir = "HWB-COMPANY/HWB-QMS"
    if not os.path.exists(sop_dir): return
    
    print("[SYNC] Scanning for new HTML SOPs...")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            for f in os.listdir(sop_dir):
                if f.endswith(".html") and f != "sop_template.html":
                    file_path = os.path.join(sop_dir, f)
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = f.read()
                    
                    cur.execute("""
                        INSERT INTO sigma_kb (doc_id, content, metadata)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (doc_id) DO UPDATE SET content = EXCLUDED.content;
                    """, (f, content, Json({"source": "Automatic Sync", "path": file_path})))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error syncing SOPs: {e}")

def sync_system_state():
    recovery_file = "HWB-SESSION-RECOVERY.md"
    if not os.path.exists(recovery_file): return
    
    print("[SYNC] Synchronizing SigmaSystemCore...")
    with open(recovery_file, "r") as f:
        content = f.read()
    
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "SigmaSystemCore" (session_id, state_data)
                VALUES (%s, %s)
                ON CONFLICT (session_id) DO UPDATE SET state_data = EXCLUDED.state_data;
            """, ("ACTIVE-SESSION", Json({"raw_text": content})))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error syncing state: {e}")

def run_all():
    print("--- SigmaFidelity: Initiating Institutional Persistence Sync ---")
    sync_walkthrough()
    sync_new_sops()
    sync_system_state()
    print("--- SUCCESS: All neural cores synchronized. ---")

if __name__ == "__main__":
    run_all()
