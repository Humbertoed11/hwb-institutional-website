"""
Migration 024: SigmaFidelity™ Bidding Evolution — Digital Bid Room, Addenda Sentinel, RFIs & McNamara-O'Hara SCA Engine
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & HWB-QMS-7.7 Estimating SOP
Authority: Humberto Dominguez (CEO) - Approved 09/22/2026
Architect: George (Systems Architect & mbB)
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

def run_migration(db_url: str = None):
    target_url = db_url or DB_URL
    print("\n==================================================================", flush=True)
    print("  Applying Migration 024: Bidding Evolution, Bid Vault & SCA Engine", flush=True)
    print("==================================================================", flush=True)

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor() as cur:
            # 1. Provision Table: BidDocuments (The Centralized Digital Bid Room)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "BidDocuments" (
                    id SERIAL PRIMARY KEY,
                    bid_type VARCHAR(50) NOT NULL, -- 'ConstructionBid', 'InstitutionalBid', 'FederalBid'
                    construction_bid_id INTEGER REFERENCES "ConstructionBids"(id) ON DELETE CASCADE,
                    institutional_bid_id INTEGER REFERENCES "InstitutionalBids"(id) ON DELETE CASCADE,
                    document_name VARCHAR(255) NOT NULL,
                    document_type VARCHAR(50) NOT NULL DEFAULT 'Other', -- 'Spec', 'Drawing', 'Addendum', 'RFI', 'Submittal', 'COI', 'Takeoff', 'WageDetermination'
                    file_path TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    mime_type VARCHAR(100) DEFAULT 'application/pdf',
                    file_hash VARCHAR(64),
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_biddocs_const_id ON "BidDocuments"(construction_bid_id);
                CREATE INDEX IF NOT EXISTS idx_biddocs_inst_id ON "BidDocuments"(institutional_bid_id);
                CREATE INDEX IF NOT EXISTS idx_biddocs_doc_type ON "BidDocuments"(document_type);
            ''')
            print("  ✓ Provisioned Table 'BidDocuments' and indexes.", flush=True)

            # 2. Provision Table: BidAddenda (The Addendum Change Sentinel)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "BidAddenda" (
                    id SERIAL PRIMARY KEY,
                    bid_type VARCHAR(50) NOT NULL DEFAULT 'ConstructionBid',
                    construction_bid_id INTEGER REFERENCES "ConstructionBids"(id) ON DELETE CASCADE,
                    institutional_bid_id INTEGER REFERENCES "InstitutionalBids"(id) ON DELETE CASCADE,
                    addendum_number VARCHAR(50) NOT NULL,
                    issue_date TIMESTAMP WITH TIME ZONE,
                    revised_bid_due_date TIMESTAMP WITH TIME ZONE,
                    summary_of_changes TEXT NOT NULL,
                    scope_impact VARCHAR(100) DEFAULT 'No Scope Change', -- 'No Scope Change', 'Scope Added', 'Scope Reduced', 'Schedule Changed Only'
                    is_acknowledged BOOLEAN DEFAULT FALSE,
                    acknowledged_by VARCHAR(100),
                    acknowledged_at TIMESTAMP WITH TIME ZONE,
                    source_email_id VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_bidaddenda_const_id ON "BidAddenda"(construction_bid_id);
                CREATE INDEX IF NOT EXISTS idx_bidaddenda_inst_id ON "BidAddenda"(institutional_bid_id);
                CREATE INDEX IF NOT EXISTS idx_bidaddenda_ack ON "BidAddenda"(is_acknowledged);
            ''')
            print("  ✓ Provisioned Table 'BidAddenda' and indexes.", flush=True)

            # 3. Provision Table: BidRFIs (Requests for Information Tracker)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "BidRFIs" (
                    id SERIAL PRIMARY KEY,
                    bid_type VARCHAR(50) NOT NULL DEFAULT 'ConstructionBid',
                    construction_bid_id INTEGER REFERENCES "ConstructionBids"(id) ON DELETE CASCADE,
                    institutional_bid_id INTEGER REFERENCES "InstitutionalBids"(id) ON DELETE CASCADE,
                    rfi_number VARCHAR(50) NOT NULL,
                    subject VARCHAR(255) NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT,
                    date_submitted TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    date_answered TIMESTAMP WITH TIME ZONE,
                    status VARCHAR(50) DEFAULT 'Submitted', -- 'Draft', 'Submitted', 'Answered', 'Closed'
                    impact_summary TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_bidrfis_const_id ON "BidRFIs"(construction_bid_id);
                CREATE INDEX IF NOT EXISTS idx_bidrfis_inst_id ON "BidRFIs"(institutional_bid_id);
                CREATE INDEX IF NOT EXISTS idx_bidrfis_status ON "BidRFIs"(status);
            ''')
            print("  ✓ Provisioned Table 'BidRFIs' and indexes.", flush=True)

            # 4. Provision Table: ScaWageDeterminations (McNamara-O'Hara Federal Wage Floors)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "ScaWageDeterminations" (
                    id SERIAL PRIMARY KEY,
                    wd_number VARCHAR(100) NOT NULL,
                    revision_number INTEGER DEFAULT 1,
                    state VARCHAR(10) DEFAULT 'TX',
                    counties TEXT NOT NULL,
                    occupation_code VARCHAR(50) NOT NULL,
                    occupation_title VARCHAR(150) NOT NULL,
                    base_hourly_wage NUMERIC(8,2) NOT NULL,
                    health_welfare_hourly NUMERIC(8,2) DEFAULT 4.98,
                    health_welfare_eo13706 NUMERIC(8,2) DEFAULT 4.98,
                    health_welfare_standard NUMERIC(8,2) DEFAULT 5.36,
                    paid_holidays_count INTEGER DEFAULT 11,
                    vacation_rules TEXT DEFAULT '2 weeks paid vacation after 1 year of service',
                    effective_date DATE DEFAULT '2026-01-01',
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_scawd_state ON "ScaWageDeterminations"(state);
                CREATE INDEX IF NOT EXISTS idx_scawd_occupation ON "ScaWageDeterminations"(occupation_title);
                CREATE INDEX IF NOT EXISTS idx_scawd_number ON "ScaWageDeterminations"(wd_number);
            ''')
            print("  ✓ Provisioned Table 'ScaWageDeterminations' and indexes.", flush=True)

            # 5. Seed Empirical DOL Wage Determinations for North & Central Texas
            sca_seeds = [
                (
                    '2015-5231', 25, 'TX', 'Collin, Dallas, Denton, Ellis, Kaufman, Rockwall, Tarrant',
                    '11150', 'Janitor / Custodian', 16.54, 4.98, 4.98, 5.36, 11,
                    '1 week paid after 1 year; 2 weeks after 2 years; 3 weeks after 5 years; 4 weeks after 15 years.',
                    'DOL Wage Determination 2015-5231 Rev 25 (DFW Metropolitan Area)'
                ),
                (
                    '2015-5231', 25, 'TX', 'Collin, Dallas, Denton, Ellis, Kaufman, Rockwall, Tarrant',
                    '11330', 'Window Cleaner', 17.85, 4.98, 4.98, 5.36, 11,
                    '1 week paid after 1 year; 2 weeks after 2 years; 3 weeks after 5 years; 4 weeks after 15 years.',
                    'DOL Wage Determination 2015-5231 Rev 25 (Commercial Window Cleaning Spec)'
                ),
                (
                    '2015-5231', 25, 'TX', 'Collin, Dallas, Denton, Ellis, Kaufman, Rockwall, Tarrant',
                    '11122', 'Floor Care Specialist / Buffer', 17.10, 4.98, 4.98, 5.36, 11,
                    '1 week paid after 1 year; 2 weeks after 2 years; 3 weeks after 5 years; 4 weeks after 15 years.',
                    'DOL Wage Determination 2015-5231 Rev 25 (Hard Surface Floor Restorative)'
                ),
                (
                    '2015-5231', 25, 'TX', 'Collin, Dallas, Denton, Ellis, Kaufman, Rockwall, Tarrant',
                    '11210', 'Janitorial Lead / Working Supervisor', 19.50, 4.98, 4.98, 5.36, 11,
                    '1 week paid after 1 year; 2 weeks after 2 years; 3 weeks after 5 years; 4 weeks after 15 years.',
                    'DOL Wage Determination 2015-5231 Rev 25 (Shift Lead & Quality Assurance)'
                ),
                (
                    '2015-5253', 24, 'TX', 'McLennan, Bell, Coryell, Falls',
                    '11150', 'Janitor / Custodian', 15.82, 4.98, 4.98, 5.36, 11,
                    '1 week paid after 1 year; 2 weeks after 2 years; 3 weeks after 5 years.',
                    'DOL Wage Determination 2015-5253 Rev 24 (Waco / Fort Cavazos Region)'
                ),
                (
                    '2015-5215', 25, 'TX', 'Bexar, Comal, Guadalupe',
                    '11150', 'Janitor / Custodian', 16.12, 4.98, 4.98, 5.36, 11,
                    '1 week paid after 1 year; 2 weeks after 2 years; 3 weeks after 5 years.',
                    'DOL Wage Determination 2015-5215 Rev 25 (San Antonio / Fort Sam Houston)'
                )
            ]

            for wd_num, rev, st, counties, code, title, base, hw, hw_eo, hw_std, hol, vac, notes in sca_seeds:
                cur.execute('''
                    SELECT id FROM "ScaWageDeterminations"
                    WHERE wd_number = %s AND occupation_code = %s;
                ''', (wd_num, code))
                if not cur.fetchone():
                    cur.execute('''
                        INSERT INTO "ScaWageDeterminations" (
                            wd_number, revision_number, state, counties,
                            occupation_code, occupation_title, base_hourly_wage,
                            health_welfare_hourly, health_welfare_eo13706, health_welfare_standard,
                            paid_holidays_count, vacation_rules, notes
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    ''', (wd_num, rev, st, counties, code, title, base, hw, hw_eo, hw_std, hol, vac, notes))
                    print(f"  ✓ Seeded DOL SCA baseline for {title} ({counties[:20]}...: ${base}/hr).", flush=True)

            conn.commit()
            print("--- Migration 024 Applied Successfully ---\n", flush=True)
    except Exception as e:
        conn.rollback()
        print(f"FAILED: Migration 024 encountered error: {str(e)}", flush=True)
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
