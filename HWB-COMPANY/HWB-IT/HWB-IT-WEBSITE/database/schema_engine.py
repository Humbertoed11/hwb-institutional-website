"""
SigmaFidelity™ Schema Migration & Database Engine
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Peter (Recovery Specialist)
"""

import os
import sys
import importlib
from typing import Any, Optional

def apply_system_migrations(conn: Any, db_url: Optional[str] = None) -> None:
    """
    Executes idempotent, version-controlled schema migrations for PostgreSQL.
    Tracks applied migrations in the 'schema_migrations' table.
    """
    try:
        with conn.cursor() as cur:
            # 1. Version tracking table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "schema_migrations" (
                    version VARCHAR(100) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                );
            """)
            conn.commit()

            # Retrieve applied migrations
            cur.execute("SELECT version FROM schema_migrations;")
            applied = {row[0] for row in cur.fetchall()}

            # --- Migration 001: Core Table Hardening & Columns ---
            if "001_core_table_hardening" not in applied:
                print("[MIGRATION] Applying 001_core_table_hardening...", flush=True)
                # Services Table
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS traffic_cycle TEXT;')
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS frequency TEXT;')
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS notes TEXT;')
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS status TEXT DEFAULT \'Active\';')

                # Customers Table
                cur.execute('ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS billing_address TEXT;')
                cur.execute('ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS contract_period TEXT;')

                # Leads Table
                cur.execute('ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS is_dnc BOOLEAN DEFAULT FALSE;')

                # GlobalActivities Table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS "GlobalActivities" (
                        id SERIAL PRIMARY KEY,
                        parent_id INTEGER NOT NULL,
                        parent_type TEXT NOT NULL,
                        activity_type TEXT NOT NULL,
                        description TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                ''')

                # SigmaInteractionLog Table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS "SigmaInteractionLog" (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_prompt TEXT,
                        agent_explanation TEXT,
                        tools_used JSONB,
                        status VARCHAR(50)
                    );
                ''')

                # RolePermissions Table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS "RolePermissions" (
                        id SERIAL PRIMARY KEY,
                        role TEXT NOT NULL,
                        module TEXT NOT NULL,
                        can_view BOOLEAN DEFAULT FALSE,
                        can_edit BOOLEAN DEFAULT FALSE,
                        can_delete BOOLEAN DEFAULT FALSE
                    );
                ''')

                cur.execute("""
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('001_core_table_hardening', 'Core operational columns and telemetry tables');
                """)
                conn.commit()
                print("[MIGRATION] 001_core_table_hardening successfully applied.", flush=True)

            # --- Migration 002: Test Lead Pruning & Data Cleanup ---
            if "002_test_data_pruning" not in applied:
                print("[MIGRATION] Applying 002_test_data_pruning...", flush=True)
                cur.execute('DELETE FROM "GlobalActivities" WHERE parent_id = 44518 AND parent_type = \'Lead\';')
                cur.execute('''
                    DELETE FROM "GlobalActivities" 
                    WHERE parent_id IN (SELECT id FROM "Leads" WHERE center_name ILIKE '%Test Lead%' OR lead_source = 'Executive Test System')
                      AND parent_type = 'Lead';
                ''')
                cur.execute('DELETE FROM "Leads" WHERE id = 44518 OR center_name ILIKE \'%DFW6%\' OR center_name ILIKE \'%Test Lead%\' OR lead_source = \'Executive Test System\';')

                cur.execute("""
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('002_test_data_pruning', 'One-time pruning of test lead 44518 and DFW6 placeholders');
                """)
                conn.commit()
                print("[MIGRATION] 002_test_data_pruning successfully applied.", flush=True)

            # --- Migration 003: Phone Number Functional Index ---
            if "003_phone_digit_indexes" not in applied:
                print("[MIGRATION] Applying 003_phone_digit_indexes...", flush=True)
                cur.execute('''
                    CREATE INDEX IF NOT EXISTS idx_leads_phone_digits 
                    ON "Leads" (regexp_replace(COALESCE(phone, ''), '\\D', '', 'g'));
                ''')
                cur.execute('''
                    CREATE INDEX IF NOT EXISTS idx_customers_phone_digits 
                    ON "Customers" (regexp_replace(COALESCE(phone, ''), '\\D', '', 'g'));
                ''')
                cur.execute("""
                    INSERT INTO "schema_migrations" (version, description)
                    VALUES ('003_phone_digit_indexes', 'Functional regex indexes on phone digits for high-speed search');
                """)
                conn.commit()
                print("[MIGRATION] 003_phone_digit_indexes successfully applied.", flush=True)

            # --- Immediate Baseline Parity Hardening (Users, Leads, Customers) ---
            cur.execute('''
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

                ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS cleaning_delivery_model VARCHAR(50) DEFAULT 'DIRECT_W2';
                ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Active';

                -- WorkOrders Parity
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS shift_window VARCHAR(100) DEFAULT 'Evening Shift (6:00 PM – 11:00 PM)';
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS service_type VARCHAR(100) DEFAULT 'Routine Nightly Custodial';
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS assigned_technician_id INTEGER;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS crew_lead_id INTEGER;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS quality_score NUMERIC(5,2);
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS completion_signature TEXT;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS supervisor_signoff TEXT;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS checklist_progress JSONB DEFAULT '[]'::jsonb;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS dock_ingress_instructions TEXT;
                ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS security_access_code VARCHAR(100);
            ''')
            conn.commit()

            # --- Modular Migrations (004 through 018) ---
            target_db_url = db_url or os.environ.get("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
            
            modular_migrations = [
                ("004_workforce_and_subcontractors", "scripts.migrate_004_workforce", "Job applicants and 1099 subcontractor partner tables with document tracking"),
                ("005_user_telegram_chat_id", "scripts.migrate_005_user_telegram", "Added telegram_chat_id to Users table for multi-user Telegram dispatch"),
                ("006_telegram_behavioral_telemetry", "scripts.migrate_006_telegram_behavioral_telemetry", "Telegram behavioral telemetry and interaction scoring"),
                ("007_human_resources_and_payroll", "scripts.migrate_007_human_resources_and_payroll", "Human Resources master personnel ledger, secure document vault, and payroll timesheet engine"),
                ("008_sigma_academy_lms", "scripts.migrate_008_sigma_academy_lms", "Sigma Academy LMS courses, enrollments, and progress tracking"),
                ("010_institutional_bids", "scripts.migrate_010_institutional_bids", "Construction bids and document attachment vault"),
                ("011_marketing_department", "scripts.migrate_011_marketing_department", "Marketing campaigns and social dispatch outbox"),
                ("012_ehsq_safety_department", "scripts.migrate_012_ehsq_safety_department", "EHSQ safety inspections, hazard tracking, and compliance certifications"),
                ("013_employee_lifecycle_suite", "scripts.migrate_013_employee_lifecycle_suite", "Employee lifecycle, W-4, PTO, and compliance columns"),
                ("014_account_lifecycle_suite", "scripts.migrate_014_account_lifecycle_suite", "Institutional account lifecycle, contract terms, and COI verification"),
                ("015_internal_dispatch_suite", "scripts.migrate_015_internal_dispatch_suite", "Internal dispatch work orders, shifts, and execution monitor"),
                ("016_sensitive_pii_vault", "scripts.migrate_016_sensitive_pii_vault", "Sensitive PII AES-256 encrypted vault for SSN/ITIN and banking"),
                ("017_job_positions_and_descriptions", "scripts.migrate_017_job_positions_and_descriptions", "Job positions catalog, digital job descriptions, and ATS linking"),
                ("018_institutional_users_and_schema_parity", "scripts.migrate_018_institutional_users_and_schema_parity", "Institutional Users table hardening, credential sync, and leads parity")
            ]

            for v_tag, mod_path, v_desc in modular_migrations:
                if v_tag not in applied:
                    print(f"[MIGRATION] Applying modular migration {v_tag} ({mod_path})...", flush=True)
                    try:
                        mod = importlib.import_module(mod_path)
                        if hasattr(mod, 'run_migration'):
                            mod.run_migration(target_db_url)
                        cur.execute("""
                            INSERT INTO "schema_migrations" (version, description)
                            VALUES (%s, %s)
                            ON CONFLICT (version) DO NOTHING;
                        """, (v_tag, v_desc))
                        conn.commit()
                        applied.add(v_tag)
                        print(f"[MIGRATION] {v_tag} successfully applied and recorded.", flush=True)
                    except Exception as mod_err:
                        conn.rollback()
                        print(f"[MIGRATION WARNING] Modular migration {v_tag} failed: {mod_err}", file=sys.stderr, flush=True)

    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION ERROR] Failed to apply schema migrations: {e}", file=sys.stderr, flush=True)
        raise e
