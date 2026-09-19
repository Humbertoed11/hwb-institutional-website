import os
import re
import psycopg2

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")

def clean_address_strings():
    print("--- SigmaFidelity: Initiating Address String Sanitization ---")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute('SELECT id, address, city, state, zipcode FROM "Leads" WHERE address IS NOT NULL;')
    rows = cur.fetchall()
    print(f"[CLEAN] Inspecting {len(rows)} lead addresses for appended city/state/zip noise...")

    cleaned_count = 0
    for r in rows:
        lead_id, addr, city, state, zipcode = r
        if not addr or not city: continue
        
        # Regex to strip trailing city + state + zip noise (e.g. 'Frisco Tx- 75034 1002')
        pattern = re.compile(rf'\s+{re.escape(city)}\s+(?:Tx|Texas)(?:-|\s|\b).*$', re.IGNORECASE)
        if pattern.search(addr):
            clean_addr = pattern.sub('', addr).strip()
            if clean_addr and clean_addr != addr:
                cur.execute('UPDATE "Leads" SET address = %s WHERE id = %s;', (clean_addr, lead_id))
                cleaned_count += 1
                if cleaned_count % 1000 == 0:
                    conn.commit()
                    print(f"[CLEAN] Sanitized {cleaned_count} addresses...")

    conn.commit()
    conn.close()
    print(f"[CLEAN SUCCESS] Successfully sanitized {cleaned_count} dirty address strings.")

if __name__ == "__main__":
    clean_address_strings()
