import sqlite3
import requests
import os
import json
from datetime import datetime

# SigmaFidelity™ LinkedIn Dispatcher
# Version 1.0.0 (George / System Architect)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "../HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db")

def dispatch_posts():
    if not os.path.exists(DATABASE_PATH):
        print(f"Error: Database not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Retrieve Credentials
    token_row = cursor.execute("SELECT value FROM SystemSettings WHERE key = 'linkedin_access_token'").fetchone()
    urn_row = cursor.execute("SELECT value FROM SystemSettings WHERE key = 'linkedin_member_urn'").fetchone()

    if not token_row or not urn_row:
        print("Muda Alert: LinkedIn not authorized. Skipping dispatch.")
        conn.close()
        return

    access_token = token_row['value']
    member_urn = urn_row['value']

    # 2. Identify APPROVED posts
    approved_posts = cursor.execute("SELECT * FROM SocialOutbox WHERE platform = 'LinkedIn' AND status = 'APPROVED'").fetchall()

    if not approved_posts:
        print("Status: No approved LinkedIn posts in queue.")
        conn.close()
        return

    print(f"--- SigmaFidelity: Dispatching {len(approved_posts)} Approved LinkedIn Posts ---")

    endpoint = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    for post in approved_posts:
        print(f"Processing Post ID: {post['id']}...")
        
        post_body = {
            "author": member_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post['content']
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        try:
            response = requests.post(endpoint, headers=headers, json=post_body)
            if response.status_code == 201:
                print(f"SUCCESS: Post {post['id']} published to LinkedIn.")
                cursor.execute("UPDATE SocialOutbox SET status = 'SENT' WHERE id = ?", (post['id'],))
                
                # Log to Activity Log
                cursor.execute(
                    "INSERT INTO ActivityLog (date, activity_name, hours, category) VALUES (?, ?, ?, ?)",
                    (datetime.now().strftime("%Y-%m-%d"), f"LinkedIn Post Published: ID {post['id']}", 0.5, "Marketing Distribution")
                )
            else:
                print(f"FAILURE: Status {response.status_code} - {response.text}")
        except Exception as e:
            print(f"CRITICAL ERROR: {str(e)}")

    conn.commit()
    conn.close()
    print("--- LinkedIn Dispatch Cycle Complete ---")

if __name__ == "__main__":
    dispatch_posts()
