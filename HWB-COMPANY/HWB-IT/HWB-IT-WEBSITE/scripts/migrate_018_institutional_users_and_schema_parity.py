"""
Migration 018: SigmaFidelity™ Institutional Users & Database Schema Parity Hardening
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
    print("  Applying Migration 018: Users & Schema Parity Hardening")
    print("=======================================================")

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor() as cur:
            # 1. Users Table Hardening
            cur.execute("""
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS full_name TEXT;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS email TEXT;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'Operator';
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Active';
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS force_pwd_reset BOOLEAN DEFAULT FALSE;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS custom_permissions TEXT;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS telegram_chat_id VARCHAR(50);
                
                UPDATE "Users" SET status = 'Active' WHERE status IS NULL;
                UPDATE "Users" SET role = 'Executive' WHERE username IN ('admin', 'hdominguez') AND (role IS NULL OR role = 'Operator');
            """)
            print("  ✓ Hardened Users table columns and default permissions.")

            # 2. Synchronize Institutional Users
            core_users = [
                ('hdominguez', 'password11', 'Humberto Dominguez', 'hdominguez@hwbcleaning.com', 'Executive'),
                ('admin', 'HWB-Admin-2026!', 'Institutional Administrator', 'admin@hwbcleaning.com', 'Executive'),
                ('ahudgins', 'bosanna2026!', 'Angelica Hudgins', 'ahudgins@bosanna.com', 'Partner_Bosanna'),
                ('sales_field', 'Sales2026!', 'Field Sales Agent', 'sales@hwbcleaning.com', 'Sales'),
                ('Bwiley', 'Sales2026!', 'Bryan Wiley', 'Sales@hwbcleaning.com', 'Sales'),
                ('mrondinella', 'Operator2026!', 'Mirna Rondinella', 'mrondinella@hwbcleaning.com', 'Operator'),
            ]

            for uname, pwd, fname, mail, urole in core_users:
                cur.execute('SELECT id, password_hash, role, status FROM "Users" WHERE LOWER(username) = LOWER(%s);', (uname,))
                row = cur.fetchone()
                if not row:
                    cur.execute("""
                        INSERT INTO "Users" (username, password_hash, full_name, email, role, status)
                        VALUES (%s, %s, %s, %s, %s, 'Active');
                    """, (uname, generate_password_hash(pwd), fname, mail, urole))
                    print(f"  ✓ Provisioned core user '{uname}' ({urole}).")
                else:
                    cur.execute("""
                        UPDATE "Users" 
                        SET full_name = COALESCE(full_name, %s),
                            email = COALESCE(email, %s),
                            role = COALESCE(role, %s),
                            status = 'Active'
                        WHERE id = %s;
                    """, (fname, mail, urole, row[0]))
                    print(f"  ✓ Synchronized profile for existing user '{uname}' ({urole}).")

            # 3. Leads Table Parity
            cur.execute("""
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS is_commercial BOOLEAN DEFAULT TRUE;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS is_dnc BOOLEAN DEFAULT FALSE;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS is_converted BOOLEAN DEFAULT FALSE;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS cleaning_delivery_model VARCHAR(50) DEFAULT 'UNKNOWN';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS commercial_status VARCHAR(50) DEFAULT 'Commercial Hub';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS acquisition_tier VARCHAR(50) DEFAULT 'Unranked';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS ownership_type VARCHAR(50) DEFAULT 'Independent Commercial';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS owner_verification_status VARCHAR(50) DEFAULT 'PENDING_PROOF';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS owner_evidence_citation TEXT;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN DEFAULT FALSE;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS duplicate_group_id VARCHAR(64);
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS umbrella_name VARCHAR(100);
            """)
            print("  ✓ Hardened Leads table parity columns.")

            # 4. Customers Table Parity
            cur.execute("""
                ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS cleaning_delivery_model VARCHAR(50) DEFAULT 'DIRECT_W2';
                ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Active';
            """)
            print("  ✓ Hardened Customers table parity columns.")

            # 5. Record Migration in schema_migrations
            cur.execute("""
                INSERT INTO "schema_migrations" (version, description)
                VALUES ('018_institutional_users_and_schema_parity', 'Institutional Users table hardening, credential sync, and leads parity')
                ON CONFLICT (version) DO NOTHING;
            """)

            conn.commit()
            print("  ✓ Migration 018 committed successfully.\n")
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Migration 018 failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration(DB_URL)
