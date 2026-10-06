#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 037: User Access Governance & Real-Time Login Telemetry
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP / SOC 2 Type II / ISO 27001
Custodians: George (Systems Architect & mbB) & Humberto Dominguez (CEO)

Objectives:
1. Harden "Users" schema with last_login_ip (VARCHAR 64) and login_count (INTEGER).
2. Backfill existing login timestamps and IP addresses from immutable "SecurityAuditLogs".
3. Record migration execution in schema_migrations ledger.
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
    print("[MIGRATION-037] Connecting to PostgreSQL database...")
    conn = psycopg2.connect(target_url)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # 1. Provision Columns
            print("[MIGRATION-037] Adding 'last_login_ip' and 'login_count' to 'Users' table...")
            cur.execute('''
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_login_ip VARCHAR(64);
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0;
            ''')

            # 2. Backfill from SecurityAuditLogs
            print("[MIGRATION-037] Backfilling login telemetry from 'SecurityAuditLogs'...")
            cur.execute('''
                UPDATE "Users" u
                SET last_login_at = s.timestamp,
                    last_login_ip = s.ip_address
                FROM (
                    SELECT DISTINCT ON (username) username, timestamp, ip_address
                    FROM "SecurityAuditLogs"
                    WHERE event_action = 'LOGIN_SUCCESS'
                    ORDER BY username, timestamp DESC
                ) s
                WHERE LOWER(u.username) = LOWER(s.username);
            ''')

            # 3. Record in schema_migrations
            print("[MIGRATION-037] Recording migration version in schema_migrations...")
            cur.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(100) PRIMARY KEY,
                    applied_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO schema_migrations (version) 
                VALUES ('037_user_access_governance_telemetry')
                ON CONFLICT (version) DO NOTHING;
            ''')

        conn.commit()
        print("[MIGRATION-037] SUCCESS: User access governance telemetry migration applied cleanly.")
        return True
    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION-037] ERROR: Migration failed: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    cli_url = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_migration(cli_url)
    sys.exit(0 if success else 1)
