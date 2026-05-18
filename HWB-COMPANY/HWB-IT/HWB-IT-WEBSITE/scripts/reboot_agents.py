import os
import sys
import json
import psycopg2
from dotenv import load_dotenv

# Ensure core is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.agents.orchestrator import SigmaOrchestrator
from core.agents.peter import PeterAgent

def run_reboot():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    print("--- SigmaFidelity: Initiating Institutional Reboot ---")
    
    # 1. Initialize Tables via PSQL
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        with open('scripts/initialize_institutional_tables.sql', 'r') as f:
            cur.execute(f.read())
        conn.commit()
        print("[SUCCESS] Institutional tables (Milestones, KB) initialized.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] SQL Initialization failed: {e}")

    # 2. Register Agents and Enqueue Startup Tasks
    try:
        orch = SigmaOrchestrator(db_url=db_url)
        peter = PeterAgent(db_url=db_url)
        
        orch.register_agent(peter)
        
        # Enqueue Initial Recovery Snapshot
        orch.enqueue_task("RECOVERY_CHECKPOINT", {"type": "db_snapshot"}, priority=1)
        print("[SUCCESS] Agents registered and startup tasks enqueued.")
    except Exception as e:
        print(f"[ERROR] Agent registration failed: {e}")

if __name__ == "__main__":
    run_reboot()
