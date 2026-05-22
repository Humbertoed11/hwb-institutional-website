import os
import re
import json
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from dotenv import load_dotenv

# SigmaFidelity™ Security: Load the .env file
load_dotenv()

def get_latest_walkthrough_path():
    base_path = os.path.expanduser("~/.gemini/antigravity-cli/brain/")
    if not os.path.exists(base_path):
        return None
    
    # Sort brain directories by modification time
    dirs = [os.path.join(base_path, d) for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    if not dirs:
        return None
        
    latest_dir = max(dirs, key=os.path.getmtime)
    walkthrough_path = os.path.join(latest_dir, "walkthrough.md")
    
    if os.path.exists(walkthrough_path):
        return walkthrough_path, os.path.basename(latest_dir)
    return None, None

def parse_walkthrough(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    title_match = re.search(r'^#\s+(.*)', content)
    title = title_match.group(1).strip() if title_match else "Untitled Session"
    
    # Extract "Changes Made" section
    changes_match = re.search(r'## Changes Made\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    changes = changes_match.group(1).strip() if changes_match else ""
    
    # Extract "Validation & Testing" section
    validation_match = re.search(r'## Validation & Testing\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    validation = validation_match.group(1).strip() if validation_match else ""
    
    # Impact summary parsing (extracting bullet points from Changes Made)
    impact_points = re.findall(r'-\s+\*\*.*?\*\*:\s*(.*)', changes)
    if not impact_points:
        impact_points = re.findall(r'###.*?\n-\s*(.*)', changes)

    return {
        "title": title,
        "content": content,
        "changes": changes,
        "validation": validation,
        "impact_points": impact_points
    }

def ingest(file_path=None):
    print("--- SigmaFidelity: Initiating Neural Walkthrough Ingestion ---")
    
    if file_path:
        path = os.path.abspath(file_path)
        # If manual path, session_id is the folder containing the md file
        session_id = os.path.basename(os.path.dirname(path))
        if session_id == "scripts" or session_id == "temp_brain":
            # Fallback to current timestamp if directory name is generic
            session_id = f"manual-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    else:
        path, session_id = get_latest_walkthrough_path()
        
    if not path or not os.path.exists(path):
        print(f"ERROR: No walkthrough.md found at {path}")
        return

    print(f"[FOUND] Session: {session_id}")
    data = parse_walkthrough(path)
    
    db_url = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
    
    try:
        conn = psycopg2.connect(db_url)
        with conn.cursor() as cur:
            # Upsert into SigmaWalkthroughs
            cur.execute("""
                INSERT INTO "SigmaWalkthroughs" 
                (session_id, project_name, narrative_content, impact_summary, validation_results)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                narrative_content = EXCLUDED.narrative_content,
                impact_summary = EXCLUDED.impact_summary,
                validation_results = EXCLUDED.validation_results,
                created_at = CURRENT_TIMESTAMP;
            """, (
                session_id,
                "SigmaFidelity Modernization",
                data["content"],
                Json({"points": data["impact_points"]}),
                data["validation"]
            ))
            
            # Also log to SigmaInteractionCore for Tier 6 visibility
            cur.execute("""
                INSERT INTO "SigmaInteractionCore" (user_prompt, agent_explanation, tools_used, status, session_id)
                VALUES (%s, %s, %s, %s, %s);
            """, (
                "Neural Walkthrough Ingestion",
                f"Successfully ingested Antigravity session {session_id} into the SQL Brain.",
                Json(["psycopg2", "ingest_walkthrough.py"]),
                "SUCCESS",
                session_id
            ))
            
        conn.commit()
        conn.close()
        print(f"--- SUCCESS: Session {session_id} Synced to SQL Brain. ---")
        
    except Exception as e:
        print(f"FAILURE: Database ingestion failed. {str(e)}")

if __name__ == "__main__":
    import sys
    manual_path = sys.argv[1] if len(sys.argv) > 1 else None
    ingest(manual_path)
