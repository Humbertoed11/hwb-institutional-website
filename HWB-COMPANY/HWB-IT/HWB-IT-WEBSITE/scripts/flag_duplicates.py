import os
import psycopg2

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")

def flag_duplicates():
    print("--- SigmaFidelity: Initiating Automated Lead Duplicate Detection ---")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute('UPDATE "Leads" SET is_duplicate = FALSE, duplicate_group_id = NULL;')
    conn.commit()

    cur.execute("""
        SELECT center_name, address, city, COUNT(*)
        FROM "Leads"
        WHERE center_name IS NOT NULL AND TRIM(center_name) != ''
          AND address IS NOT NULL AND TRIM(address) != ''
          AND city IS NOT NULL AND TRIM(city) != ''
        GROUP BY center_name, address, city
        HAVING COUNT(*) > 1;
    """)

    dup_groups = cur.fetchall()
    print(f"[FLAG] Found {len(dup_groups)} unique physical duplicate groups.")

    group_counter = 1
    for name, addr, cty, count in dup_groups:
        group_id = f"DUP-{group_counter:04d}"
        cur.execute("""
            UPDATE "Leads"
            SET is_duplicate = TRUE, duplicate_group_id = %s
            WHERE center_name = %s AND address = %s AND city = %s;
        """, (group_id, name, addr, cty))
        group_counter += 1
        if group_counter % 500 == 0:
            conn.commit()

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM "Leads" WHERE is_duplicate = TRUE;')
    actual_flagged = cur.fetchone()[0]

    conn.close()
    print(f"[FLAG SUCCESS] Flagged {actual_flagged} duplicate rows across {group_counter-1} groups.")

if __name__ == "__main__":
    flag_duplicates()
