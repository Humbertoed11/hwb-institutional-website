
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

def get_db_url():
    """Loads environment variables from the project root .env file."""
    # This script is in HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/
    # .env is in project root (3 levels up)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, "../../.."))
    load_dotenv(os.path.join(project_root, ".env"))
    return os.getenv('DATABASE_URL')

def diagnose():
    db_url = get_db_url()
    if not db_url:
        print("CRITICAL: DATABASE_URL not set in .env")
        return

    print("--- SigmaFidelity: Production Database Diagnostic ---")
    parsed_url = urlparse(db_url)
    
    conn = None
    try:
        if parsed_url.scheme in ['postgres', 'postgresql']:
            conn = psycopg2.connect(db_url, cursor_factory=DictCursor)
            cur = conn.cursor()
            
            # Get tables in Postgres
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            table_names = [row['table_name'] for row in cur.fetchall()]
            print(f"Existing Tables (Postgres): {table_names}")
            
            if 'Analytics' not in table_names:
                print("ERROR: 'Analytics' table is missing in Postgres.")
            else:
                cur.execute('SELECT * FROM "Analytics"')
                data = cur.fetchall()
                print(f"Analytics Rows Found: {len(data)}")
                for row in data:
                    print(f"- {row['tool_name']}: {row['result'][:50]}...")
                    
        else:
            # Fallback to SQLite
            db_path = parsed_url.path.lstrip('/')
            if not os.path.exists(db_path):
                print(f"CRITICAL: DB not found at {db_path}")
                return
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
            table_names = [t['name'] for t in tables]
            print(f"Existing Tables (SQLite): {table_names}")
            
            if 'Analytics' not in table_names:
                print("ERROR: 'Analytics' table is missing in SQLite.")
            else:
                data = cur.execute("SELECT * FROM Analytics").fetchall()
                print(f"Analytics Rows Found: {len(data)}")
                for row in data:
                    print(f"- {row['tool_name']}: {row['result'][:50]}...")
    
    except Exception as e:
        print(f"DIAGNOSTIC ERROR: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    diagnose()
