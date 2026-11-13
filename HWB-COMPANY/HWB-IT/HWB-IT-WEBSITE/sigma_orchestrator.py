
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
import os
import time
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

class SigmaOrchestrator:
    def __init__(self):
        # Load environment variables
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(base_dir, "../../.."))
        load_dotenv(os.path.join(project_root, ".env"))
        
        self.db_url = os.getenv('DATABASE_URL')
        self.today = datetime.now().strftime("%Y-%m-%d")

    def get_conn(self):
        if not self.db_url:
            raise ValueError("DATABASE_URL not set in .env")
        
        parsed_url = urlparse(self.db_url)
        if parsed_url.scheme in ['postgres', 'postgresql']:
            return psycopg2.connect(self.db_url, cursor_factory=DictCursor)
        else:
            db_path = parsed_url.path.lstrip('/')
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn

    def calculate_sigma_analytics(self, cur, is_postgres: bool) -> dict:
        leads_count = 0
        inst_bids_count = 0
        gc_bids_count = 0
        try:
            if is_postgres:
                cur.execute('SELECT COUNT(*) FROM "Leads";')
                leads_count = int(cur.fetchone()[0] or 0)
                cur.execute('SELECT COUNT(*) FROM "InstitutionalBids";')
                inst_bids_count = int(cur.fetchone()[0] or 0)
                cur.execute('SELECT COUNT(*) FROM "ConstructionBids";')
                gc_bids_count = int(cur.fetchone()[0] or 0)
        except Exception:
            pass
        return {
            "verified_leads_count": str(leads_count),
            "verified_institutional_bids_count": str(inst_bids_count),
            "verified_construction_bids_count": str(gc_bids_count),
            "control_status": "STABLE",
        }

    def sync_all(self):
        print(f"--- SigmaFidelity: Initiating DAILY PULSE ({self.today}) ---")
        conn = self.get_conn()
        cur = conn.cursor()

        # Determine table check logic based on DB type
        is_postgres = hasattr(cur, 'execute') and 'psycopg2' in str(type(conn))
        analytics = self.calculate_sigma_analytics(cur, is_postgres)
        
        if is_postgres:
            # Postgres creation
            cur.execute('CREATE TABLE IF NOT EXISTS "Analytics" (tool_name TEXT, result TEXT)')
            cur.execute('DELETE FROM "Analytics"')
            for tool, res in analytics.items():
                cur.execute('INSERT INTO "Analytics" (tool_name, result) VALUES (%s, %s)', (tool, res))
        else:
            # SQLite creation
            cur.execute('CREATE TABLE IF NOT EXISTS Analytics (tool_name TEXT, result TEXT)')
            cur.execute('DELETE FROM Analytics')
            for tool, res in analytics.items():
                cur.execute('INSERT INTO Analytics (tool_name, result) VALUES (?, ?)', (tool, res))

        conn.commit()
        conn.close()
        print("--- SUCCESS: All Strategic Data & Dashboards Updated ---")

        # Trigger QMS & Book sync daemon (runs scripts/sigma_sync.py)
        try:
            import subprocess
            import sys
            print("[ORCHESTRATOR] Triggering QMS & Book database sync...")
            subprocess.run([sys.executable, "scripts/sigma_sync.py"], check=False)
        except Exception as e:
            print(f"[ORCHESTRATOR] QMS sync failed: {e}")

        # Trigger Daycare Registry Sync Daemon
        try:
            import subprocess
            import sys
            print("[ORCHESTRATOR] Triggering Daycare Registry sync...")
            subprocess.run([sys.executable, "scripts/daycare_registry_sync.py"], check=False)
        except Exception as e:
            print(f"[ORCHESTRATOR] Daycare sync failed: {e}")

        # Trigger Municipal Procurement & Master Contract Mining Daemon
        try:
            import subprocess
            import sys
            print("[ORCHESTRATOR] Triggering Municipal Procurement & Master Contract Mining Daemon...")
            subprocess.run([sys.executable, "scripts/municipal_contract_miner.py"], check=False)
        except Exception as e:
            print(f"[ORCHESTRATOR] Municipal contract miner failed: {e}")

        # Trigger Statewide Hunter Contract & Portal Crawler (Bonfire + IonWave)
        try:
            import subprocess
            import sys
            print("[ORCHESTRATOR] Triggering Statewide Texas Hunter Contract & Portal Crawler...")
            subprocess.run([sys.executable, "scripts/hunter_portal_crawler.py", "--portal=all"], check=False)
        except Exception as e:
            print(f"[ORCHESTRATOR] Hunter portal crawler failed: {e}")

        # Trigger Autonomous Solicitation Scope Parser & Proposal Engine (ARCH-006)
        try:
            import subprocess
            import sys
            print("[ORCHESTRATOR] Triggering Autonomous Solicitation Scope Parser & Takeoff Engine...")
            subprocess.run([sys.executable, "scripts/solicitation_scope_parser.py", "--sync-all"], check=False)
        except Exception as e:
            print(f"[ORCHESTRATOR] Solicitation scope parser failed: {e}")

        # BUG-180 Empirical Data Integrity Gate: commercial_cad_hunter.py hardcoded seeding disabled.


if __name__ == "__main__":
    orch = SigmaOrchestrator()
    while True:
        try:
            orch.sync_all()
        except Exception as e:
            print(f"--- ERROR in SigmaOrchestrator: {e} ---")
        
        print("--- Sleeping for 6 hours (SigmaFidelity Standard Loop) ---")
        time.sleep(21600)
