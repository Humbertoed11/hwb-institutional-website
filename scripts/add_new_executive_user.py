import sqlite3
import os
from werkzeug.security import generate_password_hash

# Institutional Database Path (Root Alignment)
DB_PATH = "database/sigma_leads.db"

def add_user(username, password, full_name, email):
    if not os.path.exists(DB_PATH):
        print(f"FAILURE: Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if user already exists
        cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
        if cursor.fetchone():
            print(f"INFO: User '{username}' already exists. Updating password...")
            hashed_pw = generate_password_hash(password)
            cursor.execute("UPDATE Users SET password_hash = ? WHERE username = ?", (hashed_pw, username))
        else:
            print(f"CREATING: New user '{username}'...")
            hashed_pw = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO Users (username, password_hash, full_name, email) VALUES (?, ?, ?, ?)",
                (username, hashed_pw, full_name, email)
            )
        
        conn.commit()
        conn.close()
        print(f"SUCCESS: User '{username}' is now authorized for the SigmaFidelity™ Pulse.")
    except Exception as e:
        print(f"FAILURE: Could not register user. {str(e)}")

if __name__ == "__main__":
    # Parameters provided by the CEO
    add_user("hdominguez", "assword11", "Humberto Dominguez", "hdominguez@hwbcleaning.com")
