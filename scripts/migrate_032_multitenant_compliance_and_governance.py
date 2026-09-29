#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 032: Multi-Tenant Compliance Architecture & Governance RLS
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & ARCH-009 Multi-Tenancy
Custodians: George (Systems Architect & mbB) & Humberto Dominguez (CEO)

Objectives:
1. Add multi-tenant partition columns (tenant_id, state_code, application_progress_pct, waiver_eligibility_score) to "GovernmentPrograms".
2. Create "TenantCertificationEvidence" master ledger for white-label document vaulting.
3. Enable PostgreSQL Row-Level Security (RLS) on compliance tables.
4. Record migration in schema_migrations idempotently.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "scripts" else CURRENT_DIR.parent.parent
WEBSITE_DIR = PROJECT_ROOT / "HWB-COMPANY" / "HWB-IT" / "HWB-IT-WEBSITE"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(WEBSITE_DIR / ".env")

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

def run_migration():
    print("[MIGRATION-032] Connecting to PostgreSQL database...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # 1. Enhance GovernmentPrograms with Multi-Tenant SaaS Columns
            print("[MIGRATION-032] Enhancing 'GovernmentPrograms' with multi-tenant partition columns...")
            cur.execute('''
                ALTER TABLE "GovernmentPrograms"
                ADD COLUMN IF NOT EXISTS tenant_id INTEGER NOT NULL DEFAULT 1,
                ADD COLUMN IF NOT EXISTS state_code VARCHAR(2) DEFAULT 'TX',
                ADD COLUMN IF NOT EXISTS application_progress_pct INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS waiver_eligibility_score INTEGER DEFAULT 85,
                ADD COLUMN IF NOT EXISTS is_custom_program BOOLEAN DEFAULT FALSE;
            ''')

            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_govprograms_tenant_prog
                ON "GovernmentPrograms" (tenant_id, program_code);
            ''')

            # 2. Create TenantCertificationEvidence Table for Document Staging
            print("[MIGRATION-032] Creating 'TenantCertificationEvidence' document vault ledger...")
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "TenantCertificationEvidence" (
                    id SERIAL PRIMARY KEY,
                    tenant_id INTEGER NOT NULL DEFAULT 1,
                    program_code VARCHAR(50) NOT NULL,
                    document_name VARCHAR(255) NOT NULL,
                    document_category VARCHAR(100) NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    verification_status VARCHAR(50) DEFAULT 'Pending Review',
                    defect_notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            ''')

            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_cert_evidence_tenant_prog
                ON "TenantCertificationEvidence" (tenant_id, program_code);
            ''')

            # Seed baseline evidence items for HWB (Tenant 1)
            baseline_evidence = [
                (1, "SBA_8A", "2025 Form 1065 Federal Business Tax Return", "Tax Return", "HWB-COMPANY/HWB-LEGAL/SAM-REG/2025_Form1065.pdf", "Verified Compliant", "Filed return verifies commercial revenue runway."),
                (1, "SBA_8A", "HWB Cleaning Services LLC Operating Agreement", "Operating Agreement", "HWB-COMPANY/HWB-LEGAL/HWB-LLC-Operating-Agreement.pdf", "Verified Compliant", "Sovereign 100% executive authority verified for CEO Humberto Dominguez."),
                (1, "TX_HUB", "Texas Secretary of State Certificate of Filing", "Formation", "HWB-COMPANY/HWB-LEGAL/SAM-REG/Texas_Certificate_of_Filing.pdf", "Verified Compliant", "Domestic Texas LLC in active good standing."),
                (1, "NCTRCA_MBE", "Proof of Hispanic / Disadvantaged Heritage", "Identity", "HWB-COMPANY/HWB-LEGAL/CERTIFICATIONS/Humberto_Citizenship_Proof.pdf", "Verified Compliant", "U.S. Citizenship and disadvantaged ownership authenticated.")
            ]

            for item in baseline_evidence:
                cur.execute('''
                    INSERT INTO "TenantCertificationEvidence" (
                        tenant_id, program_code, document_name, document_category, file_path, verification_status, defect_notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                ''', item)

            # 3. Enable Row-Level Security (RLS)
            print("[MIGRATION-032] Hardening PostgreSQL Row-Level Security (RLS)...")
            cur.execute('ALTER TABLE "GovernmentPrograms" ENABLE ROW LEVEL SECURITY;')
            cur.execute('ALTER TABLE "TenantCertificationEvidence" ENABLE ROW LEVEL SECURITY;')

            # Drop old policies if they exist, then recreate
            cur.execute('DROP POLICY IF EXISTS gov_programs_tenant_isolation ON "GovernmentPrograms";')
            cur.execute('''
                CREATE POLICY gov_programs_tenant_isolation ON "GovernmentPrograms"
                FOR ALL
                USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::integer OR tenant_id = 1);
            ''')

            cur.execute('DROP POLICY IF EXISTS cert_evidence_tenant_isolation ON "TenantCertificationEvidence";')
            cur.execute('''
                CREATE POLICY cert_evidence_tenant_isolation ON "TenantCertificationEvidence"
                FOR ALL
                USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::integer OR tenant_id = 1);
            ''')

            # 4. Record migration in schema_migrations
            cur.execute('''
                INSERT INTO schema_migrations (version, description)
                VALUES ('032_multitenant_compliance_and_governance', 'Multi-tenant RLS columns on GovernmentPrograms and TenantCertificationEvidence ledger')
                ON CONFLICT (version) DO NOTHING;
            ''')

            conn.commit()
            print("[MIGRATION-032] SUCCESS: Multi-tenant compliance schema and RLS policies deployed.")

    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION-032] ERROR: Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
