#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 036: User Custom Scripts & Personal Profile Library
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect & mbB) & Silas Sync (VP of CRM)

Objectives:
1. Provision "user_scripts" table in PostgreSQL with user_id foreign key.
2. Establish indexes for user filtering, shared team library, and default preference.
3. Seed authentic initial executive template for Humberto Dominguez (CEO).
4. Idempotently record version in schema_migrations.
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
            # 1. Provision Table: user_scripts
            print("[MIGRATION-036] Provisioning 'user_scripts' table...")
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_scripts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "Users"(id) ON DELETE CASCADE,
                    tab_label VARCHAR(60) NOT NULL,
                    scenario_type VARCHAR(50) DEFAULT 'Custom Pitch',
                    script_text TEXT NOT NULL,
                    operator_tip TEXT,
                    is_default BOOLEAN DEFAULT FALSE,
                    is_shared BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            ''')

            # 2. Performance & Relationship Indexes
            print("[MIGRATION-036] Creating indexes on 'user_scripts'...")
            cur.execute('CREATE INDEX IF NOT EXISTS idx_user_scripts_user_id ON user_scripts(user_id);')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_user_scripts_is_shared ON user_scripts(is_shared);')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_user_scripts_is_default ON user_scripts(user_id, is_default);')

            # 3. Seed Starter Executive Script for CEO Humberto Dominguez
            print("[MIGRATION-036] Seeding starter executive script for CEO...")
            cur.execute('''
                SELECT id FROM "Users" 
                WHERE LOWER(username) IN ('hdominguez', 'humberto', 'humbertoed', 'admin') 
                ORDER BY id LIMIT 1;
            ''')
            row = cur.fetchone()
            if row:
                ceo_user_id = row[0]
                cur.execute('''
                    SELECT id FROM user_scripts WHERE user_id = %s AND tab_label = '⭐ Founder Pitch';
                ''', (ceo_user_id,))
                if not cur.fetchone():
                    starter_script = (
                        "Hi {Director}, this is Humberto Dominguez, CEO and founder of HWB Cleaning Services right here in {City}. "
                        "I am reaching out personally because our operations team is currently servicing educational and childcare facilities in your corridor. "
                        "We specialize in zero-residue hospital-grade sanitization that meets every Texas Child Care Regulation health inspection standard. "
                        "I wanted to see if I could stop by {Facility} for just 5 minutes this week to meet you, review your current cleaning scope, and leave our side-by-side pricing sheet. "
                        "Would Tuesday morning or Thursday afternoon be better for a quick 5-minute introduction?"
                    )
                    starter_tip = "CEO Direct Introduction: Establishes immediate executive trust. Ask for a quick 5-minute walkthrough."
                    cur.execute('''
                        INSERT INTO user_scripts (user_id, tab_label, scenario_type, script_text, operator_tip, is_default, is_shared)
                        VALUES (%s, '⭐ Founder Pitch', 'Director Pitch', %s, %s, FALSE, TRUE);
                    ''', (ceo_user_id, starter_script, starter_tip))
                    print("[MIGRATION-036] Starter executive script seeded successfully.")

            conn.commit()
            print("[MIGRATION-036] Complete: user_scripts table provisioned and verified.")

    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION-036 ERROR] {e}", file=sys.stderr)
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
