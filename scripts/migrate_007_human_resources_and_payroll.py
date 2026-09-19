"""
Migration 007: Human Resources, Onboarding, Document Vault & Payroll Ledger
Standard: HWB-QMS-7.6 Database Hardening & Schema Versioning SOP
Authority: Humberto Dominguez (CEO)
"""

import os
import sys
import psycopg2

def run_migration(db_url: str):
    print("[MIGRATION] Applying 007_human_resources_and_payroll...")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Employees Table (W-2 & Master Personnel Ledger)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "Employees" (
                    id SERIAL PRIMARY KEY,
                    employee_number VARCHAR(50) UNIQUE NOT NULL,
                    applicant_id INTEGER REFERENCES "JobApplicants"(id) ON DELETE SET NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    email VARCHAR(150),
                    date_of_birth DATE,
                    hire_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    termination_date DATE,
                    employment_status VARCHAR(50) DEFAULT 'Active',
                    employment_type VARCHAR(50) DEFAULT 'W-2 Full-Time',
                    primary_role VARCHAR(100) DEFAULT 'Commercial Cleaning Technician',
                    pay_rate_hourly NUMERIC(10,2) NOT NULL DEFAULT 16.00,
                    overtime_rate_hourly NUMERIC(10,2) DEFAULT 24.00,
                    pay_frequency VARCHAR(50) DEFAULT 'Bi-Weekly',
                    primary_language VARCHAR(50) DEFAULT 'Spanish',
                    emergency_contact_name VARCHAR(150),
                    emergency_contact_phone VARCHAR(50),
                    address_street VARCHAR(255),
                    address_city VARCHAR(100),
                    address_state VARCHAR(50) DEFAULT 'TX',
                    address_zip VARCHAR(20),
                    direct_deposit_bank VARCHAR(100),
                    direct_deposit_routing VARCHAR(50),
                    direct_deposit_account VARCHAR(50),
                    assigned_customer_id INTEGER REFERENCES "Customers"(customer_id) ON DELETE SET NULL,
                    weekly_hours_allocated NUMERIC(5,2) DEFAULT 40.00,
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_employees_status" ON "Employees" (employment_status);
                CREATE INDEX IF NOT EXISTS "idx_employees_role" ON "Employees" (primary_role);
                CREATE INDEX IF NOT EXISTS "idx_employees_number" ON "Employees" (employee_number);
                CREATE INDEX IF NOT EXISTS "idx_employees_phone" ON "Employees" (phone);
            ''')

            # 2. EmployeeDocuments Table (Encrypted PII & Compliance Vault)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "EmployeeDocuments" (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER REFERENCES "Employees"(id) ON DELETE CASCADE,
                    applicant_id INTEGER REFERENCES "JobApplicants"(id) ON DELETE SET NULL,
                    document_type VARCHAR(100) NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(255) NOT NULL,
                    file_size INTEGER,
                    mime_type VARCHAR(100),
                    verification_status VARCHAR(50) DEFAULT 'Verified',
                    expiration_date DATE,
                    verified_by VARCHAR(100) DEFAULT 'Humberto Dominguez',
                    verified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_emp_docs_employee_id" ON "EmployeeDocuments" (employee_id);
                CREATE INDEX IF NOT EXISTS "idx_emp_docs_type" ON "EmployeeDocuments" (document_type);
                CREATE INDEX IF NOT EXISTS "idx_emp_docs_status" ON "EmployeeDocuments" (verification_status);
            ''')

            # 3. PayrollLedger Table (Pay-Period Records & Timesheet Summaries)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "PayrollLedger" (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER REFERENCES "Employees"(id) ON DELETE CASCADE,
                    pay_period_start DATE NOT NULL,
                    pay_period_end DATE NOT NULL,
                    regular_hours NUMERIC(6,2) DEFAULT 0.00,
                    overtime_hours NUMERIC(6,2) DEFAULT 0.00,
                    hourly_rate NUMERIC(10,2) NOT NULL,
                    gross_pay NUMERIC(10,2) NOT NULL,
                    payment_status VARCHAR(50) DEFAULT 'Draft',
                    payment_date DATE,
                    reference_note VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_payroll_employee_id" ON "PayrollLedger" (employee_id);
                CREATE INDEX IF NOT EXISTS "idx_payroll_period" ON "PayrollLedger" (pay_period_start, pay_period_end);
                CREATE INDEX IF NOT EXISTS "idx_payroll_status" ON "PayrollLedger" (payment_status);
            ''')

            # 4. Register in schema_migrations
            cur.execute('''
                INSERT INTO schema_migrations (version, applied_at, description)
                VALUES ('007_human_resources_and_payroll', CURRENT_TIMESTAMP, 'Human Resources master personnel ledger, secure document vault, and payroll timesheet engine')
                ON CONFLICT (version) DO NOTHING;
            ''')

            conn.commit()
            print("✓ [MIGRATION 007 SUCCESS] Employees, EmployeeDocuments, and PayrollLedger tables created.")
    finally:
        conn.close()

if __name__ == '__main__':
    db_url = os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db')
    run_migration(db_url)
