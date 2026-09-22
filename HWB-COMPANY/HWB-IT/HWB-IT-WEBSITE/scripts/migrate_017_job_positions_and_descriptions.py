"""
Migration 017: SigmaFidelity™ Job Positions & Digital Job Descriptions
Standard: HWB-QMS-7.2 / ISO 9001:2015 Clause 7.2 (Competence) / HWB-FORM-7.2-001
Authority: Humberto Dominguez (CEO)
Architect: George (Systems Architect & mbB)
Purpose: Establishes the authoritative PostgreSQL JobPositions table and binds digital
         job descriptions to the ATS Candidate Pool and Employee Master Dossier.
"""

import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

JOB_POSITIONS_DATA = [
    {
        "position_code": "HWB-POS-001",
        "title": "Commercial Cleaning Technician",
        "department": "Operations",
        "reports_to": "Site Supervisor / Operations Manager",
        "summary": "Performs routine, clinical commercial janitorial and sanitization services across North Texas public facilities, corporate offices, and educational campuses.",
        "key_responsibilities": [
            "Disinfect restrooms, high-touch surfaces, door handles, and fixtures per clinical protocol.",
            "Empty trash receptacles, replace liners, and transport waste to designated disposal areas.",
            "Sweep, mop, and auto-scrub hard surface flooring; vacuum carpets with HEPA filtration units.",
            "Maintain cleaning chemical dilutions according to manufacturer Safety Data Sheets (SDS).",
            "Secure client facilities upon shift completion, locking exterior doors and arming alarm systems."
        ],
        "required_competencies": [
            "Chemical dilution accuracy and SDS label comprehension",
            "Restroom multi-point clinical sanitization",
            "HEPA backpack vacuum operation",
            "Facility key & alarm code discipline"
        ],
        "required_experience": "Entry Level to 1 Year Commercial Cleaning",
        "required_certifications": [
            "OSHA HazCom (GHS Standards)",
            "OSHA Bloodborne Pathogen (BBP) Awareness",
            "HWB Site Safety Induction"
        ],
        "physical_demands": "Must be able to stand and walk for up to 8 hours, lift up to 45 lbs, and perform repetitive bending, stretching, and reaching.",
        "work_environment": "Commercial offices, public facilities, and educational buildings. Evening and night shifts.",
        "hourly_min": 16.00,
        "hourly_max": 19.00,
        "standard_weekly_hours": 40.0
    },
    {
        "position_code": "HWB-POS-002",
        "title": "Floor Care & Heavy Equipment Specialist",
        "department": "Operations",
        "reports_to": "Operations Manager",
        "summary": "Specializes in hard surface floor restoration, machine stripping, waxing, buffing, and ride-on industrial equipment operation (Tennant M20/S20).",
        "key_responsibilities": [
            "Operate Tennant M20 scrubber-sweeper and Tennant S20 ride-on industrial equipment.",
            "Execute multi-stage floor stripping, neutral rinsing, and high-solid polymer wax finishing.",
            "Perform high-speed burnishing (2000+ RPM) and ceramic tile grout deep-extraction.",
            "Maintain equipment logbooks (HWB-FORM-7.1-001) and execute daily post-operation washdowns.",
            "Enforce wet floor signage and secondary containment barriers during stripping operations."
        ],
        "required_competencies": [
            "Tennant M20 / S20 heavy equipment certified operation",
            "Multi-coat polymer wax application and curing",
            "Rotary machine balancing (175 RPM and high-speed)",
            "Chemical spill containment and pH neutralization"
        ],
        "required_experience": "2+ Years Heavy Floor Care & Machine Operation",
        "required_certifications": [
            "Tennant Industrial Equipment Operator Certification",
            "OSHA HazCom (Stripper & Wax Safety)",
            "Slip/Trip/Fall Prevention Specialist"
        ],
        "physical_demands": "Must be able to operate heavy vibrating equipment, push/pull 100+ lb machines, and lift 50 lb chemical carboys.",
        "work_environment": "Large distribution centers, public concourses, and commercial lobbies. Night shifts.",
        "hourly_min": 19.00,
        "hourly_max": 24.00,
        "standard_weekly_hours": 40.0
    },
    {
        "position_code": "HWB-POS-003",
        "title": "Lead Cleaning Site Supervisor",
        "department": "Supervision",
        "reports_to": "Vice President of Operations / CEO",
        "summary": "Leads on-site technician crews, performs quality assurance inspections (HWB-FORM-8.1), manages building security keys, and interfaces with facility managers.",
        "key_responsibilities": [
            "Supervise crew arrivals, shift assignments, and daily Scope of Work (SOW) execution.",
            "Conduct multi-point Quality Assurance inspections using standardized pass/fail criteria.",
            "Deliver on-site safety tailgates and verify Job Hazard Analyses (JHAs) before shifts.",
            "Manage facility access keys, gate passes, and alarm disarm/arm procedures.",
            "Train new technicians on clinical sanitization techniques and equipment care."
        ],
        "required_competencies": [
            "Bilingual crew communication (English / Spanish)",
            "Mobile dispatching and shift verification",
            "Root-cause inspection auditing and correction",
            "Client escalation management"
        ],
        "required_experience": "3+ Years Commercial Cleaning with 1+ Year Team Lead/Supervisor",
        "required_certifications": [
            "OSHA 10-Hour General Industry",
            "HWB Quality Auditor Certification",
            "First Aid / CPR Certified"
        ],
        "physical_demands": "Active facility walkthroughs (10,000+ steps per shift), light lifting (up to 30 lbs), standing for extended periods.",
        "work_environment": "Multi-building campus facilities, municipal centers, and school districts.",
        "hourly_min": 22.00,
        "hourly_max": 28.00,
        "standard_weekly_hours": 40.0
    },
    {
        "position_code": "HWB-POS-004",
        "title": "Cleanroom & Sanitization Technician",
        "department": "Specialized",
        "reports_to": "Technical Director / Operations Manager",
        "summary": "Executes controlled environment sanitation in ISO Class 5–8 cleanrooms, laboratories, and high-density telecom/data center facilities.",
        "key_responsibilities": [
            "Perform particle-free wiping, vacuuming, and sanitization in ISO 5-8 clean environments.",
            "Don full cleanroom PPE (bunny suits, booties, non-shedding hoods, nitrile gloves) per protocol.",
            "Utilize deionized water and non-residual disinfectant chemistries to eliminate static and particulate.",
            "Record temperature, humidity, and particle counter verifications in quality logs.",
            "Strictly adhere to sterile air shower and gowning room transition rules."
        ],
        "required_competencies": [
            "Cleanroom gowning and laminar flow protocol",
            "Zero-particle microfiber technique",
            "ESD (Electrostatic Discharge) safety awareness",
            "Strict chain-of-custody logging"
        ],
        "required_experience": "1+ Years Controlled Environment / Hospital / Lab Sanitization",
        "required_certifications": [
            "ISO 14644 Cleanroom Protocol Certification",
            "OSHA Bloodborne Pathogens",
            "Electrostatic Discharge (ESD) Awareness"
        ],
        "physical_demands": "Ability to work in fully enclosed cleanroom garments for extended durations with high dexterity.",
        "work_environment": "Semiconductor cleanrooms, data centers, biomedical laboratories, and healthcare centers.",
        "hourly_min": 20.00,
        "hourly_max": 26.00,
        "standard_weekly_hours": 40.0
    }
]


def run_migration(db_url: str):
    print("\n=======================================================")
    print("  Applying Migration 017: Job Positions & Descriptions")
    print("=======================================================")

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Create "JobPositions" Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "JobPositions" (
                    id SERIAL PRIMARY KEY,
                    position_code VARCHAR(50) UNIQUE NOT NULL,
                    title VARCHAR(100) NOT NULL,
                    department VARCHAR(50) NOT NULL,
                    reports_to VARCHAR(100) NOT NULL,
                    summary TEXT NOT NULL,
                    key_responsibilities JSONB NOT NULL,
                    required_competencies JSONB NOT NULL,
                    required_experience VARCHAR(100) NOT NULL,
                    required_certifications JSONB NOT NULL,
                    physical_demands TEXT NOT NULL,
                    work_environment TEXT NOT NULL,
                    hourly_min NUMERIC(8,2) NOT NULL,
                    hourly_max NUMERIC(8,2) NOT NULL,
                    standard_weekly_hours NUMERIC(4,1) DEFAULT 40.0,
                    is_active BOOLEAN DEFAULT TRUE,
                    sop_template_id VARCHAR(50) DEFAULT 'HWB-FORM-7.2-001',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            print("  ✓ Verified/created 'JobPositions' table.")

            # 2. Add columns to "Employees"
            cur.execute("""
                ALTER TABLE "Employees"
                ADD COLUMN IF NOT EXISTS job_position_id INTEGER REFERENCES "JobPositions"(id) ON DELETE SET NULL,
                ADD COLUMN IF NOT EXISTS job_description_acknowledged_at TIMESTAMP WITH TIME ZONE;
            """)
            print("  ✓ Added job_position_id & job_description_acknowledged_at to 'Employees'.")

            # 3. Add columns to "JobApplicants"
            cur.execute("""
                ALTER TABLE "JobApplicants"
                ADD COLUMN IF NOT EXISTS job_position_id INTEGER REFERENCES "JobPositions"(id) ON DELETE SET NULL;
            """)
            print("  ✓ Added job_position_id to 'JobApplicants'.")

            # 4. Insert or Update Job Positions
            for pos in JOB_POSITIONS_DATA:
                cur.execute("""
                    INSERT INTO "JobPositions" (
                        position_code, title, department, reports_to, summary,
                        key_responsibilities, required_competencies, required_experience,
                        required_certifications, physical_demands, work_environment,
                        hourly_min, hourly_max, standard_weekly_hours, is_active,
                        sop_template_id, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, TRUE,
                        'HWB-FORM-7.2-001', NOW()
                    )
                    ON CONFLICT (position_code) DO UPDATE SET
                        title = EXCLUDED.title,
                        department = EXCLUDED.department,
                        reports_to = EXCLUDED.reports_to,
                        summary = EXCLUDED.summary,
                        key_responsibilities = EXCLUDED.key_responsibilities,
                        required_competencies = EXCLUDED.required_competencies,
                        required_experience = EXCLUDED.required_experience,
                        required_certifications = EXCLUDED.required_certifications,
                        physical_demands = EXCLUDED.physical_demands,
                        work_environment = EXCLUDED.work_environment,
                        hourly_min = EXCLUDED.hourly_min,
                        hourly_max = EXCLUDED.hourly_max,
                        standard_weekly_hours = EXCLUDED.standard_weekly_hours,
                        updated_at = NOW();
                """, (
                    pos["position_code"], pos["title"], pos["department"], pos["reports_to"], pos["summary"],
                    json.dumps(pos["key_responsibilities"]), json.dumps(pos["required_competencies"]),
                    pos["required_experience"], json.dumps(pos["required_certifications"]),
                    pos["physical_demands"], pos["work_environment"],
                    pos["hourly_min"], pos["hourly_max"], pos["standard_weekly_hours"]
                ))
            print(f"  ✓ Seeded {len(JOB_POSITIONS_DATA)} institutional Job Positions.")

            # 5. Link existing employees based on primary_role
            cur.execute("""
                UPDATE "Employees" e
                SET job_position_id = jp.id,
                    job_description_acknowledged_at = COALESCE(e.hire_date::timestamp with time zone, NOW())
                FROM "JobPositions" jp
                WHERE e.job_position_id IS NULL
                  AND (
                      (jp.position_code = 'HWB-POS-003' AND e.primary_role ILIKE '%Supervisor%')
                      OR (jp.position_code = 'HWB-POS-002' AND e.primary_role ILIKE '%Floor%')
                      OR (jp.position_code = 'HWB-POS-004' AND (e.primary_role ILIKE '%Cleanroom%' OR e.primary_role ILIKE '%Sanitization%'))
                      OR (jp.position_code = 'HWB-POS-001' AND jp.position_code NOT IN ('HWB-POS-002', 'HWB-POS-003', 'HWB-POS-004'))
                  );
            """)
            print("  ✓ Linked existing Employees to active Job Positions.")

            # 6. Link existing JobApplicants based on desired_role
            cur.execute("""
                UPDATE "JobApplicants" a
                SET job_position_id = jp.id
                FROM "JobPositions" jp
                WHERE a.job_position_id IS NULL
                  AND (
                      (jp.position_code = 'HWB-POS-003' AND a.desired_role ILIKE '%Supervisor%')
                      OR (jp.position_code = 'HWB-POS-002' AND a.desired_role ILIKE '%Floor%')
                      OR (jp.position_code = 'HWB-POS-004' AND (a.desired_role ILIKE '%Cleanroom%' OR a.desired_role ILIKE '%Sanitization%'))
                      OR (jp.position_code = 'HWB-POS-001')
                  );
            """)
            print("  ✓ Linked existing JobApplicants to active Job Positions.")

            conn.commit()
            print("=======================================================")
            print("  Migration 017 Completed Successfully.")
            print("=======================================================\n")
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Migration 017 Failed: {e}")
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration(DB_URL)
