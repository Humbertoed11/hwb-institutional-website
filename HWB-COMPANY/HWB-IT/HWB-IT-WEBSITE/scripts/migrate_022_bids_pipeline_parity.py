"""
Migration 022: Commercial Construction Bids & Institutional Solicitations Pipeline Parity
Standard: HWB-QMS-7.7 Commercial Construction Takeoff & Estimating SOP
Authority: Humberto Dominguez (CEO) - Approved 09/22/2026
Architect: George (Systems Architect & mbB)
"""

import os
import sys
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

def run_migration(db_url: str = None):
    target_url = db_url or DB_URL
    print("\n=======================================================", flush=True)
    print("  Applying Migration 022: Bids Pipeline Parity & Seeder", flush=True)
    print("=======================================================", flush=True)

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor() as cur:
            # 1. Provision Table: ConstructionBids if not exists
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "ConstructionBids" (
                    id SERIAL PRIMARY KEY,
                    gc_name VARCHAR(255) NOT NULL,
                    project_name VARCHAR(255) NOT NULL,
                    project_address VARCHAR(255),
                    city VARCHAR(100),
                    state VARCHAR(50) DEFAULT 'TX',
                    zipcode VARCHAR(20),
                    bid_due_date TIMESTAMP WITH TIME ZONE,
                    estimated_start_date DATE,
                    estimated_end_date DATE,
                    cleanable_sqft NUMERIC DEFAULT 0,
                    estimated_value NUMERIC DEFAULT 0,
                    scope_phase VARCHAR(150) DEFAULT 'Rough, Final & Touch-Up Clean',
                    special_requirements TEXT,
                    estimator_name VARCHAR(150),
                    estimator_title VARCHAR(100),
                    estimator_email VARCHAR(150),
                    estimator_phone VARCHAR(50),
                    platform VARCHAR(100) DEFAULT 'BuildingConnected',
                    rfp_url TEXT,
                    plan_url TEXT,
                    status VARCHAR(50) DEFAULT 'Invited',
                    prequal_status VARCHAR(50) DEFAULT 'Ready',
                    last_contact_date TIMESTAMP WITH TIME ZONE,
                    next_action VARCHAR(255),
                    next_action_date DATE,
                    notes TEXT,
                    email_id VARCHAR(255) UNIQUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_gc_bids_status ON "ConstructionBids" (status);
                CREATE INDEX IF NOT EXISTS idx_gc_bids_due_date ON "ConstructionBids" (bid_due_date);
                CREATE INDEX IF NOT EXISTS idx_gc_bids_gc_name ON "ConstructionBids" (gc_name);
            ''')

            # 2. Provision Table: InstitutionalBids if not exists
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
                CREATE INDEX IF NOT EXISTS idx_inst_bids_solicitation ON "InstitutionalBids" (solicitation_number);
                CREATE INDEX IF NOT EXISTS idx_inst_bids_agency ON "InstitutionalBids" (agency_name);
                CREATE INDEX IF NOT EXISTS idx_inst_bids_due_date ON "InstitutionalBids" (bid_due_date);
                CREATE INDEX IF NOT EXISTS idx_inst_bids_status ON "InstitutionalBids" (status);
            ''')

            # 3. Seed ConstructionBids from dump file
            json_paths = [
                os.path.join(os.path.dirname(__file__), 'construction_bids_dump.json'),
                os.path.join(os.path.dirname(__file__), '..', 'scripts', 'construction_bids_dump.json'),
                '/app/scripts/construction_bids_dump.json',
            ]
            dump_data = None
            for jp in json_paths:
                if os.path.exists(jp):
                    with open(jp, 'r') as jf:
                        dump_data = json.load(jf)
                    print(f"  ✓ Loaded bids dataset from {jp} ({len(dump_data)} records).", flush=True)
                    break

            if dump_data:
                cb_inserted = 0
                cb_updated = 0
                for b in dump_data:
                    email_id = b.get('email_id')
                    if email_id:
                        cur.execute('''
                            INSERT INTO "ConstructionBids" (
                                gc_name, project_name, project_address, city, state, zipcode,
                                bid_due_date, estimated_start_date, estimated_end_date,
                                cleanable_sqft, estimated_value, scope_phase, special_requirements,
                                estimator_name, estimator_title, estimator_email, estimator_phone,
                                platform, rfp_url, plan_url, status, prequal_status,
                                next_action, next_action_date, notes, email_id, created_at, updated_at
                            ) VALUES (
                                %(gc_name)s, %(project_name)s, %(project_address)s, %(city)s, %(state)s, %(zipcode)s,
                                %(bid_due_date)s, %(estimated_start_date)s, %(estimated_end_date)s,
                                %(cleanable_sqft)s, %(estimated_value)s, %(scope_phase)s, %(special_requirements)s,
                                %(estimator_name)s, %(estimator_title)s, %(estimator_email)s, %(estimator_phone)s,
                                %(platform)s, %(rfp_url)s, %(plan_url)s, %(status)s, %(prequal_status)s,
                                %(next_action)s, %(next_action_date)s, %(notes)s, %(email_id)s,
                                COALESCE(%(created_at)s::timestamptz, NOW()), COALESCE(%(updated_at)s::timestamptz, NOW())
                            )
                            ON CONFLICT (email_id) DO UPDATE SET
                                gc_name = EXCLUDED.gc_name,
                                project_name = EXCLUDED.project_name,
                                status = EXCLUDED.status,
                                estimated_value = CASE WHEN EXCLUDED.estimated_value > 0 THEN EXCLUDED.estimated_value ELSE "ConstructionBids".estimated_value END,
                                cleanable_sqft = CASE WHEN EXCLUDED.cleanable_sqft > 0 THEN EXCLUDED.cleanable_sqft ELSE "ConstructionBids".cleanable_sqft END,
                                updated_at = NOW();
                        ''', b)
                        cb_inserted += 1
                    else:
                        # Check by gc_name + project_name + cleanable_sqft
                        cur.execute('''
                            SELECT id FROM "ConstructionBids"
                            WHERE gc_name = %(gc_name)s AND project_name = %(project_name)s
                              AND cleanable_sqft = %(cleanable_sqft)s;
                        ''', b)
                        exists = cur.fetchone()
                        if not exists:
                            cur.execute('''
                                INSERT INTO "ConstructionBids" (
                                    gc_name, project_name, project_address, city, state, zipcode,
                                    bid_due_date, estimated_start_date, estimated_end_date,
                                    cleanable_sqft, estimated_value, scope_phase, special_requirements,
                                    estimator_name, estimator_title, estimator_email, estimator_phone,
                                    platform, rfp_url, plan_url, status, prequal_status,
                                    next_action, next_action_date, notes, created_at, updated_at
                                ) VALUES (
                                    %(gc_name)s, %(project_name)s, %(project_address)s, %(city)s, %(state)s, %(zipcode)s,
                                    %(bid_due_date)s, %(estimated_start_date)s, %(estimated_end_date)s,
                                    %(cleanable_sqft)s, %(estimated_value)s, %(scope_phase)s, %(special_requirements)s,
                                    %(estimator_name)s, %(estimator_title)s, %(estimator_email)s, %(estimator_phone)s,
                                    %(platform)s, %(rfp_url)s, %(plan_url)s, %(status)s, %(prequal_status)s,
                                    %(next_action)s, %(next_action_date)s, %(notes)s,
                                    COALESCE(%(created_at)s::timestamptz, NOW()), COALESCE(%(updated_at)s::timestamptz, NOW())
                                );
                            ''', b)
                            cb_inserted += 1

                print(f"  ✓ Processed {cb_inserted} ConstructionBids records.", flush=True)

            # 4. Sync sequences
            cur.execute('''
                SELECT setval(pg_get_serial_sequence('"ConstructionBids"', 'id'), COALESCE(MAX(id), 1))
                FROM "ConstructionBids";
            ''')
            cur.execute('''
                SELECT setval(pg_get_serial_sequence('"InstitutionalBids"', 'id'), COALESCE(MAX(id), 1))
                FROM "InstitutionalBids";
            ''')

            # 5. Verify Institutional Bids baseline
            inst_records = [
                {
                    "solicitation_number": "06507-NTT-00-GS-MA",
                    "title": "Janitorial Services for Ancillary Facilities",
                    "agency_name": "North Texas Tollway Authority",
                    "sector": "Transportation & Infrastructure",
                    "portal_name": "NTTA Marketplace",
                    "portal_doc_id": "B2600001083",
                    "procurement_officer": "Kimberly Madewell",
                    "officer_email": "kmadewell@ntta.org",
                    "officer_phone": "(214) 461-2000",
                    "contract_term_months": 24,
                    "cleanable_sqft": 38367,
                    "facilities_count": 9,
                    "published_budget": 276323.00,
                    "hwb_bid_total": 273238.58,
                    "monthly_base_rate": 7475.69,
                    "annual_base_rate": 89708.28,
                    "hourly_porter_rate": 21.75,
                    "bid_due_date": "2026-10-07 16:00:00+00",
                    "status": "Pre-Bid Scheduled",
                    "compliance_status": "Package Unified & Ready",
                    "compliance_summary": "100% compliant with NTTA Special Provisions. COI $2M statutory umbrella, HUB certified partnership, OSHA-30 certified supervisor.",
                    "notes": "9 facilities across Collin, Dallas, and Denton counties. 24-month base term with optional 2-year renewal."
                },
                {
                    "solicitation_number": "FY2024-RFP-005",
                    "title": "District Janitorial Services - Frisco Campus (Incumbent Tracking)",
                    "agency_name": "Collin County Community College District",
                    "sector": "Higher Education",
                    "portal_name": "Collin College Purchasing",
                    "portal_doc_id": "CSP-2026-088",
                    "procurement_officer": "Collin Purchasing Director",
                    "officer_email": "purchasing@collin.edu",
                    "officer_phone": "(972) 599-3100",
                    "contract_term_months": 36,
                    "cleanable_sqft": 485000,
                    "facilities_count": 10,
                    "published_budget": 5200000.00,
                    "hwb_bid_total": 4890000.00,
                    "monthly_base_rate": 135833.33,
                    "annual_base_rate": 1630000.00,
                    "hourly_porter_rate": 22.50,
                    "status": "Incumbent Intelligence",
                    "compliance_status": "Pre-RFP Scouting",
                    "compliance_summary": "Tier 3 Proposal Ready. 10 Campus buildings. Day porter and night scrub rotation.",
                    "notes": "Campus walk completed. High-priority public sector account."
                }
            ]

            for ir in inst_records:
                cur.execute('''
                    INSERT INTO "InstitutionalBids" (
                        solicitation_number, title, agency_name, sector, portal_name, portal_doc_id,
                        procurement_officer, officer_email, officer_phone, contract_term_months,
                        cleanable_sqft, facilities_count, published_budget, hwb_bid_total,
                        monthly_base_rate, annual_base_rate, hourly_porter_rate,
                        bid_due_date, status, compliance_status, compliance_summary, notes
                    ) VALUES (
                        %(solicitation_number)s, %(title)s, %(agency_name)s, %(sector)s, %(portal_name)s, %(portal_doc_id)s,
                        %(procurement_officer)s, %(officer_email)s, %(officer_phone)s, %(contract_term_months)s,
                        %(cleanable_sqft)s, %(facilities_count)s, %(published_budget)s, %(hwb_bid_total)s,
                        %(monthly_base_rate)s, %(annual_base_rate)s, %(hourly_porter_rate)s,
                        %(bid_due_date)s, %(status)s, %(compliance_status)s, %(compliance_summary)s, %(notes)s
                    )
                    ON CONFLICT (solicitation_number) DO UPDATE SET
                        hwb_bid_total = EXCLUDED.hwb_bid_total,
                        status = EXCLUDED.status,
                        compliance_status = EXCLUDED.compliance_status,
                        updated_at = NOW();
                ''', {
                    **ir,
                    'bid_due_date': ir.get('bid_due_date')
                })

            # Check counts
            cur.execute('SELECT COUNT(*), COALESCE(SUM(estimated_value), 0) FROM "ConstructionBids";')
            cbc, cbv = cur.fetchone()
            cur.execute('SELECT COUNT(*), COALESCE(SUM(hwb_bid_total), 0) FROM "InstitutionalBids";')
            ibc, ibv = cur.fetchone()

            conn.commit()
            print(f"  ✓ Migration 022 complete: {cbc} Construction Bids (${cbv:,.2f}), {ibc} Institutional Bids (${ibv:,.2f}).", flush=True)

    except Exception as e:
        conn.rollback()
        print(f"  ✗ Migration 022 failed: {e}", file=sys.stderr, flush=True)
        raise e
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()
