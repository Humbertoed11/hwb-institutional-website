import os
import time
import requests
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# --- SigmaFidelity™ Texas Daycare Registry Sync Daemon ---
# Responsibility: George (Systems Architect)
# Mandated by HWB-QMS-11.1 (Incremental Lead Ingestion)

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
if "@localhost" in DB_URL and os.path.exists("/.dockerenv"):
    DB_URL = DB_URL.replace("@localhost", "@db")

API_ENDPOINT = "https://data.texas.gov/resource/bc5r-88dy.json"
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'HWB-COMPANY', 'HWB-IT', 'HWB-IT-WEBSITE'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from core.services.sanitizer import clean_phone
except ImportError:
    try:
        from HWB_COMPANY.HWB_IT.HWB_IT_WEBSITE.core.services.sanitizer import clean_phone
    except ImportError:
        def clean_phone(p):
            if not p: return None
            d = ''.join(c for c in str(p) if c.isdigit())
            if len(d) == 11 and d.startswith('1'): d = d[1:]
            if len(d) == 10: return f"({d[:3]})-{d[3:6]}-{d[6:]}"
            return p

def sync_daycares(force=False):
    print(f"--- SigmaFidelity: Initiating Texas Daycare API Sync ---", flush=True)
    
    # Check last run timestamp to prevent redundant API hits
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("SELECT last_run FROM routine_schedule WHERE routine_id = 'daycare_sync';")
        row = cur.fetchone()
        if row and not force:
            last_run = row[0]
            days_since = (datetime.now() - last_run).days
            if days_since < 30:
                print(f"[SKIP] Daycare sync was run {days_since} days ago. Monthly interval not reached.", flush=True)
                conn.close()
                return True
        conn.close()
    except Exception as e:
        print(f"[DATABASE WARNING] Could not check routine schedule: {e}", flush=True)

    start_time = time.time()
    
    # 1. Fetch active Licensed Centers statewide across all of Texas (2026-07-22 Mandate)
    params = {
        "$where": "operation_type = 'Licensed Center' AND operation_status = 'Y'",
        "$limit": 15000
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params, timeout=30)
        if response.status_code != 200:
            print(f"[API ERROR] Texas Daycare Portal returned status {response.status_code}: {response.text}", flush=True)
            return False
        
        records = response.json()
        fetch_latency = time.time() - start_time
        print(f"[SYNC] Successfully fetched {len(records)} active Texas Licensed Centers in {fetch_latency:.2f}s", flush=True)
    except Exception as e:
        print(f"[API ERROR] Failed to query Texas Daycare Portal: {e}", flush=True)
        return False
    
    # 2. Database Ingestion Core
    new_count = 0
    updated_count = 0
    skipped_count = 0
    
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        for idx, item in enumerate(records):
            op_num = item.get("operation_number")
            if not op_num:
                continue
                
            process_id = f"texas-ccl-{op_num}"
            center_name = item.get("operation_name", "").strip()
            raw_phone = item.get("phone_number", "").strip()
            phone = clean_phone(raw_phone) or raw_phone
            address = item.get("address_line") or item.get("location_address", "")
            address = address.strip()
            city = item.get("city", "").strip().upper()
            county = item.get("county", "").strip().upper()
            zipcode = item.get("zipcode", "").strip()
            director = item.get("administrator_director_name", "").strip()
            
            try:
                capacity = int(item.get("total_capacity", 0))
            except ValueError:
                capacity = 0
                
            state = item.get("state", "TX").strip().upper()
            
            # Lookup lead by unique process_id or center_name + address
            cur.execute("""
                SELECT id, capacity, phone, director, address, process_id FROM "Leads"
                WHERE process_id = %s OR (LOWER(center_name) = LOWER(%s) AND LOWER(address) = LOWER(%s))
                LIMIT 1;
            """, (process_id, center_name, address))
            row = cur.fetchone()
            
            if row:
                lead_id, db_capacity, db_phone, db_director, db_address, db_pid = row
                
                # Check for updates or format drift
                needs_update = False
                update_fields = []
                
                if db_capacity != capacity:
                    needs_update = True
                    update_fields.append("capacity")
                clean_db_phone = clean_phone(db_phone) or (db_phone or "")
                if clean_db_phone != (phone or ""):
                    needs_update = True
                    update_fields.append("phone")
                if (db_director or "") != director:
                    needs_update = True
                    update_fields.append("director")
                if (db_address or "").lower() != address.lower():
                    needs_update = True
                    update_fields.append("address")
                if db_pid != process_id:
                    needs_update = True
                    update_fields.append("process_id")
                    
                if needs_update:
                    cur.execute("""
                        UPDATE "Leads"
                        SET capacity = %s, phone = %s, director = %s, address = %s, process_id = %s, updated_at = %s
                        WHERE id = %s;
                    """, (capacity, phone, director, address, process_id, datetime.now().date(), lead_id))
                    updated_count += 1
                else:
                    skipped_count += 1
            else:
                # Insert new daycare lead
                cur.execute("""
                    INSERT INTO "Leads" (
                        center_name, phone, address, county, zipcode, director, capacity, city, state,
                        industry, input_date, status, is_converted, lead_source, process_id, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    center_name, phone, address, county, zipcode, director, capacity, city, state,
                    'Child Care', datetime.now().date(), 'NEW', False, 'Texas CCL API', process_id, datetime.now().date()
                ))
                new_count += 1
                
        # 3. Log routine status and telemetry
        total_latency = time.time() - start_time
        
        # Upsert schedule registry
        cur.execute("""
            INSERT INTO routine_schedule (routine_id, task_type, frequency_seconds, last_run, status)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
            ON CONFLICT (routine_id) DO UPDATE SET 
                last_run = EXCLUDED.last_run, 
                status = EXCLUDED.status;
        """, ("daycare_sync", "API Sync", 2592000, "SUCCESS"))
        
        # Log to ActivityLog
        activity_msg = f"Daycare API Sync: Ingested {new_count} new, updated {updated_count} facilities."
        cur.execute("""
            INSERT INTO "ActivityLog" (date, activity_name, hours, category)
            VALUES (CURRENT_DATE, %s, 0.25, 'Marketing Ingestion');
        """, (activity_msg,))
        
        conn.commit()
        conn.close()
        
        print(f"--- Sync Complete: {new_count} inserted, {updated_count} updated, {skipped_count} skipped in {total_latency:.2f}s ---", flush=True)

        # 4. Autonomous Corporate Umbrella Classification & Propagation
        try:
            from autonomous_umbrella_engine import run_engine
            run_engine()
        except Exception as u_err:
            print(f"[UMBRELLA PROPAGATION NOTICE] Auto-classification deferred: {u_err}", flush=True)

        return True
        
    except Exception as e:
        print(f"[DATABASE ERROR] Sync failed: {e}", flush=True)
        return False

if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    sync_daycares(force=force_flag)
