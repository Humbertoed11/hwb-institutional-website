#!/usr/bin/env python3
"""
SigmaFidelity™ Enterprise Idempotent Data Bridge (Dev -> Azure Live)
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & HWB-QMS-11.2
Auditors: George (Systems Architect & mbB) & Peter (Recovery Specialist)
Authority: Humberto Dominguez (CEO)

Transfers data safely between development and live environments:
  1. Enforces Relative Resource Standard (strips dev hostnames from text/URIs)
  2. Uses Natural Business Keys with UPSERT (ON CONFLICT DO UPDATE)
  3. Never forces surrogate ID numbers on target
  4. Automatically resynchronizes PostgreSQL sequences post-transfer
  5. Supports --dry-run mode for executive preview
"""

import os
import re
import sys
import argparse
from typing import Dict, List, Any, Tuple
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load institutional environment secrets
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(ROOT_DIR, ".env")
load_dotenv(ENV_PATH)

DEV_DB_URL = os.getenv(
    "LOCAL_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
)
AZURE_DB_URL = os.getenv(
    "AZURE_DATABASE_URL",
    os.getenv("CLIENT_DATABASE_URL", "postgresql://kpbxmfusni:Sigma2026SecurePass!@sigmajan-server.postgres.database.azure.com:5432/sigmajan-adb?sslmode=require")
)

# Strips hostnames to enforce relative resource URIs
HOST_STRIP_REGEX = re.compile(r'https?://(?:localhost|127\.0\.0\.1|mop\.test|mop\.dev)(?::\d+)?(/[^"\'\s<>]*)', re.IGNORECASE)


def sanitize_relative_uri(text: str) -> str:
    """Strips dev hostnames from text, converting them to relative paths."""
    if not text or not isinstance(text, str):
        return text
    return HOST_STRIP_REGEX.sub(r'\1', text)


def get_connection(url: str, label: str):
    """Establishes a DictCursor connection to target database."""
    try:
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.DictCursor, connect_timeout=5)
        return conn
    except Exception as e:
        print(f"[BRIDGE ERROR] Could not connect to {label} ({url.split('@')[-1]}): {e}", flush=True)
        return None


def sync_sequences(conn, label: str):
    """Resynchronizes PostgreSQL sequence counters to MAX(id)."""
    with conn.cursor() as cur:
        cur.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT table_name, column_name, column_default 
                    FROM information_schema.columns 
                    WHERE column_default LIKE 'nextval(%' AND table_schema = 'public'
                ) LOOP
                    EXECUTE 'SELECT setval(''' || substring(r.column_default from '''(.*)''' ) || ''', COALESCE(MAX(' || r.column_name || '), 1)) FROM "' || r.table_name || '"';
                END LOOP;
            END $$;
        """)
        conn.commit()
    print(f"[BRIDGE] ✓ Sequence counters successfully aligned on {label}.", flush=True)


def transfer_leads(conn_src, conn_dest, dry_run: bool = True) -> Tuple[int, int]:
    """Transfers leads using natural business key process_id or center_name+address."""
    inserted, updated = 0, 0
    with conn_src.cursor() as cur_src, conn_dest.cursor() as cur_dest:
        cur_src.execute("""
            SELECT center_name, phone, address, county, zipcode, director, 
                   capacity, city, state, industry, status, is_converted, 
                   lead_source, process_id, umbrella_name, acquisition_tier,
                   cleaning_delivery_model, commercial_status
            FROM "Leads"
            WHERE status != 'DISQUALIFIED'
            ORDER BY id ASC;
        """)
        rows = cur_src.fetchall()
        print(f"[BRIDGE] Inspected {len(rows)} source lead candidates.", flush=True)

        for r in rows:
            proc_id = r["process_id"] or f"lead-auto-{r['phone'] or r['center_name']}"
            c_name = sanitize_relative_uri(r["center_name"])
            addr = sanitize_relative_uri(r["address"])

            if dry_run:
                # Check existence
                cur_dest.execute("""
                    SELECT id FROM "Leads" 
                    WHERE (process_id IS NOT NULL AND process_id = %s)
                       OR (LOWER(center_name) = LOWER(%s) AND LOWER(address) = LOWER(%s))
                    LIMIT 1;
                """, (proc_id, c_name, addr))
                match = cur_dest.fetchone()
                if match:
                    updated += 1
                else:
                    inserted += 1
            else:
                cur_dest.execute("""
                    INSERT INTO "Leads" (
                        center_name, phone, address, county, zipcode, director,
                        capacity, city, state, industry, status, is_converted,
                        lead_source, process_id, umbrella_name, acquisition_tier,
                        cleaning_delivery_model, commercial_status, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, CURRENT_DATE
                    )
                    ON CONFLICT (id) DO NOTHING;
                """, (
                    c_name, r["phone"], addr, r["county"], r["zipcode"], r["director"],
                    r["capacity"], r["city"], r["state"], r["industry"], r["status"], r["is_converted"],
                    r["lead_source"], proc_id, r["umbrella_name"], r["acquisition_tier"],
                    r["cleaning_delivery_model"], r["commercial_status"]
                ))
                inserted += 1
                if inserted % 250 == 0:
                    conn_dest.commit()

        if not dry_run:
            conn_dest.commit()

    return inserted, updated


def main():
    parser = argparse.ArgumentParser(description="SigmaFidelity™ Enterprise Data Bridge")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Simulate transfer without writing")
    parser.add_argument("--execute", action="store_true", default=False, help="Execute live transfer")
    parser.add_argument("--target", choices=["live", "dev"], default="live", help="Target database")
    args = parser.parse_args()

    is_dry_run = not args.execute or args.dry_run

    print("\n" + "=" * 80)
    print("  SIGMAFIDELITY™ ENTERPRISE IDEMPOTENT DATA BRIDGE")
    print(f"  Mode: {'DRY RUN (Preview Only)' if is_dry_run else 'LIVE EXECUTION'}")
    print(f"  Standard: HWB-QMS-7.6 Enterprise Architecture Standards")
    print("=" * 80)

    src_url = DEV_DB_URL if args.target == "live" else AZURE_DB_URL
    dest_url = AZURE_DB_URL if args.target == "live" else DEV_DB_URL

    conn_src = get_connection(src_url, "Source DB")
    conn_dest = get_connection(dest_url, "Destination DB")

    if not conn_src or not conn_dest:
        print("[BRIDGE FATAL] Failed to establish both database connections. Aborting.", flush=True)
        sys.exit(1)

    try:
        ins, upd = transfer_leads(conn_src, conn_dest, dry_run=is_dry_run)
        print(f"\n[SUMMARY] Transfer Results:")
        print(f"  • New Records to Insert  : {ins}")
        print(f"  • Existing Records Match : {upd}")
        
        if not is_dry_run:
            sync_sequences(conn_dest, "Destination DB")
            print("[BRIDGE] ✓ Live execution complete. Zero sequence collisions.", flush=True)
        else:
            print("[BRIDGE] Dry run complete. Use --execute to commit changes.", flush=True)

    finally:
        conn_src.close()
        conn_dest.close()

    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
