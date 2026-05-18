import requests
import sqlite3
import os
import datetime
import sys

# SigmaFidelity™ Federal Bridge: SAM.gov Sync Engine
# Version 1.2.0 (George / System Architect)
# Added: State-specific filtering and command-line arguments

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(BASE_DIR, "../HWB-COMPANY/HWB-IT/sigma-sam-key.txt")
DATABASE_PATH = os.path.join(BASE_DIR, "../HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db")
API_ENDPOINT = "https://api.sam.gov/opportunities/v2/search"

NAICS_CODES = ["561720", "561210"]

def get_api_key():
    if not os.path.exists(KEY_PATH):
        return None
    with open(KEY_PATH, 'r') as f:
        return f.read().strip()

def sync_sam(state=None, days=30):
    api_key = get_api_key()
    if not api_key: return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    print(f"--- SigmaFidelity: Initiating SAM.gov Sync [State: {state or 'National'}] ---")

    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=days)
    
    total_found = 0
    total_ingested = 0

    for code in NAICS_CODES:
        print(f"Scanning NAICS {code}...")
        
        params = {
            "api_key": api_key,
            "ncode": code,
            "postedFrom": start_date.strftime("%m/%d/%Y"),
            "postedTo": today.strftime("%m/%d/%Y"),
            "limit": 100
        }
        if state:
            params["state"] = state

        try:
            response = requests.get(API_ENDPOINT, params=params, timeout=20)
            if response.status_code != 200: continue
                
            data = response.json()
            opportunities = data.get('opportunitiesData', [])
            total_found += len(opportunities)

            for opp in opportunities:
                title = opp.get('title', 'Unknown')
                sol_id = opp.get('solicitationNumber', 'N/A')
                center_name = f"FED: {title} ({sol_id})"
                
                # Deduplication
                cursor.execute("SELECT id FROM Leads WHERE center_name = ?", (center_name,))
                if cursor.fetchone(): continue

                office = opp.get('officeAddress', {})
                address = f"{office.get('streetAddress', '')}, {office.get('city', '')}, {office.get('state', '')} {office.get('zipcode', '')}".strip(", ")
                city = office.get('city', 'USA')
                st = office.get('state', state or 'FEDERAL')
                zipc = office.get('zipcode', 'N/A')
                
                poc_list = opp.get('pointOfContact', [])
                primary_poc = poc_list[0] if poc_list else {}
                email = primary_poc.get('email', 'N/A')
                phone = primary_poc.get('phone', 'N/A')
                director = primary_poc.get('fullName', 'Contracting Officer')
                
                industry = "Federal Janitorial" if code == "561720" else "Federal Facility Support"

                cursor.execute('''
                    INSERT INTO Leads (
                        process_id, job_title, center_name, email, phone, 
                        address, calculated_waste, director, city, state, 
                        zipcode, industry, sqf
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ('FED-BID', 'Contracting Officer', center_name, email, phone,
                    address, 15000.0, director, city, st, zipc, industry, 25000))
                total_ingested += 1

        except Exception as e:
            print(f"Error: {str(e)}")

    conn.commit()
    conn.close()
    print(f"Sync Complete. Ingested: {total_ingested} opportunities.")

if __name__ == "__main__":
    state_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sync_sam(state=state_arg)
