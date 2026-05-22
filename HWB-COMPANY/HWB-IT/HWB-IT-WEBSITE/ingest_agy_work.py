import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()

def ingest():
    with open(".antigravity_plan.md", "r") as f:
        plan_content = f.read()
    with open(".antigravity_walkthrough.md", "r") as f:
        walkthrough_content = f.read()
    
    db_url = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
    conn = psycopg2.connect(db_url)
    with conn.cursor() as cur:
        # Ingest into SigmaInteractionCore
        cur.execute("""
            INSERT INTO "SigmaInteractionCore" 
            (session_id, user_prompt, agent_explanation, tools_used, status)
            VALUES (%s, %s, %s, %s, %s);
        """, (
            "b86debf3-9c83-40f5-b07c-7f60e9c521f0",
            "Modernize QMS Web Manual (BUG-032)",
            "Antigravity drafted a detailed implementation plan for dynamic sidebars and Salesforce-tier controls. (Note: Initial write failed due to quota; manual recovery performed).",
            Json(["Antigravity CLI", "implementation_plan.md"]),
            "SUCCESS"
        ))
        
        # Ingest into SigmaWalkthroughs
        cur.execute("""
            INSERT INTO "SigmaWalkthroughs" 
            (session_id, project_name, narrative_content)
            VALUES (%s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET narrative_content = EXCLUDED.narrative_content;
        """, ("b86debf3-9c83-40f5-b07c-7f60e9c521f0", "QMS Hardening", walkthrough_content))

    conn.commit()
    conn.close()
    print("SUCCESS: Antigravity local work synced to SQL Brain.")

if __name__ == "__main__":
    ingest()
