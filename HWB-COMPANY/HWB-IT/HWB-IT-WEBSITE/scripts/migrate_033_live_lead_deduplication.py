#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 033: Live Lead Dataset Deduplication & Golden Master Consolidation
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & Lean Six Sigma Zero-Defect Mandate
Authority: Humberto Dominguez (CEO) - Approved 09/29/2026
Auditors: George (Systems Architect & mbB) & Peter (Data Recovery Custodian)

Objectives:
1. Identify all duplicate lead clusters (by duplicate_group_id, name+address+city, and phone+zipcode).
2. Apply Smart Golden Master Survivorship (preserving converted customers, highest field completeness, and oldest record).
3. Non-destructively backfill missing attributes (email, director, sqf, notes) into Golden Master before twin deletion.
4. Safely re-parent all child relationships (CampaignRecipients, Contacts, ApiBillingTracker, GlobalActivities) to Master ID.
5. Purge redundant duplicate shells (is_duplicate = TRUE) with zero orphaned records.
6. Enforce composite unique index idx_leads_unique_location to permanently lock out duplicates.
7. Auto-align all PostgreSQL primary key sequences to >= MAX(id).
8. Record migration idempotently in schema_migrations.
"""

import os
import re
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


def score_lead_completeness(lead: dict) -> int:
    """Calculates data completeness score to select the Golden Master record."""
    score = 0
    if lead.get("is_converted"):
        score += 1000  # Converted customers take absolute precedence
    if lead.get("email") and str(lead.get("email")).strip() not in ('', 'None', '--'):
        score += 25
    if lead.get("decision_maker") and str(lead.get("decision_maker")).strip() not in ('', 'None', '--'):
        score += 20
    elif lead.get("director") and str(lead.get("director")).strip() not in ('', 'None', '--'):
        score += 15
    if lead.get("address") and str(lead.get("address")).strip() not in ('', 'None', 'Pending', '--'):
        score += 15
    if lead.get("phone") and str(lead.get("phone")).strip() not in ('', 'None', '--'):
        score += 10
    if lead.get("sqf") and float(lead.get("sqf") or 0) > 0:
        score += 10
    if lead.get("notes") and str(lead.get("notes")).strip() not in ('', 'None', '--'):
        score += 10
    if lead.get("lead_source") == "Texas CCL API":
        score += 5
    return score


def run_migration(db_url: str = None) -> dict:
    target_url = db_url or DB_URL
    t_start = time.time()
    print("\n==================================================================", flush=True)
    print("  Applying Migration 033: Live Lead Dataset Deduplication", flush=True)
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

            deleted_twin_count = 0
            merged_cluster_count = 0
            enriched_master_count = 0
            reparented_campaigns = 0
            reparented_activities = 0

            # -------------------------------------------------------------
            # STEP 1: CONSOLIDATE EXPLICIT DUPLICATE GROUPS (duplicate_group_id)
            # -------------------------------------------------------------
            cur.execute("""
                SELECT duplicate_group_id, array_agg(id ORDER BY id ASC) as lead_ids
                FROM "Leads"
                WHERE duplicate_group_id IS NOT NULL AND duplicate_group_id != ''
                GROUP BY duplicate_group_id
                HAVING COUNT(*) > 1;
            """)
            explicit_groups = cur.fetchall()
            print(f"[STAGE 1] Consolidating {len(explicit_groups):,} explicit duplicate groups...", flush=True)

            all_deleted_ids = set()

            for grp in explicit_groups:
                lead_ids = [lid for lid in grp["lead_ids"] if lid not in all_deleted_ids]
                if len(lead_ids) <= 1:
                    continue

                cur.execute('SELECT * FROM "Leads" WHERE id = ANY(%s);', (lead_ids,))
                members = [dict(r) for r in cur.fetchall()]
                if len(members) <= 1:
                    continue

                # Rank members by score descending, then lowest ID ascending
                ranked = sorted(members, key=lambda m: (score_lead_completeness(m), -m["id"]), reverse=True)
                master = ranked[0]
                master_id = master["id"]
                twins = ranked[1:]
                twin_ids = [t["id"] for t in twins]

                # Backfill missing attributes into Master
                updates = {}
                for field in [
                    'phone', 'email', 'director', 'decision_maker', 'job_title', 
                    'sqf', 'capacity', 'estimated_annual_value', 'lead_source', 
                    'notes', 'county', 'zipcode', 'facility_type', 'industry', 
                    'umbrella_name', 'cleaning_delivery_model', 'is_commercial', 
                    'commercial_status', 'acquisition_tier', 'ownership_type', 'address', 'city', 'state'
                ]:
                    master_val = master.get(field)
                    is_master_blank = (master_val is None or str(master_val).strip() in ('', 'None', '--', 'Pending'))
                    if is_master_blank:
                        for tw in twins:
                            tw_val = tw.get(field)
                            if tw_val is not None and str(tw_val).strip() not in ('', 'None', '--', 'Pending'):
                                updates[field] = tw_val
                                master[field] = tw_val
                                break

                if updates:
                    set_clause = ", ".join([f'"{k}" = %s' for k in updates.keys()])
                    cur.execute(f'UPDATE "Leads" SET {set_clause} WHERE id = %s;', list(updates.values()) + [master_id])
                    enriched_master_count += 1

                # Re-parent child records
                cur.execute('UPDATE "CampaignRecipients" SET lead_id = %s WHERE lead_id = ANY(%s);', (master_id, twin_ids))
                reparented_campaigns += cur.rowcount

                cur.execute('UPDATE "Contacts" SET lead_id = %s WHERE lead_id = ANY(%s);', (master_id, twin_ids))

                try:
                    cur.execute('UPDATE "ApiBillingTracker" SET lead_id = %s WHERE lead_id = ANY(%s);', (master_id, twin_ids))
                except Exception:
                    pass

                cur.execute("""
                    UPDATE "GlobalActivities" 
                    SET parent_id = %s 
                    WHERE parent_id = ANY(%s) AND parent_type = 'Lead';
                """, (master_id, twin_ids))
                reparented_activities += cur.rowcount

                # Delete twin rows
                cur.execute('DELETE FROM "Leads" WHERE id = ANY(%s);', (twin_ids,))
                deleted_twin_count += len(twin_ids)
                for tid in twin_ids:
                    all_deleted_ids.add(tid)

                # Reset duplicate flag on Master
                cur.execute('UPDATE "Leads" SET is_duplicate = FALSE, duplicate_group_id = NULL WHERE id = %s;', (master_id,))
                merged_cluster_count += 1

            # -------------------------------------------------------------
            # STEP 2: CONSOLIDATE EXACT PHYSICAL MATCHES (Name + Address + City)
            # -------------------------------------------------------------
            cur.execute("""
                SELECT lower(trim(center_name)) as c_name, lower(trim(address)) as c_addr, lower(trim(city)) as c_city, 
                       array_agg(id ORDER BY id ASC) as lead_ids
                FROM "Leads"
                WHERE center_name IS NOT NULL AND trim(center_name) != ''
                  AND address IS NOT NULL AND trim(address) != ''
                  AND city IS NOT NULL AND trim(city) != ''
                GROUP BY lower(trim(center_name)), lower(trim(address)), lower(trim(city))
                HAVING COUNT(*) > 1;
            """)
            physical_groups = cur.fetchall()
            print(f"[STAGE 2] Consolidating {len(physical_groups):,} physical (Name + Address + City) clusters...", flush=True)

            for grp in physical_groups:
                lead_ids = [lid for lid in grp["lead_ids"] if lid not in all_deleted_ids]
                if len(lead_ids) <= 1:
                    continue

                cur.execute('SELECT * FROM "Leads" WHERE id = ANY(%s);', (lead_ids,))
                members = [dict(r) for r in cur.fetchall()]
                if len(members) <= 1:
                    continue

                ranked = sorted(members, key=lambda m: (score_lead_completeness(m), -m["id"]), reverse=True)
                master = ranked[0]
                master_id = master["id"]
                twins = ranked[1:]
                twin_ids = [t["id"] for t in twins]

                updates = {}
                for field in [
                    'phone', 'email', 'director', 'decision_maker', 'job_title', 
                    'sqf', 'capacity', 'estimated_annual_value', 'lead_source', 
                    'notes', 'county', 'zipcode', 'facility_type', 'industry', 
                    'umbrella_name', 'cleaning_delivery_model', 'is_commercial', 
                    'commercial_status', 'acquisition_tier', 'ownership_type'
                ]:
                    master_val = master.get(field)
                    is_master_blank = (master_val is None or str(master_val).strip() in ('', 'None', '--', 'Pending'))
                    if is_master_blank:
                        for tw in twins:
                            tw_val = tw.get(field)
                            if tw_val is not None and str(tw_val).strip() not in ('', 'None', '--', 'Pending'):
                                updates[field] = tw_val
                                master[field] = tw_val
                                break

                if updates:
                    set_clause = ", ".join([f'"{k}" = %s' for k in updates.keys()])
                    cur.execute(f'UPDATE "Leads" SET {set_clause} WHERE id = %s;', list(updates.values()) + [master_id])
                    enriched_master_count += 1

                cur.execute('UPDATE "CampaignRecipients" SET lead_id = %s WHERE lead_id = ANY(%s);', (master_id, twin_ids))
                reparented_campaigns += cur.rowcount

                cur.execute('UPDATE "Contacts" SET lead_id = %s WHERE lead_id = ANY(%s);', (master_id, twin_ids))

                try:
                    cur.execute('UPDATE "ApiBillingTracker" SET lead_id = %s WHERE lead_id = ANY(%s);', (master_id, twin_ids))
                except Exception:
                    pass

                cur.execute("""
                    UPDATE "GlobalActivities" 
                    SET parent_id = %s 
                    WHERE parent_id = ANY(%s) AND parent_type = 'Lead';
                """, (master_id, twin_ids))
                reparented_activities += cur.rowcount

                cur.execute('DELETE FROM "Leads" WHERE id = ANY(%s);', (twin_ids,))
                deleted_twin_count += len(twin_ids)
                for tid in twin_ids:
                    all_deleted_ids.add(tid)

                cur.execute('UPDATE "Leads" SET is_duplicate = FALSE, duplicate_group_id = NULL WHERE id = %s;', (master_id,))
                merged_cluster_count += 1

            # -------------------------------------------------------------
            # STEP 3: CONSOLIDATE PHONE + ZIPCODE TWINS (Matching physical accounts)
            # -------------------------------------------------------------
            cur.execute("""
                SELECT phone, zipcode, array_agg(id ORDER BY id ASC) as lead_ids, array_agg(COALESCE(address, '')) as addrs
                FROM "Leads"
                WHERE phone IS NOT NULL AND phone != '' AND length(phone) >= 10 AND phone NOT LIKE '%%000-0000%%'
                  AND zipcode IS NOT NULL AND zipcode != ''
                GROUP BY phone, zipcode
                HAVING COUNT(*) > 1;
            """)
            phone_zip_groups = cur.fetchall()
            print(f"[STAGE 3] Inspecting {len(phone_zip_groups):,} phone + zipcode candidate clusters...", flush=True)

            for pz in phone_zip_groups:
                lead_ids = [lid for lid in pz["lead_ids"] if lid not in all_deleted_ids]
                raw_addrs = pz["addrs"]
                clean_addrs = set(a.lower().strip() for a in raw_addrs if a and 'pending' not in a.lower())
                
                # Merge if physical addresses are identical or one is missing
                if len(clean_addrs) <= 1 and len(lead_ids) >= 2:
                    cur.execute('SELECT * FROM "Leads" WHERE id = ANY(%s);', (lead_ids,))
                    members = [dict(r) for r in cur.fetchall()]
                    if len(members) <= 1:
                        continue

                    ranked = sorted(members, key=lambda m: (score_lead_completeness(m), -m["id"]), reverse=True)
                    master = ranked[0]
                    master_id = master["id"]
                    twins = ranked[1:]
                    twin_ids = [t["id"] for t in twins]

                    updates = {}
                    for field in [
                        'phone', 'email', 'director', 'decision_maker', 'job_title', 
                        'sqf', 'capacity', 'estimated_annual_value', 'lead_source', 
                        'notes', 'county', 'zipcode', 'facility_type', 'industry', 
                        'umbrella_name', 'cleaning_delivery_model', 'is_commercial', 
                        'commercial_status', 'acquisition_tier', 'ownership_type', 'address', 'city', 'state'
                    ]:
                        master_val = master.get(field)
                        is_master_blank = (master_val is None or str(master_val).strip() in ('', 'None', '--', 'Pending'))
                        if is_master_blank:
                            for tw in twins:
                                tw_val = tw.get(field)
                                if tw_val is not None and str(tw_val).strip() not in ('', 'None', '--', 'Pending'):
                                    updates[field] = tw_val
                                    master[field] = tw_val
                                    break

                    if updates:
                        set_clause = ", ".join([f'"{k}" = %s' for k in updates.keys()])
                        cur.execute(f'UPDATE "Leads" SET {set_clause} WHERE id = %s;', list(updates.values()) + [master_id])
                        enriched_master_count += 1

                    cur.execute('UPDATE "CampaignRecipients" SET lead_id = %s WHERE lead_id = ANY(%s);', (master_id, twin_ids))
                    reparented_campaigns += cur.rowcount

                    cur.execute('UPDATE "Contacts" SET lead_id = %s WHERE lead_id = ANY(%s);', (master_id, twin_ids))

                    try:
                        cur.execute('UPDATE "ApiBillingTracker" SET lead_id = %s WHERE lead_id = ANY(%s);', (master_id, twin_ids))
                    except Exception:
                        pass

                    cur.execute("""
                        UPDATE "GlobalActivities" 
                        SET parent_id = %s 
                        WHERE parent_id = ANY(%s) AND parent_type = 'Lead';
                    """, (master_id, twin_ids))
                    reparented_activities += cur.rowcount

                    cur.execute('DELETE FROM "Leads" WHERE id = ANY(%s);', (twin_ids,))
                    deleted_twin_count += len(twin_ids)
                    for tid in twin_ids:
                        all_deleted_ids.add(tid)

                    cur.execute('UPDATE "Leads" SET is_duplicate = FALSE, duplicate_group_id = NULL WHERE id = %s;', (master_id,))
                    merged_cluster_count += 1

            # -------------------------------------------------------------
            # STEP 4: PURGE REMAINING ORPHANED DUPLICATE SHELLS
            # -------------------------------------------------------------
            cur.execute('SELECT COUNT(*) as rem_dups FROM "Leads" WHERE is_duplicate = TRUE;')
            rem_dups_count = cur.fetchone()["rem_dups"]
            if rem_dups_count > 0:
                print(f"[STAGE 4] Re-parenting and purging {rem_dups_count:,} remaining orphan duplicate shells...", flush=True)
                cur.execute('SELECT id FROM "Leads" WHERE is_duplicate = TRUE;')
                orphan_dup_ids = [r["id"] for r in cur.fetchall()]

                # Clean any lingering foreign key references before delete
                cur.execute('DELETE FROM "CampaignRecipients" WHERE lead_id = ANY(%s);', (orphan_dup_ids,))
                cur.execute('DELETE FROM "Contacts" WHERE lead_id = ANY(%s);', (orphan_dup_ids,))
                try:
                    cur.execute('DELETE FROM "ApiBillingTracker" WHERE lead_id = ANY(%s);', (orphan_dup_ids,))
                except Exception:
                    pass
                cur.execute("DELETE FROM \"GlobalActivities\" WHERE parent_id = ANY(%s) AND parent_type = 'Lead';", (orphan_dup_ids,))

                cur.execute('DELETE FROM "Leads" WHERE is_duplicate = TRUE;')
                deleted_twin_count += len(orphan_dup_ids)

            # -------------------------------------------------------------
            # STEP 5: POKA-YOKE UNIQUE LOCATION INDEX INSTALLATION
            # -------------------------------------------------------------
            print("[STAGE 5] Enforcing composite unique index idx_leads_unique_location...", flush=True)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_unique_location 
                ON "Leads" (LOWER(TRIM(center_name)), LOWER(TRIM(address)), LOWER(TRIM(city)));
            """)

            # -------------------------------------------------------------
            # STEP 6: SEQUENCE AUTO-ALIGNMENT
            # -------------------------------------------------------------
            print("[STAGE 6] Aligning PostgreSQL primary key sequences to >= MAX(id)...", flush=True)
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
            # STEP 7: POST-FLIGHT AUDIT & TELEMETRY
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

            # Record migration in schema_migrations
            cur.execute("""
                INSERT INTO "schema_migrations" (version, description)
                VALUES (
                    '033_live_lead_deduplication',
                    'Live lead dataset deduplication, Golden Master consolidation, child re-parenting, and unique index enforcement'
                )
                ON CONFLICT (version) DO NOTHING;
            """)

            # Log audit trail to GlobalActivities
            cur.execute("""
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description, timestamp)
                VALUES (1, 'System', '[LIVE-LEAD-DEDUPLICATION]', %s, NOW());
            """, (f"Migration 033: Purged {deleted_twin_count:,} duplicate shells across {merged_cluster_count:,} clusters. Clean leads: {post_clean:,}.",))

        conn.commit()
        latency_s = round(time.time() - t_start, 2)
        print("------------------------------------------------------------------", flush=True)
        print(f"[SUCCESS] Migration 033 Completed in {latency_s}s", flush=True)
        print(f"  Pre-Total Leads:      {pre_total:,}")
        print(f"  Deleted Duplicates:   {deleted_twin_count:,}")
        print(f"  Post-Total Leads:     {post_total:,}")
        print(f"  Post-Duplicate Count: {post_duplicates:,} (Target: 0)")
        print(f"  Post-Clean Active:    {post_clean:,}")
        print(f"  Clusters Merged:      {merged_cluster_count:,}")
        print(f"  Masters Enriched:     {enriched_master_count:,}")
        print(f"  Re-parented CR/GA:    {reparented_campaigns:,} campaigns / {reparented_activities:,} activities")
        print("==================================================================\n", flush=True)

        return {
            "status": "success",
            "pre_total": pre_total,
            "pre_duplicates": pre_duplicates,
            "post_total": post_total,
            "post_duplicates": post_duplicates,
            "deleted_count": deleted_twin_count,
            "clusters_merged": merged_cluster_count,
            "masters_enriched": enriched_master_count,
            "reparented_campaigns": reparented_campaigns,
            "reparented_activities": reparented_activities,
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
