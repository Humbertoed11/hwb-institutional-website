#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 030: Purchasing Cooperatives Master Registry & Charter Institutions
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & Zero-Defect Poka-Yoke Protocol
Execution Authority: George (Systems Architect & mbB) & Humberto Dominguez (CEO)

Objectives:
1. Create "PurchasingCooperatives" master table for the 6 primary Texas education cooperatives.
2. Seed the 6 verified cooperatives (TIPS, BuyBoard, EPCNT, Choice Partners, PACE, Omnia Partners) + Texas SmartBuy.
3. Enhance "Leads" table with TEA AskTED integration columns: cdcn, student_enrollment, region_priority, esc_region, charter_parent.
4. Enhance "CorporateUmbrellas" with accepted_cooperatives array.
5. Record migration idempotently in schema_migrations.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

COOPERATIVES_SEED = [
    {
        "coop_code": "TIPS",
        "coop_name": "The Interlocal Purchasing System (TIPS)",
        "sponsoring_agency": "Region 8 Education Service Center (Pittsburg, TX)",
        "jurisdiction": "Texas & National",
        "portal_url": "https://www.tips-usa.com",
        "bid_portal_type": "IonWave",
        "custodial_category": "Custodial, Janitorial, Trades & Labor Services",
        "active_hwb_status": "Application Staged",
        "notes": "Major Texas K-12 and charter purchasing vehicle. Annual competitive RFP cycles."
    },
    {
        "coop_code": "BUYBOARD",
        "coop_name": "Texas BuyBoard Purchasing Cooperative",
        "sponsoring_agency": "Texas Association of School Boards (TASB)",
        "jurisdiction": "Texas Statewide",
        "portal_url": "https://www.buyboard.com",
        "bid_portal_type": "BuyBoard Internal",
        "custodial_category": "Building Maintenance, Repair, Custodial Supplies & Services",
        "active_hwb_status": "Application Staged",
        "notes": "Standard purchasing co-op for 95%+ of Texas school districts and charter school boards."
    },
    {
        "coop_code": "EPCNT",
        "coop_name": "Educational Purchasing Cooperative of North Texas (EPCNT)",
        "sponsoring_agency": "ESC Region 10 & ESC Region 11 (Dallas / Fort Worth)",
        "jurisdiction": "DFW Metroplex (Region 10 & 11)",
        "portal_url": "https://epcnt.esc11.net",
        "bid_portal_type": "Interlocal Contract Sharing / Rider",
        "custodial_category": "Custodial & Facility Service Contracts",
        "active_hwb_status": "Prospective",
        "notes": "Contract-sharing consortium of 100+ DFW school districts and charter networks. Allows interlocal piggybacking on member awards."
    },
    {
        "coop_code": "CHOICE_PARTNERS",
        "coop_name": "Choice Partners Cooperative",
        "sponsoring_agency": "Harris County Department of Education (HCDE)",
        "jurisdiction": "Texas Statewide",
        "portal_url": "https://www.choicepartners.org",
        "bid_portal_type": "Choice Partners Internal",
        "custodial_category": "Contract #22/053KN Custodial Supplies and Services",
        "active_hwb_status": "Prospective",
        "notes": "Primary Texas cooperative for facilities management. Currently holds active prime contracts for Ambassador Services LLC."
    },
    {
        "coop_code": "PACE",
        "coop_name": "Purchasing Association of Cooperative Entities (PACE)",
        "sponsoring_agency": "Region 20 Education Service Center (San Antonio, TX)",
        "jurisdiction": "Texas Statewide (South/Central)",
        "portal_url": "https://www.pacecoop.org",
        "bid_portal_type": "PACE Internal",
        "custodial_category": "Facility Maintenance & Custodial Services",
        "active_hwb_status": "Prospective",
        "notes": "Serves education, city, and county entities statewide across Texas."
    },
    {
        "coop_code": "OMNIA",
        "coop_name": "Omnia Partners Public Sector (incorporating TCPN)",
        "sponsoring_agency": "Region 4 Education Service Center (Houston, TX)",
        "jurisdiction": "Texas & National",
        "portal_url": "https://www.omniapartners.com",
        "bid_portal_type": "Omnia Portal",
        "custodial_category": "Facilities Management, Janitorial & Sanitation",
        "active_hwb_status": "Prospective",
        "notes": "National cooperative with Texas lead public agency backing from Region 4 ESC."
    },
    {
        "coop_code": "TX_SMARTBUY",
        "coop_name": "Texas SmartBuy & Electronic State Business Daily (ESBD)",
        "sponsoring_agency": "Texas Comptroller of Public Accounts",
        "jurisdiction": "Texas Statewide (State Agencies & CO-OP Members)",
        "portal_url": "http://www.txsmartbuy.com",
        "bid_portal_type": "Texas Comptroller",
        "custodial_category": "Class 910: Building Maintenance & Janitorial Services",
        "active_hwb_status": "Prospective",
        "notes": "State of Texas Centralized Master Bidders List (CMBL) and municipal co-op program."
    }
]


def run_migration():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[FATAL] DATABASE_URL environment variable is missing!", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("="*80)
        print(" SIGMAFIDELITY™ MIGRATION 030: PURCHASING COOPERATIVES & CHARTER INSTITUTIONS")
        print("="*80)

        # 1. Create PurchasingCooperatives Table
        print("[MIG-030] 1. Creating PurchasingCooperatives master table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "PurchasingCooperatives" (
                id SERIAL PRIMARY KEY,
                coop_code VARCHAR(32) UNIQUE NOT NULL,
                coop_name VARCHAR(128) NOT NULL,
                sponsoring_agency VARCHAR(128),
                jurisdiction VARCHAR(64) DEFAULT 'Texas',
                portal_url TEXT,
                bid_portal_type VARCHAR(64),
                custodial_category VARCHAR(128),
                active_hwb_status VARCHAR(64) DEFAULT 'Prospective',
                hwb_contract_number VARCHAR(64),
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        # 2. Seed the Cooperatives
        print("[MIG-030] 2. Seeding 7 Master Cooperatives...")
        for coop in COOPERATIVES_SEED:
            cur.execute("""
                INSERT INTO "PurchasingCooperatives" (
                    coop_code, coop_name, sponsoring_agency, jurisdiction,
                    portal_url, bid_portal_type, custodial_category,
                    active_hwb_status, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (coop_code) DO UPDATE SET
                    coop_name = EXCLUDED.coop_name,
                    sponsoring_agency = EXCLUDED.sponsoring_agency,
                    portal_url = EXCLUDED.portal_url,
                    bid_portal_type = EXCLUDED.bid_portal_type,
                    custodial_category = EXCLUDED.custodial_category,
                    notes = EXCLUDED.notes;
            """, (
                coop["coop_code"], coop["coop_name"], coop["sponsoring_agency"],
                coop["jurisdiction"], coop["portal_url"], coop["bid_portal_type"],
                coop["custodial_category"], coop["active_hwb_status"], coop["notes"]
            ))

        # 3. Enhance Leads Table with TEA AskTED Columns
        print("[MIG-030] 3. Enhancing Leads table with TEA AskTED integration columns...")
        leads_cols = [
            ("cdcn", "VARCHAR(32)"),
            ("student_enrollment", "INTEGER"),
            ("region_priority", "VARCHAR(32)"),
            ("esc_region", "INTEGER"),
            ("charter_parent", "VARCHAR(128)")
        ]
        for col_name, col_type in leads_cols:
            cur.execute(f"""
                ALTER TABLE "Leads" 
                ADD COLUMN IF NOT EXISTS {col_name} {col_type};
            """)

        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_cdcn 
            ON "Leads"(cdcn) 
            WHERE cdcn IS NOT NULL;
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_leads_region_priority 
            ON "Leads"(region_priority);
        """)

        # 4. Enhance CorporateUmbrellas Table
        print("[MIG-030] 4. Enhancing CorporateUmbrellas with accepted_cooperatives...")
        cur.execute("""
            ALTER TABLE "CorporateUmbrellas" 
            ADD COLUMN IF NOT EXISTS accepted_cooperatives TEXT[];
        """)

        # Seed initial accepted co-ops for Uplift and IDEA
        cur.execute("""
            UPDATE "CorporateUmbrellas"
            SET accepted_cooperatives = ARRAY['TIPS', 'BUYBOARD', 'EPCNT', 'CHOICE_PARTNERS', 'PACE', 'OMNIA']
            WHERE umbrella_name = 'Uplift Education';
        """)

        cur.execute("""
            UPDATE "CorporateUmbrellas"
            SET accepted_cooperatives = ARRAY['TIPS', 'BUYBOARD', 'TX_SMARTBUY', 'CHOICE_PARTNERS']
            WHERE umbrella_name = 'IDEA Public Schools Pre-K' OR umbrella_name = 'IDEA Public Schools';
        """)

        # 5. Record Migration in schema_migrations
        print("[MIG-030] 5. Recording migration in schema_migrations...")
        cur.execute("""
            INSERT INTO schema_migrations (version, description)
            VALUES ('030_purchasing_cooperatives_and_charter_institutions', 'PurchasingCooperatives table, TEA AskTED lead columns, and cooperative tracking')
            ON CONFLICT (version) DO NOTHING;
        """)

        conn.commit()
        print("[MIG-030] === SUCCESS: Migration 030 applied cleanly! ===")

    except Exception as e:
        conn.rollback()
        print(f"[FATAL] Migration 030 failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
