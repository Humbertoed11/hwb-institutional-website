import sqlite3
import os

# Root Database Path
DB_PATH = "database/sigma_leads.db"

def audit_users():
    if not os.path.exists(DB_PATH):
        print(f"FAILURE: Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        print("--- SigmaFidelity: Production User Audit ---")
        cursor.execute("SELECT id, username, full_name, email FROM Users")
        users = cursor.fetchall()
        
        if not users:
            print("WARNING: No users found in the database.")
        else:
            for u in users:
                print(f"- ID: {u['id']} | Username: {u['username']} | Name: {u['full_name']} | Email: {u['email']}")
        
        conn.close()
    except Exception as e:
        print(f"FAILURE: Could not audit users. {str(e)}")

if __name__ == "__main__":
    audit_users()
