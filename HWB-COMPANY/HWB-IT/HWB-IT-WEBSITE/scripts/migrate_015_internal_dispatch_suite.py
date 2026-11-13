"""
Migration 015: SigmaFidelity™ Internal Work Order Dispatch & Execution Suite
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
    print("  Applying Migration 015: Internal Dispatch Suite")
    print("=======================================================")

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Add Dispatch, Shift, Checklist, and Execution columns to WorkOrders
            cur.execute("""
                ALTER TABLE "WorkOrders"
                ADD COLUMN IF NOT EXISTS shift_window VARCHAR(100) DEFAULT 'Evening Shift (6:00 PM – 11:00 PM)',
                ADD COLUMN IF NOT EXISTS service_type VARCHAR(100) DEFAULT 'Routine Nightly Custodial',
                ADD COLUMN IF NOT EXISTS assigned_technician_id INTEGER REFERENCES "Employees"(id) ON DELETE SET NULL,
                ADD COLUMN IF NOT EXISTS quality_score NUMERIC(5,2),
                ADD COLUMN IF NOT EXISTS completion_signature TEXT,
                ADD COLUMN IF NOT EXISTS supervisor_signoff TEXT,
                ADD COLUMN IF NOT EXISTS checklist_progress JSONB DEFAULT '[]'::jsonb,
                ADD COLUMN IF NOT EXISTS dock_ingress_instructions TEXT,
                ADD COLUMN IF NOT EXISTS security_access_code VARCHAR(100);
            """)
            print("  ✓ Added dispatch columns to 'WorkOrders'.")

            # 2. Add performance indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS "idx_workorders_assigned_tech" ON "WorkOrders"(assigned_technician_id);
                CREATE INDEX IF NOT EXISTS "idx_workorders_scheduled_date" ON "WorkOrders"(scheduled_date);
                CREATE INDEX IF NOT EXISTS "idx_workorders_status" ON "WorkOrders"(status);
            """)
            print("  ✓ Created performance indexes on WorkOrders.")
            # BUG-180 Empirical Data Integrity Gate: Synthetic employee/work-order seed rows removed.

            conn.commit()
            print("  ✓ Migration 015 completed successfully!\n")
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Migration 015 failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration(DB_URL)
