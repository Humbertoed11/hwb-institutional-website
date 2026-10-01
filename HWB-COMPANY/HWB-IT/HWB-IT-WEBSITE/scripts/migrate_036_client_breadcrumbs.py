#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 036: Client Breadcrumbs & Micro-Interaction Telemetry Ledger
Standard: HWB-QMS-11.2 / HWB-QMS-9.6 (ISO 27001 Control A.8.15 / SOC 2 CC6.8)
Custodians: George (Systems Architect & mbB) & Humberto Dominguez (CEO)

Objectives:
1. Provision "ClientBreadcrumbs" telemetry ledger in PostgreSQL.
2. Index forensic columns: timestamp, session_id, event_type, page_url.
3. Establish 30-day automated rolling data purge function (Peter's Surge Protector).
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
    print("[MIGRATION-036] Connecting to PostgreSQL database...")
    conn = psycopg2.connect(target_url)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # 1. Provision Table: ClientBreadcrumbs
            print("[MIGRATION-036] Provisioning 'ClientBreadcrumbs' telemetry ledger...")
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "ClientBreadcrumbs" (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    session_id VARCHAR(100) NOT NULL,
                    page_url VARCHAR(255) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    element_tag VARCHAR(50) NULL,
                    element_id VARCHAR(100) NULL,
                    element_class VARCHAR(150) NULL,
                    element_text VARCHAR(150) NULL,
                    details JSONB NULL,
                    ip_address VARCHAR(45) NOT NULL DEFAULT '127.0.0.1',
                    user_agent TEXT NULL
                );
            ''')

            # 2. Performance Query Indexes
            print("[MIGRATION-036] Creating query indexes on 'ClientBreadcrumbs'...")
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_client_bc_ts ON "ClientBreadcrumbs" (timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_client_bc_session ON "ClientBreadcrumbs" (session_id);
                CREATE INDEX IF NOT EXISTS idx_client_bc_event ON "ClientBreadcrumbs" (event_type);
                CREATE INDEX IF NOT EXISTS idx_client_bc_page ON "ClientBreadcrumbs" (page_url);
            ''')

            # 3. Rolling Data Retention Purge Function (30-day ISO 27001 / SOC 2 Compliance)
            print("[MIGRATION-036] Creating rolling data retention function...")
            cur.execute('''
                CREATE OR REPLACE FUNCTION purge_expired_client_breadcrumbs(retention_days INTEGER DEFAULT 30)
                RETURNS INTEGER AS $$
                DECLARE
                    deleted_rows INTEGER;
                BEGIN
                    DELETE FROM "ClientBreadcrumbs"
                    WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL;
                    GET DIAGNOSTICS deleted_rows = ROW_COUNT;
                    RETURN deleted_rows;
                END;
                $$ LANGUAGE plpgsql;
            ''')

            # 4. Insert Initial Provisioning Event
            cur.execute('''
                INSERT INTO "ClientBreadcrumbs" (
                    timestamp, session_id, page_url, event_type, element_tag, element_id, element_text, ip_address, details
                ) VALUES (
                    NOW(), 'SYSTEM-INIT-036', '/system', 'SYSTEM_PROVISION', 'SYSTEM', 'MIGRATION_036', 
                    'ClientBreadcrumbs Ledger Active', '127.0.0.1',
                    '{"status": "INITIALIZED", "retention_policy_days": 30}'::jsonb
                );
            ''')

            # 5. Record Migration in schema_migrations
            cur.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO schema_migrations (version, applied_at)
                VALUES ('036_client_breadcrumbs', CURRENT_TIMESTAMP)
                ON CONFLICT (version) DO NOTHING;
            ''')

        conn.commit()
        print("[MIGRATION-036] SUCCESS: 'ClientBreadcrumbs' ledger and retention function successfully applied.")
    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION-036] FAILED: Rolling back changes due to error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
