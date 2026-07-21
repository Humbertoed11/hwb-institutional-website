#!/usr/bin/env python3
"""
SigmaFidelity™ Safe One-Way Database Synchronization Daemon (Dev -> Azure Production)
Fulfills HWB-QMS-9.3 Section 5.6 & Resolves BUG-044.

This daemon connects to:
  1. Local Dev Postgres (hwb_dev_db on hwb_postgres_dev:5432)
  2. Azure Cloud Postgres (sigmajan-adb on sigmajan-server:5432)

Executes safe, non-destructive DDL schema migrations and UPSERTs (no deletions)
from Dev to Azure Production prior to container deployment.
"""

import os
import sys
import json
import psycopg2
import psycopg2.extras

DEV_DB_URL_CANDIDATES = [
    os.environ.get("LOCAL_DATABASE_URL"),
    "postgresql://hwbdev:hwbpassword@hwb_postgres_dev:5432/hwb_dev_db",
    "postgresql://hwb_user:mop_incident_2026!@hwb_postgres:5432/hwb_db",
    "postgresql://hwb_user:mop_incident_2026!@db:5432/hwb_db",
    "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db"
]
AZURE_DB_URL = os.environ.get("DATABASE_URL", "postgresql://kpbxmfusni:Sigma2026SecurePass!@sigmajan-server.postgres.database.azure.com:5432/sigmajan-adb?sslmode=require")

def get_dev_connection():
    for url in DEV_DB_URL_CANDIDATES:
        if not url: continue
        try:
            conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.DictCursor)
            return conn, url
        except Exception:
            pass
    return None, None

def run_sync():
    print("=== SigmaFidelity™ Dev-to-Azure Production Database Sync ===", flush=True)

    # 1. Connect to Dev DB
    conn_dev, dev_url_used = get_dev_connection()
    if conn_dev:
        print(f"[SYNC] Connected to Local Dev PostgreSQL via {dev_url_used.split('@')[-1]}.", flush=True)
    else:
        print("[SYNC] WARNING: Could not connect to Local Dev DB candidates.", flush=True)
        return False

    # 2. Connect to Azure DB
    try:
        conn_azure = psycopg2.connect(AZURE_DB_URL, cursor_factory=psycopg2.extras.DictCursor)
        print("[SYNC] Connected to Azure Production PostgreSQL (sigmajan-adb).", flush=True)
    except Exception as e:
        print(f"[SYNC] ERROR: Could not connect to Azure Cloud DB: {e}", flush=True)
        return False

    with conn_dev.cursor() as cur_dev, conn_azure.cursor() as cur_azure:
        # Schema Hardening (DDL)
        print("[SYNC] Verifying Azure DB Schema Hardening...", flush=True)
        cur_azure.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS traffic_cycle TEXT;')
        cur_azure.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS frequency TEXT;')
        cur_azure.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS notes TEXT;')
        cur_azure.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS status TEXT DEFAULT \'Active\';')
        cur_azure.execute('ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS billing_address TEXT;')
        cur_azure.execute('ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS contract_period TEXT;')
        cur_azure.execute('''
            CREATE TABLE IF NOT EXISTS "GlobalActivities" (
                id SERIAL PRIMARY KEY,
                parent_id INTEGER NOT NULL,
                parent_type TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        cur_azure.execute('''
            CREATE TABLE IF NOT EXISTS "SigmaInteractionLog" (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_prompt TEXT,
                agent_explanation TEXT,
                tools_used JSONB,
                status VARCHAR(50)
            );
        ''')

        # Telemetry comparison
        cur_dev.execute('SELECT COUNT(*) FROM "Leads";')
        dev_lead_count = cur_dev.fetchone()[0]

        cur_azure.execute('SELECT COUNT(*) FROM "Leads";')
        azure_lead_count = cur_azure.fetchone()[0]

        print(f"[SYNC] Dev Leads: {dev_lead_count:,} | Azure Leads: {azure_lead_count:,}", flush=True)

        # Sync Leads via UPSERT
        cur_dev.execute('SELECT * FROM "Leads";')
        dev_leads = cur_dev.fetchall()

        upsert_count = 0
        for l in dev_leads:
            cur_azure.execute('''
                INSERT INTO "Leads" (
                    id, center_name, lead_source, status, phone, email, address, city, state, zipcode,
                    sqf, capacity, estimated_annual_value, priority_level, facility_type, decision_maker,
                    job_title, traffic_cycle, service_interest, next_action_date, is_dnc, is_converted, input_date
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_DATE)
                ) ON CONFLICT (id) DO UPDATE SET
                    center_name = EXCLUDED.center_name,
                    lead_source = EXCLUDED.lead_source,
                    status = EXCLUDED.status,
                    phone = EXCLUDED.phone,
                    email = EXCLUDED.email,
                    address = EXCLUDED.address,
                    city = EXCLUDED.city,
                    state = EXCLUDED.state,
                    zipcode = EXCLUDED.zipcode,
                    sqf = EXCLUDED.sqf,
                    capacity = EXCLUDED.capacity,
                    estimated_annual_value = EXCLUDED.estimated_annual_value,
                    priority_level = EXCLUDED.priority_level,
                    facility_type = EXCLUDED.facility_type,
                    decision_maker = EXCLUDED.decision_maker,
                    is_dnc = EXCLUDED.is_dnc,
                    input_date = COALESCE(EXCLUDED.input_date, "Leads".input_date);
            ''', (
                l.get('id'), l.get('center_name'), l.get('lead_source'), l.get('status'), l.get('phone'), l.get('email'), l.get('address'), l.get('city'), l.get('state'), l.get('zipcode'),
                l.get('sqf'), l.get('capacity'), l.get('estimated_annual_value'), l.get('priority_level'), l.get('facility_type'), l.get('decision_maker'),
                l.get('job_title'), l.get('traffic_cycle'), l.get('service_interest'), l.get('next_action_date'), l.get('is_dnc', False), l.get('is_converted', False), l.get('input_date')
            ))
            upsert_count += 1

        conn_azure.commit()
        print(f"[SYNC] SUCCESS: Processed safe UPSERT across {upsert_count:,} records in Azure Cloud DB.", flush=True)

    conn_dev.close()
    conn_azure.close()
    return True

if __name__ == '__main__':
    run_sync()
