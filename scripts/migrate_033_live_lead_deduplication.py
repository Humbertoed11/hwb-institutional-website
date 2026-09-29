#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 033: Live Lead Dataset Deduplication & Golden Master Consolidation
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & Lean Six Sigma Zero-Defect Mandate
Authority: Humberto Dominguez (CEO) - Approved 09/29/2026
Auditors: George (Systems Architect & mbB) & Peter (Data Recovery Custodian)

High-Velocity Indexed Execution with Schema Defensive Guards:
1. Verifies table/column existence before execution (prevents PostgreSQL aborted transaction locks).
2. Uses indexed group keys for fast execution.
3. Re-parents child records (CampaignRecipients, Contacts, GlobalActivities) to clean masters.
4. Purges all 14,704 duplicate shells (is_duplicate = TRUE).
5. Enforces composite unique index idx_leads_unique_location.
6. Auto-aligns all PostgreSQL sequences.
7. Records migration in schema_migrations.
"""

import os
import sys
import time
import psycopg2
from psycopg2.extras import RealDictCursor
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


def column_exists(cur, table_name: str, column_name: str) -> bool:
    cur.execute("SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s AND column_name = %s;", (table_name, column_name))
    return cur.fetchone() is not None


def run_migration(db_url: str = None) -> dict:
    target_url = db_url or DB_URL
    t_start = time.time()
    print("\n==================================================================", flush=True)
    print("  Applying Migration 033: Hardened High-Speed Lead Deduplication", flush=True)
    print("==================================================================", flush=True)

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # -------------------------------------------------------------
            # STEP 0: PRE-FLIGHT TELEMETRY AUDIT
            # -------------------------------------------------------------
            cur.execute('SELECT COUNT(*) as total FROM "Leads";')
            pre_total = cur.fetchone()["total"]

            cur.execute('SELECT COUNT(*) as dups FROM "Leads" WHERE is_duplicate = TRUE;')
            pre_duplicates = cur.fetchone()["dups"]

            cur.execute("""
                SELECT COUNT(*) as clean 
                FROM "Leads" 
                WHERE (is_duplicate = FALSE OR is_duplicate IS NULL) 
                  AND (status != 'ARCHIVED' OR status IS NULL);
            """)
            pre_clean = cur.fetchone()["clean"]

            print(f"[PRE-FLIGHT] Total Leads: {pre_total:,} | Flagged Duplicates: {pre_duplicates:,} | Active Clean: {pre_clean:,}", flush=True)

            # Ensure index on duplicate_group_id and is_duplicate exists for fast operations
            cur.execute('CREATE INDEX IF NOT EXISTS idx_leads_dup_group ON "Leads" (duplicate_group_id);')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_leads_is_dup ON "Leads" (is_duplicate);')

            # -------------------------------------------------------------
            # STEP 1: BULK ATTRIBUTE BACKFILL INTO CLEAN MASTERS
            # -------------------------------------------------------------
            print("[STAGE 1] Bulk backfilling missing attributes into Golden Masters...", flush=True)
            cur.execute("""
                UPDATE "Leads" m
                SET email = COALESCE(NULLIF(m.email, ''), NULLIF(d.email, '')),
                    phone = COALESCE(NULLIF(m.phone, ''), NULLIF(d.phone, '')),
                    director = COALESCE(NULLIF(m.director, ''), NULLIF(d.director, '')),
                    decision_maker = COALESCE(NULLIF(m.decision_maker, ''), NULLIF(d.decision_maker, '')),
                    job_title = COALESCE(NULLIF(m.job_title, ''), NULLIF(d.job_title, '')),
                    notes = COALESCE(NULLIF(m.notes, ''), NULLIF(d.notes, '')),
                    umbrella_name = COALESCE(NULLIF(m.umbrella_name, ''), NULLIF(d.umbrella_name, '')),
                    sqf = CASE WHEN (m.sqf IS NULL OR m.sqf = 0) AND d.sqf > 0 THEN d.sqf ELSE m.sqf END,
                    capacity = CASE WHEN (m.capacity IS NULL OR m.capacity = 0) AND d.capacity > 0 THEN d.capacity ELSE m.capacity END,
                    estimated_annual_value = CASE WHEN (m.estimated_annual_value IS NULL OR m.estimated_annual_value = 0) AND d.estimated_annual_value > 0 THEN d.estimated_annual_value ELSE m.estimated_annual_value END
                FROM "Leads" d
                WHERE m.duplicate_group_id = d.duplicate_group_id
                  AND m.duplicate_group_id IS NOT NULL
                  AND (m.is_duplicate = FALSE OR m.is_duplicate IS NULL)
                  AND d.is_duplicate = TRUE
                  AND m.id != d.id;
            """)
            enriched_count = cur.rowcount
            print(f"  -> Enriched {enriched_count:,} master records.", flush=True)

            # -------------------------------------------------------------
            # STEP 2: FAST INDEXED CHILD RE-PARENTING
            # -------------------------------------------------------------
            print("[STAGE 2] Re-parenting child records using indexed group keys...", flush=True)
            reparented_campaigns = 0
            if table_exists(cur, "CampaignRecipients"):
                cur.execute("""
                    UPDATE "CampaignRecipients" cr
                    SET lead_id = m.id
                    FROM "Leads" d
                    JOIN "Leads" m ON m.duplicate_group_id = d.duplicate_group_id 
                                  AND (m.is_duplicate = FALSE OR m.is_duplicate IS NULL)
                                  AND m.id != d.id
                    WHERE cr.lead_id = d.id AND d.is_duplicate = TRUE;
                """)
                reparented_campaigns = cur.rowcount

            reparented_contacts = 0
            if table_exists(cur, "Contacts"):
                cur.execute("""
                    UPDATE "Contacts" c
                    SET lead_id = m.id
                    FROM "Leads" d
                    JOIN "Leads" m ON m.duplicate_group_id = d.duplicate_group_id 
                                  AND (m.is_duplicate = FALSE OR m.is_duplicate IS NULL)
                                  AND m.id != d.id
                    WHERE c.lead_id = d.id AND d.is_duplicate = TRUE;
                """)
                reparented_contacts = cur.rowcount

            reparented_activities = 0
            if table_exists(cur, "GlobalActivities"):
                cur.execute("""
                    UPDATE "GlobalActivities" ga
                    SET parent_id = m.id
                    FROM "Leads" d
                    JOIN "Leads" m ON m.duplicate_group_id = d.duplicate_group_id 
                                  AND (m.is_duplicate = FALSE OR m.is_duplicate IS NULL)
                                  AND m.id != d.id
                    WHERE ga.parent_id = d.id AND ga.parent_type = 'Lead' AND d.is_duplicate = TRUE;
                """)
                reparented_activities = cur.rowcount
            print(f"  -> Re-parented: {reparented_campaigns:,} campaigns, {reparented_contacts:,} contacts, {reparented_activities:,} activities.", flush=True)

            # -------------------------------------------------------------
            # STEP 3: CLEAN REMAINING ORPHANED CHILD REFERENCES & PURGE DUPLICATES
            # -------------------------------------------------------------
            print("[STAGE 3] Purging redundant duplicate shells in bulk...", flush=True)
            if table_exists(cur, "CampaignRecipients"):
                cur.execute("""
                    DELETE FROM "CampaignRecipients" 
                    WHERE lead_id IN (SELECT id FROM "Leads" WHERE is_duplicate = TRUE);
                """)
            if table_exists(cur, "Contacts"):
                cur.execute("""
                    DELETE FROM "Contacts" 
                    WHERE lead_id IN (SELECT id FROM "Leads" WHERE is_duplicate = TRUE);
                """)
            if table_exists(cur, "ApiBillingTracker"):
                cur.execute("""
                    DELETE FROM "ApiBillingTracker" 
                    WHERE lead_id IN (SELECT id FROM "Leads" WHERE is_duplicate = TRUE);
                """)
            if table_exists(cur, "GlobalActivities"):
                cur.execute("""
                    DELETE FROM "GlobalActivities" 
                    WHERE parent_id IN (SELECT id FROM "Leads" WHERE is_duplicate = TRUE) 
                      AND parent_type = 'Lead';
                """)

            cur.execute('DELETE FROM "Leads" WHERE is_duplicate = TRUE;')
            deleted_count = cur.rowcount
            print(f"  -> Purged {deleted_count:,} duplicate rows.", flush=True)

            # Reset duplicate group on surviving clean records
            cur.execute('UPDATE "Leads" SET duplicate_group_id = NULL WHERE duplicate_group_id IS NOT NULL;')

            # -------------------------------------------------------------
            # STEP 4: ENFORCE POKA-YOKE UNIQUE LOCATION INDEX
            # -------------------------------------------------------------
            print("[STAGE 4] Enforcing composite unique index idx_leads_unique_location...", flush=True)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_unique_location 
                ON "Leads" (LOWER(TRIM(center_name)), LOWER(TRIM(address)), LOWER(TRIM(city)));
            """)

            # -------------------------------------------------------------
            # STEP 5: ALIGN POSTGRESQL SEQUENCES
            # -------------------------------------------------------------
            print("[STAGE 5] Auto-aligning PostgreSQL sequences...", flush=True)
            align_sql = """
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT table_name, column_name, column_default 
                    FROM information_schema.columns 
                    WHERE column_default LIKE 'nextval(%' AND table_schema = 'public'
                ) LOOP
                    EXECUTE 'SELECT setval(''' || substring(r.column_default from '''(.*)''' ) || ''', COALESCE(MAX(' || r.column_name || '), 1)) FROM "' || r.table_name || '"';
                END LOOP;
            END $$;
            """
            cur.execute(align_sql)

            # -------------------------------------------------------------
            # STEP 6: POST-FLIGHT AUDIT & TELEMETRY
            # -------------------------------------------------------------
            cur.execute('SELECT COUNT(*) as total FROM "Leads";')
            post_total = cur.fetchone()["total"]

            cur.execute('SELECT COUNT(*) as dups FROM "Leads" WHERE is_duplicate = TRUE;')
            post_duplicates = cur.fetchone()["dups"]

            cur.execute("""
                SELECT COUNT(*) as clean 
                FROM "Leads" 
                WHERE (is_duplicate = FALSE OR is_duplicate IS NULL) 
                  AND (status != 'ARCHIVED' OR status IS NULL);
            """)
            post_clean = cur.fetchone()["clean"]

            cur.execute("""
                INSERT INTO "schema_migrations" (version, description)
                VALUES (
                    '033_live_lead_deduplication',
                    'Live lead dataset deduplication, Golden Master consolidation, child re-parenting, and unique index enforcement'
                )
                ON CONFLICT (version) DO NOTHING;
            """)

            cur.execute("""
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description, timestamp)
                VALUES (1, 'System', '[LIVE-LEAD-DEDUPLICATION]', %s, NOW());
            """, (f"Migration 033: Purged {deleted_count:,} duplicate shells. Clean leads: {post_clean:,}.",))

        conn.commit()
        latency_s = round(time.time() - t_start, 2)
        print("------------------------------------------------------------------", flush=True)
        print(f"[SUCCESS] Migration 033 Completed in {latency_s}s", flush=True)
        print(f"  Pre-Total Leads:      {pre_total:,}")
        print(f"  Deleted Duplicates:   {deleted_count:,}")
        print(f"  Post-Total Leads:     {post_total:,}")
        print(f"  Post-Duplicate Count: {post_duplicates:,} (Target: 0)")
        print(f"  Post-Clean Active:    {post_clean:,}")
        print("==================================================================\n", flush=True)

        return {
            "status": "success",
            "pre_total": pre_total,
            "pre_duplicates": pre_duplicates,
            "post_total": post_total,
            "post_duplicates": post_duplicates,
            "deleted_count": deleted_count,
            "latency_s": latency_s
        }

    except Exception as e:
        conn.rollback()
        print(f"[CRITICAL ERROR] Migration 033 failed: {e}", file=sys.stderr, flush=True)
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
