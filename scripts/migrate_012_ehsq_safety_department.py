"""
Migration 012: Safety & EHSQ Department Architecture
Standard: HWB-QMS-5.7 Departmental Parity and Functional Operations Standard SOP
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
Purpose: Creates SafetyManuals, JobHazardAnalyses, and SafetyIncidents tables.
         Seeds active safety manuals (HWB-EHS-001, HWB-EHS-002, HWB-EHS-003) and empirical JHAs.
"""

import os
import sys
import psycopg2
from datetime import datetime, date

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL not set in environment.")
    sys.exit(1)

def run_migration():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- Starting Migration 012: Safety & EHSQ Department ---")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Check if already applied
        cur.execute("SELECT version FROM schema_migrations WHERE version = '012_ehsq_safety_department';")
        if cur.fetchone():
            print("[INFO] Migration 012_ehsq_safety_department already applied. Skipping schema creation.")
            conn.close()
            return

        print("[STEP 1] Creating Safety & EHSQ relational tables...")

        # 2. Table: SafetyManuals
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "SafetyManuals" (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                title VARCHAR(255) NOT NULL,
                subtitle VARCHAR(255),
                department VARCHAR(50) DEFAULT 'EHSQ',
                version VARCHAR(20) DEFAULT '1.0.0',
                status VARCHAR(50) DEFAULT 'APPROVED',
                regulatory_scope VARCHAR(255) NOT NULL,
                target_sector VARCHAR(100) NOT NULL,
                docx_url VARCHAR(255) NOT NULL,
                html_url VARCHAR(255) NOT NULL,
                approved_by VARCHAR(100) DEFAULT 'Humberto Dominguez, CEO',
                approval_date DATE DEFAULT '2026-09-21',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_safetymanuals_code ON "SafetyManuals"(code);
            CREATE INDEX IF NOT EXISTS idx_safetymanuals_status ON "SafetyManuals"(status);
        """)

        # 3. Table: JobHazardAnalyses (JHA)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "JobHazardAnalyses" (
                id SERIAL PRIMARY KEY,
                jha_number VARCHAR(50) UNIQUE NOT NULL,
                project_name VARCHAR(255) NOT NULL,
                location VARCHAR(255) NOT NULL,
                facility_type VARCHAR(100) NOT NULL,
                inspection_date DATE NOT NULL,
                lead_inspector VARCHAR(100) NOT NULL,
                hazards_identified TEXT NOT NULL,
                ppe_mandates TEXT NOT NULL,
                engineering_controls TEXT NOT NULL,
                crew_count INTEGER DEFAULT 1,
                status VARCHAR(50) DEFAULT 'Active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_jha_number ON "JobHazardAnalyses"(jha_number);
            CREATE INDEX IF NOT EXISTS idx_jha_date ON "JobHazardAnalyses"(inspection_date);
        """)

        # 4. Table: SafetyIncidents (Zero-Tolerance & Poka-Yoke CEO Reporting Gate)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "SafetyIncidents" (
                id SERIAL PRIMARY KEY,
                incident_number VARCHAR(50) UNIQUE NOT NULL,
                incident_date DATE NOT NULL,
                incident_type VARCHAR(50) NOT NULL, -- Near-Miss, First Aid, OSHA Recordable, Property Damage
                location VARCHAR(255) NOT NULL,
                person_involved VARCHAR(100),
                description TEXT NOT NULL,
                corrective_action TEXT,
                days_away_from_work INTEGER DEFAULT 0,
                ceo_reviewed BOOLEAN DEFAULT FALSE,
                status VARCHAR(50) DEFAULT 'Logged',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_incident_number ON "SafetyIncidents"(incident_number);
            CREATE INDEX IF NOT EXISTS idx_incident_date ON "SafetyIncidents"(incident_date);
        """)

        print("[STEP 2] Seeding active Safety Manuals into \"SafetyManuals\"...")
        manuals = [
            (
                'HWB-EHS-001',
                'Master Environmental Health and Safety (EHS) Manual',
                'Corporate Safety Governance, Hazard Communication GHS & Regulatory Compliance',
                'EHSQ',
                '3.0.0',
                'APPROVED',
                'ISO 45001:2018 | OSHA 29 CFR 1910 & 29 CFR 1926',
                'Company-Wide Commercial Operations',
                '/static/ehsq/HWB-EHS-001-Master-Safety-Manual.docx',
                '/static/ehsq/HWB-EHS-001.html',
                'Humberto Dominguez, CEO',
                date(2026, 9, 21)
            ),
            (
                'HWB-EHS-002',
                'Construction Site Safety and Silica Dust Control Plan (CSSP)',
                'Rough, Final & Touch-Up Post-Construction Cleaning Safety Program',
                'EHSQ',
                '1.0.0',
                'APPROVED',
                'CSI MasterFormat Div 01 35 23 & 01 74 00 | OSHA 29 CFR 1926.1153',
                'General Contractors & Construction Jobsites',
                '/static/ehsq/HWB-EHS-002-Construction-Site-Safety-Plan.docx',
                '/static/ehsq/HWB-EHS-002.html',
                'Humberto Dominguez, CEO',
                date(2026, 9, 21)
            ),
            (
                'HWB-EHS-003',
                'Institutional Facilities Health and Safety Plan (IFSP)',
                'Public Sector, Multi-Facility & Occupied Campus Custodial Safety Program',
                'EHSQ',
                '1.0.0',
                'APPROVED',
                'OSHA 29 CFR 1910 (General Industry) | NTTA & Higher Ed Compliance',
                'Public Authorities (NTTA, Collin College, Municipalities)',
                '/static/ehsq/HWB-EHS-003-Institutional-Facility-Safety-Plan.docx',
                '/static/ehsq/HWB-EHS-003.html',
                'Humberto Dominguez, CEO',
                date(2026, 9, 21)
            )
        ]

        for m in manuals:
            cur.execute("""
                INSERT INTO "SafetyManuals" (
                    code, title, subtitle, department, version, status,
                    regulatory_scope, target_sector, docx_url, html_url,
                    approved_by, approval_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET
                    title = EXCLUDED.title,
                    subtitle = EXCLUDED.subtitle,
                    version = EXCLUDED.version,
                    status = EXCLUDED.status,
                    regulatory_scope = EXCLUDED.regulatory_scope,
                    docx_url = EXCLUDED.docx_url,
                    html_url = EXCLUDED.html_url,
                    updated_at = CURRENT_TIMESTAMP;
            """, m)

        print("[STEP 3] Seeding active empirical Job Hazard Analyses (JHAs)...")
        jhas = [
            (
                'JHA-2026-NTTA-001',
                'NTTA Ancillary Facilities Pre-Bid Site Walk Assessment',
                '1240 E. Tollway Blvd, Plano & Frisco Plazas, TX',
                'Public Transportation / Tolling Administration',
                date(2026, 9, 29),
                'Humberto Dominguez / Field Operations Supervisor',
                'High-speed highway toll lane proximity; active traffic; secure facility electronic gates; slip/trip on wet terrazzo floors; high voltage toll equipment cabinets.',
                'High-visibility reflective safety vests (ANSI Class 3); steel-toe boots (ASTM F2413); safety glasses with side shields (ANSI Z87.1+); NTTA visitor badges displayed.',
                'Stay strictly within designated pedestrian walkways; coordinate with NTTA escort vehicle; zero unauthorized photography of secure toll servers; 100% escort required.',
                2,
                'Active'
            ),
            (
                'JHA-2026-COL-001',
                'Collin College Frisco Campus High-Ceiling & Lab Sanitation Audit',
                '9700 Wade Blvd, Frisco, TX 75035',
                'Higher Education Campus & Science Laboratories',
                date(2026, 9, 21),
                'Field Operations Supervisor',
                'High-ceiling atrium dust accumulation (24 ft); wet laboratory biological chemical residue; student pedestrian traffic during class changes.',
                'Nitrile chemical gloves; eye splash goggles; slip-resistant rubber-soled footwear; high-visibility lanyard badges.',
                'MEWP scissor lift with 100% harness tie-off for high-ceiling dusting; bilingual Caution Wet Floor cones deployed at all entrances; class passing period buffer stops.',
                4,
                'Active'
            )
        ]

        for j in jhas:
            cur.execute("""
                INSERT INTO "JobHazardAnalyses" (
                    jha_number, project_name, location, facility_type,
                    inspection_date, lead_inspector, hazards_identified,
                    ppe_mandates, engineering_controls, crew_count, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (jha_number) DO UPDATE SET
                    project_name = EXCLUDED.project_name,
                    hazards_identified = EXCLUDED.hazards_identified,
                    ppe_mandates = EXCLUDED.ppe_mandates,
                    engineering_controls = EXCLUDED.engineering_controls;
            """, j)

        # 5. Record migration in schema_migrations
        cur.execute("""
            INSERT INTO schema_migrations (version, applied_at, description)
            VALUES ('012_ehsq_safety_department', CURRENT_TIMESTAMP, 'Safety & EHSQ Department schema, SafetyManuals, JobHazardAnalyses, and SafetyIncidents tables')
            ON CONFLICT DO NOTHING;
        """)

        conn.commit()
        print("[SUCCESS] Migration 012 applied successfully! Safety & EHSQ tables provisioned and seeded.")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration 012 failed: {e}")
        raise e
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()
