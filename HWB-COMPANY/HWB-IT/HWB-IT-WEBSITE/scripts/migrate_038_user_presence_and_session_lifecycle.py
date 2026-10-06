#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 038: User Presence & Session Lifecycle Telemetry
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP / SOC 2 Type II / ISO 27001
Custodians: George (Systems Architect & mbB) & Humberto Dominguez (CEO)

Objectives:
1. Harden "Users" schema with last_logout_at and last_heartbeat_at timestamps.
2. Backfill existing logout timestamps from immutable "SecurityAuditLogs".
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
    print("[MIGRATION-038] Connecting to PostgreSQL database...")
    conn = psycopg2.connect(target_url)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # 1. Provision Columns
            print("[MIGRATION-038] Adding 'last_logout_at' and 'last_heartbeat_at' to 'Users' table...")
            cur.execute('''
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_logout_at TIMESTAMP WITHOUT TIME ZONE;
                ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS last_heartbeat_at TIMESTAMP WITHOUT TIME ZONE;
            ''')

            # 2. Backfill logout telemetry from SecurityAuditLogs
            print("[MIGRATION-038] Backfilling logout telemetry from 'SecurityAuditLogs'...")
            cur.execute('''
                UPDATE "Users" u
                SET last_logout_at = s.timestamp
                FROM (
                    SELECT DISTINCT ON (username) username, timestamp
                    FROM "SecurityAuditLogs"
                    WHERE event_action = 'LOGOUT'
                    ORDER BY username, timestamp DESC
                ) s
                WHERE LOWER(u.username) = LOWER(s.username);
            ''')

            # 3. Initialize heartbeat for users with an open session
            print("[MIGRATION-038] Initializing last_heartbeat_at for active sessions...")
            cur.execute('''
                UPDATE "Users"
                SET last_heartbeat_at = last_login_at
                WHERE last_login_at IS NOT NULL 
                  AND (last_logout_at IS NULL OR last_login_at > last_logout_at);
            ''')

            # 4. Record in schema_migrations
            print("[MIGRATION-038] Recording migration version in schema_migrations...")
            cur.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(100) PRIMARY KEY,
                    applied_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO schema_migrations (version) 
                VALUES ('038_user_presence_and_session_lifecycle')
                ON CONFLICT (version) DO NOTHING;
            ''')

        conn.commit()
        print("[MIGRATION-038] SUCCESS: User presence and session lifecycle migration applied cleanly.")
        return True
    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION-038] ERROR: Migration failed: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    cli_url = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_migration(cli_url)
    sys.exit(0 if success else 1)
