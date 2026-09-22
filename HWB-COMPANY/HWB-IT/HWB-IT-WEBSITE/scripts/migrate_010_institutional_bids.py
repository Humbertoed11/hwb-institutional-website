"""
Migration 010: SigmaFidelity™ Institutional & Public Sector Solicitations Architecture
Standard: HWB-QMS-7.6 Database Hardening & Schema Versioning SOP
Authority: Humberto Dominguez (CEO)
Architect: George (Systems Architect & mbB)
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

def run_migration(db_url: str):
    print("[MIGRATION] Applying 010_institutional_bids...")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Provision Table: InstitutionalBids
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "InstitutionalBids" (
                    id SERIAL PRIMARY KEY,
                    solicitation_number VARCHAR(100) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    agency_name VARCHAR(255) NOT NULL,
                    sector VARCHAR(100) DEFAULT 'Transportation & Infrastructure',
                    portal_name VARCHAR(100) DEFAULT 'NTTA Marketplace',
                    portal_doc_id VARCHAR(100),
                    procurement_officer VARCHAR(150),
                    officer_email VARCHAR(150),
                    officer_phone VARCHAR(50),
                    contract_term_months INTEGER DEFAULT 24,
                    cleanable_sqft NUMERIC DEFAULT 0,
                    facilities_count INTEGER DEFAULT 1,
                    published_budget NUMERIC(12,2) DEFAULT 0.00,
                    hwb_bid_total NUMERIC(12,2) DEFAULT 0.00,
                    monthly_base_rate NUMERIC(10,2) DEFAULT 0.00,
                    annual_base_rate NUMERIC(12,2) DEFAULT 0.00,
                    hourly_porter_rate NUMERIC(8,2) DEFAULT 0.00,
                    pre_bid_datetime TIMESTAMP WITH TIME ZONE,
                    pre_bid_type VARCHAR(100),
                    pre_bid_url TEXT,
                    site_walk_datetime TIMESTAMP WITH TIME ZONE,
                    site_walk_location VARCHAR(255),
                    questions_due_date TIMESTAMP WITH TIME ZONE,
                    bid_due_date TIMESTAMP WITH TIME ZONE,
                    public_opening_datetime TIMESTAMP WITH TIME ZONE,
                    public_opening_url TEXT,
                    status VARCHAR(50) DEFAULT 'Active Solicitation',
                    compliance_status VARCHAR(100) DEFAULT 'Package Unified & Ready',
                    compliance_summary TEXT,
                    local_quote_path VARCHAR(255),
                    bid_sheet_path VARCHAR(255),
                    dossier_path VARCHAR(255),
                    rfp_url TEXT,
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_inst_bids_solicitation" ON "InstitutionalBids" (solicitation_number);
                CREATE INDEX IF NOT EXISTS "idx_inst_bids_agency" ON "InstitutionalBids" (agency_name);
                CREATE INDEX IF NOT EXISTS "idx_inst_bids_due_date" ON "InstitutionalBids" (bid_due_date);
                CREATE INDEX IF NOT EXISTS "idx_inst_bids_status" ON "InstitutionalBids" (status);
            ''')
            print("  -> Table InstitutionalBids and indexes provisioned.")

            # 2. Seed NTTA Ancillary Facilities (Solicitation 06507-NTT-00-GS-MA / Doc B2600001083)
            cur.execute('''
                INSERT INTO "InstitutionalBids" (
                    solicitation_number, title, agency_name, sector, portal_name, portal_doc_id,
                    procurement_officer, officer_email, officer_phone, contract_term_months,
                    cleanable_sqft, facilities_count, published_budget, hwb_bid_total,
                    monthly_base_rate, annual_base_rate, hourly_porter_rate,
                    pre_bid_datetime, pre_bid_type, pre_bid_url,
                    site_walk_datetime, site_walk_location,
                    questions_due_date, bid_due_date, public_opening_datetime, public_opening_url,
                    status, compliance_status, compliance_summary,
                    local_quote_path, bid_sheet_path, dossier_path, rfp_url, notes
                ) VALUES (
                    '06507-NTT-00-GS-MA',
                    'Janitorial Services for Ancillary Facilities',
                    'North Texas Tollway Authority',
                    'Transportation & Infrastructure',
                    'NTTA Marketplace',
                    'B2600001083',
                    'Kimberly Madewell',
                    'kmadewell@ntta.org',
                    '(214) 461-2000',
                    24,
                    38367,
                    9,
                    276323.00,
                    273238.58,
                    7475.69,
                    89708.28,
                    21.75,
                    '2026-09-28 14:00:00-05',
                    'Virtual Microsoft Teams',
                    'https://teams.microsoft.com/meet/264482031787224',
                    '2026-09-29 09:00:00-05',
                    '1080 Ohio Dr, Plano, TX 75093 (Stop 1 Plano Maintenance Center)',
                    '2026-10-01 17:00:00-05',
                    '2026-10-07 11:00:00-05',
                    '2026-10-07 15:00:00-05',
                    'https://teams.microsoft.com/meet/213086374308310',
                    'Pre-Bid Scheduled',
                    'Package Unified & Ready',
                    '5 mandatory compliance forms unified into single PDF: Service Location, Business Info, COI Agreement, Form CIQ, and BDOD GFE 100% Self-Performance Certification.',
                    'HWB-COMPANY/HWB-QUOTES/NTTA-06507-ANCILLARY',
                    'HWB-COMPANY/HWB-QUOTES/NTTA-06507-ANCILLARY/06507-NTTA-BID-SHEET-HWB-SUBMISSION.xlsx',
                    'HWB-COMPANY/HWB-QUOTES/NTTA-06507-ANCILLARY/NTTA-06507-PRE-BID-SITE-WALK-DOSSIER.html',
                    'https://www.nttamarketplace.org/bso/external/bidDetail.sda?docId=B2600001083&external=true&parentUrl=close',
                    'Firm 2-year bid. Zero-bag recycling SOP mandatory to avoid $200 fine. 2,080 annual day porter hours. Locked green input cells on official Excel bid sheet.'
                )
                ON CONFLICT (solicitation_number) DO UPDATE SET
                    title = EXCLUDED.title,
                    agency_name = EXCLUDED.agency_name,
                    hwb_bid_total = EXCLUDED.hwb_bid_total,
                    monthly_base_rate = EXCLUDED.monthly_base_rate,
                    pre_bid_datetime = EXCLUDED.pre_bid_datetime,
                    site_walk_datetime = EXCLUDED.site_walk_datetime,
                    bid_due_date = EXCLUDED.bid_due_date,
                    status = EXCLUDED.status,
                    compliance_status = EXCLUDED.compliance_status,
                    updated_at = CURRENT_TIMESTAMP;
            ''')
            print("  -> Seeded NTTA Ancillary Facilities (06507-NTT-00-GS-MA).")

            # 3. Seed Collin College Frisco Campus Incumbent Intelligence
            cur.execute('''
                INSERT INTO "InstitutionalBids" (
                    solicitation_number, title, agency_name, sector, portal_name, portal_doc_id,
                    procurement_officer, officer_email, officer_phone, contract_term_months,
                    cleanable_sqft, facilities_count, published_budget, hwb_bid_total,
                    monthly_base_rate, annual_base_rate, hourly_porter_rate,
                    pre_bid_datetime, pre_bid_type, pre_bid_url,
                    site_walk_datetime, site_walk_location,
                    questions_due_date, bid_due_date, public_opening_datetime, public_opening_url,
                    status, compliance_status, compliance_summary,
                    local_quote_path, bid_sheet_path, dossier_path, rfp_url, notes
                ) VALUES (
                    'FY2024-RFP-005',
                    'District Janitorial Services - Frisco Campus (Incumbent Tracking)',
                    'Collin County Community College District',
                    'Higher Education',
                    'Collin College Procurement / Public Records',
                    'FY2024-RFP-005',
                    'Purchasing Department',
                    'purchasing@collin.edu',
                    '(972) 548-6700',
                    36,
                    478418,
                    11,
                    4950000.00,
                    4890000.00,
                    135833.33,
                    1630000.00,
                    24.50,
                    NULL,
                    'In-Person Mandatory',
                    NULL,
                    NULL,
                    '9700 Wade Blvd, Frisco, TX 75035',
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    'Incumbent Intelligence',
                    'Wage Matrix & Subcontractor Clearance Prepared',
                    'Incumbent contractor Pritchard Industries Southwest ($14.5M 3-yr award). Collin County living wage modeled at $16-$17.50/hr base, $19 loaded.',
                    'HWB-COMPANY/HWB-QUOTES/BOSANNA-COLLIN-COLLEGE',
                    NULL,
                    NULL,
                    'https://www.collin.edu/purchasing/',
                    'Incumbent intelligence captured. Bosanna inquiry pending turnkey scope and submission date confirmation.'
                )
                ON CONFLICT (solicitation_number) DO UPDATE SET
                    title = EXCLUDED.title,
                    agency_name = EXCLUDED.agency_name,
                    hwb_bid_total = EXCLUDED.hwb_bid_total,
                    monthly_base_rate = EXCLUDED.monthly_base_rate,
                    status = EXCLUDED.status,
                    compliance_status = EXCLUDED.compliance_status,
                    updated_at = CURRENT_TIMESTAMP;
            ''')
            print("  -> Seeded Collin College Frisco Campus (FY2024-RFP-005).")

            # 4. Record Migration in schema_migrations
            cur.execute('''
                INSERT INTO schema_migrations (version, description)
                VALUES ('010_institutional_bids', 'Institutional & Public Sector Solicitations schema and active pipeline seed')
                ON CONFLICT (version) DO UPDATE SET
                    applied_at = CURRENT_TIMESTAMP,
                    description = EXCLUDED.description;
            ''')
            print("  -> Logged version 010_institutional_bids in schema_migrations.")

        conn.commit()
        print("[MIGRATION] 010_institutional_bids applied successfully.")
    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION ERROR] Failed to apply 010_institutional_bids: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DB_URL
    run_migration(url)
