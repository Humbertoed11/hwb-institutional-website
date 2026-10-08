"""
Migration 039: Add Remote Sales, Outside Sales & Account Executive Positions
Standard: HWB-QMS-7.2 (Job Description & Position Catalog)
Authority: Humberto Dominguez (CEO) - Approved 10/08/2026
Architect: George (Systems Architect & mbB)

Inserts official digital job descriptions for:
1. HWB-POS-005: Remote B2B Sales Representative
2. HWB-POS-006: Outside Commercial Sales Representative
3. HWB-POS-007: Commercial Account Executive
"""

import os
import json
import psycopg2
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

SALES_POSITIONS = [
    {
        "position_code": "HWB-POS-005",
        "title": "Remote B2B Sales Representative",
        "department": "Sales & Marketing",
        "reports_to": "Department Head",
        "summary": "Conducts high-volume remote outbound calling, prospect qualification, and scheduling of on-site commercial cleaning walkthroughs across Texas metropolitan markets.",
        "key_responsibilities": [
            "Execute daily outbound telephone outreach to commercial facilities, daycares, corporate offices, and medical centers.",
            "Qualify prospective client building size, cleaning frequency, and current service pain points.",
            "Schedule confirmed on-site walkthrough appointments for outside commercial sales representatives.",
            "Send professional follow-up emails and introductory service overviews using standardized letterheads.",
            "Log call activities, contact updates, and callback dates accurately in the HWB backoffice CRM."
        ],
        "required_competencies": [
            "High-energy professional phone communication and objection handling",
            "CRM data entry discipline and lead pipeline status tracking",
            "B2B cold outreach and telephone discovery questioning",
            "Google Calendar and Microsoft Outlook appointment scheduling"
        ],
        "required_experience": "1+ Years B2B Phone Sales, Appointment Setting, or Customer Outreach",
        "required_certifications": [
            "Paid Company Sales Training",
            "HWB Lead Calling & CRM Compliance Certification"
        ],
        "physical_demands": "Prolonged sitting at computer workstation with telephone headset; dedicated quiet home office environment.",
        "work_environment": "100% Remote / Work from Home. High-speed internet connection required. Monday through Friday business hours.",
        "hourly_min": 18.00,
        "hourly_max": 22.00,
        "standard_weekly_hours": 40.0
    },
    {
        "position_code": "HWB-POS-006",
        "title": "Outside Commercial Sales Representative",
        "department": "Sales & Marketing",
        "reports_to": "Department Head",
        "summary": "Conducts on-site commercial property walkthroughs, measures facility square footage, presents janitorial service proposals, and closes recurring commercial contracts across Dallas-Fort Worth.",
        "key_responsibilities": [
            "Conduct in-person walkthroughs of commercial offices, private schools, medical facilities, and industrial warehouses across DFW.",
            "Measure cleanable square footage and document floor types, restroom fixture counts, and specialized scope needs.",
            "Present customized cleaning scopes of work and monthly service agreements directly to property managers and business owners.",
            "Close recurring commercial janitorial contracts and post-construction cleaning projects to meet monthly revenue targets.",
            "Coordinate initial service startup with operations site supervisors to ensure flawless first-day client onboarding."
        ],
        "required_competencies": [
            "Face-to-face commercial contract negotiation and consultative selling",
            "Accurate field measurement and scope takeoff calculation",
            "Professional presentation and client relationship development",
            "DFW metropolitan market geography and driving efficiency"
        ],
        "required_experience": "2+ Years Outside B2B Sales (Commercial Facilities or Construction Subcontracting Preferred)",
        "required_certifications": [
            "Valid Texas Driver License & Clean Driving Record",
            "Commercial Cleaning Estimating & Scope Formulation"
        ],
        "physical_demands": "Active facility walkthroughs (climbing stairs, inspecting multi-story buildings), driving throughout DFW, carrying presentation materials.",
        "work_environment": "Field-based commercial properties across Dallas, Fort Worth, Arlington, and Plano. Professional business attire required.",
        "hourly_min": 21.63,  # Base salary $45k + commission
        "hourly_max": 26.44,  # Base salary $55k + commission
        "standard_weekly_hours": 40.0
    },
    {
        "position_code": "HWB-POS-007",
        "title": "Commercial Account Executive",
        "department": "Executive Sales",
        "reports_to": "Department Head",
        "summary": "Develops high-ticket commercial accounts, negotiates multi-facility enterprise contracts, secures general contractor post-construction partnerships, and manages public institutional solicitations across Texas.",
        "key_responsibilities": [
            "Identify, pursue, and close enterprise commercial accounts generating $3,000 to $25,000+ in monthly recurring revenue.",
            "Establish master subcontractor relationships with commercial general contractors for post-construction cleanup bids.",
            "Evaluate public school district, municipal authority, and government purchasing cooperative solicitations (RFPs).",
            "Lead high-stakes contract negotiations, Master Service Agreements (MSAs), and annual contract renewal escalations.",
            "Serve as senior client relationship executive for high-profile institutional accounts, ensuring zero-defect retention."
        ],
        "required_competencies": [
            "Enterprise contract negotiation and C-suite commercial presentation",
            "Commercial general contractor bidding processes and retainage mechanics",
            "RFP review, public procurement regulations, and bid compliance",
            "Multi-year customer lifetime value and retention optimization"
        ],
        "required_experience": "3–5+ Years B2B Enterprise & Institutional Contract Sales",
        "required_certifications": [
            "Commercial Janitorial Enterprise Contract Negotiation",
            "B2G Procurement & Public Cooperative Bidding Specialist"
        ],
        "physical_demands": "Standard executive office and hybrid commercial travel; client executive boardrooms and project job sites.",
        "work_environment": "Hybrid: Corporate office, remote strategy planning, and regional Texas client executive meetings.",
        "hourly_min": 31.25,  # Base salary $65k + commission
        "hourly_max": 36.06,  # Base salary $75k + commission
        "standard_weekly_hours": 40.0
    }
]


def run_migration(db_url: Optional[str] = None):
    """Execute migration 039 to add sales and account executive positions."""
    target_url = db_url or DEFAULT_DB_URL
    print(f"[MIGRATION-039] Connecting to database: {target_url.split('@')[-1] if '@' in target_url else target_url}")

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor() as cur:
            cur.execute('ALTER TABLE "JobPositions" ALTER COLUMN required_experience TYPE character varying(255);')
            for pos in SALES_POSITIONS:
                cur.execute('SELECT id FROM "JobPositions" WHERE position_code = %s;', (pos['position_code'],))
                existing = cur.fetchone()

                if existing:
                    pos_id = existing[0]
                    cur.execute('''
                        UPDATE "JobPositions"
                        SET title = %s,
                            department = %s,
                            reports_to = %s,
                            summary = %s,
                            key_responsibilities = %s,
                            required_competencies = %s,
                            required_experience = %s,
                            required_certifications = %s,
                            physical_demands = %s,
                            work_environment = %s,
                            hourly_min = %s,
                            hourly_max = %s,
                            standard_weekly_hours = %s,
                            sop_template_id = 'HWB-FORM-7.2-001',
                            is_active = TRUE,
                            updated_at = NOW()
                        WHERE id = %s;
                    ''', (
                        pos['title'],
                        pos['department'],
                        pos['reports_to'],
                        pos['summary'],
                        json.dumps(pos['key_responsibilities']),
                        json.dumps(pos['required_competencies']),
                        pos['required_experience'],
                        json.dumps(pos['required_certifications']),
                        pos['physical_demands'],
                        pos['work_environment'],
                        pos['hourly_min'],
                        pos['hourly_max'],
                        pos['standard_weekly_hours'],
                        pos_id
                    ))
                    print(f"[MIGRATION-039] Updated existing position: {pos['position_code']} - {pos['title']} (ID: {pos_id})")
                else:
                    cur.execute('''
                        INSERT INTO "JobPositions" (
                            position_code, title, department, reports_to, summary,
                            key_responsibilities, required_competencies, required_experience,
                            required_certifications, physical_demands, work_environment,
                            hourly_min, hourly_max, standard_weekly_hours,
                            sop_template_id, is_active, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            'HWB-FORM-7.2-001', TRUE, NOW(), NOW()
                        ) RETURNING id;
                    ''', (
                        pos['position_code'],
                        pos['title'],
                        pos['department'],
                        pos['reports_to'],
                        pos['summary'],
                        json.dumps(pos['key_responsibilities']),
                        json.dumps(pos['required_competencies']),
                        pos['required_experience'],
                        json.dumps(pos['required_certifications']),
                        pos['physical_demands'],
                        pos['work_environment'],
                        pos['hourly_min'],
                        pos['hourly_max'],
                        pos['standard_weekly_hours']
                    ))
                    new_id = cur.fetchone()[0]
                    print(f"[MIGRATION-039] Created new position: {pos['position_code']} - {pos['title']} (ID: {new_id})")

            conn.commit()
            print("[MIGRATION-039] All 3 sales positions verified and committed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION-039 ERROR] Failed to execute migration: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    run_migration()
