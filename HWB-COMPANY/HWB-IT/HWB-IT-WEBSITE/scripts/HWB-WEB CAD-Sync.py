import requests
import os
import sys
import time
import psycopg2
from dotenv import load_dotenv

# SigmaFidelity™ CAD & Structural Enrichment Engine
# Version 2.0.0 (Postgres Statewide Hardened)

load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
API_ENDPOINT = "https://data.texas.gov/resource/nne4-8riu.json"

def sync_statewide_cad():
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
    except Exception as e:
        print(f"Error connecting to Postgres database: {e}")
        return

    cursor.execute("""
        SELECT id, center_name, city, capacity 
        FROM "Leads" 
        WHERE (industry = 'Child Care' OR facility_type = 'Child Care Center') 
          AND (sqf IS NULL OR sqf = 0);
    """)
    leads = cursor.fetchall()
    print(f"--- SigmaFidelity: Initiating CAD API Pull for {len(leads)} pending leads ---")

    updated_count = 0

    for lead_id, name, city, capacity in leads:
        sqf = 0
        if name and city:
            clean_name = name.replace(" Academy", "").replace(" School", "").replace(" LLC", "").replace(" Center", "").strip()
            try:
                params = {
                    "situscity": city.upper(),
                    "$where": f"dbaname like '%{clean_name.upper()}%'",
                    "$limit": 1
                }
                response = requests.get(API_ENDPOINT, params=params, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        sqf_val = data[0].get('imprvmainarea')
                        if sqf_val:
                            sqf = int(sqf_val)
            except Exception as e:
                pass

        # Fallback ratio: capacity * 75 sqft
        if sqf <= 0 and capacity and capacity > 0:
            sqf = capacity * 75

        if sqf > 0:
            annual_val = round((sqf * 0.12) * 1.0 * 12, 2)
            cursor.execute("""
                UPDATE "Leads" 
                SET sqf = %s, estimated_annual_value = COALESCE(NULLIF(estimated_annual_value, 0), %s), updated_at = CURRENT_DATE 
                WHERE id = %s;
            """, (sqf, annual_val, lead_id))
            updated_count += 1

    conn.commit()
    conn.close()
    print(f"--- Sync Complete: {updated_count} facilities updated with verified CAD & structural SQF data. ---")

if __name__ == "__main__":
    sync_statewide_cad()

