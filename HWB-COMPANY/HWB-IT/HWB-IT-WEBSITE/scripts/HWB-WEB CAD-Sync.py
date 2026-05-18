import requests
import sqlite3
import os
import time

# SigmaFidelity™ CAD Synchronization Engine
# Version 1.0.0 (Silas Sync Prototype)

DATABASE_PATH = "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db"
API_ENDPOINT = "https://data.texas.gov/resource/nne4-8riu.json"

def sync_collin_cad():
    if not os.path.exists(DATABASE_PATH):
        print("Error: Database not found.")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Select leads in Collin County cities
    cursor.execute("SELECT id, center_name, city FROM Leads WHERE city IN ('MCKINNEY', 'PLANO', 'FRISCO', 'ALLEN', 'PROSPER') AND industry = 'Child Care';")
    leads = cursor.fetchall()

    print(f"--- Silas Sync: Initiating CCAD API Pull for {len(leads)} leads ---")

    updated_count = 0

    for lead_id, name, city in leads:
        # Clean name for API query (remove common suffixes)
        clean_name = name.replace(" Academy", "").replace(" School", "").replace(" LLC", "").strip()
        
        try:
            # Query by DBA name and City
            params = {
                "situscity": city.upper(),
                "$where": f"dbaname like '%{clean_name.upper()}%'"
            }
            
            response = requests.get(API_ENDPOINT, params=params, timeout=10)
            data = response.json()

            if data and len(data) > 0:
                # Extract main area (SQF)
                # Note: 'imprvmainarea' is the SODA column for Gross Building Area
                sqf_val = data[0].get('imprvmainarea')
                
                if sqf_val:
                    sqf = int(sqf_val)
                    cursor.execute("UPDATE Leads SET sqf = ? WHERE id = ?", (sqf, lead_id))
                    print(f"SYNC SUCCESS: {name} -> {sqf} SQF")
                    updated_count += 1
                else:
                    print(f"SYNC GAP: {name} found but no main area data available.")
            else:
                print(f"SYNC GAP: No records found for {name} in {city}")
            
            # Rate limiting safety
            time.sleep(0.5)

        except Exception as e:
            print(f"API ERROR for {name}: {str(e)}")

    conn.commit()
    conn.close()
    print(f"--- Sync Complete: {updated_count} facilities updated with verified CAD data. ---")

if __name__ == "__main__":
    sync_collin_cad()
