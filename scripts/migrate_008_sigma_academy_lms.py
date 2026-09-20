"""
Migration 008: SigmaAcademy™ Multi-Tenant Training & Compliance LMS
Standard: HWB-QMS-7.6 Database Hardening & Schema Versioning SOP
Authority: Humberto Dominguez (CEO)
Architect: George (Systems Architect & mbB)
"""

import os
import sys
import uuid
import json
import psycopg2

def run_migration(db_url: str):
    print("[MIGRATION] Applying 008_sigma_academy_lms...")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. AcademyTenants Table (Multi-Tenant Partitioning)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "AcademyTenants" (
                    id SERIAL PRIMARY KEY,
                    slug VARCHAR(64) UNIQUE NOT NULL,
                    display_name VARCHAR(255) NOT NULL,
                    brand_logo_url VARCHAR(512),
                    brand_primary_color VARCHAR(32) DEFAULT '#2563eb',
                    tenant_type VARCHAR(32) DEFAULT 'INTERNAL',
                    subscription_tier VARCHAR(64) DEFAULT 'ENTERPRISE',
                    contact_email VARCHAR(255),
                    custom_domain VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_academy_tenants_slug" ON "AcademyTenants" (slug);
                CREATE INDEX IF NOT EXISTS "idx_academy_tenants_active" ON "AcademyTenants" (is_active);
            ''')

            # 2. AcademyCourses Table (Master Curriculum Registry)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "AcademyCourses" (
                    id SERIAL PRIMARY KEY,
                    course_code VARCHAR(64) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    category VARCHAR(64) DEFAULT 'SAFETY_COMPLIANCE',
                    regulatory_standard VARCHAR(255),
                    description TEXT,
                    estimated_minutes INTEGER DEFAULT 30,
                    renewal_months INTEGER DEFAULT 12,
                    badge_icon VARCHAR(64) DEFAULT 'shield-check',
                    is_global_template BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_academy_courses_code" ON "AcademyCourses" (course_code);
                CREATE INDEX IF NOT EXISTS "idx_academy_courses_cat" ON "AcademyCourses" (category);
            ''')

            # 3. AcademyCourseModules Table (Course Chapters & Content)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "AcademyCourseModules" (
                    id SERIAL PRIMARY KEY,
                    course_id INTEGER REFERENCES "AcademyCourses"(id) ON DELETE CASCADE,
                    module_order INTEGER NOT NULL,
                    module_code VARCHAR(64),
                    title VARCHAR(255) NOT NULL,
                    summary TEXT,
                    content_html TEXT NOT NULL,
                    key_takeaways JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_academy_modules_course" ON "AcademyCourseModules" (course_id);
                CREATE INDEX IF NOT EXISTS "idx_academy_modules_order" ON "AcademyCourseModules" (course_id, module_order);
            ''')

            # 4. AcademyQuizQuestions Table (Assessment Bank)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "AcademyQuizQuestions" (
                    id SERIAL PRIMARY KEY,
                    course_id INTEGER REFERENCES "AcademyCourses"(id) ON DELETE CASCADE,
                    module_id INTEGER REFERENCES "AcademyCourseModules"(id) ON DELETE SET NULL,
                    question_order INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    options JSONB NOT NULL,
                    correct_option_id VARCHAR(8) NOT NULL,
                    explanation_text TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_academy_quiz_course" ON "AcademyQuizQuestions" (course_id);
            ''')

            # 5. AcademyEnrollments Table (Progress, Scores & Credentialing)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "AcademyEnrollments" (
                    id SERIAL PRIMARY KEY,
                    enrollment_uuid VARCHAR(64) UNIQUE NOT NULL,
                    tenant_id INTEGER REFERENCES "AcademyTenants"(id) ON DELETE CASCADE,
                    course_id INTEGER REFERENCES "AcademyCourses"(id) ON DELETE CASCADE,
                    worker_type VARCHAR(32) NOT NULL DEFAULT 'W2_EMPLOYEE',
                    employee_id INTEGER REFERENCES "Employees"(id) ON DELETE SET NULL,
                    subcontractor_id INTEGER REFERENCES "SubcontractorPartners"(id) ON DELETE SET NULL,
                    student_name VARCHAR(255) NOT NULL,
                    student_email VARCHAR(255),
                    student_phone VARCHAR(64),
                    status VARCHAR(32) DEFAULT 'ENROLLED',
                    progress_pct INTEGER DEFAULT 0,
                    quiz_score INTEGER DEFAULT 0,
                    quiz_attempts INTEGER DEFAULT 0,
                    quiz_responses JSONB DEFAULT '{}'::jsonb,
                    practical_skills_verified BOOLEAN DEFAULT FALSE,
                    supervisor_evaluator_name VARCHAR(255),
                    supervisor_evaluation_date DATE,
                    certified_at TIMESTAMP WITH TIME ZONE,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    certificate_pdf_url VARCHAR(512),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_academy_enrollments_uuid" ON "AcademyEnrollments" (enrollment_uuid);
                CREATE INDEX IF NOT EXISTS "idx_academy_enrollments_tenant" ON "AcademyEnrollments" (tenant_id);
                CREATE INDEX IF NOT EXISTS "idx_academy_enrollments_course" ON "AcademyEnrollments" (course_id);
                CREATE INDEX IF NOT EXISTS "idx_academy_enrollments_status" ON "AcademyEnrollments" (status);
                CREATE INDEX IF NOT EXISTS "idx_academy_enrollments_worker" ON "AcademyEnrollments" (worker_type, employee_id, subcontractor_id);
            ''')

            # 6. AcademyTenantAccess Table (Licensing & Seat Limits)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "AcademyTenantAccess" (
                    id SERIAL PRIMARY KEY,
                    tenant_id INTEGER REFERENCES "AcademyTenants"(id) ON DELETE CASCADE,
                    course_id INTEGER REFERENCES "AcademyCourses"(id) ON DELETE CASCADE,
                    seat_limit INTEGER DEFAULT 50,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_id, course_id)
                );
            ''')

            # --- SEED DEFAULT TENANTS ---
            cur.execute('''
                INSERT INTO "AcademyTenants" (slug, display_name, brand_logo_url, brand_primary_color, tenant_type, subscription_tier)
                VALUES 
                    ('hwb', 'HWB Cleaning Services LLC', '/static/HWB-LOGO.png', '#2563eb', 'INTERNAL', 'ENTERPRISE'),
                    ('collin-college', 'Collin College Facilities Management', '/static/collin_logo.png', '#0284c7', 'CLIENT', 'FACILITY_PREMIUM'),
                    ('bright-horizons', 'Bright Horizons Child Care Academy', '', '#059669', 'SAAS_SUBSCRIBER', 'DAYCARE_STANDARD')
                ON CONFLICT (slug) DO NOTHING;
            ''')

            # --- SEED COURSE: TRN-SAF-01 ---
            cur.execute('''
                INSERT INTO "AcademyCourses" (
                    course_code, title, category, regulatory_standard, description, estimated_minutes, renewal_months, badge_icon
                ) VALUES (
                    'TRN-SAF-01',
                    'Safe Work Habits & Ergonomic Injury Prevention',
                    'SAFETY_COMPLIANCE',
                    'OSHA 1910.1200 / Collin College SOW § 127 & T&C § 132 / ISO 45001:2018',
                    'Mandatory field safety certification covering safe lifting in the Power Zone, heavy trash liner handling, Figure-8 mopping posture, backpack vacuum harness fitting, heavy machine operation, and slip/fall prevention.',
                    30,
                    12,
                    'shield-check'
                ) ON CONFLICT (course_code) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    regulatory_standard = EXCLUDED.regulatory_standard
                RETURNING id;
            ''')
            course_id = cur.fetchone()[0]

            # Clear existing modules & questions for TRN-SAF-01 before re-seeding
            cur.execute('DELETE FROM "AcademyCourseModules" WHERE course_id = %s;', (course_id,))
            cur.execute('DELETE FROM "AcademyQuizQuestions" WHERE course_id = %s;', (course_id,))

            # Modules Data
            modules = [
                (
                    1, 'MOD-01', 'Safe Lifting & The Power Zone',
                    'Biomechanical principles of the Power Zone, 5-step box squat lifting, avoiding spinal torsion, and the Tilt-and-Slide method for 44-gallon trash liners.',
                    '''<h3>The Power Zone</h3>
<p>The <strong>Power Zone</strong> is the area between your mid-thighs and mid-chest. In this zone, your muscles and joints have maximum mechanical leverage with minimum strain on your spine.</p>
<h4>The 5-Step Box Lift</h4>
<ol>
  <li><strong>Test the Weight:</strong> Nudge the object with your foot to test weight and stability.</li>
  <li><strong>Wide Base:</strong> Stand right against the object, feet shoulder-width apart.</li>
  <li><strong>Bend Knees & Hips:</strong> Squat down keeping back straight and head up. Never bend from the waist.</li>
  <li><strong>Full Palm Grip:</strong> Secure a firm diagonal palm grip on opposite corners.</li>
  <li><strong>Leg Drive:</strong> Push through your heels to stand. Keep the load close to your chest.</li>
</ol>
<div class="callout callout-caution">
  <strong>Never Twist While Loaded:</strong> Pivot with your feet using small steps to turn. Twisting while loaded is the #1 cause of disc herniation.
</div>
<h4>Emptying Heavy Trash (T&C § 132 & SOW § 127)</h4>
<ul>
  <li>Tilt the trash barrel slightly to break the air suction before pulling up the liner.</li>
  <li>Rest the edge of the can against the lip of your rolling tilt truck to slide the liner over the edge.</li>
  <li>If a trash bag exceeds 30 lbs, a <strong>team lift (2 technicians)</strong> is mandatory.</li>
</ul>''',
                    json.dumps(['Lift strictly between mid-thigh and mid-chest', 'Team lift mandatory for loads >30 lbs', 'Always pivot with feet, never twist spine'])
                ),
                (
                    2, 'MOD-02', 'Mopping & Floor Care Ergonomics',
                    'Figure-8 continuous mopping strokes, chin-height telescoping handle adjustment, and bucket draining without dangerous lifting.',
                    '''<h3>The Figure-8 Mopping Stroke</h3>
<p>Traditional "push-pull" mopping causes chronic lower back strain. Use the ergonomic Figure-8 stroke:</p>
<ol>
  <li><strong>Adjust Handle:</strong> Telescoping handles must be set so the top aligns with your chin while standing tall.</li>
  <li><strong>Upright Posture:</strong> Keep your shoulders relaxed and back straight.</li>
  <li><strong>Continuous "S" Curve:</strong> Move the mop head in a 6-foot wide Figure-8 pattern while walking backward.</li>
  <li><strong>Hip & Leg Drive:</strong> Shift your body weight side-to-side with your legs to power the mop rather than pushing with your arms.</li>
</ol>
<h4>Safe Mop Bucket Handling</h4>
<ul>
  <li>Fill buckets on the floor using a flexible hose at the janitor sink—never carry a full 35-quart bucket (70+ lbs).</li>
  <li>Empty dirty water using the bottom drain spigot or siphon hose into floor drains.</li>
</ul>''',
                    json.dumps(['Adjust mop handle to chin height', 'Drive Figure-8 stroke with hips and legs', 'Empty buckets via floor drain spigot, never hoist'])
                ),
                (
                    3, 'MOD-03', 'Backpack Vacuum & Wand Posture',
                    '3-point harness fitting transferring 90% of weight to hips, natural walking stride mechanics, and alternating lead hands.',
                    '''<h3>3-Point Ergonomic Harness Fitting</h3>
<p>Backpack vacuums weigh 10–14 lbs. Improper strap adjustment places all load on neck and collarbone nerves:</p>
<ol>
  <li><strong>Step 1 (Waist Belt):</strong> Fasten and cinch the padded waist belt first over your pelvic hip bones. 90% of the machine weight must rest on your hips.</li>
  <li><strong>Step 2 (Shoulder Straps):</strong> Snug the shoulder straps until the vacuum rests flat against your upper back without pulling down on shoulders.</li>
  <li><strong>Step 3 (Sternum Clip):</strong> Fasten the chest clip to prevent shoulder straps from slipping outward.</li>
</ol>
<h4>Walking Stride Wand Movement</h4>
<ul>
  <li>Keep elbows bent at 90 degrees close to your torso.</li>
  <li>Walk forward in a natural rhythm to guide the wand rather than wildly swinging your shoulders.</li>
  <li>Switch top and bottom hands every 20–30 minutes to balance muscular effort across both sides of your body.</li>
</ul>''',
                    json.dumps(['Waist belt supports 90% of backpack weight', 'Guide wand with natural walking stride', 'Switch leading hands every 20-30 minutes'])
                ),
                (
                    4, 'MOD-04', 'Operating Heavy Floor Equipment',
                    'Auto-scrubber and 2000 RPM burnisher operation, wrist alignment, foot-lever pad tilting, and electric cord management.',
                    '''<h3>Auto-Scrubbers & Burnishers</h3>
<ul>
  <li><strong>Wrist Neutrality:</strong> Adjust handlebars so wrists remain in a straight line with elbows slightly bent. Bent wrists under machine vibration cause carpal tunnel syndrome.</li>
  <li><strong>Leg Drive Steering:</strong> Push and steer walk-behind machines using your lower body momentum; do not wrestle the machine with your wrists.</li>
  <li><strong>Changing Pads:</strong> Always use the rear transport wheel foot-pedal to tip the machine backward. Never bend over from the waist to reach beneath an untipped deck.</li>
  <li><strong>Cord Management:</strong> Drape cord loosely over your dominant shoulder and maintain visual awareness. Never wrap power cords tightly around hands or wrists.</li>
  <li><strong>Always PUSH:</strong> Always push wheeled tilt trucks and trash gondolas. Pulling twists your spine and knees under heavy load.</li>
</ul>''',
                    json.dumps(['Maintain straight wrists on machine controls', 'Tip decks using foot pedal before changing pads', 'Always push wheeled carts and tilt trucks'])
                ),
                (
                    5, 'MOD-05', 'Slip, Trip & Fall Prevention',
                    'Pre-placement of yellow caution cones, corridor half-splitting, ASTM F2913 rubber siped shoes, and 3 points of contact.',
                    '''<h3>The 100% Slip Prevention Standard</h3>
<ol>
  <li><strong>Cones Before Water:</strong> Place high-visibility yellow "Wet Floor" signs at all entrances and hallway junctions before applying liquid or cleaner.</li>
  <li><strong>Corridor Half-Splitting:</strong> Mop long hallways one side at a time, keeping a dry walkway open for building occupants.</li>
  <li><strong>Cone Removal Rule:</strong> Never remove caution cones until the floor surface is 100% dry to the touch.</li>
</ol>
<h4>Footwear & Ladder Rules</h4>
<ul>
  <li><strong>Certified Slip-Resistant Footwear:</strong> ASTM F2913 rated rubber tread with deep siping. Running shoes with smooth foam soles or open footwear are strictly prohibited.</li>
  <li><strong>Three Points of Contact:</strong> Keep two hands and one foot, or two feet and one hand, in firm contact on stairs and ladders at all times.</li>
  <li><strong>Belt-Buckle Rule:</strong> Keep belt buckle centered between ladder rails; never lean sideways. Never step on top two rungs of a stepladder.</li>
</ul>''',
                    json.dumps(['Cones must be placed before water touches floor', 'Cones stay in place until 100% dry', 'Maintain 3 points of contact on ladders'])
                ),
                (
                    6, 'MOD-06', 'Pre-Shift Warm-Up & Fatigue Reset',
                    '3-minute dynamic pre-shift stretch routine, 45-minute micro-breaks, and hydration schedule.',
                    '''<h3>3-Minute Pre-Shift Dynamic Stretch</h3>
<table>
  <thead><tr><th>Stretch</th><th>Action</th><th>Target Muscles</th></tr></thead>
  <tbody>
    <tr><td><strong>Torso Swings</strong></td><td>Feet shoulder-width, gently rotate arms and torso side-to-side (10 reps).</td><td>Spine, hips, obliques</td></tr>
    <tr><td><strong>Calf Lunges</strong></td><td>Step one foot forward, keep rear heel pressed to floor (15s per side).</td><td>Calves, hamstrings, leg drive</td></tr>
    <tr><td><strong>Chest Opener</strong></td><td>Clasp hands behind lower back, gently pull shoulders backward (15s).</td><td>Chest, posture, neck</td></tr>
    <tr><td><strong>Wrist Flexor</strong></td><td>Extend arm forward, gently pull fingertips backward (10s per hand).</td><td>Forearms, carpal tunnel prevention</td></tr>
  </tbody>
</table>
<h4>Micro-Breaks & Hydration</h4>
<ul>
  <li><strong>30-Second Micro-Breaks:</strong> Pause every 45 minutes of repetitive wiping or mopping to stand tall and roll shoulders.</li>
  <li><strong>Hydration:</strong> Drink 8–12 oz of water every 60–90 minutes to prevent muscle cramps and heat exhaustion.</li>
</ul>''',
                    json.dumps(['Complete 3-minute stretch before shift starts', 'Take 30-second posture micro-breaks every 45 mins', 'Drink water regularly to prevent fatigue'])
                )
            ]

            for m_order, m_code, m_title, m_summary, m_content, m_takeaways in modules:
                cur.execute('''
                    INSERT INTO "AcademyCourseModules" (
                        course_id, module_order, module_code, title, summary, content_html, key_takeaways
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                ''', (course_id, m_order, m_code, m_title, m_summary, m_content, m_takeaways))

            # Quiz Questions Data
            questions = [
                (
                    1,
                    'When lifting a 35-lb supply box from the floor, how should your body be positioned?',
                    json.dumps([
                        {'id': 'A', 'text': 'Bend at the waist with straight legs and pull quickly.'},
                        {'id': 'B', 'text': 'Feet shoulder-width apart close to the box, bend at knees and hips with straight back, grip with full palms, push up with legs in the Power Zone.'},
                        {'id': 'C', 'text': 'Twist your torso while pulling up with your arms to clear your knees.'},
                        {'id': 'D', 'text': 'Lift the box onto your fingertips and carry it at shoulder height.'}
                    ]),
                    'B',
                    'Lifting in the Power Zone with bent knees, neutral spine, and leg drive protects lower spinal discs and utilizes the body\'s strongest leg muscles.'
                ),
                (
                    2,
                    'What is the mandatory procedure before lifting a heavy, wet commercial trash liner from a 44-gallon barrel (Collin SOW § 127)?',
                    json.dumps([
                        {'id': 'A', 'text': 'Yank the liner as hard as possible with a single arm.'},
                        {'id': 'B', 'text': 'Hoist the liner using your knee as a fulcrum.'},
                        {'id': 'C', 'text': 'Tilt the barrel and pull the liner away from the inside rim to break the vacuum seal; use a team lift if over 30 lbs.'},
                        {'id': 'D', 'text': 'Drag the barrel to the dumpster and tip the entire barrel inside.'}
                    ]),
                    'C',
                    'Tilting the barrel breaks the vacuum suction that locks wet liners inside, drastically reducing required pulling force and preventing acute spinal strain.'
                ),
                (
                    3,
                    'How should a commercial backpack vacuum harness be adjusted to eliminate shoulder and neck strain?',
                    json.dumps([
                        {'id': 'A', 'text': 'Tighten the shoulder straps as hard as possible so the unit hangs from the neck.'},
                        {'id': 'B', 'text': 'Leave the waist belt unfastened and use only the chest strap.'},
                        {'id': 'C', 'text': 'Cinch the padded waist belt first so 90% of the weight rests on the hips, then snug the shoulder straps and fasten the chest clip.'},
                        {'id': 'D', 'text': 'Carry the vacuum in one hand using the carry handle while vacuuming.'}
                    ]),
                    'C',
                    'The pelvic hip girdle is engineered to support substantial load; transferring 90% of the weight to the hips protects delicate neck and shoulder nerve bundles.'
                ),
                (
                    4,
                    'When moving a rolling tilt truck or heavy wheeled trash gondola, what is the required biomechanical rule?',
                    json.dumps([
                        {'id': 'A', 'text': 'Always PULL the cart behind you with one arm twisted.'},
                        {'id': 'B', 'text': 'Always PUSH using leg momentum and an upright spine; never pull.'},
                        {'id': 'C', 'text': 'Run ahead of the cart and let momentum carry it forward.'},
                        {'id': 'D', 'text': 'Pull the cart walking backward without looking.'}
                    ]),
                    'B',
                    'Pushing utilizes forward leg drive and keeps the spinal column aligned, whereas pulling forces torsional twisting and knee shearing under load.'
                ),
                (
                    5,
                    'When is it permissible to remove yellow "Caution: Wet Floor" warning cones from a mopped corridor?',
                    json.dumps([
                        {'id': 'A', 'text': 'As soon as the mop bucket is returned to the janitor closet.'},
                        {'id': 'B', 'text': 'After 5 minutes regardless of floor dampness.'},
                        {'id': 'C', 'text': 'Only after the floor surface is 100% dry to the touch.'},
                        {'id': 'D', 'text': 'Whenever building occupants ask to walk through.'}
                    ]),
                    'C',
                    'Removing caution cones before the surface is 100% dry is a severe safety violation and exposes the company and property owner to slip-and-fall liability.'
                )
            ]

            for q_order, q_text, q_opts, q_correct, q_exp in questions:
                cur.execute('''
                    INSERT INTO "AcademyQuizQuestions" (
                        course_id, question_order, question_text, options, correct_option_id, explanation_text
                    ) VALUES (%s, %s, %s, %s, %s, %s);
                ''', (course_id, q_order, q_text, q_opts, q_correct, q_exp))

            # --- SEED A SAMPLE VERIFIED CERTIFIED ENROLLMENT (CEO Demo Verification) ---
            sample_uuid = "cert-demo-7f8a9b2c3d4e"
            cur.execute('''
                INSERT INTO "AcademyEnrollments" (
                    enrollment_uuid, tenant_id, course_id, worker_type, student_name, student_email,
                    status, progress_pct, quiz_score, quiz_attempts, practical_skills_verified,
                    supervisor_evaluator_name, supervisor_evaluation_date, certified_at, expires_at
                ) VALUES (
                    %s,
                    (SELECT id FROM "AcademyTenants" WHERE slug = 'hwb'),
                    %s,
                    'W2_EMPLOYEE',
                    'Carlos E. Mendoza',
                    'carlos.mendoza@hwbcleaning.com',
                    'PASSED',
                    100,
                    100,
                    1,
                    TRUE,
                    'George (Systems Architect)',
                    CURRENT_DATE,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP + INTERVAL '1 year'
                ) ON CONFLICT (enrollment_uuid) DO NOTHING;
            ''', (sample_uuid, course_id))

            conn.commit()
            print("[MIGRATION SUCCESS] 008_sigma_academy_lms completed successfully!")
            print(f"[MIGRATION] Seeded Course ID {course_id} with {len(modules)} modules and {len(questions)} quiz questions.")

    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION ERROR] 008_sigma_academy_lms failed: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
    run_migration(db_url)
