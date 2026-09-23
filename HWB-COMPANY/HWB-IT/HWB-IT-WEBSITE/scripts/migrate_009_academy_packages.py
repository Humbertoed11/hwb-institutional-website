"""
Migration 009: SigmaAcademy™ Role-Based Training Packages & Magic Token Delivery
Standard: HWB-QMS-7.6 Database Hardening & Schema Versioning SOP
Authority: Humberto Dominguez (CEO)
Architect: George (Systems Architect & mbB)
"""

import os
import sys
import psycopg2

def run_migration(db_url: str):
    print("[MIGRATION] Applying 009_academy_packages...")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. AcademyPackages Table (Curriculum Bundles)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "AcademyPackages" (
                    id SERIAL PRIMARY KEY,
                    package_code VARCHAR(64) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    target_role VARCHAR(100) NOT NULL,
                    description TEXT,
                    regulatory_standards VARCHAR(255),
                    price_usd NUMERIC(10,2) DEFAULT 0.00,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_academy_packages_code" ON "AcademyPackages" (package_code);
                CREATE INDEX IF NOT EXISTS "idx_academy_packages_role" ON "AcademyPackages" (target_role);
            ''')

            # 2. AcademyPackageCourses Table (Mapping Packages to Courses)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "AcademyPackageCourses" (
                    id SERIAL PRIMARY KEY,
                    package_id INTEGER REFERENCES "AcademyPackages"(id) ON DELETE CASCADE,
                    course_id INTEGER REFERENCES "AcademyCourses"(id) ON DELETE CASCADE,
                    display_order INTEGER DEFAULT 1,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(package_id, course_id)
                );
            ''')

            # 3. Add Magic Token & Assignment Fields to AcademyEnrollments
            cur.execute('''
                ALTER TABLE "AcademyEnrollments"
                ADD COLUMN IF NOT EXISTS magic_token VARCHAR(64) UNIQUE,
                ADD COLUMN IF NOT EXISTS assigned_package_code VARCHAR(64),
                ADD COLUMN IF NOT EXISTS assigned_by VARCHAR(100),
                ADD COLUMN IF NOT EXISTS due_date DATE,
                ADD COLUMN IF NOT EXISTS notification_sent BOOLEAN DEFAULT FALSE;

                CREATE INDEX IF NOT EXISTS "idx_academy_enrollments_token" ON "AcademyEnrollments" (magic_token);
                CREATE INDEX IF NOT EXISTS "idx_academy_enrollments_pkg" ON "AcademyEnrollments" (assigned_package_code);
            ''')

            # 4. Seed Standardized Role & Client Packages
            packages = [
                (
                    'PKG-CORE-W2',
                    'Commercial Custodial Baseline Pack',
                    'W-2 Cleaning Technicians & Day Porters',
                    'Mandatory onboarding safety foundation covering biomechanical power-zone lifting, chemical proportioners, bloodborne pathogen cleanup, and restroom sanitation standards.',
                    'OSHA 1910 General Industry / HWB-QMS 7.2',
                    0.00
                ),
                (
                    'PKG-COLLIN-CAMPUS',
                    'Higher-Ed Campus Facility Pack (Collin College)',
                    'Collin College Frisco Custodians & Porters',
                    'Specialized academic facility curriculum covering heavy trash handling, classroom dry-erase care, exterior plaza trash navigation, and restroom barrier safety poles.',
                    'Collin College SOW § 127 & § 197 / Custodial T&C § 132',
                    0.00
                ),
                (
                    'PKG-COLLIN-LEAD',
                    'Campus Shift Supervisor & Lead Pack',
                    'Non-Cleaning Supervisors & Shift Leads',
                    'Advanced campus supervisory pack including certified First Aid, adult CPR, AED emergency response, and digital Quality Audit defect logging.',
                    'Collin College Custodial T&C § 140 / ISO 9001 Clause 8.5',
                    0.00
                ),
                (
                    'PKG-DAYCARE-SAFE',
                    'Early Childhood Sanitization & Child Care Pack',
                    'Daycare Staff & Educational Porters',
                    'Statewide Texas HHS-compliant sanitization standards for preschools, daycares, and nursery facilities. Includes non-toxic dwell times and diaper table sanitizing.',
                    'Texas HHS Child Care Regulations / B2B SaaS ($149/mo)',
                    149.00
                ),
                (
                    'PKG-CONSTR-FINAL',
                    'Post-Construction Rough & Final Cleaning Pack',
                    'CSI 017423 Final Cleaning Crews',
                    'Industrial construction site safety, heavy debris lifting, PPE standards, and zero-scratch glass scraper protocols.',
                    'OSHA 1926 Construction Standards / GC MSA',
                    0.00
                ),
                (
                    'PKG-1099-FASTPASS',
                    'Subcontractor Rapid Clearance Pass',
                    '1099 Trade Partners & Subcontractor Crews',
                    'Accelerated clearance pass for trade partners covering jobsite safety, proportioner calibration, and HWB quality inspection standards.',
                    'Subcontractor Agreement / $49 Pass-Through Fee',
                    49.00
                )
            ]

            for code, title, role, desc, standards, price in packages:
                cur.execute('''
                    INSERT INTO "AcademyPackages" (
                        package_code, title, target_role, description, regulatory_standards, price_usd
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (package_code) DO UPDATE SET
                        title = EXCLUDED.title,
                        target_role = EXCLUDED.target_role,
                        description = EXCLUDED.description,
                        regulatory_standards = EXCLUDED.regulatory_standards,
                        price_usd = EXCLUDED.price_usd;
                ''', (code, title, role, desc, standards, price))

            # 5. Map Course TRN-SAF-01 to All Foundation Packages
            cur.execute('SELECT id FROM "AcademyCourses" WHERE course_code = \'TRN-SAF-01\';')
            c_row = cur.fetchone()
            if c_row:
                course_saf_id = c_row[0]
                cur.execute('SELECT id FROM "AcademyPackages";')
                all_pkg_ids = [r[0] for r in cur.fetchall()]
                for pkg_id in all_pkg_ids:
                    cur.execute('''
                        INSERT INTO "AcademyPackageCourses" (package_id, course_id, display_order)
                        VALUES (%s, %s, 1)
                        ON CONFLICT (package_id, course_id) DO NOTHING;
                    ''', (pkg_id, course_saf_id))

            conn.commit()
            print("[MIGRATION SUCCESS] 009_academy_packages applied successfully!")
            print(f"[MIGRATION] Seeded {len(packages)} standardized packages mapped to foundation courses.")

    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION ERROR] 009_academy_packages failed: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
    run_migration(db_url)
