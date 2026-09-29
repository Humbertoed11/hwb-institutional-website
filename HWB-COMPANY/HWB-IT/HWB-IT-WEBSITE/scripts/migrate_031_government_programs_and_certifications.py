#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 031: Government Programs & Certification Compliance Registry
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & HWB-QMS-8.9 Playbook
Custodians: George (Systems Architect & mbB) & Humberto Dominguez (CEO)

Objectives:
1. Create "GovernmentPrograms" master table in PostgreSQL for tracking federal, state, and regional certifications.
2. Seed verified programs: SBA 8(a), State of Texas HUB, NCTRCA MBE, NCTRCA SBE, DFW MSDC MBE, and SBA SDB.
3. Record migration idempotently in schema_migrations.
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "scripts" else CURRENT_DIR.parent.parent
WEBSITE_DIR = PROJECT_ROOT / "HWB-COMPANY" / "HWB-IT" / "HWB-IT-WEBSITE"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(WEBSITE_DIR / ".env")

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

PROGRAMS_SEED = [
    {
        "program_code": "SBA_8A",
        "program_name": "SBA 8(a) Business Development Program",
        "sponsoring_agency": "U.S. Small Business Administration (SBA)",
        "jurisdiction": "Federal",
        "benefit_tier": "Sole-Source Awards up to $4.5 Million & Set-Aside Competitions",
        "status": "Waiver Eligible / In Preparation",
        "operating_requirement": "2 Years Active (Waiver Under 13 CFR § 124.107(b))",
        "net_worth_limit": 850000.00,
        "primary_naics": "561720, 561210",
        "portal_url": "https://certifications.sba.gov",
        "api_endpoint": "https://api.sam.gov/entity-information/v3/entities",
        "readiness_score": 85,
        "required_documents": [
            "3 Years Business Tax Returns (Form 1065)",
            "3 Years Personal Tax Returns (Form 1040)",
            "SBA Form 413 (Personal Financial Statement)",
            "Social Disadvantage Narrative (Post-Ultima Ruling)",
            "Texas LLC Operating Agreement with 51% Sovereign Control",
            "Proof of U.S. Citizenship",
            "Active SAM.gov Registration (UEI & CAGE)"
        ],
        "notes": "9-year statutory term. Direct sole-source awards without competitive bidding up to $4.5M for janitorial/services. Unlocks SBA Mentor-Protégé Joint Ventures."
    },
    {
        "program_code": "TX_HUB",
        "program_name": "State of Texas Historically Underutilized Business (HUB)",
        "sponsoring_agency": "Texas Comptroller of Public Accounts",
        "jurisdiction": "State of Texas",
        "benefit_tier": "Non-Competitive Discretionary Purchases ($3,000–$50,000) & State Agency Rotation",
        "status": "Application Staged",
        "operating_requirement": "Immediate / No Minimum Time in Business",
        "net_worth_limit": None,
        "primary_naics": "561720, 238990 (NIGP 910-39, 962-58)",
        "portal_url": "https://comptroller.texas.gov/purchasing/vendor/hub/",
        "api_endpoint": "https://mycpa.cpa.state.tx.us/tpasscmblsearch/",
        "readiness_score": 95,
        "required_documents": [
            "Texas Secretary of State Certificate of Filing",
            "Texas LLC Operating Agreement",
            "IRS EIN Letter (CP-575 / 147C)",
            "Proof of Texas Resident & Hispanic / Disadvantaged Heritage",
            "Signed HUB Sworn Notarized Affidavit"
        ],
        "notes": "Under Texas Local Government Code § 252.0215, all state agencies and municipal bodies must rotate quotes to at least two certified HUBs for work under $50,000 without formal RFP cycles."
    },
    {
        "program_code": "NCTRCA_MBE",
        "program_name": "NCTRCA Minority Business Enterprise (MBE)",
        "sponsoring_agency": "North Central Texas Regional Certification Agency",
        "jurisdiction": "North Texas Regional",
        "benefit_tier": "Mandatory 23.8%–25% Prime Subcontracting Carve-Out (City of Dallas, NTTA, DFW Airport)",
        "status": "Application Staged",
        "operating_requirement": "Immediate / Verified Operational Control",
        "net_worth_limit": None,
        "primary_naics": "561720, 238990",
        "portal_url": "https://nctrca.diversitysoftware.com",
        "api_endpoint": "https://dallas.diversitycompliance.com (B2Gnow API)",
        "readiness_score": 92,
        "required_documents": [
            "Texas Certificate of Formation",
            "Operating Agreement (showing 51% unconditional ownership)",
            "Personal Resume of CEO Humberto Dominguez",
            "Bank Signature Card showing sole signature authority",
            "Commercial Lease / Operating Facility Deed",
            "Client References / 3 Commercial Contracts"
        ],
        "notes": "The primary diversity currency across DFW public entities. Mandatory for Ambassador Services ($45.8M Master Contract) and NTTA M/WBE participation."
    },
    {
        "program_code": "NCTRCA_SBE",
        "program_name": "NCTRCA Small Business Enterprise (SBE)",
        "sponsoring_agency": "North Central Texas Regional Certification Agency",
        "jurisdiction": "North Texas Regional",
        "benefit_tier": "Race & Gender-Neutral Regional Small Business Set-Asides",
        "status": "Application Staged",
        "operating_requirement": "Immediate (SBA Size Standards Compliant)",
        "net_worth_limit": 1320000.00,
        "primary_naics": "561720",
        "portal_url": "https://nctrca.diversitysoftware.com",
        "api_endpoint": "https://nctrca.diversitysoftware.com",
        "readiness_score": 95,
        "required_documents": [
            "Concurrently submitted with NCTRCA MBE application",
            "Company Balance Sheet & 3-Year Gross Receipts Summary"
        ],
        "notes": "Ensures eligibility on public bids where race/gender preferences are prohibited but small business quotas apply."
    },
    {
        "program_code": "DFW_MSDC",
        "program_name": "DFW Minority Supplier Development Council (Corporate MBE)",
        "sponsoring_agency": "Dallas Fort Worth MSDC / NMSDC",
        "jurisdiction": "National Private / Corporate",
        "benefit_tier": "Private Corporate Supply Chain Access (Toyota HQ, AT&T, American Airlines, CBRE, JLL)",
        "status": "Phase II Target",
        "operating_requirement": "1 Year Operating History & Commercial Financials",
        "net_worth_limit": None,
        "primary_naics": "561720",
        "portal_url": "https://dfwmsdc.com",
        "api_endpoint": "https://nmsdc.org",
        "readiness_score": 80,
        "required_documents": [
            "Corporate Financial Statements (P&L and Balance Sheet)",
            "LLC Formation and Governance Articles",
            "Proof of Minority Ownership & Operating Control",
            "Site Visit & Virtual Interview with Certification Committee"
        ],
        "notes": "Accepted by major Fortune 500 corporate headquarters headquartered in North Texas for private corporate facility janitorial master agreements."
    },
    {
        "program_code": "SAM_SDB",
        "program_name": "Small Disadvantaged Business (SDB) Self-Certification",
        "sponsoring_agency": "U.S. Small Business Administration / SAM.gov",
        "jurisdiction": "Federal",
        "benefit_tier": "10% Price Evaluation Adjustment & Federal Prime Subcontracting Credits",
        "status": "Active / Verified",
        "operating_requirement": "Immediate with Active SAM.gov Profile",
        "net_worth_limit": 850000.00,
        "primary_naics": "561720, 561210",
        "portal_url": "https://sam.gov",
        "api_endpoint": "https://api.sam.gov/entity-information/v3/entities",
        "readiness_score": 100,
        "required_documents": [
            "SAM.gov Active Core Data",
            "CAGE Code Assignment",
            "SBA Small Business Profile (DSBS) Synchronization"
        ],
        "notes": "Active on SAM.gov under primary NAICS 561720. Grants federal prime contractors small business utilization credits for subcontracting to HWB."
    }
]

def run_migration():
    print(f"[MIGRATION-031] Connecting to database...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # 1. Create GovernmentPrograms table
            print("[MIGRATION-031] Creating 'GovernmentPrograms' master table...")
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "GovernmentPrograms" (
                    id SERIAL PRIMARY KEY,
                    program_code VARCHAR(50) UNIQUE NOT NULL,
                    program_name VARCHAR(255) NOT NULL,
                    sponsoring_agency VARCHAR(255) NOT NULL,
                    jurisdiction VARCHAR(50) NOT NULL,
                    benefit_tier VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'Evaluating',
                    operating_requirement VARCHAR(255),
                    net_worth_limit NUMERIC(12, 2),
                    primary_naics VARCHAR(100) DEFAULT '561720',
                    portal_url TEXT,
                    api_endpoint TEXT,
                    readiness_score INTEGER DEFAULT 80,
                    required_documents JSONB DEFAULT '[]'::jsonb,
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            ''')

            # 2. Seed verified programs
            print("[MIGRATION-031] Seeding verified government programs and certifications...")
            for prog in PROGRAMS_SEED:
                cur.execute('''
                    INSERT INTO "GovernmentPrograms" (
                        program_code, program_name, sponsoring_agency, jurisdiction,
                        benefit_tier, status, operating_requirement, net_worth_limit,
                        primary_naics, portal_url, api_endpoint, readiness_score,
                        required_documents, notes
                    ) VALUES (
                        %(program_code)s, %(program_name)s, %(sponsoring_agency)s, %(jurisdiction)s,
                        %(benefit_tier)s, %(status)s, %(operating_requirement)s, %(net_worth_limit)s,
                        %(primary_naics)s, %(portal_url)s, %(api_endpoint)s, %(readiness_score)s,
                        %(required_documents)s, %(notes)s
                    )
                    ON CONFLICT (program_code) DO UPDATE SET
                        program_name = EXCLUDED.program_name,
                        sponsoring_agency = EXCLUDED.sponsoring_agency,
                        jurisdiction = EXCLUDED.jurisdiction,
                        benefit_tier = EXCLUDED.benefit_tier,
                        status = EXCLUDED.status,
                        operating_requirement = EXCLUDED.operating_requirement,
                        net_worth_limit = EXCLUDED.net_worth_limit,
                        primary_naics = EXCLUDED.primary_naics,
                        portal_url = EXCLUDED.portal_url,
                        api_endpoint = EXCLUDED.api_endpoint,
                        readiness_score = EXCLUDED.readiness_score,
                        required_documents = EXCLUDED.required_documents,
                        notes = EXCLUDED.notes,
                        updated_at = CURRENT_TIMESTAMP;
                ''', {
                    "program_code": prog["program_code"],
                    "program_name": prog["program_name"],
                    "sponsoring_agency": prog["sponsoring_agency"],
                    "jurisdiction": prog["jurisdiction"],
                    "benefit_tier": prog["benefit_tier"],
                    "status": prog["status"],
                    "operating_requirement": prog["operating_requirement"],
                    "net_worth_limit": prog["net_worth_limit"],
                    "primary_naics": prog["primary_naics"],
                    "portal_url": prog["portal_url"],
                    "api_endpoint": prog["api_endpoint"],
                    "readiness_score": prog["readiness_score"],
                    "required_documents": json.dumps(prog["required_documents"]),
                    "notes": prog["notes"]
                })

            # 3. Log to schema_migrations idempotently
            cur.execute('''
                INSERT INTO schema_migrations (version, description)
                VALUES ('031_government_programs_and_certifications', 'GovernmentPrograms master table and seed verified programs')
                ON CONFLICT (version) DO NOTHING;
            ''')

            conn.commit()
            print("[MIGRATION-031] SUCCESS: GovernmentPrograms table created and 6 programs seeded.")

    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION-031] ERROR: Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
