import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import requests
import psycopg2
from dotenv import load_dotenv

# --- SigmaFidelity™ Texas Daycare Registry Sync & Closure Reconciliation Daemon ---
# Responsibility: George (Systems Architect) & Silas Sync (VP of CRM)
# Mandated by HWB-QMS-11.1 (Incremental Lead Ingestion & 4-Safeguard Closure Reconciliation)

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
if "@localhost" in DB_URL and os.path.exists("/.dockerenv"):
    DB_URL = DB_URL.replace("@localhost", "@db")

API_ENDPOINT = "https://data.texas.gov/resource/bc5r-88dy.json"
CIRCUIT_BREAKER_MIN_ACTIVE_RECORDS = 7500

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'HWB-COMPANY', 'HWB-IT', 'HWB-IT-WEBSITE'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from core.services.sanitizer import clean_phone, clean_city, clean_email
    from core.services.classifier import BusinessClassifierEngine
except ImportError:
    try:
        from HWB_COMPANY.HWB_IT.HWB_IT_WEBSITE.core.services.sanitizer import clean_phone, clean_city, clean_email
        from HWB_COMPANY.HWB_IT.HWB_IT_WEBSITE.core.services.classifier import BusinessClassifierEngine
    except ImportError:
        def clean_phone(p: Optional[str]) -> Optional[str]:
            if not p:
                return None
            d = ''.join(c for c in str(p) if c.isdigit())
            if len(d) == 11 and d.startswith('1'):
                d = d[1:]
            if len(d) == 10:
                return f"({d[:3]})-{d[3:6]}-{d[6:]}"
            return p

        def clean_city(c: Optional[str]) -> Optional[str]:
            return str(c).strip().title() if c else None

        def clean_email(e: Optional[str]) -> Optional[str]:
            if not e:
                return None
            s = str(e).strip().lower().rstrip('.,;:')
            return s if ('@' in s and '.' in s.split('@')[-1]) else None

        class BusinessClassifierEngine:
            @classmethod
            def classify(cls, center_name: str, capacity: Optional[int] = None,
                         lead_source: Optional[str] = None, raw_payload: Any = None) -> Any:
                class Dummy:
                    industry = 'Child Care'
                    facility_type = 'Child Care Center'
                    normalized_lead_source = lead_source or 'Texas CCL API'
                return Dummy()


def compute_facility_economics(capacity: int) -> Dict[str, Any]:
    """Calculates standard cleanable square footage, annual value, and size tier."""
    cap = max(capacity or 0, 0)
    sqf = max(cap * 50, 1500) if cap > 0 else 2500
    est_val = round(sqf * 0.14 * 12, 2)
    if cap >= 200:
        tier = "Tier 1 - Mega Institutional"
    elif cap >= 100:
        tier = "Tier 2 - Regional Commercial"
    elif cap >= 50:
        tier = "Tier 3 - Standard Commercial"
    else:
        tier = "Tier 4 - Boutique"
    return {
        "sqf": sqf,
        "estimated_annual_value": est_val,
        "acquisition_tier": tier
    }


def fetch_paginated_socrata(where_clause: str, page_size: int = 5000, max_pages: int = 10) -> Optional[List[Dict[str, Any]]]:
    """Fetches all pages from the Texas HHS Socrata API for a given $where filter."""
    all_rows: List[Dict[str, Any]] = []
    for page_idx in range(max_pages):
        offset = page_idx * page_size
        params = {
            "$where": where_clause,
            "$limit": page_size,
            "$offset": offset,
            "$order": "operation_number ASC"
        }
        resp = requests.get(API_ENDPOINT, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"[API ERROR] Texas Daycare Portal returned status {resp.status_code}: {resp.text[:200]}", flush=True)
            return None
        batch = resp.json()
        if not isinstance(batch, list):
            return None
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
    return all_rows


def sync_daycares(force: bool = False) -> bool:
    """
    Executes statewide Texas Daycare Registry ingestion, sanitization, and
    4-Safeguard Closure Reconciliation.
    """
    print("--- SigmaFidelity: Initiating Texas Daycare API Sync & Closure Reconciliation ---", flush=True)

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

    # 1. Fetch active Licensed Centers statewide across all of Texas (Paginated)
    records = fetch_paginated_socrata("operation_type = 'Licensed Center' AND operation_status = 'Y'")
    if records is None:
        print("[API ERROR] Aborting sync due to Socrata API error.", flush=True)
        return False

    fetch_latency = time.time() - start_time
    print(f"[SYNC] Successfully fetched {len(records)} active Texas Licensed Centers in {fetch_latency:.2f}s", flush=True)

    # 2. Fetch explicitly closed Licensed Centers from Texas HHS API (Safeguard 2)
    closed_records = fetch_paginated_socrata("operation_type = 'Licensed Center' AND operation_status = 'N'", page_size=5000, max_pages=6) or []
    explicit_closed_pids: Set[str] = {
        f"texas-ccl-{item.get('operation_number')}"
        for item in closed_records
        if item.get("operation_number")
    }

    new_count = 0
    updated_count = 0
    reopened_count = 0
    closed_archived_count = 0
    protected_review_count = 0
    skipped_count = 0
    active_pids: Set[str] = set()

    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        for item in records:
            op_num = item.get("operation_number")
            if not op_num:
                continue

            process_id = f"texas-ccl-{op_num}"
            active_pids.add(process_id)

            center_name = (item.get("operation_name") or "").strip()
            raw_phone = (item.get("phone_number") or "").strip()
            phone = clean_phone(raw_phone) or raw_phone
            raw_email = (item.get("email_address") or "").strip()
            api_email = clean_email(raw_email)

            # Reject known agency/compliance background-check addresses from state registry
            if api_email and ("backgroundchecks@" in api_email or api_email.endswith(".gov") or api_email.endswith(".state.tx.us")):
                api_email = None

            address = (item.get("address_line") or item.get("location_address") or "").strip()
            city = clean_city(item.get("city")) or (item.get("city") or "").strip().title()
            county = (item.get("county") or "").strip().upper()
            zipcode = (item.get("zipcode") or "").strip()
            raw_director = (item.get("administrator_director_name") or "").strip()
            director = raw_director.title() if raw_director.isupper() else raw_director

            try:
                capacity = int(float(item.get("total_capacity") or 0))
            except (ValueError, TypeError):
                capacity = 0

            state = (item.get("state") or "TX").strip().upper()
            econ = compute_facility_economics(capacity)

            classification = BusinessClassifierEngine.classify(
                center_name=center_name,
                capacity=capacity,
                lead_source='Texas CCL API'
            )

            cur.execute("""
                SELECT id, capacity, phone, email, director, address, process_id,
                       status, commercial_status, is_dnc, sqf, estimated_annual_value
                FROM "Leads"
                WHERE process_id = %s OR (LOWER(center_name) = LOWER(%s) AND LOWER(address) = LOWER(%s))
                LIMIT 1;
            """, (process_id, center_name, address))
            row = cur.fetchone()

            if row:
                (lead_id, db_capacity, db_phone, db_email, db_director, db_address,
                 db_pid, db_status, db_comm_status, db_is_dnc, db_sqf, db_val) = row

                merged_email = api_email or clean_email(db_email)
                clean_db_phone = clean_phone(db_phone) or (db_phone or "")

                # Safeguard 4: Self-Healing Re-Activation if previously closed facility reopens
                was_closed = (
                    (db_status or "").upper() in ("ARCHIVED", "CLOSED")
                    or "closed" in (db_comm_status or "").lower()
                )
                reopen_needed = was_closed and not bool(db_is_dnc)

                needs_update = (
                    reopen_needed
                    or db_capacity != capacity
                    or clean_db_phone != (phone or "")
                    or (merged_email and merged_email != (db_email or ""))
                    or (director and (db_director or "") != director)
                    or (db_address or "").lower() != address.lower()
                    or db_pid != process_id
                    or not db_sqf
                    or not db_val
                )

                if needs_update:
                    new_status = "NEW" if reopen_needed else (db_status or "NEW")
                    new_comm_status = "Active Commercial" if reopen_needed else (db_comm_status or "Active Commercial")
                    cur.execute("""
                        UPDATE "Leads"
                        SET capacity = %s,
                            phone = COALESCE(%s, phone),
                            email = COALESCE(%s, email),
                            director = COALESCE(NULLIF(%s, ''), director),
                            address = %s,
                            city = COALESCE(NULLIF(%s, ''), city),
                            county = COALESCE(NULLIF(%s, ''), county),
                            zipcode = COALESCE(NULLIF(%s, ''), zipcode),
                            process_id = %s,
                            industry = %s,
                            facility_type = %s,
                            sqf = %s,
                            estimated_annual_value = %s,
                            acquisition_tier = %s,
                            status = %s,
                            commercial_status = %s,
                            is_commercial = CASE WHEN COALESCE(is_dnc, FALSE) = TRUE THEN is_commercial ELSE TRUE END,
                            updated_at = CURRENT_DATE
                        WHERE id = %s;
                    """, (
                        capacity, phone, merged_email, director, address, city, county, zipcode,
                        process_id, classification.industry, classification.facility_type,
                        econ["sqf"], econ["estimated_annual_value"], econ["acquisition_tier"],
                        new_status, new_comm_status, lead_id
                    ))
                    if reopen_needed:
                        reopened_count += 1
                        cur.execute("""
                            INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                            VALUES (%s, 'Lead', 'Registry Re-Activation', %s);
                        """, (lead_id, f"Texas HHS permit ({process_id}) verified active again (operation_status='Y'). Facility automatically reopened."))
                    else:
                        updated_count += 1
                else:
                    skipped_count += 1
            else:
                cur.execute("""
                    INSERT INTO "Leads" (
                        center_name, phone, email, address, county, zipcode, director, capacity, city, state,
                        industry, facility_type, sqf, estimated_annual_value, acquisition_tier,
                        is_commercial, commercial_status, input_date, status, is_converted, lead_source, process_id, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, 'Active Commercial', CURRENT_DATE, 'NEW', FALSE, %s, %s, CURRENT_DATE);
                """, (
                    center_name, phone, api_email, address, county, zipcode, director, capacity, city, state,
                    classification.industry, classification.facility_type,
                    econ["sqf"], econ["estimated_annual_value"], econ["acquisition_tier"],
                    classification.normalized_lead_source, process_id
                ))
                new_count += 1

        # =========================================================================
        # 3. 4-SAFEGUARD PERMANENT CLOSURE RECONCILIATION ENGINE
        # =========================================================================
        if len(active_pids) < CIRCUIT_BREAKER_MIN_ACTIVE_RECORDS:
            # Safeguard 1: Circuit-Breaker Threshold
            print(
                f"[SAFEGUARD 1 CIRCUIT-BREAKER] Fetched {len(active_pids)} active records "
                f"(< {CIRCUIT_BREAKER_MIN_ACTIVE_RECORDS} minimum). Skipping closure reconciliation to prevent partial-response archival.",
                flush=True
            )
        else:
            cur.execute("""
                SELECT id, center_name, process_id, status, is_converted, email
                FROM "Leads"
                WHERE process_id LIKE 'texas-ccl-%%'
                  AND COALESCE(status, '') NOT IN ('ARCHIVED', 'Closed')
                  AND COALESCE(commercial_status, '') NOT ILIKE '%%Closed%%';
            """)
            tracked_ccl_leads = cur.fetchall()
            protected_statuses = {'ACTIVE', 'QUALIFIED', 'TRAINED', 'ENGAGED'}

            for lid, cname, pid, lstatus, is_conv, lemail in tracked_ccl_leads:
                if pid in active_pids:
                    continue

                # Safeguard 2: Verify facility is explicitly closed ('N') in Texas HHS or absent from full active feed
                is_explicitly_closed = (pid in explicit_closed_pids) or (len(active_pids) >= CIRCUIT_BREAKER_MIN_ACTIVE_RECORDS)
                if not is_explicitly_closed:
                    continue

                # Safeguard 3: Active-Deal & Customer Protection
                if bool(is_conv) or (lstatus or "").strip().upper() in protected_statuses:
                    protected_review_count += 1
                    cur.execute("""
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                        VALUES (%s, 'Lead', 'Registry Closure Alert', %s);
                    """, (
                        lid,
                        f"[SAFEGUARD 3 PROTECTION] Texas HHS permit ({pid}) reported inactive/closed, "
                        f"but lead is in active sales stage ('{lstatus}'). Preserved record for human review."
                    ))
                    continue

                # Safeguard 4: Archive unworked closed facility & cancel unsent campaign/outbox drafts
                # Note: trg_leads_campaign_readiness automatically sets campaign_ready = FALSE and email_hygiene_status = 'FACILITY_CLOSED'
                cur.execute("""
                    UPDATE "Leads"
                    SET status = 'ARCHIVED',
                        commercial_status = 'Permanently Closed',
                        is_commercial = FALSE,
                        campaign_ready = FALSE,
                        email_hygiene_status = 'FACILITY_CLOSED',
                        updated_at = CURRENT_DATE
                    WHERE id = %s;
                """, (lid,))

                cur.execute("""
                    UPDATE "CampaignRecipients"
                    SET status = 'CANCELLED_CLOSED', updated_at = CURRENT_TIMESTAMP
                    WHERE lead_id = %s AND status IN ('STAGED', 'AWAITING_APPROVAL');
                """, (lid,))

                if lemail:
                    cur.execute("""
                        UPDATE "PendingOutbox"
                        SET status = 'CANCELLED'
                        WHERE (recipient_id = %s OR LOWER(recipient) = LOWER(%s))
                          AND status = 'PENDING';
                    """, (lid, lemail))

                cur.execute("""
                    INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                    VALUES (%s, 'Lead', 'Facility Closed', %s);
                """, (
                    lid,
                    f"Texas HHS permit ({pid}) verified inactive/closed. Lead archived, removed from campaign eligibility, and unsent email drafts cancelled."
                ))
                closed_archived_count += 1

        # 4. Log routine status and telemetry
        total_latency = time.time() - start_time

        cur.execute("""
            INSERT INTO routine_schedule (routine_id, task_type, frequency_seconds, last_run, status)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
            ON CONFLICT (routine_id) DO UPDATE SET 
                last_run = EXCLUDED.last_run, 
                status = EXCLUDED.status;
        """, ("daycare_sync", "API Sync", 2592000, "SUCCESS"))

        activity_msg = (
            f"Daycare API Sync: {new_count} new, {updated_count} updated, "
            f"{reopened_count} reopened, {closed_archived_count} closed/archived "
            f"({protected_review_count} active deals protected)."
        )
        cur.execute("""
            INSERT INTO "ActivityLog" (date, activity_name, hours, category)
            VALUES (CURRENT_DATE, %s, 0.25, 'Marketing Ingestion');
        """, (activity_msg,))

        conn.commit()
        conn.close()

        print(
            f"--- Sync Complete: {new_count} inserted, {updated_count} updated, "
            f"{reopened_count} reopened, {closed_archived_count} closed/archived, "
            f"{ skipped_count} unchanged in {total_latency:.2f}s ---",
            flush=True
        )

        # 5. Autonomous Corporate Umbrella Classification & Propagation
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
