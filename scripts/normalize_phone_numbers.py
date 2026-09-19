#!/usr/bin/env python3
"""
SigmaFidelity™ Database Phone Normalization Migration
Standard: HWB-QMS-11.2
Responsibility: Systems Architect George
Objective: Standardize all phone numbers to (###)-###-#### across Leads, Customers, ConstructionBids, and Contacts.
"""

import os
import re
import sys
import psycopg2

def format_phone_standard(phone: str) -> str:
    if not phone or str(phone).strip() in ('', 'None', 'null', 'N/A', '--'):
        return phone
    phone_str = str(phone).strip()
    ext = ''
    ext_match = re.search(r'(?:ext\.?|x)\s*(\d+)', phone_str, re.IGNORECASE)
    if ext_match:
        ext = f' ext. {ext_match.group(1)}'
        base_phone = phone_str[:ext_match.start()]
    else:
        base_phone = phone_str
        
    digits = re.sub(r'\D', '', base_phone)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
        
    if len(digits) == 10:
        return f'({digits[0:3]})-{digits[3:6]}-{digits[6:10]}{ext}'
    return phone_str

def main():
    db_url = os.environ.get('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db')
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    print("--- SigmaFidelity: Initiating Phone Normalization ---")

    # 1. Normalize Leads table
    cur.execute('SELECT id, phone FROM "Leads" WHERE phone IS NOT NULL AND phone != \'\';')
    leads_to_update = []
    for lid, p in cur.fetchall():
        np = format_phone_standard(p)
        if np != p:
            leads_to_update.append((np, lid))
    
    if leads_to_update:
        print(f"Normalizing {len(leads_to_update)} Leads phone numbers...")
        cur.executemany('UPDATE "Leads" SET phone = %s WHERE id = %s;', leads_to_update)
        conn.commit()
        print(f"[SUCCESS] Updated {len(leads_to_update)} records in Leads.")
    else:
        print("[INFO] Leads already normalized.")

    # 2. Normalize Customers table
    cur.execute('SELECT customer_id, phone FROM "Customers" WHERE phone IS NOT NULL AND phone != \'\';')
    cust_to_update = []
    for cid, p in cur.fetchall():
        np = format_phone_standard(p)
        if np != p:
            cust_to_update.append((np, cid))

    if cust_to_update:
        print(f"Normalizing {len(cust_to_update)} Customers phone numbers...")
        cur.executemany('UPDATE "Customers" SET phone = %s WHERE customer_id = %s;', cust_to_update)
        conn.commit()
        print(f"[SUCCESS] Updated {len(cust_to_update)} records in Customers.")
    else:
        print("[INFO] Customers already normalized.")

    # 3. Normalize ConstructionBids table
    cur.execute('SELECT id, estimator_phone FROM "ConstructionBids" WHERE estimator_phone IS NOT NULL AND estimator_phone != \'\';')
    bids_to_update = []
    for bid, p in cur.fetchall():
        np = format_phone_standard(p)
        if np != p:
            bids_to_update.append((np, bid))

    if bids_to_update:
        print(f"Normalizing {len(bids_to_update)} ConstructionBids phone numbers...")
        cur.executemany('UPDATE "ConstructionBids" SET estimator_phone = %s WHERE id = %s;', bids_to_update)
        conn.commit()
        print(f"[SUCCESS] Updated {len(bids_to_update)} records in ConstructionBids.")
    else:
        print("[INFO] ConstructionBids already normalized.")

    # 4. Normalize Contacts table
    cur.execute('SELECT contact_id, phone FROM "Contacts" WHERE phone IS NOT NULL AND phone != \'\';')
    contacts_to_update = []
    for cid, p in cur.fetchall():
        np = format_phone_standard(p)
        if np != p:
            contacts_to_update.append((np, cid))

    if contacts_to_update:
        print(f"Normalizing {len(contacts_to_update)} Contacts phone numbers...")
        cur.executemany('UPDATE "Contacts" SET phone = %s WHERE contact_id = %s;', contacts_to_update)
        conn.commit()
        print(f"[SUCCESS] Updated {len(contacts_to_update)} records in Contacts.")
    else:
        print("[INFO] Contacts already normalized.")

    conn.close()
    print("--- Phone Normalization Complete ---")

if __name__ == '__main__':
    main()
