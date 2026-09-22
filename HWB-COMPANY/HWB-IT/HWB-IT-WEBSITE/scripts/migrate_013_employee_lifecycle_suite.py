"""
Migration 013: SigmaFidelity™ Employee Lifecycle & Compliance Dossier Suite
Standard: HWB-QMS-7.6 Database Hardening & Schema Versioning SOP
Authority: Humberto Dominguez (CEO)
Architect: George (Systems Architect & mbB)
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")


def run_migration(db_url: str):
    print("\n=======================================================")
    print("  Applying Migration 013: Employee Lifecycle Suite")
    print("=======================================================")

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Add Lifecycle, W-4, and Compliance columns to Employees
            cur.execute("""
                ALTER TABLE "Employees"
                ADD COLUMN IF NOT EXISTS w4_filing_status VARCHAR(50) DEFAULT 'Single',
                ADD COLUMN IF NOT EXISTS w4_step2_multiple_jobs BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS w4_step3_dependents NUMERIC(10,2) DEFAULT 0.00,
                ADD COLUMN IF NOT EXISTS w4_step4c_extra_withholding NUMERIC(10,2) DEFAULT 0.00,
                ADD COLUMN IF NOT EXISTS pto_start_date DATE,
                ADD COLUMN IF NOT EXISTS pto_end_date DATE,
                ADD COLUMN IF NOT EXISTS termination_reason VARCHAR(255),
                ADD COLUMN IF NOT EXISTS eligible_for_rehire BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS badge_status VARCHAR(50) DEFAULT 'Active',
                ADD COLUMN IF NOT EXISTS state_id_number VARCHAR(100),
                ADD COLUMN IF NOT EXISTS state_id_expiration DATE,
                ADD COLUMN IF NOT EXISTS dps_clearance_date DATE,
                ADD COLUMN IF NOT EXISTS i9_verification_date DATE;
            """)
            print("  ✓ Added lifecycle, W-4, PTO, and compliance columns to 'Employees'.")

            # 2. Add Index on badge_status and employment_status for fast security lookups
            cur.execute("""
                CREATE INDEX IF NOT EXISTS "idx_employees_status" ON "Employees" (employment_status);
                CREATE INDEX IF NOT EXISTS "idx_employees_badge_status" ON "Employees" (badge_status);
            """)
            print("  ✓ Created performance indexes on employment and badge statuses.")

            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during Migration 013: {e}")
        raise e
    finally:
        conn.close()

    print("=======================================================")
    print("  ✓ Migration 013 Applied Successfully.")
    print("=======================================================\n")


if __name__ == "__main__":
    run_migration(DB_URL)
