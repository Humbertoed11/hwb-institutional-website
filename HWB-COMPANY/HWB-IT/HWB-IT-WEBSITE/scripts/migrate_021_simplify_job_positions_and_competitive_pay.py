"""
Migration 021: Simplify Job Positions & Calibrate Competitive Pay
Standard: Everyday Words Public Recruitment Protocol
Authority: Humberto Dominguez (CEO) - Approved 09/22/2026
Architect: George (Systems Architect & mbB)
"""

import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

JOB_POSITIONS_UPDATE = [
    {
        "position_code": "HWB-POS-001",
        "title": "Commercial Cleaning Technician",
        "department": "Operations",
        "reports_to": "Site Supervisor / Operations Manager",
        "summary": "Performs routine commercial janitorial and sanitization services across North Texas public facilities, corporate offices, and educational campuses.",
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
            "Paid Company Safety Training"
        ],
        "physical_demands": "Must be able to stand and walk for up to 8 hours, lift up to 45 lbs, and perform repetitive bending, stretching, and reaching.",
        "work_environment": "Commercial offices, public facilities, and educational buildings. Evening and night shifts.",
        "hourly_min": 14.00,
        "hourly_max": 16.50,
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
            "Maintain equipment inspection check sheets and execute daily post-operation washdowns.",
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
        "hourly_min": 17.00,
        "hourly_max": 20.00,
        "standard_weekly_hours": 40.0
    },
    {
        "position_code": "HWB-POS-003",
        "title": "Lead Cleaning Site Supervisor",
        "department": "Supervision",
        "reports_to": "Vice President of Operations / CEO",
        "summary": "Leads on-site technician crews, performs quality assurance inspections, manages building security keys, and interfaces with facility managers.",
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
            "Lead Supervisor Safety & Quality Training",
            "First Aid / CPR Certified"
        ],
        "physical_demands": "Active facility walkthroughs (10,000+ steps per shift), light lifting (up to 30 lbs), standing for extended periods.",
        "work_environment": "Multi-building campus facilities, municipal centers, and school districts.",
        "hourly_min": 19.50,
        "hourly_max": 23.50,
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
        "hourly_min": 18.50,
        "hourly_max": 22.00,
        "standard_weekly_hours": 40.0
    }
]


def run_migration(db_url: str = None):
    target_url = db_url or DB_URL
    print("\n=======================================================")
    print("  Applying Migration 021: Simplify Job Positions")
    print("=======================================================")

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor() as cur:
            for pos in JOB_POSITIONS_UPDATE:
                cur.execute("""
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
                        updated_at = NOW()
                    WHERE position_code = %s;
                """, (
                    pos["title"], pos["department"], pos["reports_to"], pos["summary"],
                    json.dumps(pos["key_responsibilities"]), json.dumps(pos["required_competencies"]),
                    pos["required_experience"], json.dumps(pos["required_certifications"]),
                    pos["physical_demands"], pos["work_environment"],
                    pos["hourly_min"], pos["hourly_max"], pos["standard_weekly_hours"],
                    pos["position_code"]
                ))
            conn.commit()
            print(f"  ✓ Successfully updated {len(JOB_POSITIONS_UPDATE)} Job Positions with everyday language and calibrated pay.")
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
