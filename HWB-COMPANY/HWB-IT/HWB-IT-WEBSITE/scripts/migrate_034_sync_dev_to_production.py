#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 034: Full Production Synchronization & Mined Leads Ingestion
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & Lean Six Sigma Zero-Defect Mandate
Authority: Humberto Dominguez (CEO) - Approved 09/29/2026
Auditors: George (Systems Architect & mbB) & Peter (Data Recovery Custodian)

Synchronizes:
1. PurchasingCooperatives (7 Texas cooperative vehicles: TIPS, BuyBoard, EPCNT, Choice Partners, etc.)
2. GovernmentPrograms (6 certification and procurement programs: SBA 8(a), HUB, MBE, SBE, etc.)
3. CorporateUmbrellas (225 charter school and commercial facility networks)
4. InstitutionalBids (21 verified public sector solicitations)
5. GeneralContractors (8 master commercial general contractor profiles)
6. ConstructionBids (46 commercial general contractor bids)
7. Leads (1,231 verified newly mined leads: AskTED charter schools, CAD multi-family BTR, commercial owner-occupants, and Texas CCL daycares)
8. Sequence Auto-Alignment across all primary key sequences.
9. Schema migration ledger persistence.
"""

import os
import sys
import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from dotenv import load_dotenv
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "scripts" else CURRENT_DIR.parent.parent
WEBSITE_DIR = PROJECT_ROOT / "HWB-COMPANY" / "HWB-IT" / "HWB-IT-WEBSITE"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(WEBSITE_DIR / ".env")

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")


def table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s;", (table_name,))
    return cur.fetchone() is not None


def align_sequences(cur):
    """Aligns all PostgreSQL primary key sequences using native pg_get_serial_sequence."""
    align_sql = """
    DO $$ DECLARE
        r RECORD;
        seq TEXT;
    BEGIN
        FOR r IN (
            SELECT table_name, column_name 
            FROM information_schema.columns 
            WHERE column_default LIKE 'nextval(%' AND table_schema = 'public'
        ) LOOP
            seq := pg_get_serial_sequence('"' || r.table_name || '"', r.column_name);
            IF seq IS NOT NULL THEN
                EXECUTE 'SELECT setval(''' || seq || ''', COALESCE(MAX("' || r.column_name || '"), 1)) FROM "' || r.table_name || '"';
            END IF;
        END LOOP;
    END $$;
    """
    cur.execute(align_sql)


def dynamic_upsert(cur, table_name: str, records: list, conflict_col: str, exclude_update: set = None) -> int:
    """Bulletproof dynamic upsert matching payload keys to target table schema."""
    if not records or not table_exists(cur, table_name):
        return 0
    exclude_update = set(exclude_update or [])
    if conflict_col != 'id':
        exclude_update.add('id')

    cur.execute("""
        SELECT column_name, data_type FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = %s;
    """, (table_name,))
    col_info = {r['column_name']: r['data_type'] for r in cur.fetchall()}
    valid_cols = set(col_info.keys())

    first_rec = records[0]
    cols = [c for c in first_rec.keys() if c in valid_cols]
    if conflict_col not in cols:
        print(f"  [WARN] Conflict column {conflict_col} not in table {table_name}. Skipping.", flush=True)
        return 0

    # Format records for json/jsonb columns
    formatted_records = []
    for r in records:
        new_r = dict(r)
        for c in cols:
            if col_info.get(c) in ('json', 'jsonb'):
                val = new_r.get(c)
                if val is not None and not isinstance(val, str):
                    new_r[c] = json.dumps(val)
        formatted_records.append(new_r)

    update_cols = [c for c in cols if c != conflict_col and c not in exclude_update]
    cols_str = ', '.join([f'"{c}"' for c in cols])
    vals_str = ', '.join([f'%({c})s::jsonb' if col_info.get(c) in ('json', 'jsonb') else f'%({c})s' for c in cols])
    
    if update_cols:
        updates_str = ', '.join([f'"{c}" = EXCLUDED."{c}"' for c in update_cols])
        conflict_action = f"DO UPDATE SET {updates_str}"
    else:
        conflict_action = "DO NOTHING"

    sql = f"""
        INSERT INTO "{table_name}" ({cols_str})
        VALUES ({vals_str})
        ON CONFLICT ("{conflict_col}") {conflict_action};
    """
    execute_batch(cur, sql, formatted_records, page_size=100)
    return len(formatted_records)


def sync_construction_bids(cur, const_bids: list) -> tuple:
    """Reconciles and synchronizes ConstructionBids without unique constraint violations."""
    if not const_bids or not table_exists(cur, "ConstructionBids"):
        return 0, 0

    cur.execute("""
        SELECT column_name, data_type FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'ConstructionBids';
    """)
    col_info = {r['column_name']: r['data_type'] for r in cur.fetchall()}
    valid_cols = set(col_info.keys())

    cur.execute('SELECT id, email_id, LOWER(TRIM(project_name)) as pname, LOWER(TRIM(COALESCE(gc_name, \'\'))) as gname FROM "ConstructionBids";')
    existing_rows = cur.fetchall()
    existing_by_email = {r['email_id']: r['id'] for r in existing_rows if r.get('email_id')}
    existing_by_pname = {(r['pname'], r['gname']): r['id'] for r in existing_rows if r.get('pname')}
    existing_ids = {r['id'] for r in existing_rows}

    updated_count = 0
    inserted_count = 0

    for cb in const_bids:
        matched_id = None
        email_id = cb.get('email_id')
        pname = (cb.get('project_name') or '').strip().lower()
        gname = (cb.get('gc_name') or '').strip().lower()

        if email_id and email_id in existing_by_email:
            matched_id = existing_by_email[email_id]
        elif (pname, gname) in existing_by_pname:
            matched_id = existing_by_pname[(pname, gname)]

        if matched_id:
            upd_cols = [c for c in cb.keys() if c in valid_cols and c != 'id']
            set_clauses = ', '.join([f'"{c}" = %({c})s' for c in upd_cols])
            sql_upd = f'UPDATE "ConstructionBids" SET {set_clauses} WHERE id = %(target_id)s;'
            params = {c: cb[c] for c in upd_cols}
            params['target_id'] = matched_id
            cur.execute(sql_upd, params)
            updated_count += 1
        else:
            ins_rec = {c: cb[c] for c in cb.keys() if c in valid_cols}
            if ins_rec.get('id') in existing_ids:
                del ins_rec['id']
            ins_cols = list(ins_rec.keys())
            cols_str = ', '.join([f'"{c}"' for c in ins_cols])
            vals_str = ', '.join([f'%({c})s' for c in ins_cols])
            sql_ins = f'INSERT INTO "ConstructionBids" ({cols_str}) VALUES ({vals_str});'
            cur.execute(sql_ins, ins_rec)
            inserted_count += 1

    return inserted_count, updated_count


def run_migration(db_url: str = None) -> dict:
    target_url = db_url or DB_URL
    t_start = time.time()
    print("\n==================================================================", flush=True)
    print("  Applying Migration 034: Full Production Sync & Mined Leads Ingestion", flush=True)
    print("==================================================================", flush=True)

    # Resolve payload path
    possible_paths = [
        WEBSITE_DIR / "database" / "seeds" / "production_sync_payload.json",
        PROJECT_ROOT / "database" / "seeds" / "production_sync_payload.json",
        Path("/app/database/seeds/production_sync_payload.json"),
        CURRENT_DIR / "production_sync_payload.json"
    ]
    payload_file = None
    for p in possible_paths:
        if p.exists():
            payload_file = p
            break

    if not payload_file:
        raise FileNotFoundError("production_sync_payload.json not found in search paths")

    print(f"[STAGE 0] Loading synchronization payload from {payload_file}...", flush=True)
    with open(payload_file, "r") as pf:
        payload = json.load(pf)

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Pre-flight alignment
            align_sequences(cur)

            # -------------------------------------------------------------
            # STEP 1: PURCHASING COOPERATIVES (7 rows)
            # -------------------------------------------------------------
            coops = payload.get("purchasing_cooperatives", [])
            print(f"[STAGE 1] Syncing {len(coops)} Purchasing Cooperatives...", flush=True)
            n_coops = dynamic_upsert(cur, "PurchasingCooperatives", coops, conflict_col="coop_code")
            print(f"  -> Synced {n_coops} PurchasingCooperatives.", flush=True)

            # -------------------------------------------------------------
            # STEP 2: GOVERNMENT PROGRAMS (6 rows)
            # -------------------------------------------------------------
            gov_progs = payload.get("government_programs", [])
            print(f"[STAGE 2] Syncing {len(gov_progs)} Government Programs...", flush=True)
            n_gov = dynamic_upsert(cur, "GovernmentPrograms", gov_progs, conflict_col="program_code")
            print(f"  -> Synced {n_gov} GovernmentPrograms.", flush=True)

            # -------------------------------------------------------------
            # STEP 3: CORPORATE UMBRELLAS (225 rows)
            # -------------------------------------------------------------
            umbrellas = payload.get("corporate_umbrellas", [])
            print(f"[STAGE 3] Syncing {len(umbrellas)} Corporate Umbrellas...", flush=True)
            n_umb = dynamic_upsert(cur, "CorporateUmbrellas", umbrellas, conflict_col="umbrella_name")
            print(f"  -> Synced {n_umb} CorporateUmbrellas.", flush=True)

            # -------------------------------------------------------------
            # STEP 4: INSTITUTIONAL BIDS (21 rows)
            # -------------------------------------------------------------
            inst_bids = payload.get("institutional_bids", [])
            print(f"[STAGE 4] Syncing {len(inst_bids)} Institutional Bids...", flush=True)
            n_inst = dynamic_upsert(cur, "InstitutionalBids", inst_bids, conflict_col="solicitation_number")
            print(f"  -> Synced {n_inst} InstitutionalBids.", flush=True)

            # -------------------------------------------------------------
            # STEP 5: GENERAL CONTRACTORS (8 rows)
            # -------------------------------------------------------------
            gcs = payload.get("general_contractors", [])
            print(f"[STAGE 5] Syncing {len(gcs)} General Contractors...", flush=True)
            n_gc = dynamic_upsert(cur, "GeneralContractors", gcs, conflict_col="company_name")
            print(f"  -> Synced {n_gc} GeneralContractors.", flush=True)

            # -------------------------------------------------------------
            # STEP 6: CONSTRUCTION BIDS (46 rows)
            # -------------------------------------------------------------
            const_bids = payload.get("construction_bids", [])
            print(f"[STAGE 6] Syncing {len(const_bids)} Construction Bids...", flush=True)
            ins_cb, upd_cb = sync_construction_bids(cur, const_bids)
            print(f"  -> ConstructionBids: {ins_cb} inserted, {upd_cb} enriched.", flush=True)

            # -------------------------------------------------------------
            # STEP 7: NEW LEADS (1,231 rows) WITH POKA-YOKE CONFLICT DEFENSE
            # -------------------------------------------------------------
            new_leads = payload.get("new_leads", [])
            print(f"[STAGE 7] Syncing {len(new_leads)} Newly Mined Leads...", flush=True)
            
            # Map existing unique locations in database
            cur.execute("""
                SELECT id, LOWER(TRIM(center_name)) as cname, 
                       LOWER(TRIM(COALESCE(address, ''))) as addr, 
                       LOWER(TRIM(COALESCE(city, ''))) as cty
                FROM "Leads";
            """)
            existing_locs = {(r['cname'], r['addr'], r['cty']): r['id'] for r in cur.fetchall()}

            leads_to_insert = []
            leads_to_update = []
            for l in new_leads:
                key = (
                    (l.get('center_name') or '').strip().lower(),
                    (l.get('address') or '').strip().lower(),
                    (l.get('city') or '').strip().lower()
                )
                if key in existing_locs:
                    existing_id = existing_locs[key]
                    leads_to_update.append({
                        'email': l.get('email'),
                        'phone': l.get('phone'),
                        'director': l.get('director'),
                        'decision_maker': l.get('decision_maker'),
                        'job_title': l.get('job_title'),
                        'sqf': l.get('sqf') or 0,
                        'capacity': l.get('capacity') or 0,
                        'estimated_annual_value': l.get('estimated_annual_value') or 0.0,
                        'facility_type': l.get('facility_type'),
                        'industry': l.get('industry'),
                        'lead_source': l.get('lead_source'),
                        'umbrella_name': l.get('umbrella_name'),
                        'notes': l.get('notes'),
                        'existing_id': existing_id
                    })
                else:
                    leads_to_insert.append(l)

            print(f"  -> New Locations to Insert: {len(leads_to_insert):,}", flush=True)
            print(f"  -> Existing Locations to Enrich: {len(leads_to_update):,}", flush=True)

            if leads_to_insert:
                n_inserted = dynamic_upsert(cur, "Leads", leads_to_insert, conflict_col="id")
                print(f"  -> Inserted {n_inserted:,} leads.", flush=True)

            if leads_to_update:
                lead_update_sql = """
                    UPDATE "Leads" SET
                        email = COALESCE(NULLIF(email, ''), NULLIF(%(email)s, '')),
                        phone = COALESCE(NULLIF(phone, ''), NULLIF(%(phone)s, '')),
                        director = COALESCE(NULLIF(director, ''), NULLIF(%(director)s, '')),
                        decision_maker = COALESCE(NULLIF(decision_maker, ''), NULLIF(%(decision_maker)s, '')),
                        job_title = COALESCE(NULLIF(job_title, ''), NULLIF(%(job_title)s, '')),
                        sqf = CASE WHEN (sqf IS NULL OR sqf = 0) AND %(sqf)s > 0 THEN %(sqf)s ELSE sqf END,
                        capacity = CASE WHEN (capacity IS NULL OR capacity = 0) AND %(capacity)s > 0 THEN %(capacity)s ELSE capacity END,
                        estimated_annual_value = CASE WHEN (estimated_annual_value IS NULL OR estimated_annual_value = 0) AND %(estimated_annual_value)s > 0 THEN %(estimated_annual_value)s ELSE estimated_annual_value END,
                        facility_type = COALESCE(NULLIF(facility_type, ''), NULLIF(%(facility_type)s, '')),
                        industry = COALESCE(NULLIF(industry, ''), NULLIF(%(industry)s, '')),
                        lead_source = COALESCE(NULLIF(lead_source, ''), NULLIF(%(lead_source)s, '')),
                        umbrella_name = COALESCE(NULLIF(umbrella_name, ''), NULLIF(%(umbrella_name)s, '')),
                        notes = COALESCE(NULLIF(notes, ''), NULLIF(%(notes)s, ''))
                    WHERE id = %(existing_id)s;
                """
                execute_batch(cur, lead_update_sql, leads_to_update, page_size=200)
                print(f"  -> Enriched {len(leads_to_update):,} existing leads.", flush=True)

            # -------------------------------------------------------------
            # STEP 8: POST-PURGE SEQUENCE AUTO-ALIGNMENT
            # -------------------------------------------------------------
            print("[STAGE 8] Auto-aligning all PostgreSQL sequences...", flush=True)
            align_sequences(cur)

            # -------------------------------------------------------------
            # STEP 9: TELEMETRY & AUDIT VERIFICATION
            # -------------------------------------------------------------
            cur.execute('SELECT COUNT(*) FROM "Leads";')
            post_leads_total = cur.fetchone()['count']

            cur.execute('SELECT COUNT(*) FROM "Leads" WHERE is_duplicate = TRUE;')
            post_dups = cur.fetchone()['count']

            cur.execute("""
                INSERT INTO "schema_migrations" (version, description)
                VALUES (
                    '034_sync_dev_to_production',
                    'Full production sync: 1,231 mined leads, corporate umbrellas, coops, gov programs, and institutional bids'
                )
                ON CONFLICT (version) DO NOTHING;
            """)

            # Safe audit log insert
            try:
                cur.execute("SAVEPOINT ga_sync_savepoint;")
                cur.execute("""
                    INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description, timestamp)
                    VALUES (1, 'System', '[DEV-TO-PROD-SYNC]', %s, NOW());
                """, (f"Migration 034: Synced {len(leads_to_insert)} new leads, {len(umbrellas)} umbrellas, {len(inst_bids)} inst bids. Total leads: {post_leads_total:,}.",))
                cur.execute("RELEASE SAVEPOINT ga_sync_savepoint;")
            except Exception as audit_err:
                cur.execute("ROLLBACK TO SAVEPOINT ga_sync_savepoint;")
                print(f"[AUDIT LOG WARNING] GlobalActivities insert skipped: {audit_err}", flush=True)

        conn.commit()
        latency_s = round(time.time() - t_start, 2)
        print("------------------------------------------------------------------", flush=True)
        print(f"[SUCCESS] Migration 034 Completed in {latency_s}s", flush=True)
        print(f"  Post-Total Leads:     {post_leads_total:,}")
        print(f"  Post-Duplicate Count: {post_dups:,} (Target: 0)")
        print(f"  Inserted Leads:       {len(leads_to_insert):,}")
        print(f"  Enriched Leads:       {len(leads_to_update):,}")
        print("==================================================================\n", flush=True)

        return {
            "status": "success",
            "inserted_leads": len(leads_to_insert),
            "enriched_leads": len(leads_to_update),
            "post_leads_total": post_leads_total,
            "post_dups": post_dups,
            "latency_s": latency_s
        }

    except Exception as e:
        conn.rollback()
        print(f"[CRITICAL ERROR] Migration 034 failed: {e}", file=sys.stderr, flush=True)
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
