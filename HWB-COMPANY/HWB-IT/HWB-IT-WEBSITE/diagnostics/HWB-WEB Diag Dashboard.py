import sqlite3
import os

def diagnose():
    db_path = 'database/sigma_leads.db'
    if not os.path.exists(db_path):
        print(f"CRITICAL: DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- SigmaFidelity: Production Database Diagnostic ---")
    
    # Check for Analytics table
    try:
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        table_names = [t['name'] for t in tables]
        print(f"Existing Tables: {table_names}")
        
        if 'Analytics' not in table_names:
            print("ERROR: 'Analytics' table is missing.")
        else:
            data = cursor.execute("SELECT * FROM Analytics").fetchall()
            print(f"Analytics Rows Found: {len(data)}")
            for row in data:
                print(f"- {row['tool_name']}: {row['result'][:50]}...")

    except Exception as e:
        print(f"SQL ERROR: {e}")

    conn.close()

if __name__ == "__main__":
    diagnose()
