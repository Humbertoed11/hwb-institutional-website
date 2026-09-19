import os
import psycopg2

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")

def auto_deduplicate():
    print("--- SigmaFidelity: Initiating Automated Smart Deduplication Engine ---")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Query all duplicate groups
    cur.execute("""
        SELECT duplicate_group_id, ARRAY_AGG(id ORDER BY id ASC) as lead_ids
        FROM "Leads"
        WHERE is_duplicate = TRUE AND duplicate_group_id IS NOT NULL
        GROUP BY duplicate_group_id;
    """)
    groups = cur.fetchall()
    print(f"[AUTO DEDUP] Processing {len(groups)} unique duplicate groups...")

    merged_groups = 0
    deleted_rows = 0

    for group_id, lead_ids in groups:
        if len(lead_ids) <= 1:
            continue

        primary_id = lead_ids[0]
        secondary_ids = lead_ids[1:]

        for sec_id in secondary_ids:
            # Reassign touchpoint logs
            cur.execute("""
                UPDATE "GlobalActivities"
                SET parent_id = %s
                WHERE parent_id = %s AND parent_type = 'Lead';
            """, (primary_id, sec_id))

            # Fetch data to enrich primary
            cur.execute('SELECT * FROM "Leads" WHERE id = %s;', (sec_id,))
            sec_row = cur.fetchone()
            cur.execute('SELECT * FROM "Leads" WHERE id = %s;', (primary_id,))
            pri_row = cur.fetchone()

            if pri_row and sec_row:
                colnames = [desc[0] for desc in cur.description]
                pri = dict(zip(colnames, pri_row))
                sec = dict(zip(colnames, sec_row))

                updates = {}
                for field in ['phone', 'email', 'director', 'decision_maker', 'job_title', 'sqf', 'capacity', 'estimated_annual_value', 'lead_source', 'notes', 'county', 'zipcode']:
                    if field in pri and field in sec:
                        pri_val = pri[field]
                        sec_val = sec[field]
                        if (pri_val is None or str(pri_val).strip() in ['', 'None', '--']) and (sec_val is not None and str(sec_val).strip() not in ['', 'None', '--']):
                            updates[field] = sec_val

                if updates:
                    set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
                    cur.execute(f'UPDATE "Leads" SET {set_clause} WHERE id = %s;', list(updates.values()) + [primary_id])

            # Delete secondary record
            cur.execute('DELETE FROM "Leads" WHERE id = %s;', (sec_id,))
            deleted_rows += 1

        # Clear duplicate flag on primary
        cur.execute('UPDATE "Leads" SET is_duplicate = FALSE, duplicate_group_id = NULL WHERE id = %s;', (primary_id,))
        merged_groups += 1

        if merged_groups % 500 == 0:
            conn.commit()
            print(f"[AUTO DEDUP] Merged {merged_groups} groups, removed {deleted_rows} redundant rows...")

    conn.commit()

    # Verify remaining duplicates
    cur.execute('SELECT COUNT(*) FROM "Leads" WHERE is_duplicate = TRUE;')
    rem_dups = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM "Leads";')
    total_leads = cur.fetchone()[0]

    # Install Poka-Yoke Unique Index
    try:
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_unique_location 
            ON "Leads" (LOWER(TRIM(center_name)), LOWER(TRIM(address)), LOWER(TRIM(city)));
        """)
        conn.commit()
        print("[POKA-YOKE] Installed composite unique index idx_leads_unique_location.")
    except Exception as e:
        conn.rollback()
        print(f"[POKA-YOKE WARNING] Unique index creation skipped or encountered duplicates: {e}")

    conn.close()
    print(f"[AUTO DEDUP SUCCESS] Merged {merged_groups} groups. Deleted {deleted_rows} redundant rows. Remaining total leads: {total_leads}.")

if __name__ == "__main__":
    auto_deduplicate()
