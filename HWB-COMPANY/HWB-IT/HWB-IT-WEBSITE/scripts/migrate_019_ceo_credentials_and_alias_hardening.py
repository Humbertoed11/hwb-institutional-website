"""
Migration 019: SigmaFidelity™ CEO Credentials & Identity Alias Hardening
Standard: HWB-QMS-7.6 Database Hardening & Schema Versioning SOP
Authority: Humberto Dominguez (CEO)
Architect: George (Systems Architect & mbB)
"""

import os
import psycopg2
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")


def run_migration(db_url: str = None):
    target_url = db_url or DB_URL
    print("\n=======================================================")
    print("  Applying Migration 019: CEO Credentials & Alias Hardening")
    print("=======================================================")

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor() as cur:
            # 1. Ensure hdominguez has active Executive status and synchronized password hash
            cur.execute("""
                UPDATE "Users"
                SET role = 'Executive',
                    status = 'Active',
                    full_name = 'Humberto Dominguez',
                    email = 'hdominguez@hwbcleaning.com',
                    password_hash = %s
                WHERE LOWER(username) = 'hdominguez';
            """, (generate_password_hash("password11"),))
            print("  ✓ Updated primary CEO account 'hdominguez'.")

            # 2. Synchronize CEO aliases ('humberto', 'humbertoed')
            aliases = [
                ('humberto', 'password11', 'Humberto Dominguez', 'humbertoed@gmail.com', 'Executive'),
                ('humbertoed', 'password11', 'Humberto Dominguez', 'humbertoed@gmail.com', 'Executive'),
            ]

            for uname, pwd, fname, mail, urole in aliases:
                cur.execute('SELECT id FROM "Users" WHERE LOWER(username) = LOWER(%s);', (uname,))
                row = cur.fetchone()
                if not row:
                    cur.execute("""
                        INSERT INTO "Users" (username, password_hash, full_name, email, role, status)
                        VALUES (%s, %s, %s, %s, %s, 'Active');
                    """, (uname, generate_password_hash(pwd), fname, mail, urole))
                    print(f"  ✓ Provisioned CEO alias account '{uname}'.")
                else:
                    cur.execute("""
                        UPDATE "Users"
                        SET password_hash = %s,
                            full_name = %s,
                            email = %s,
                            role = %s,
                            status = 'Active'
                        WHERE id = %s;
                    """, (generate_password_hash(pwd), fname, mail, urole, row[0]))
                    print(f"  ✓ Synchronized CEO alias account '{uname}'.")

        conn.commit()
        print("  ✓ Migration 019 completed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Migration 019 failed: {e}")
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
