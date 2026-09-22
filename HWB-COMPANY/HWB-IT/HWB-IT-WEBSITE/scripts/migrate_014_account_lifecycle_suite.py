"""
Migration 014: SigmaFidelity™ Institutional Account Lifecycle & Master Dossier Suite
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
    print("  Applying Migration 014: Institutional Account Suite")
    print("=======================================================")

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Add Lifecycle, Contract, Compliance, and Facility columns to Customers
            cur.execute("""
                ALTER TABLE "Customers"
                ADD COLUMN IF NOT EXISTS cleaning_delivery_model VARCHAR(50) DEFAULT 'DIRECT_W2',
                ADD COLUMN IF NOT EXISTS cleanable_sqft INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS monthly_billing_rate NUMERIC(10,2) DEFAULT 0.00,
                ADD COLUMN IF NOT EXISTS overtime_billing_rate NUMERIC(10,2) DEFAULT 0.00,
                ADD COLUMN IF NOT EXISTS accounts_payable_email VARCHAR(150),
                ADD COLUMN IF NOT EXISTS accounts_payable_phone VARCHAR(50),
                ADD COLUMN IF NOT EXISTS tax_exempt BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS tax_exempt_number VARCHAR(100),
                ADD COLUMN IF NOT EXISTS contract_start_date DATE,
                ADD COLUMN IF NOT EXISTS contract_expiration_date DATE,
                ADD COLUMN IF NOT EXISTS escalation_clause_pct NUMERIC(5,2) DEFAULT 0.00,
                ADD COLUMN IF NOT EXISTS coi_expiration_date DATE,
                ADD COLUMN IF NOT EXISTS coi_liability_limit VARCHAR(100) DEFAULT '$1,000,000 / $2,000,000',
                ADD COLUMN IF NOT EXISTS additional_insured_verified BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS sb9_fingerprint_required BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS consumables_agreement VARCHAR(100) DEFAULT 'Contractor Provides All Consumables',
                ADD COLUMN IF NOT EXISTS closet_access_instructions TEXT,
                ADD COLUMN IF NOT EXISTS target_quality_level VARCHAR(100) DEFAULT 'Level 2: Ordinary Tidiness (APPA Standard)',
                ADD COLUMN IF NOT EXISTS termination_date DATE,
                ADD COLUMN IF NOT EXISTS termination_reason VARCHAR(255),
                ADD COLUMN IF NOT EXISTS service_shift_window VARCHAR(100) DEFAULT 'Evening Shift (6:00 PM – 11:00 PM)';
            """)
            print("  ✓ Added institutional lifecycle, contract, COI, and scope columns to 'Customers'.")

            # 2. Performance indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS "idx_customers_status" ON "Customers" (status);
                CREATE INDEX IF NOT EXISTS "idx_customers_delivery_model" ON "Customers" (cleaning_delivery_model);
            """)
            print("  ✓ Created performance indexes on customer status and delivery model.")

            # 3. Seed Bosanna LLC (ID 4) with institutional contract baseline
            cur.execute("""
                UPDATE "Customers"
                SET cleanable_sqft = 120000,
                    monthly_billing_rate = 18500.00,
                    overtime_billing_rate = 35.00,
                    tax_exempt = TRUE,
                    tax_exempt_number = 'TX-COL-75034-EXEMPT',
                    coi_expiration_date = '2027-04-30',
                    coi_liability_limit = '$5,000,000 Umbrella / $2,000,000 Aggregate',
                    additional_insured_verified = TRUE,
                    sb9_fingerprint_required = TRUE,
                    target_quality_level = 'Level 2: Ordinary Tidiness (APPA Standard)',
                    service_shift_window = 'Evening Shift (6:00 PM – 11:00 PM)',
                    consumables_agreement = 'Client Provides Paper/Soap; Contractor Provides Chemicals',
                    closet_access_instructions = 'Security desk sign-in; janitorial keys issued via Lockbox Room 114.'
                WHERE customer_id = 4 AND (cleanable_sqft IS NULL OR cleanable_sqft = 0);
            """)
            print("  ✓ Seeded Bosanna LLC (ACC-004) baseline institutional parameters.")

            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during Migration 014: {e}")
        raise e
    finally:
        conn.close()

    print("=======================================================")
    print("  ✓ Migration 014 Applied Successfully.")
    print("=======================================================\n")


if __name__ == "__main__":
    run_migration(DB_URL)
