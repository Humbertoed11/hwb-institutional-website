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
            # 1. Correct Contradicted Industry on Non-Childcare Legacy Records
            # -------------------------------------------------------------------------
            cur.execute("""
                UPDATE "Leads"
                SET industry = 'Commercial Legacy'
                WHERE commercial_status = 'Non-Childcare Legacy'
                  AND (industry = 'Child Care' OR industry IS NULL OR trim(industry) = '');
            """)
            fixed_ind_count = cur.rowcount
            print(f"  ✓ Corrected industry to 'Commercial Legacy' on {fixed_ind_count:,} legacy commercial records.")

            # -------------------------------------------------------------------------
            # 2. Correct Contradicted Facility Type on Non-Childcare Legacy Records
            # -------------------------------------------------------------------------
            cur.execute("""
                UPDATE "Leads"
                SET facility_type = 'Commercial Property'
                WHERE commercial_status = 'Non-Childcare Legacy'
                  AND (facility_type = 'Child Care Center' OR facility_type IS NULL OR trim(facility_type) = '');
            """)
            fixed_fac_count = cur.rowcount
            print(f"  ✓ Corrected facility_type to 'Commercial Property' on {fixed_fac_count:,} legacy commercial records.")

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

            for lead_id, center_name, raw_addr, city_val in jammed_rows:
                cleaned_addr = clean_jammed_address(raw_addr, city_val)
                if cleaned_addr and cleaned_addr != raw_addr:
                    # Check if a clean record already exists at this location
                    cur.execute("""
                        SELECT id FROM "Leads"
                        WHERE lower(trim(center_name)) = lower(trim(%s))
                          AND lower(trim(address)) = lower(trim(%s))
                          AND lower(trim(city)) = lower(trim(%s))
                          AND id != %s;
                    """, (center_name, cleaned_addr, city_val, lead_id))
                    match = cur.fetchone()
                    if match:
                        # Existing clean record exists - mark dirty row as duplicate
                        cur.execute("""
                            UPDATE "Leads"
                            SET is_duplicate = TRUE,
                                duplicate_group_id = %s,
                                status = 'ARCHIVED',
                                notes = COALESCE(notes, '') || ' [Hidden duplicate resolved by Migration 020]'
                            WHERE id = %s;
                        """, (str(match[0]), lead_id))
                        hidden_dupes_flagged += 1
                    else:
                        # No duplicate exists - safely update address
                        cur.execute("""
                            UPDATE "Leads"
                            SET address = %s
                            WHERE id = %s;
                        """, (cleaned_addr, lead_id))
                        cleaned_addr_count += 1

            print(f"  ✓ Cleaned {cleaned_addr_count:,} jammed street addresses and resolved {hidden_dupes_flagged:,} hidden duplicate records.")

            # -------------------------------------------------------------------------
            # 4. Classify Remaining Blank Industry Fields
            # -------------------------------------------------------------------------
            cur.execute("""
                SELECT id, center_name, commercial_status, capacity
                FROM "Leads"
                WHERE industry IS NULL OR trim(industry) = '';
            """)
            blank_rows = cur.fetchall()
            blank_remediated = 0

            for lead_id, center_name, comm_status, capacity in blank_rows:
                c_name = center_name or ""
                new_ind = 'Commercial Legacy'
                if 'FED:' in c_name or 'Army' in c_name or 'Solicitation' in c_name:
                    new_ind = 'Government & Defense'
                elif capacity and capacity > 0:
                    new_ind = 'Child Care'
                elif any(k in c_name for k in ['Lowe', 'Tractor', 'Truck', 'Auto', 'Properties']):
                    new_ind = 'Commercial Retail'

                cur.execute("""
                    UPDATE "Leads"
                    SET industry = %s
                    WHERE id = %s;
                """, (new_ind, lead_id))
                blank_remediated += 1

            print(f"  ✓ Accurately categorized {blank_remediated:,} previously blank industry fields.")

            # -------------------------------------------------------------------------
            # 5. Consolidate Duplicate Facility Pairs
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

            for name_key, addr_key, id_list in duplicate_clusters:
                primary_id = id_list[0]
                secondary_ids = id_list[1:]
                for sec_id in secondary_ids:
                    cur.execute("""
                        UPDATE "Leads"
                        SET is_duplicate = TRUE,
                            duplicate_group_id = %s,
                            status = 'ARCHIVED'
                        WHERE id = %s;
                    """, (str(primary_id), sec_id))
                    marked_dupes += 1

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
                    # Social or EIN in phone field - remove for privacy
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

            print(f"  ✓ Standardized {cleaned_phones:,} irregular phone numbers and preserved extensions in notes.")

        conn.commit()
        print("================================================================================")
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
