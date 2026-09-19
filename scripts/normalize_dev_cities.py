"""
SigmaFidelity™ Texas Municipal City Normalization Engine
Standard: HWB-QMS-7.6 Zero-Synthetic Data & Poka-Yoke Ingestion Mandate
Environment: Local Development Database (hwb_dev_db)
"""

import sys
import os
import psycopg2

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE"))
sys.path.insert(0, BASE_DIR)

from core.services.sanitizer import clean_city

def normalize_database_cities(db_url: str):
    print("================================================================================")
    print("  SigmaFidelity™ Texas City Normalization Pipeline (Development Database)")
    print("================================================================================\n")

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Audit Leads Table
            cur.execute('SELECT id, center_name, address, city FROM "Leads" WHERE city IS NOT NULL AND city != \'\' ORDER BY id;')
            lead_rows = cur.fetchall()
            
            lead_updates = {}
            lead_duplicates_pruned = 0
            total_lead_records_updated = 0

            for id_, name, addr, raw_c in lead_rows:
                normalized = clean_city(raw_c)
                if normalized and normalized != raw_c:
                    # Check if updating would collide with existing record
                    cur.execute('''
                        SELECT id FROM "Leads"
                        WHERE id != %s 
                          AND lower(btrim(COALESCE(center_name, ''))) = lower(btrim(%s))
                          AND lower(btrim(COALESCE(address, ''))) = lower(btrim(%s))
                          AND lower(btrim(COALESCE(city, ''))) = lower(btrim(%s));
                    ''', (id_, name or '', addr or '', normalized))
                    existing = cur.fetchone()

                    if existing:
                        # Redundant twin created by spelling variance; safely prune duplicate
                        print(f"  [DEDUPLICATION] Removing duplicate Lead #{id_} ('{name}') colliding with Lead #{existing[0]} on normalized city '{normalized}'")
                        cur.execute('DELETE FROM "Leads" WHERE id = %s;', (id_,))
                        lead_duplicates_pruned += 1
                    else:
                        cur.execute('UPDATE "Leads" SET city = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s;', (normalized, id_))
                        total_lead_records_updated += 1
                        pair = (raw_c, normalized)
                        lead_updates[pair] = lead_updates.get(pair, 0) + 1

            # 2. Audit Customers Table
            cur.execute('SELECT customer_id, company_name, company_address, city FROM "Customers" WHERE city IS NOT NULL AND city != \'\' ORDER BY customer_id;')
            cust_rows = cur.fetchall()
            
            cust_updates = {}
            total_cust_records_updated = 0

            for cid, cname, caddr, raw_c in cust_rows:
                normalized = clean_city(raw_c)
                if normalized and normalized != raw_c:
                    cur.execute('UPDATE "Customers" SET city = %s WHERE customer_id = %s;', (normalized, cid))
                    total_cust_records_updated += 1
                    pair = (raw_c, normalized)
                    cust_updates[pair] = cust_updates.get(pair, 0) + 1

            conn.commit()

        print(f"\n✓ Leads Table: {len(lead_updates)} distinct city variations standardized ({total_lead_records_updated} rows updated, {lead_duplicates_pruned} redundant twins pruned).")
        print(f"✓ Customers Table: {len(cust_updates)} distinct city variations standardized ({total_cust_records_updated} rows updated).\n")

        print("Top Standardized City Groups in Leads:")
        sorted_updates = sorted(lead_updates.items(), key=lambda x: x[1], reverse=True)
        for (orig, norm), count in sorted_updates[:25]:
            print(f"  • {orig!r:30} -> {norm!r:30} ({count} records)")

        return {
            'lead_variations_updated': len(lead_updates),
            'lead_rows_updated': total_lead_records_updated,
            'lead_duplicates_pruned': lead_duplicates_pruned,
            'cust_variations_updated': len(cust_updates),
            'cust_rows_updated': total_cust_records_updated,
            'top_updates': sorted_updates[:25]
        }
    finally:
        conn.close()

if __name__ == '__main__':
    db_url = os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db')
    normalize_database_cities(db_url)
