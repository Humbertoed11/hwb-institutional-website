#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 035: Site Security Rack #9 & Immutable Audit Ledger
Standard: HWB-QMS-11.2 / HWB-QMS-9.6 (ISO 27001 / SOC 2 Type II / NIST SP 800-92)
Custodians: George (Systems Architect & mbB) & Humberto Dominguez (CEO)

Objectives:
1. Provision "SecurityAuditLogs" master ledger in PostgreSQL.
2. Establish PostgreSQL WORM (Write-Once, Read-Many) immutability trigger to block UPDATE/DELETE.
3. Index forensic columns: timestamp, event_category, severity, ip_address, username.
4. Record version in schema_migrations idempotently.
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

def run_migration(db_url: str = None):
    target_url = db_url or os.getenv("DATABASE_URL", DB_URL)
    print("[MIGRATION-035] Connecting to PostgreSQL database...")
    conn = psycopg2.connect(target_url)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # 1. Provision Table: SecurityAuditLogs
            print("[MIGRATION-035] Provisioning 'SecurityAuditLogs' immutable master ledger...")
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "SecurityAuditLogs" (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    event_category VARCHAR(50) NOT NULL,
                    event_action VARCHAR(50) NOT NULL,
                    user_id INTEGER NULL,
                    username VARCHAR(100) NULL,
                    user_role VARCHAR(50) NULL,
                    ip_address VARCHAR(45) NOT NULL DEFAULT '127.0.0.1',
                    user_agent TEXT NULL,
                    endpoint VARCHAR(255) NOT NULL DEFAULT '/',
                    http_method VARCHAR(10) NOT NULL DEFAULT 'GET',
                    status_code INTEGER NOT NULL DEFAULT 200,
                    severity VARCHAR(20) NOT NULL DEFAULT 'INFO',
                    details JSONB NULL
                );
            ''')

            # 2. Forensic High-Performance Indexes
            print("[MIGRATION-035] Creating forensic query indexes on 'SecurityAuditLogs'...")
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_sec_audit_ts ON "SecurityAuditLogs" (timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_sec_audit_cat_sev ON "SecurityAuditLogs" (event_category, severity);
                CREATE INDEX IF NOT EXISTS idx_sec_audit_ip ON "SecurityAuditLogs" (ip_address);
                CREATE INDEX IF NOT EXISTS idx_sec_audit_user ON "SecurityAuditLogs" (username);
                CREATE INDEX IF NOT EXISTS idx_sec_audit_action ON "SecurityAuditLogs" (event_action);
            ''')

            # 3. WORM Immutability Trigger Function & Trigger
            print("[MIGRATION-035] Enforcing WORM (Write-Once, Read-Many) immutability trigger...")
            cur.execute('''
                CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'SECURITY AUDIT VIOLATION: Records in SecurityAuditLogs are immutable and cannot be updated or deleted.';
                END;
                $$ LANGUAGE plpgsql;

                DROP TRIGGER IF EXISTS trg_security_audit_immutable ON "SecurityAuditLogs";
                CREATE TRIGGER trg_security_audit_immutable
                BEFORE UPDATE OR DELETE ON "SecurityAuditLogs"
                FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
            ''')

            # 4. Insert Initial Provisioning Event
            cur.execute('''
                INSERT INTO "SecurityAuditLogs" (
                    timestamp, event_category, event_action, username, user_role, ip_address, endpoint, http_method, status_code, severity, details
                ) VALUES (
                    NOW(), 'SYSTEM', 'RACK_09_INITIALIZED', 'admin', 'Executive', '127.0.0.1', '/admin/operations?view=it', 'SYSTEM', 200, 'INFO', 
                    '{"message": "Site Security Rack #9 provisioned with WORM immutability trigger active."}'::jsonb
                );
            ''')

            # 5. Record Migration in schema_migrations
            cur.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO schema_migrations (version, applied_at)
                VALUES ('035_site_security_rack_09', NOW())
                ON CONFLICT (version) DO NOTHING;
            ''')

        conn.commit()
        print("✓ [MIGRATION-035] Successfully deployed SecurityAuditLogs with WORM immutability.")
    except Exception as e:
        conn.rollback()
        print(f"❌ [MIGRATION-035 FAILED] Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()
