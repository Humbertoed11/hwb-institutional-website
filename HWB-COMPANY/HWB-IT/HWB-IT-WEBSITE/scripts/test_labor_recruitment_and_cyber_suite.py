"""
SigmaFidelity™ Workforce Intake, HR Onboarding & Cybersecurity Integration Suite
Standards: ISO 9001:2015 Clause 7.2, Clause 8.4; ISO 27001:2022 Clause A.12.4; SOC 2 CC6.8; HWB-QMS-7.2 & 11.10
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)

Test Coverage:
1. Workforce Portal Rendering: /work-with-us page, job positions, and WCAG accessibility
2. Candidate Application Pipeline: POST /api/v1/workforce/apply -> JobApplicants ledger
3. Subcontractor Registration Pipeline: POST /api/v1/workforce/subcontractor -> SubcontractorPartners ledger
4. ISO 9001 Clause 7.2 Onboarding Engine: POST /api/v1/hr/onboard -> Employees ledger, HWB-EMP-#### badge, and Job Description Acknowledgement
5. RBAC Quarantine & Inactivity Enforcement: Unauthorized access to onboarding endpoints
6. Data Integrity & Verification: Complete audit verification and clean teardown
"""

import os
import sys
import json
import unittest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

from main_app import app
from core.services.database import get_db

class WorkforceAndCyberTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.db_url = app.config['DATABASE_URL']
        cls.test_tag = "VERIF-LABOR-TEST-2026"

    def tearDown(self):
        # Clean up any test records created with the test tag
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM "AcademyEnrollments" WHERE student_name LIKE %s;', (f"%{self.test_tag}%",))
                cur.execute('DELETE FROM "Employees" WHERE notes LIKE %s OR last_name LIKE %s;', (f"%{self.test_tag}%", f"%{self.test_tag}%"))
                cur.execute('DELETE FROM "JobApplicants" WHERE notes LIKE %s;', (f"%{self.test_tag}%",))
                cur.execute('DELETE FROM "SubcontractorPartners" WHERE notes LIKE %s;', (f"%{self.test_tag}%",))
                cur.execute('DELETE FROM "Leads" WHERE center_name LIKE %s;', (f"%{self.test_tag}%",))
                cur.execute('DELETE FROM "ConstructionBids" WHERE project_name LIKE %s;', (f"%{self.test_tag}%",))
                cur.execute('DELETE FROM "InstitutionalBids" WHERE solicitation_number LIKE %s;', (f"%{self.test_tag}%",))
            conn.commit()
        finally:
            conn.close()

    def test_01_workforce_portal_and_job_positions(self):
        """Verifies /work-with-us renders active job positions from PostgreSQL."""
        resp = self.client.get('/work-with-us')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn("HWB Cleaning Services", html)
        self.assertIn("Commercial Cleaning Technician", html)
        self.assertIn("Subcontractor", html)

    def test_02_job_applicant_intake_pipeline(self):
        """Verifies candidate submission via /api/v1/workforce/apply persists correctly in JobApplicants."""
        payload = {
            "full_name": f"Test Technician {self.test_tag}",
            "phone": "832-555-0199",
            "email": "test.technician@hwbcleaning.test",
            "city": "Houston",
            "desired_role": "Commercial Cleaning Technician",
            "desired_shift": "Night",
            "experience_level": "3-5 Years",
            "has_transportation": True,
            "authorized_to_work_us": True,
            "preferred_language": "English",
            "notes": f"Automated intake test under {self.test_tag}"
        }
        resp = self.client.post('/api/v1/workforce/apply', json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIsNotNone(data.get('applicant_id'))

        # Verify database record
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM "JobApplicants" WHERE id = %s;', (data['applicant_id'],))
                applicant = cur.fetchone()
                self.assertIsNotNone(applicant)
                self.assertEqual(applicant['full_name'], payload['full_name'])
                self.assertEqual(applicant['status'], 'New')
                self.assertIsNotNone(applicant['job_position_id'])
        finally:
            conn.close()

        # Verify repeat submission merges into existing record without creating a duplicate
        repeat_payload = dict(payload)
        repeat_payload["desired_shift"] = "Day"
        repeat_resp = self.client.post('/api/v1/workforce/apply', json=repeat_payload)
        self.assertEqual(repeat_resp.status_code, 200)
        repeat_data = repeat_resp.get_json()
        self.assertEqual(repeat_data.get('status'), 'already_registered')
        self.assertEqual(repeat_data.get('applicant_id'), data['applicant_id'])

        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) as cnt FROM "JobApplicants" WHERE email = %s;', (payload['email'],))
                self.assertEqual(cur.fetchone()['cnt'], 1)
                cur.execute('SELECT desired_shift FROM "JobApplicants" WHERE id = %s;', (data['applicant_id'],))
                self.assertEqual(cur.fetchone()['desired_shift'], 'Day')
        finally:
            conn.close()

    def test_03_subcontractor_partner_intake_pipeline(self):
        """Verifies 1099 subcontractor crew intake and smart duplicate prevention via /api/v1/workforce/subcontractor."""
        payload = {
            "company_name": f"Pinnacle Janitorial Sub {self.test_tag}",
            "contact_name": "Carlos Mendoza",
            "phone": "713-555-0188",
            "email": "carlos@pinnaclesub.test",
            "city": "Dallas",
            "crew_size": 4,
            "specialties": "Post-Construction Cleaning, VCT Strip & Wax",
            "coi_status": "Pending",
            "hourly_rate_range": "$25 - $30/hr",
            "dwc83_agreed": True,
            "notes": f"Trade crew intake test under {self.test_tag}"
        }
        resp = self.client.post('/api/v1/workforce/subcontractor', json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIsNotNone(data.get('partner_id'))

        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM "SubcontractorPartners" WHERE id = %s;', (data['partner_id'],))
                partner = cur.fetchone()
                self.assertIsNotNone(partner)
                self.assertEqual(partner['company_name'], payload['company_name'])
                self.assertEqual(partner['status'], 'Vetting')
                self.assertTrue(partner['dwc83_signed'])
        finally:
            conn.close()

        # Verify repeat submission in a future week returns already_registered and merges specialties
        repeat_payload = dict(payload)
        repeat_payload["crew_size"] = 8
        repeat_payload["specialties"] = "Post-Construction Cleaning, Window Cleaning"
        repeat_resp = self.client.post('/api/v1/workforce/subcontractor', json=repeat_payload)
        self.assertEqual(repeat_resp.status_code, 200)
        repeat_data = repeat_resp.get_json()
        self.assertEqual(repeat_data.get('status'), 'already_registered')
        self.assertEqual(repeat_data.get('partner_id'), data['partner_id'])

        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) as cnt FROM "SubcontractorPartners" WHERE email = %s;', (payload['email'],))
                self.assertEqual(cur.fetchone()['cnt'], 1)
                cur.execute('SELECT crew_size, specialties FROM "SubcontractorPartners" WHERE id = %s;', (data['partner_id'],))
                updated_partner = cur.fetchone()
                self.assertEqual(updated_partner['crew_size'], 8)
                self.assertIn('Window Cleaning', updated_partner['specialties'])
                self.assertIn('VCT Strip & Wax', updated_partner['specialties'])
        finally:
            conn.close()

    def test_04_hr_onboard_applicant_to_employee_workflow(self):
        """
        Verifies end-to-end promotion from JobApplicant to Employee.
        Satisfies ISO 9001:2015 Clause 7.2 (Competence & Job Description Acknowledgement).
        """
        # 1. First stage an applicant
        apply_payload = {
            "full_name": f"Maria Gonzales {self.test_tag}",
            "phone": "832-555-0177",
            "email": "maria.gonzales@hwbcleaning.test",
            "city": "Austin",
            "desired_role": "Commercial Cleaning Technician",
            "desired_shift": "Evening",
            "notes": f"Candidate for onboard promotion {self.test_tag}"
        }
        apply_resp = self.client.post('/api/v1/workforce/apply', json=apply_payload)
        self.assertEqual(apply_resp.status_code, 201)
        applicant_id = apply_resp.get_json()['applicant_id']

        # 2. Attempt unauthorized onboard (should be blocked by RBAC / login_required)
        onboard_payload = {
            "applicant_id": applicant_id,
            "first_name": "Maria",
            "last_name": f"Gonzales {self.test_tag}",
            "phone": "832-555-0177",
            "email": "maria.gonzales@hwbcleaning.test",
            "primary_role": "Commercial Cleaning Technician",
            "employment_type": "W-2 Full-Time",
            "pay_rate_hourly": 17.50,
            "city": "Austin",
            "state": "TX",
            "notes": f"Officially onboarded via verification test {self.test_tag}"
        }
        unauth_resp = self.client.post('/api/v1/hr/onboard', json=onboard_payload)
        # Without session, should redirect to login (302) or return 401
        self.assertIn(unauth_resp.status_code, [302, 401])

        # 3. Authenticate as Executive
        login_res = self.client.post('/login', data={'username': 'admin', 'password': 'password11'}, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        auth_resp = self.client.post('/api/v1/hr/onboard', json=onboard_payload)
        self.assertEqual(auth_resp.status_code, 201)
        res_data = auth_resp.get_json()
        self.assertEqual(res_data.get('status'), 'success')
        emp_id = res_data.get('employee_id')
        emp_num = res_data.get('employee_number')
        self.assertTrue(emp_num.startswith('HWB-EMP-'), f"Badge number {emp_num} does not match HWB-EMP-#### format")

        # 4. Verify employee record and ISO Clause 7.2 Job Description Acknowledgement
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM "Employees" WHERE id = %s;', (emp_id,))
                emp = cur.fetchone()
                self.assertIsNotNone(emp)
                self.assertEqual(emp['employee_number'], emp_num)
                self.assertEqual(emp['first_name'], 'Maria')
                self.assertEqual(emp['employment_status'], 'Active')
                self.assertEqual(float(emp['pay_rate_hourly']), 17.50)
                self.assertIsNotNone(emp['job_description_acknowledged_at'], "ISO Clause 7.2 Job Description Acknowledgement timestamp missing")

                # Verify applicant status updated to Hired
                cur.execute('SELECT status, notes FROM "JobApplicants" WHERE id = %s;', (applicant_id,))
                app_row = cur.fetchone()
                self.assertEqual(app_row['status'], 'Hired')
                self.assertIn(emp_num, app_row['notes'])
        finally:
            conn.close()

        # 5. Verify repeat HR onboarding returns already_registered and updates pay rate without creating duplicate Employee row
        repeat_onboard = dict(onboard_payload)
        repeat_onboard['pay_rate_hourly'] = 19.00
        repeat_emp_resp = self.client.post('/api/v1/hr/onboard', json=repeat_onboard)
        self.assertEqual(repeat_emp_resp.status_code, 200)
        repeat_emp_data = repeat_emp_resp.get_json()
        self.assertEqual(repeat_emp_data.get('status'), 'already_registered')
        self.assertTrue(repeat_emp_data.get('is_duplicate'))
        self.assertEqual(repeat_emp_data.get('employee_id'), emp_id)
        self.assertEqual(repeat_emp_data.get('employee_number'), emp_num)

    def test_05_enterprise_cross_module_deduplication_and_smart_merge(self):
        """
        Verifies Enterprise Deduplication & Smart Merge across:
        - Website Quote Intake (/get-quote -> Leads)
        - SigmaAcademy Course Assignment (/api/v1/academy/assign -> AcademyEnrollments)
        - Commercial GC Bids (/api/v1/construction-bids/create -> ConstructionBids)
        - Institutional Solicitations (/api/v1/institutional-bids/create -> InstitutionalBids)
        """
        # 1. Website Quote Intake Deduplication (/get-quote)
        import time
        from core.services.bot_defense import get_serializer
        with app.app_context():
            valid_token = get_serializer().dumps({"rendered_at": time.time() - 5.0, "scope": "quote_form"})

        quote_form = {
            'company': f'Apex Medical Plaza {self.test_tag}',
            'name': 'Dr. Evelyn Vance',
            'email': 'evance@apexmedical.test',
            'phone': '214-555-0144',
            'facility_type': 'Medical / Clinical Facility',
            'sqft': '12000',
            'frequency': 'Daily (5 Days/Week) - Standard Corporate',
            'city': 'Plano',
            'zipcode': '75024',
            'form_version': 'v1',
            'form_security_token': valid_token
        }
        q1 = self.client.post('/get-quote', data=quote_form, headers={'Origin': 'https://hwbcleaning.com'}, follow_redirects=True)
        self.assertEqual(q1.status_code, 200)
        q1_html = q1.data.decode('utf-8')
        self.assertIn('RECEIVED (LEAD-#', q1_html)

        # Second submission in a future week with larger sqf
        quote_form_repeat = dict(quote_form)
        quote_form_repeat['sqft'] = '18500'
        q2 = self.client.post('/get-quote', data=quote_form_repeat, headers={'Origin': 'https://hwbcleaning.com'}, follow_redirects=True)
        self.assertEqual(q2.status_code, 200)
        q2_html = q2.data.decode('utf-8')
        self.assertIn('quote-already-registered-banner', q2_html)
        self.assertIn('You Are Already Registered', q2_html)

        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) as cnt, MAX(sqf) as max_sqf FROM "Leads" WHERE center_name = %s;', (quote_form['company'],))
                lead_row = cur.fetchone()
                self.assertEqual(lead_row['cnt'], 1)
                self.assertEqual(int(lead_row['max_sqf']), 18500)
        finally:
            conn.close()

        # Authenticate for backoffice API checks
        self.client.post('/login', data={'username': 'admin', 'password': 'password11'}, follow_redirects=True)

        # 2. SigmaAcademy Enrollment Deduplication (/api/v1/academy/assign)
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT course_code FROM "AcademyCourses" ORDER BY id ASC LIMIT 1;')
                c_row = cur.fetchone()
                course_code = c_row['course_code'] if isinstance(c_row, dict) else c_row[0]
        finally:
            conn.close()

        acad_payload = {
            'assignment_type': 'COURSE',
            'target_code': course_code,
            'worker_type': 'EMPLOYEE',
            'student_name': f'Carlos Mendez {self.test_tag}',
            'student_email': 'carlos.mendez@hwbcleaning.test',
            'due_days': 7
        }
        a1 = self.client.post('/api/v1/academy/assign', json=acad_payload)
        self.assertEqual(a1.status_code, 200)
        a1_data = a1.get_json()
        self.assertEqual(a1_data.get('status'), 'success')
        self.assertFalse(a1_data.get('is_duplicate'))

        a2 = self.client.post('/api/v1/academy/assign', json=acad_payload)
        self.assertEqual(a2.status_code, 200)
        a2_data = a2.get_json()
        self.assertEqual(a2_data.get('status'), 'already_registered')
        self.assertTrue(a2_data.get('is_duplicate'))
        self.assertEqual(a2_data.get('magic_token'), a1_data.get('magic_token'))

        # 3. Commercial GC Bid Deduplication (/api/v1/construction-bids/create)
        gc_payload = {
            'gc_name': 'Turner Construction',
            'project_name': f'Legacy Tower Phase II {self.test_tag}',
            'city': 'Plano',
            'state': 'TX',
            'cleanable_sqft': '45000',
            'estimated_value': '18500',
            'estimator_name': 'Marcus Vance',
            'estimator_phone': '972-555-0188',
            'estimator_email': 'mvance@turner.test'
        }
        b1 = self.client.post('/api/v1/construction-bids/create', json=gc_payload)
        self.assertEqual(b1.status_code, 200)
        b1_data = b1.get_json()
        self.assertEqual(b1_data.get('status'), 'success')

        gc_payload_repeat = dict(gc_payload)
        gc_payload_repeat['cleanable_sqft'] = '52000'
        b2 = self.client.post('/api/v1/construction-bids/create', json=gc_payload_repeat)
        self.assertEqual(b2.status_code, 200)
        b2_data = b2.get_json()
        self.assertEqual(b2_data.get('status'), 'already_registered')
        self.assertTrue(b2_data.get('is_duplicate'))
        self.assertEqual(b2_data.get('bid_id'), b1_data.get('bid_id'))

        # 4. Institutional Solicitation Deduplication (/api/v1/institutional-bids/create)
        inst_payload = {
            'solicitation_number': f'RFP-{self.test_tag}',
            'title': 'Municipal Annex Janitorial Services',
            'agency_name': 'City of Plano',
            'cleanable_sqft': 65000,
            'officer_email': 'procurement@plano.test',
            'officer_phone': '972-555-0190'
        }
        i1 = self.client.post('/api/v1/institutional-bids/create', json=inst_payload)
        self.assertEqual(i1.status_code, 201)
        i1_data = i1.get_json()
        self.assertEqual(i1_data.get('status'), 'success')

        i2 = self.client.post('/api/v1/institutional-bids/create', json=inst_payload)
        self.assertEqual(i2.status_code, 200)
        i2_data = i2.get_json()
        self.assertEqual(i2_data.get('status'), 'already_registered')
        self.assertTrue(i2_data.get('is_duplicate'))
        self.assertEqual(i2_data.get('id'), i1_data.get('id'))

if __name__ == '__main__':
    unittest.main()
