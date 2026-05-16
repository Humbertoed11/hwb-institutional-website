import sqlite3
import os
import datetime
import sys
import requests
from dotenv import load_dotenv

# SigmaFidelity™ Federal Bridge: SAM.gov Sync Engine
# Version 1.3.1 (George / System Architect)
# Fix: Added postedTo parameter and MM/dd/yyyy format enforcement

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if "/app/scripts" in BASE_DIR:
    PROJECT_ROOT = "/app"
else:
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

IS_CONTAINER = os.path.exists("/app/main_app.py")

if IS_CONTAINER:
    KEY_PATH = "/app/sigma-sam-key.txt"
    DATABASE_PATH = "/app/database/sigma_leads.db"
else:
    KEY_PATH = os.path.join(PROJECT_ROOT, "HWB-COMPANY/HWB-IT/sigma-sam-key.txt")
    DATABASE_PATH = os.path.join(PROJECT_ROOT, "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db")

API_ENDPOINT = "https://api.sam.gov/opportunities/v2/search"
NAICS_CODES = ["561720", "561210"]

def get_api_key():
    env_key = os.getenv("SAM_API_KEY")
    if env_key: return env_key
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, 'r') as f:
            return f.read().strip()
    return None

def sync_sam(state=None, days=30):
    api_key = get_api_key()
    if not api_key: return

    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS sam_opportunities 
                     (notice_id TEXT PRIMARY KEY, title TEXT, naics TEXT, state TEXT, url TEXT, posted_date TEXT)''')
    
    today = datetime.datetime.now()
    since_date = (today - datetime.timedelta(days=days)).strftime('%m/%d/%Y')
    to_date = today.strftime('%m/%d/%Y')
    
    print(f"--- SigmaFidelity: Initiating SAM.gov Sync [State: {state if state else 'ALL'}] ---")
    
    count = 0
    for naics in NAICS_CODES:
        print(f"Scanning NAICS {naics}...")
        params = {
            "api_key": api_key,
            "ncode": naics,
            "postedFrom": since_date,
            "postedTo": to_date,
            "limit": 100
        }
        if state:
            params["state"] = state
            
        try:
            response = requests.get(API_ENDPOINT, params=params)
            if response.status_code == 200:
                data = response.json()
                for opp in data.get('opportunitiesData', []):
                    cursor.execute("INSERT OR IGNORE INTO sam_opportunities VALUES (?, ?, ?, ?, ?, ?)",
                                 (opp.get('noticeId'), opp.get('title'), naics, opp.get('state'), opp.get('uiLink'), opp.get('postedDate')))
                    count += 1
            elif response.status_code == 429:
                print("[CRITICAL] SAM.gov API Quota Exceeded. Throttled until next reset.")
                break
            else:
                print(f"[WARN] API Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[ERROR] Failed to query SAM.gov: {str(e)}")
            
    conn.commit()
    conn.close()
    print(f"Sync Complete. Ingested: {count} opportunities.")

if __name__ == "__main__":
    state_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sync_sam(state=state_arg)
