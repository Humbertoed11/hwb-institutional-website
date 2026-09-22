"""
Migration 020: SigmaFidelity™ Lead Data Integrity & Classification Cleansing
Standard: HWB-QMS-7.8 M&A Target Deal Radar & Daycare Commercial Partitioning SOP
Authority: Humberto Dominguez (CEO) - Approved 09/21/2026
Architect: George (Systems Architect & mbB)
"""

import os
import re
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")


def clean_jammed_address(raw_addr: str, city: str) -> str:
    if not raw_addr:
        return raw_addr
    addr = raw_addr.strip()

    # Pattern 1: ', City, TX 75182' or ', Sunnyvale, Tx 75182'
    p1 = re.sub(r',\s*[^,]+,\s*(?:TX|Tx|Texas)\s*\d{5}(?:-\d{4})?', '', addr, flags=re.IGNORECASE)
    if p1 != addr:
        return p1.strip()

    # Pattern 2: '  CITY TX- 78552 3345' or '  CITY TX 78552'
    if city:
        p2 = re.sub(rf'\s+{re.escape(city)}\s+(?:TX|Texas)-?\s*\d{{5}}.*$', '', addr, flags=re.IGNORECASE)
        if p2 != addr:
            return p2.strip()

    # Pattern 3: General trailing TX- or TX \d{5}
    p3 = re.sub(r'\s+[A-Za-z\s]+(?:TX|Texas)-?\s*\d{5}.*$', '', addr, flags=re.IGNORECASE)
    return p3.strip()


def run_migration(db_url: str = None):
    target_url = db_url or DB_URL
    print("\n================================================================================")
    print("  Applying Migration 020: Lead Data Integrity & Classification Cleansing")
    print("================================================================================")

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor() as cur:
            # -------------------------------------------------------------------------
            # 1 & 2. Correct Contradicted Industry & Facility Type (Unified Query)
            # -------------------------------------------------------------------------
            cur.execute("""
                UPDATE "Leads"
                SET industry = CASE 
                        WHEN (industry = 'Child Care' OR industry IS NULL OR trim(industry) = '') THEN 'Commercial Legacy' 
                        ELSE industry 
                    END,
                    facility_type = CASE 
                        WHEN (facility_type = 'Child Care Center' OR facility_type IS NULL OR trim(facility_type) = '') THEN 'Commercial Property' 
                        ELSE facility_type 
                    END
                WHERE commercial_status = 'Non-Childcare Legacy'
                  AND (
                      (industry = 'Child Care' OR industry IS NULL OR trim(industry) = '')
                      OR (facility_type = 'Child Care Center' OR facility_type IS NULL OR trim(facility_type) = '')
                  );
            """)
            fixed_count = cur.rowcount
            conn.commit()
            print(f"  ✓ Corrected industry & facility_type on {fixed_count:,} legacy commercial records.")

            # -------------------------------------------------------------------------
            # 3. Clean Jammed Street Addresses & Resolve Hidden Duplicates
            # -------------------------------------------------------------------------
            cur.execute("""
                SELECT id, center_name, address, city
                FROM "Leads"
                WHERE address ILIKE '%TX-%' OR address ILIKE '%TX %';
            """)
            jammed_rows = cur.fetchall()
            cleaned_addr_count = 0
            hidden_dupes_flagged = 0

            candidates = []
            for lead_id, center_name, raw_addr, city_val in jammed_rows:
                cleaned = clean_jammed_address(raw_addr, city_val)
                if cleaned and cleaned != raw_addr:
                    candidates.append((lead_id, center_name or "", cleaned, city_val or ""))

            if candidates:
                # Fast in-memory lookup via single batch query by center_name
                names_to_check = list(set(c[1].strip().lower() for c in candidates if c[1].strip()))
                existing_map = {}
                if names_to_check:
                    cur.execute("""
                        SELECT id, lower(trim(center_name)), lower(trim(address)), lower(trim(city))
                        FROM "Leads"
                        WHERE lower(trim(center_name)) = ANY(%s);
                    """, (names_to_check,))
                    for ex_id, ex_name, ex_addr, ex_city in cur.fetchall():
                        existing_map[(ex_name, ex_addr, ex_city)] = ex_id

                for lead_id, center_name, cleaned_addr, city_val in candidates:
                    key = (center_name.strip().lower(), cleaned_addr.strip().lower(), city_val.strip().lower())
                    existing_id = existing_map.get(key)
                    if existing_id and existing_id != lead_id:
                        cur.execute("""
                            UPDATE "Leads"
                            SET is_duplicate = TRUE,
                                duplicate_group_id = %s,
                                status = 'ARCHIVED',
                                notes = COALESCE(notes, '') || ' [Hidden duplicate resolved by Migration 020]'
                            WHERE id = %s;
                        """, (str(existing_id), lead_id))
                        hidden_dupes_flagged += 1
                    else:
                        cur.execute("""
                            UPDATE "Leads"
                            SET address = %s
                            WHERE id = %s;
                        """, (cleaned_addr, lead_id))
                        cleaned_addr_count += 1
                        existing_map[key] = lead_id

            conn.commit()
            print(f"  ✓ Cleaned {cleaned_addr_count:,} jammed street addresses and resolved {hidden_dupes_flagged:,} hidden duplicate records.")

            # -------------------------------------------------------------------------
            # 4. Classify Remaining Blank Industry Fields (Single Set-Based Query)
            # -------------------------------------------------------------------------
            cur.execute("""
                UPDATE "Leads"
                SET industry = CASE
                    WHEN center_name ILIKE '%FED:%' OR center_name ILIKE '%Army%' OR center_name ILIKE '%Solicitation%' THEN 'Government & Defense'
                    WHEN capacity IS NOT NULL AND capacity > 0 THEN 'Child Care'
                    WHEN center_name ILIKE '%Lowe%' OR center_name ILIKE '%Tractor%' OR center_name ILIKE '%Truck%' OR center_name ILIKE '%Auto%' OR center_name ILIKE '%Properties%' THEN 'Commercial Retail'
                    ELSE 'Commercial Legacy'
                END
                WHERE industry IS NULL OR trim(industry) = '';
            """)
            blank_remediated = cur.rowcount
            conn.commit()
            print(f"  ✓ Accurately categorized {blank_remediated:,} previously blank industry fields.")

            # -------------------------------------------------------------------------
            # 5. Consolidate Duplicate Facility Pairs (Batch Execution)
            # -------------------------------------------------------------------------
            cur.execute("""
                SELECT lower(trim(center_name)), lower(trim(address)), array_agg(id ORDER BY id ASC)
                FROM "Leads"
                WHERE address IS NOT NULL AND trim(address) != '' AND address != 'Address Pending Audit'
                  AND is_duplicate = FALSE
                GROUP BY lower(trim(center_name)), lower(trim(address))
                HAVING count(*) > 1;
            """)
            duplicate_clusters = cur.fetchall()
            marked_dupes = 0
            sec_updates = []

            for name_key, addr_key, id_list in duplicate_clusters:
                primary_id = id_list[0]
                secondary_ids = id_list[1:]
                for sec_id in secondary_ids:
                    sec_updates.append((str(primary_id), sec_id))
                    marked_dupes += 1

            if sec_updates:
                from psycopg2.extras import execute_batch
                execute_batch(cur, """
                    UPDATE "Leads"
                    SET is_duplicate = TRUE,
                        duplicate_group_id = %s,
                        status = 'ARCHIVED'
                    WHERE id = %s;
                """, sec_updates)

            conn.commit()
            print(f"  ✓ Safely flagged and consolidated {marked_dupes:,} duplicate secondary records across {len(duplicate_clusters)} clusters.")

            # -------------------------------------------------------------------------
            # 6. Standardize Irregular Phone Numbers
            # -------------------------------------------------------------------------
            cur.execute("""
                SELECT id, phone, notes
                FROM "Leads"
                WHERE phone IS NOT NULL AND phone != '' AND phone !~ '^\\(\\d{3}\\)-\\d{3}-\\d{4}$';
            """)
            irregular_phones = cur.fetchall()
            cleaned_phones = 0

            for lead_id, raw_phone, existing_notes in irregular_phones:
                clean_p = raw_phone.strip()
                notes_addition = ""
                new_phone = clean_p

                if clean_p == '0':
                    new_phone = None
                elif 'NO PHONE CALLS' in clean_p.upper():
                    new_phone = None
                    notes_addition = "Notice: Facility states no phone calls accepted."
                elif 'ext.' in clean_p.lower():
                    parts = clean_p.split('ext.')
                    base_p = parts[0].strip()
                    ext_num = parts[1].strip()
                    new_phone = base_p
                    notes_addition = f"Phone Extension: {ext_num}"
                elif re.match(r'^\d{3}-\d{2}-\d{4}$', clean_p):
                    new_phone = None
                    notes_addition = "Irregular number purged during Data Integrity Cleansing."

                updated_notes = (existing_notes or "").strip()
                if notes_addition:
                    updated_notes = f"{updated_notes}\n{notes_addition}".strip()

                cur.execute("""
                    UPDATE "Leads"
                    SET phone = %s, notes = %s
                    WHERE id = %s;
                """, (new_phone, updated_notes if updated_notes else None, lead_id))
                cleaned_phones += 1

            conn.commit()
            print(f"  ✓ Standardized {cleaned_phones:,} irregular phone numbers and preserved extensions in notes.")

        print("  ✓ Migration 020 successfully applied and committed.")
        print("================================================================================\n")
    except Exception as err:
        conn.rollback()
        print(f"  ✗ Migration 020 failed: {err}")
        raise err
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
