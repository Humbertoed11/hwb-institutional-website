#!/usr/bin/env python3
"""
SO-COM-001 Lead Deduplication & Golden Master Consolidation Script
Authority: Approved by CEO Humberto Dominguez under SO-COM-001-DIR-01
Lead Auditor: Super George (Systems Architect & Lead Autonomous Commander)
Tactical Builder: George Bytes (Lead Software Engineer)

Execution standard:
1. Group leads by LOWER(TRIM(email)) where email is not null/empty.
2. Select Golden Master based on profile completeness and activity.
3. Enrich Golden Master with non-empty attributes from duplicate records.
4. Re-parent child records (CampaignRecipients, Contacts, GlobalActivities, ApiBillingTracker).
5. Delete 2,606 duplicate shells.
6. Verify post-flight metrics: 25,378 clean leads, 0 duplicate emails, $11,221,846.94 pipeline intact.
"""

import sys
import time
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db"

def score_lead(lead: dict) -> int:
    score = 0
    if lead.get("phone") and lead["phone"].strip():
        score += 2
    if lead.get("director") and lead["director"].strip():
        score += 2
    if lead.get("decision_maker") and lead["decision_maker"].strip():
        score += 1
    if lead.get("address") and lead["address"].strip():
        score += 2
    if lead.get("city") and lead["city"].strip():
        score += 1
    if lead.get("state") and lead["state"].strip():
        score += 1
    if lead.get("sqf") and lead["sqf"] > 0:
        score += 2
    if lead.get("capacity") and lead["capacity"] > 0:
        score += 2
    if lead.get("estimated_annual_value") and lead["estimated_annual_value"] > 0:
        score += 2
    if lead.get("notes") and lead["notes"].strip():
        score += 1
    if lead.get("umbrella_name") and lead["umbrella_name"].strip():
        score += 1
    if lead.get("is_converted"):
        score += 5
    return score

def run_deduplication(dry_run: bool = False):
    t0 = time.time()
    print("=" * 70)
    print(f"  SO-COM-001 LEAD DEDUPLICATION ENGINE (DryRun={dry_run})")
    print("=" * 70)

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Pre-flight checks
            cur.execute('SELECT COUNT(*) as cnt FROM "Leads";')
            pre_lead_count = cur.fetchone()["cnt"]
            print(f"[PRE-FLIGHT] Total Leads on File: {pre_lead_count:,}")

            cur.execute("""
                SELECT LOWER(TRIM(email)) as em, COUNT(*) as c
                FROM "Leads"
                WHERE email IS NOT NULL AND TRIM(email) != ''
                GROUP BY LOWER(TRIM(email))
                HAVING COUNT(*) > 1;
            """)
            dup_groups = cur.fetchall()
            num_dup_groups = len(dup_groups)
            total_leads_in_dup_groups = sum(g["c"] for g in dup_groups)
            expected_duplicates = total_leads_in_dup_groups - num_dup_groups
            expected_clean_leads = pre_lead_count - expected_duplicates

            print(f"[PRE-FLIGHT] Duplicate Email Groups: {num_dup_groups:,}")
            print(f"[PRE-FLIGHT] Leads in Duplicate Groups: {total_leads_in_dup_groups:,}")
            print(f"[PRE-FLIGHT] Excess Duplicate Shells to Remove: {expected_duplicates:,}")
            print(f"[PRE-FLIGHT] Expected Post-Clean Lead Count: {expected_clean_leads:,}")

            # Child records pre-flight
            cur.execute('SELECT COUNT(*) as cnt FROM "CampaignRecipients";')
            pre_cr_count = cur.fetchone()["cnt"]
            cur.execute('SELECT COUNT(*) as cnt FROM "Contacts";')
            pre_c_count = cur.fetchone()["cnt"]
            cur.execute('SELECT COUNT(*) as cnt FROM "GlobalActivities" WHERE parent_type = \'Lead\';')
            pre_ga_count = cur.fetchone()["cnt"]
            print(f"[PRE-FLIGHT] Child Records: CampaignRecipients={pre_cr_count}, Contacts={pre_c_count}, GlobalActivities={pre_ga_count}")

            # Bid pipelines pre-flight
            cur.execute('SELECT COUNT(*) as cnt, COALESCE(SUM(estimated_value), 0) as total FROM "ConstructionBids";')
            pre_cb = cur.fetchone()
            cur.execute('SELECT COUNT(*) as cnt, COALESCE(SUM(hwb_bid_total), 0) as total FROM "InstitutionalBids";')
            pre_ib = cur.fetchone()
            pre_pipeline_total = float(pre_cb["total"]) + float(pre_ib["total"])
            print(f"[PRE-FLIGHT] Pipeline: {pre_cb['cnt']} Commercial (${float(pre_cb['total']):,.2f}) + {pre_ib['cnt']} Institutional (${float(pre_ib['total']):,.2f}) = ${pre_pipeline_total:,.2f}")

            # 2. Process each duplicate group
            all_dup_ids = []
            reparented_cr = 0
            reparented_c = 0
            reparented_ga = 0
            reparented_ab = 0
            enriched_masters = 0

            print(f"\n[EXECUTION] Processing {num_dup_groups:,} duplicate email groups...")

            for g_idx, g in enumerate(dup_groups):
                email = g["em"]
                cur.execute('SELECT * FROM "Leads" WHERE LOWER(TRIM(email)) = %s ORDER BY id ASC;', (email,))
                records = cur.fetchall()

                # Score each record and select Golden Master
                scored_records = sorted(records, key=lambda r: (score_lead(r), -r["id"]), reverse=True)
                master = dict(scored_records[0])
                duplicates = [dict(r) for r in scored_records[1:]]

                # Enrich master with fields from duplicates
                updated_master = False
                fields_to_coalesce = [
                    "phone", "director", "decision_maker", "job_title", "address", 
                    "city", "state", "zipcode", "county", "notes", "umbrella_name", 
                    "website", "lead_source", "service_interest", "facility_type"
                ]

                master_sqf = master.get("sqf") or 0
                master_capacity = master.get("capacity") or 0
                master_eav = master.get("estimated_annual_value") or 0.0
                master_cw = master.get("calculated_waste") or 0.0

                for dup in duplicates:
                    all_dup_ids.append(dup["id"])
                    
                    # Numeric fields: take maximum
                    if (dup.get("sqf") or 0) > master_sqf:
                        master_sqf = dup["sqf"]
                        updated_master = True
                    if (dup.get("capacity") or 0) > master_capacity:
                        master_capacity = dup["capacity"]
                        updated_master = True
                    if (dup.get("estimated_annual_value") or 0.0) > master_eav:
                        master_eav = dup["estimated_annual_value"]
                        updated_master = True
                    if (dup.get("calculated_waste") or 0.0) > master_cw:
                        master_cw = dup["calculated_waste"]
                        updated_master = True

                    # String fields: coalesce if empty
                    for f in fields_to_coalesce:
                        val = dup.get(f)
                        if val and (not master.get(f) or not str(master.get(f)).strip()):
                            master[f] = val
                            updated_master = True

                if updated_master and not dry_run:
                    cur.execute("""
                        UPDATE "Leads"
                        SET phone = %s, director = %s, decision_maker = %s, job_title = %s,
                            address = %s, city = %s, state = %s, zipcode = %s, county = %s,
                            notes = %s, umbrella_name = %s, website = %s, lead_source = %s,
                            service_interest = %s, facility_type = %s, sqf = %s, capacity = %s,
                            estimated_annual_value = %s, calculated_waste = %s
                        WHERE id = %s;
                    """, (
                        master.get("phone"), master.get("director"), master.get("decision_maker"), master.get("job_title"),
                        master.get("address"), master.get("city"), master.get("state"), master.get("zipcode"), master.get("county"),
                        master.get("notes"), master.get("umbrella_name"), master.get("website"), master.get("lead_source"),
                        master.get("service_interest"), master.get("facility_type"), master_sqf, master_capacity,
                        master_eav, master_cw, master["id"]
                    ))
                    enriched_masters += 1

                # Re-parent children for all duplicates in this group
                dup_ids = [d["id"] for d in duplicates]
                if not dry_run:
                    cur.execute('UPDATE "CampaignRecipients" SET lead_id = %s WHERE lead_id = ANY(%s);', (master["id"], dup_ids))
                    reparented_cr += cur.rowcount

                    cur.execute('UPDATE "Contacts" SET lead_id = %s WHERE lead_id = ANY(%s);', (master["id"], dup_ids))
                    reparented_c += cur.rowcount

                    cur.execute('UPDATE "GlobalActivities" SET parent_id = %s WHERE parent_id = ANY(%s) AND parent_type = \'Lead\';', (master["id"], dup_ids))
                    reparented_ga += cur.rowcount

                    cur.execute('UPDATE "ApiBillingTracker" SET lead_id = %s WHERE lead_id = ANY(%s);', (master["id"], dup_ids))
                    reparented_ab += cur.rowcount

            print(f"[RE-PARENTING] CampaignRecipients: {reparented_cr} | Contacts: {reparented_c} | GlobalActivities: {reparented_ga} | ApiBillingTracker: {reparented_ab}")
            print(f"[ENRICHMENT] Golden Masters enriched with merged attributes: {enriched_masters:,}")
            print(f"[PURGE] Deleting {len(all_dup_ids):,} duplicate lead shells...")

            if not dry_run:
                # Delete duplicate shells in bulk
                cur.execute('DELETE FROM "Leads" WHERE id = ANY(%s);', (all_dup_ids,))
                deleted_rows = cur.rowcount
                print(f"[PURGE] Rows deleted from Leads: {deleted_rows:,}")
                assert deleted_rows == expected_duplicates, f"Mismatch in deleted rows: {deleted_rows} != {expected_duplicates}"

                # Align sequence
                cur.execute('SELECT setval(\'"Leads_id_seq"\', COALESCE((SELECT MAX(id) FROM "Leads"), 1));')

                # 3. Post-flight verification
                cur.execute('SELECT COUNT(*) as cnt FROM "Leads";')
                post_lead_count = cur.fetchone()["cnt"]
                print(f"[POST-FLIGHT] Total Clean Leads: {post_lead_count:,} (Expected: {expected_clean_leads:,})")
                assert post_lead_count == expected_clean_leads, f"Post lead count {post_lead_count} does not match expected {expected_clean_leads}!"

                cur.execute("""
                    SELECT COUNT(*) as cnt FROM (
                        SELECT LOWER(TRIM(email)) 
                        FROM "Leads" 
                        WHERE email IS NOT NULL AND TRIM(email) != '' 
                        GROUP BY LOWER(TRIM(email)) 
                        HAVING COUNT(*) > 1
                    ) s;
                """)
                post_dup_groups = cur.fetchone()["cnt"]
                print(f"[POST-FLIGHT] Duplicate Email Groups Remaining: {post_dup_groups} (Target: 0)")
                assert post_dup_groups == 0, f"Remaining duplicate groups: {post_dup_groups}!"

                # Verify child row totals conserved
                cur.execute('SELECT COUNT(*) as cnt FROM "CampaignRecipients";')
                post_cr_count = cur.fetchone()["cnt"]
                cur.execute('SELECT COUNT(*) as cnt FROM "Contacts";')
                post_c_count = cur.fetchone()["cnt"]
                cur.execute('SELECT COUNT(*) as cnt FROM "GlobalActivities" WHERE parent_type = \'Lead\';')
                post_ga_count = cur.fetchone()["cnt"]
                print(f"[POST-FLIGHT] Child Conservation: CampaignRecipients={post_cr_count}/{pre_cr_count}, Contacts={post_c_count}/{pre_c_count}, GlobalActivities={post_ga_count}/{pre_ga_count}")
                assert post_cr_count == pre_cr_count, "CampaignRecipients count changed!"
                assert post_c_count == pre_c_count, "Contacts count changed!"
                assert post_ga_count == pre_ga_count, "GlobalActivities count changed!"

                # Verify active bid pipeline intact
                cur.execute('SELECT COUNT(*) as cnt, COALESCE(SUM(estimated_value), 0) as total FROM "ConstructionBids";')
                post_cb = cur.fetchone()
                cur.execute('SELECT COUNT(*) as cnt, COALESCE(SUM(hwb_bid_total), 0) as total FROM "InstitutionalBids";')
                post_ib = cur.fetchone()
                post_pipeline_total = float(post_cb["total"]) + float(post_ib["total"])
                print(f"[POST-FLIGHT] Active Bid Pipeline: {post_cb['cnt']} Commercial (${float(post_cb['total']):,.2f}) + {post_ib['cnt']} Institutional (${float(post_ib['total']):,.2f}) = ${post_pipeline_total:,.2f}")
                assert abs(post_pipeline_total - pre_pipeline_total) < 0.01, f"Pipeline changed from ${pre_pipeline_total} to ${post_pipeline_total}!"

                # Record in schema_migrations
                cur.execute("""
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('033_so_com_001_lead_deduplication', 'Deduplicated 2,606 email duplicates into Golden Masters, re-parented 322 child ties, verified zero dollar loss')
                    ON CONFLICT (version) DO NOTHING;
                """)

                conn.commit()
                print("\n[SUCCESS] Transaction COMMITTED successfully.")
            else:
                conn.rollback()
                print("\n[DRY RUN] Transaction rolled back. No changes made.")

        elapsed = round(time.time() - t0, 2)
        print(f"[COMPLETE] Deduplication process completed in {elapsed}s.")
        return {
            "status": "success",
            "pre_count": pre_lead_count,
            "deleted": len(all_dup_ids),
            "post_count": expected_clean_leads,
            "reparented_campaigns": reparented_cr,
            "reparented_contacts": reparented_c,
            "reparented_activities": reparented_ga,
            "duration_s": elapsed
        }

    except Exception as e:
        conn.rollback()
        print(f"\n[CRITICAL ERROR] Deduplication failed: {e}", file=sys.stderr)
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    run_deduplication(dry_run=is_dry)
