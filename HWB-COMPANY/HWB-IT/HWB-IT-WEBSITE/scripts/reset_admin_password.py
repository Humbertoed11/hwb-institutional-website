import sqlite3
import os
from werkzeug.security import generate_password_hash

# Institutional Database Path
DB_PATH = "database/sigma_leads.db"

def reset_passwords():
    if not os.path.exists(DB_PATH):
        print("FAILURE: DB not found.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Reset 'admin'
        hashed_admin = generate_password_hash("HWB-Admin-2026!")
        cursor.execute("UPDATE Users SET password_hash = ? WHERE username = 'admin'", (hashed_admin,))
        
        # Reset 'hdominguez'
        hashed_humb = generate_password_hash("assword11")
        cursor.execute("UPDATE Users SET password_hash = ? WHERE username = 'hdominguez'", (hashed_humb,))

        conn.commit()
        conn.close()
        print("SUCCESS: Passwords for 'admin' and 'hdominguez' have been reset and synchronized.")
    except Exception as e:
        print(f"FAILURE: {str(e)}")

if __name__ == "__main__":
    reset_passwords()
