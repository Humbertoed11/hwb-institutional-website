"""
Migration 023: SigmaFidelity™ Field Sales Desk Decoupling & Sales Credentials Parity
Standard: HWB-QMS-7.6 Enterprise Architecture Standards
Authority: Humberto Dominguez (CEO) - Approved 09/22/2026
Architect: George (Systems Architect & mbB)
"""

import os
import json
import psycopg2
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

def run_migration(db_url: str = None):
    target_url = db_url or DB_URL
    print("\n=======================================================", flush=True)
    print("  Applying Migration 023: Sales Desk & Credentials Parity", flush=True)
    print("=======================================================", flush=True)

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor() as cur:
            # 1. Synchronize credentials and permissions for sales accounts
            sales_accounts = [
                (
                    'sales_field',
                    'Field Sales Representative',
                    'sales@hwbcleaning.com',
                    'Sales',
                    'Active',
                    json.dumps({'magic_token': 'hwb-sales-desk-2026', 'can_access_sales_desk': True})
                ),
                (
                    'Bwiley',
                    'Brian Wiley',
                    'bwiley@hwbcleaning.com',
                    'Sales',
                    'Active',
                    json.dumps({'magic_token': 'hwb-bwiley-2026', 'can_access_sales_desk': True})
                )
            ]

            pwd_hash = generate_password_hash("password11")

            for uname, fname, email, role, status, perms in sales_accounts:
                cur.execute('SELECT id FROM "Users" WHERE LOWER(username) = LOWER(%s);', (uname,))
                row = cur.fetchone()
                if not row:
                    cur.execute("""
                        INSERT INTO "Users" (username, password_hash, full_name, email, role, status, custom_permissions)
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb);
                    """, (uname, pwd_hash, fname, email, role, status, perms))
                    print(f"  ✓ Provisioned Sales account '{uname}'.", flush=True)
                else:
                    cur.execute("""
                        UPDATE "Users"
                        SET password_hash = %s,
                            full_name = %s,
                            email = %s,
                            role = %s,
                            status = %s,
                            custom_permissions = %s::jsonb
                        WHERE id = %s;
                    """, (pwd_hash, fname, email, role, status, perms, row[0]))
                    print(f"  ✓ Synchronized Sales account '{uname}'.", flush=True)

            # 2. Ensure RolePermissions contains sales_desk module for relevant roles
            role_perms = [
                ('Sales', 'sales_desk', True, True, False),
                ('Executive', 'sales_desk', True, True, True),
                ('Admin', 'sales_desk', True, True, True),
                ('Manager', 'sales_desk', True, True, False)
            ]

            for role, module, cv, ce, cd in role_perms:
                cur.execute("""
                    INSERT INTO "RolePermissions" (role, module, can_view, can_edit, can_delete)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (role, module, cv, ce, cd))

            conn.commit()
            print("  ✓ Migration 023 successfully applied and committed.", flush=True)

    except Exception as e:
        conn.rollback()
        print(f"  ✗ Migration 023 failed: {e}", flush=True)
        raise e
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()
