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

            # 3. Ensure Gonzalo Bolanos is onboarded into Employees as HWB-EMP-1002 if not already present
            cur.execute('SELECT id FROM "Employees" WHERE phone = %s OR employee_number = %s;', ('(214)-566-9999', 'HWB-EMP-1002'))
            existing_gonzalo = cur.fetchone()
            if not existing_gonzalo:
                cur.execute("""
                    INSERT INTO "Employees" (
                        employee_number, applicant_id, first_name, last_name, phone, email,
                        hire_date, employment_status, employment_type, primary_role,
                        pay_rate_hourly, overtime_rate_hourly, pay_frequency, primary_language,
                        address_city, address_state, assigned_customer_id, weekly_hours_allocated,
                        badge_status, state_id_number, state_id_expiration, dps_clearance_date, notes
                    ) VALUES (
                        'HWB-EMP-1002', 9, 'Gonzalo', 'Bolanos', '(214)-566-9999', 'gbolanos@gmail.com',
                        CURRENT_DATE, 'Active', 'W-2 Full-Time', 'Commercial Cleaning Technician',
                        18.00, 27.00, 'Bi-Weekly', 'English',
                        'Dallas', 'TX', 4, 40.00,
                        'Active', 'TX-32151555', '2026-10-31', '2026-09-20',
                        'TIPS #260102 Prime Dispatch Technician for Collin College Frisco Campus. Badge ID: BOS-2026-9566.'
                    );
                """)
                print("  ✓ Onboarded Gonzalo Bolanos (HWB-EMP-1002) into Employees with DPS FACT clearance.")
            else:
                print("  ✓ Gonzalo Bolanos already present in Employees.")

            # 4. Synchronize Work Order #2 (Bosanna LLC Collin College Frisco) with Carlos Mendoza (ID 2)
            cur.execute("""
                UPDATE "WorkOrders"
                SET assigned_technician_id = COALESCE(assigned_technician_id, 2),
                    crew_lead_id = COALESCE(crew_lead_id, 2),
                    shift_window = 'Evening Shift (6:00 PM – 11:00 PM)',
                    service_type = 'Routine Nightly Custodial',
                    dock_ingress_instructions = 'Dock Ingress: Access loading bay via 9700 Wade Blvd, Frisco, TX 75035. Must wear Bosanna / TIPS photo ID badge at all times.',
                    security_access_code = 'KEY-FOB-BAY-04'
                WHERE work_order_id = 2;
            """)
            print("  ✓ Updated Work Order #2 with dispatch metadata and assigned technician Carlos Mendoza.")

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
