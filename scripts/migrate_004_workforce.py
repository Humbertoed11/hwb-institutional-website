"""
Migration 004: Workforce & Subcontractor Network Schema
Standard: HWB-QMS-7.6 Database Hardening & Schema Versioning SOP
"""

import os
import sys
import psycopg2

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE"))
sys.path.insert(0, BASE_DIR)

def run_migration(db_url: str):
    print("[MIGRATION] Applying 004_workforce_and_subcontractors...")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. JobApplicants Table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "JobApplicants" (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(150) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    email VARCHAR(150),
                    city VARCHAR(100),
                    state VARCHAR(50) DEFAULT 'TX',
                    desired_role VARCHAR(100) DEFAULT 'Commercial Cleaning Technician',
                    desired_shift VARCHAR(50) DEFAULT 'Night',
                    experience_level VARCHAR(50) DEFAULT '1-2 Years',
                    has_transportation BOOLEAN DEFAULT TRUE,
                    authorized_to_work_us BOOLEAN DEFAULT TRUE,
                    preferred_language VARCHAR(50) DEFAULT 'English',
                    status VARCHAR(50) DEFAULT 'New',
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_job_applicants_status" ON "JobApplicants" (status);
                CREATE INDEX IF NOT EXISTS "idx_job_applicants_city" ON "JobApplicants" (city);
                CREATE INDEX IF NOT EXISTS "idx_job_applicants_created_at" ON "JobApplicants" (created_at DESC);
            ''')

            # 2. SubcontractorPartners Table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "SubcontractorPartners" (
                    id SERIAL PRIMARY KEY,
                    company_name VARCHAR(255) NOT NULL,
                    ein_or_ssn VARCHAR(50),
                    contact_name VARCHAR(150) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    email VARCHAR(150),
                    city VARCHAR(100),
                    state VARCHAR(50) DEFAULT 'TX',
                    coverage_counties TEXT,
                    crew_size INTEGER DEFAULT 2,
                    specialties TEXT,
                    coi_file_url VARCHAR(255),
                    w9_file_url VARCHAR(255),
                    coi_expiration_date DATE,
                    coi_status VARCHAR(50) DEFAULT 'Pending',
                    w9_status VARCHAR(50) DEFAULT 'Pending',
                    dwc83_signed BOOLEAN DEFAULT FALSE,
                    hourly_rate_range VARCHAR(50),
                    rating NUMERIC(2,1) DEFAULT 5.0,
                    status VARCHAR(50) DEFAULT 'Vetting',
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_subcontractors_status" ON "SubcontractorPartners" (status);
                CREATE INDEX IF NOT EXISTS "idx_subcontractors_city" ON "SubcontractorPartners" (city);
                CREATE INDEX IF NOT EXISTS "idx_subcontractors_coi_status" ON "SubcontractorPartners" (coi_status);
            ''')

            # 3. Register in schema_migrations
            cur.execute('''
                INSERT INTO schema_migrations (version, applied_at, description)
                VALUES ('004_workforce_and_subcontractors', CURRENT_TIMESTAMP, 'Job applicants and 1099 subcontractor partner tables with document tracking')
                ON CONFLICT (version) DO NOTHING;
            ''')

            conn.commit()
            print("✓ [MIGRATION 004 SUCCESS] JobApplicants and SubcontractorPartners tables created and indexed.")
    finally:
        conn.close()

if __name__ == '__main__':
    db_url = os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db')
    run_migration(db_url)
