import os
import re
import psycopg2

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")

def normalize_phone(phone_str):
    if not phone_str: return None
    ext = ''
    phone_clean = str(phone_str).strip()
    ext_match = re.search(r'(?:ext|x|ext\.)\s*(\d+)', phone_clean, re.IGNORECASE)
    if ext_match:
        ext = f' ext. {ext_match.group(1)}'
        phone_clean = phone_clean[:ext_match.start()].strip()
    digits = re.sub(r'\D', '', phone_clean)
    if digits.startswith('1') and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f'({digits[:3]}) {digits[3:6]}-{digits[6:]}{ext}'
    elif len(digits) > 10:
        return f'({digits[:3]}) {digits[3:6]}-{digits[6:10]}{ext}'
    else:
        return phone_clean if phone_clean else None

def normalize_address(address_str):
    if not address_str: return None
    addr = str(address_str).strip().strip('"').strip("'")
    addr = re.sub(r'\s+', ' ', addr)
    words = addr.split(' ')
    norm_words = []
    abbrevs = {
        'RD': 'Rd', 'RD.': 'Rd', 'ROAD': 'Rd',
        'ST': 'St', 'ST.': 'St', 'STREET': 'St',
        'BLVD': 'Blvd', 'BLVD.': 'Blvd', 'BOULEVARD': 'Blvd',
        'DR': 'Dr', 'DR.': 'Dr', 'DRIVE': 'Dr',
        'AVE': 'Ave', 'AVE.': 'Ave', 'AVENUE': 'Ave',
        'HWY': 'Hwy', 'HWY.': 'Hwy', 'HIGHWAY': 'Hwy',
        'EXPY': 'Expy', 'EXPY.': 'Expy', 'EXPRESSWAY': 'Expy',
        'PKWY': 'Pkwy', 'PKWY.': 'Pkwy', 'PARKWAY': 'Pkwy',
        'LN': 'Ln', 'LN.': 'Ln', 'LANE': 'Ln',
        'CT': 'Ct', 'CT.': 'Ct', 'COURT': 'Ct',
        'STE': 'Ste', 'STE.': 'Ste', 'SUITE': 'Ste',
        'APT': 'Apt', 'APT.': 'Apt', 'UNIT': 'Unit',
        'N': 'N', 'S': 'S', 'E': 'E', 'W': 'W',
        'NE': 'NE', 'NW': 'NW', 'SE': 'SE', 'SW': 'SW'
    }
    for w in words:
        w_upper = w.upper()
        if w_upper in abbrevs:
            norm_words.append(abbrevs[w_upper])
        elif len(w) > 1 and w[0].isalpha():
            norm_words.append(w.capitalize())
        else:
            norm_words.append(w)
    return ' '.join(norm_words)

def normalize_title_case(name_str):
    if not name_str: return None
    val = str(name_str).strip().strip('"').strip("'")
    val = re.sub(r'\s+', ' ', val)
    if not val or val.lower() in ['none', 'null', 'unknown', 'n/a', '--']:
        return None
    return val.title()

def run_normalization():
    print("--- SigmaFidelity: Initiating Lead Field Normalization ---")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    cur.execute('SELECT id, phone, address, city, director, county FROM "Leads";')
    rows = cur.fetchall()
    print(f"[NORM] Normalizing {len(rows)} lead records...")
    
    updated_count = 0
    for r in rows:
        lead_id, phone, address, city, director, county = r
        n_phone = normalize_phone(phone)
        n_addr = normalize_address(address)
        n_city = normalize_title_case(city)
        n_dir = normalize_title_case(director)
        n_county = normalize_title_case(county)
        
        if (n_phone != phone) or (n_addr != address) or (n_city != city) or (n_dir != director) or (n_county != county):
            cur.execute("""
                UPDATE "Leads"
                SET phone = %s, address = %s, city = %s, director = %s, county = %s
                WHERE id = %s;
            """, (n_phone, n_addr, n_city, n_dir, n_county, lead_id))
            updated_count += 1
            if updated_count % 2000 == 0:
                conn.commit()
                print(f"[NORM] Processed {updated_count} updates...")
                
    conn.commit()
    conn.close()
    print(f"[NORM SUCCESS] Successfully normalized {updated_count} lead records.")

if __name__ == "__main__":
    run_normalization()
