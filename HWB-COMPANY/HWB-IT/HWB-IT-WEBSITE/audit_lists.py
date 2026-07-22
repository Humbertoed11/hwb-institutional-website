import psycopg2, os, re

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=== SIGMAFIDELITY SYSTEM DROPDOWN AUDIT ===")

db_values = {}
fields = ["status", "priority_level", "facility_type", "traffic_cycle", "service_interest", "lead_source"]
for field in fields:
    try:
        cur.execute(f'SELECT DISTINCT {field} FROM "Leads" WHERE {field} IS NOT NULL;')
        db_values[field] = [r[0] for r in cur.fetchall()]
    except Exception as e:
        print(f"Error querying {field}:", e)
        conn.rollback()

for k, v in db_values.items():
    print(f"  • DB [{k}]: {v}")

with open("templates/backoffice_operations.html", "r", encoding="utf-8") as f:
    html = f.read()

pattern = re.compile(r'<select[^>]*name=["\']([^"\']+)["\'][^>]*>(.*?)</select>', re.DOTALL)
matches = pattern.findall(html)

print(f"\nFound {len(matches)} Select Lists in backoffice_operations.html:")
for sel_name, content in matches:
    option_vals = re.findall(r'value=["\']([^"\']*)["\']', content)
    print(f"\n📋 Dropdown [name=\"{sel_name}\"] ({len(option_vals)} options): {option_vals}")
    db_list = db_values.get(sel_name, [])
    if db_list:
        missing = [v for v in db_list if v not in option_vals]
        if missing:
            print(f"   ⚠️ DISCREPANCY: DB values missing from HTML dropdown: {missing}")
        else:
            print(f"   ✅ ALIGNED with Database.")
