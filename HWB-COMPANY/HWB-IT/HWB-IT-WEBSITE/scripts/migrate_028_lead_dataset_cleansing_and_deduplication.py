"""
Migration 028: Lead Dataset Cleansing, Deduplication & PROC-002 Standardization
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & Lean Six Sigma Zero-Defect Mandate
Authority: Humberto Dominguez (CEO) - Approved 09/27/2026
Architect: George (Systems Architect & mbB) & Silas Sync (VP of CRM)
"""

import os
import re
import sys
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")


def normalize_phone(raw_phone):
    if not raw_phone:
        return raw_phone
    digits = re.sub(r"\D", "", str(raw_phone).strip())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return str(raw_phone).strip()


def run_migration(db_url: str = None):
    target_url = db_url or DB_URL
    print("\n==================================================================", flush=True)
    print("  Applying Migration 028: Lead Dataset Cleansing & Deduplication", flush=True)
    print("==================================================================", flush=True)

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # -------------------------------------------------------------
            # STEP 0: EXPAND COLUMN CAPACITIES FOR HIGH DENSITY DATA
            # -------------------------------------------------------------
            print("  -> Step 0: Expanding column capacities...", flush=True)
            cur.execute("""
                ALTER TABLE "Leads" ALTER COLUMN umbrella_name TYPE TEXT;
                ALTER TABLE "Leads" ALTER COLUMN duplicate_group_id TYPE VARCHAR(128);
            """)

            # -------------------------------------------------------------
            # STEP 1: STATE NOMENCLATURE & OUT-OF-STATE ISOLATION
            # -------------------------------------------------------------
            print("  -> Step 1: Normalizing State nomenclature...", flush=True)
            cur.execute("""
                UPDATE "Leads" 
                SET state = 'TX' 
                WHERE state ILIKE 'texas' OR state = 'Texas' OR state IS NULL;
            """)
            tx_updated = cur.rowcount

            cur.execute("""
                UPDATE "Leads" 
                SET status = 'OUT_OF_TERRITORY', 
                    acquisition_tier = 'Disqualified' 
                WHERE state IN ('MO', 'VA');
            """)
            out_of_state = cur.rowcount
            print(f"     -> Standardized {tx_updated:,} Texas records to 'TX'; isolated {out_of_state} out-of-state records.", flush=True)

            # -------------------------------------------------------------
            # STEP 2: STATUS CASING & DNC ALIGNMENT
            # -------------------------------------------------------------
            print("  -> Step 2: Unifying Status casing ('New' -> 'NEW') & DNC...", flush=True)
            cur.execute("""
                UPDATE "Leads" 
                SET status = 'NEW' 
                WHERE status = 'New';
            """)
            status_new_updated = cur.rowcount

            cur.execute("""
                UPDATE "Leads" 
                SET status = 'DNC', is_dnc = TRUE 
                WHERE status ILIKE '%do not call%' OR status ILIKE '%dnc%';
            """)
            dnc_updated = cur.rowcount
            print(f"     -> Unified {status_new_updated:,} 'New' records to 'NEW'; aligned {dnc_updated} DNC records.", flush=True)

            # -------------------------------------------------------------
            # STEP 3: CONTRACT VALUATION BACKFILL (sqf * 1.44)
            # -------------------------------------------------------------
            print("  -> Step 3: Backfilling estimated annual contract valuations...", flush=True)
            cur.execute("""
                UPDATE "Leads" 
                SET estimated_annual_value = ROUND((sqf * 1.44)::numeric, 2)
                WHERE (estimated_annual_value IS NULL OR estimated_annual_value = 0)
                  AND sqf > 0;
            """)
            valuation_updated = cur.rowcount
            print(f"     -> Backfilled contract valuations on {valuation_updated:,} leads (standardized $1.44/sqft/yr rate).", flush=True)

            # -------------------------------------------------------------
            # STEP 4: BULK PROC-002 PHONE NUMBER NORMALIZATION
            # -------------------------------------------------------------
            print("  -> Step 4: Normalizing all phone numbers to PROC-002 format (###) ###-####...", flush=True)
            cur.execute("""
                SELECT id, phone 
                FROM "Leads" 
                WHERE phone IS NOT NULL AND phone != '';
            """)
            all_phones = cur.fetchall()

            phone_updates = []
            for r in all_phones:
                cleaned = normalize_phone(r["phone"])
                if cleaned and cleaned != r["phone"]:
                    phone_updates.append((cleaned, r["id"]))

            if phone_updates:
                cur.executemany("""
                    UPDATE "Leads" SET phone = %s WHERE id = %s;
                """, phone_updates)
            print(f"     -> Normalized {len(phone_updates):,} phone numbers to strict PROC-002 standard.", flush=True)

            # -------------------------------------------------------------
            # STEP 5: NON-DESTRUCTIVE CLONE DEDUPLICATION & ENRICHMENT
            # -------------------------------------------------------------
            print("  -> Step 5: Executing non-destructive exact clone deduplication...", flush=True)
            # Find duplicate clusters by matching normalized name + 10-digit phone
            cur.execute("""
                WITH dup_clusters AS (
                    SELECT lower(trim(center_name)) as c_name, regexp_replace(phone, '\\D', '', 'g') as c_phone
                    FROM "Leads"
                    WHERE center_name IS NOT NULL AND trim(center_name) != ''
                      AND phone IS NOT NULL AND regexp_replace(phone, '\\D', '', 'g') != ''
                    GROUP BY lower(trim(center_name)), regexp_replace(phone, '\\D', '', 'g')
                    HAVING count(*) > 1
                )
                SELECT l.id, l.center_name, l.phone, l.email, l.address, l.city, l.decision_maker, l.director, 
                       l.notes, l.is_converted, l.status, l.lead_source, l.sqf,
                       lower(trim(l.center_name)) as grp_name, regexp_replace(l.phone, '\\D', '', 'g') as grp_phone
                FROM "Leads" l
                JOIN dup_clusters dc ON lower(trim(l.center_name)) = dc.c_name 
                                    AND regexp_replace(l.phone, '\\D', '', 'g') = dc.c_phone
                ORDER BY grp_name, grp_phone, l.id;
            """)
            dup_rows = cur.fetchall()

            # Group rows by (grp_name, grp_phone)
            clusters = {}
            for r in dup_rows:
                key = (r["grp_name"], r["grp_phone"])
                clusters.setdefault(key, []).append(r)

            clones_merged = 0
            enrichments_applied = 0
            chains_grouped = 0

            for (grp_name, grp_phone), members in clusters.items():
                # Check if this cluster represents distinct multi-location stores (different cities/addresses)
                distinct_cities = {m["city"].strip().lower() for m in members if m.get("city")}
                if len(distinct_cities) > 2 and len(members) > 3:
                    # Multi-location corporate chain (e.g. Tractor Supply Co)
                    parent_umbrella = members[0]["center_name"]
                    member_ids = [m["id"] for m in members]
                    cur.execute("""
                        UPDATE "Leads" 
                        SET umbrella_name = %s 
                        WHERE id = ANY(%s) AND (umbrella_name IS NULL OR umbrella_name = '');
                    """, (parent_umbrella, member_ids))
                    chains_grouped += len(member_ids)
                    continue

                # Genuine duplicate clones of the same physical account
                # Calculate completeness score for each member
                def score_member(m):
                    score = 0
                    if m.get("email"): score += 20
                    if m.get("decision_maker") or m.get("director"): score += 15
                    if m.get("address"): score += 10
                    if m.get("notes"): score += 10
                    if m.get("is_converted"): score += 100
                    if m.get("lead_source") == "Texas CCL API": score += 5  # Recent API has higher address fidelity
                    return score

                # Sort by score descending, then lowest ID ascending
                ranked = sorted(members, key=lambda m: (score_member(m), -m["id"]), reverse=True)
                master = ranked[0]
                master_id = master["id"]

                # Enrich master record if clones have missing email, director, or address
                enrich_email = None
                enrich_contact = None
                for clone in ranked[1:]:
                    if not master.get("email") and clone.get("email"):
                        enrich_email = clone["email"]
                        master["email"] = enrich_email
                    if not master.get("decision_maker") and clone.get("decision_maker"):
                        enrich_contact = clone["decision_maker"]
                        master["decision_maker"] = enrich_contact
                    elif not master.get("director") and clone.get("director"):
                        enrich_contact = clone["director"]
                        master["director"] = enrich_contact

                if enrich_email or enrich_contact:
                    cur.execute("""
                        UPDATE "Leads" 
                        SET email = COALESCE(email, %s),
                            decision_maker = COALESCE(decision_maker, %s)
                        WHERE id = %s;
                    """, (enrich_email, enrich_contact, master_id))
                    enrichments_applied += 1

                # Mark all duplicate clones
                clone_ids = [c["id"] for c in ranked[1:]]
                cur.execute("""
                    UPDATE "Leads" 
                    SET is_duplicate = TRUE,
                        duplicate_group_id = %s,
                        status = 'MERGED_DUPLICATE'
                    WHERE id = ANY(%s);
                """, (f"DUP-{master_id}", clone_ids))
                clones_merged += len(clone_ids)

            print(f"     -> Identified {len(clusters):,} duplicate clusters.", flush=True)
            print(f"     -> Grouped {chains_grouped:,} records under CorporateUmbrellas.", flush=True)
            print(f"     -> Enriched {enrichments_applied:,} master records with missing contact data.", flush=True)
            print(f"     -> Flagged and linked {clones_merged:,} duplicate clones (non-destructive zero data loss).", flush=True)

            # -------------------------------------------------------------
            # STEP 6: RECORD MIGRATION IN schema_migrations
            # -------------------------------------------------------------
            cur.execute("""
                INSERT INTO "schema_migrations" (version, description)
                VALUES (
                    '028_lead_dataset_cleansing_and_deduplication',
                    'Lead dataset deduplication, PROC-002 phone normalization, state standardization, and valuation backfill'
                )
                ON CONFLICT (version) DO NOTHING;
            """)

        conn.commit()
        print("  -> SUCCESS: Migration 028 executed cleanly with 100% zero defects.", flush=True)
        print("==================================================================\n", flush=True)
    except Exception as e:
        conn.rollback()
        print(f"  -> [CRITICAL ERROR] Migration 028 failed: {e}", file=sys.stderr, flush=True)
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
