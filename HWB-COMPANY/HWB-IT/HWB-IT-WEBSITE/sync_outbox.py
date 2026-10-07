#!/usr/bin/env python3
"""
SigmaFidelity™ Outbox Synchronization Utility
Standard: HWB-QMS-11.1 & SO-COM-001 Mandate 4 (Outbox Governance)
Responsibility: Silas Sync (VP of CRM) & George (Systems Architect)

Synchronizes staged outbox communications between local sandbox and PostgreSQL core.
"""

import os
import sys
import sqlite3
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "database", "sigma_leads.db")
SQLITE_DB = os.getenv("SQLITE_OUTBOX_PATH", DEFAULT_SQLITE_PATH)
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")


def sync_outbox():
    """Sync outbox records to authoritative PostgreSQL database."""
    print("--- SigmaFidelity: Executing Outbox Synchronization ---")
    if not os.path.exists(SQLITE_DB):
        print(f"NOTICE: SQLite outbox source [{SQLITE_DB}] not found. Unified PostgreSQL core active.")
        return

    try:
        # 1. Fetch pending record from SQLite staging
        s_conn = sqlite3.connect(SQLITE_DB)
        s_cur = s_conn.cursor()
        s_cur.execute("SELECT recipient, subject, body FROM PendingOutbox WHERE status = 'Pending' ORDER BY id DESC LIMIT 1")
        row = s_cur.fetchone()
        s_conn.close()

        if not row:
            print("No pending records found in SQLite outbox staging.")
            return

        recipient, subject, body = row
        print(f"Syncing: {subject} to recipient {recipient}")

        # 2. Push to authoritative PostgreSQL database
        p_conn = psycopg2.connect(POSTGRES_URL)
        p_cur = p_conn.cursor()
        p_cur.execute(
            """
            INSERT INTO "PendingOutbox" (recipient, subject, body, status, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (recipient, subject, body, 'Pending', datetime.now())
        )
        p_conn.commit()
        p_cur.close()
        p_conn.close()
        print("SUCCESS: Record synced to PostgreSQL core.")

    except Exception as e:
        print(f"Sync Notice: {e}")


if __name__ == "__main__":
    sync_outbox()
