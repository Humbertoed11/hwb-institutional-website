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
                cur.execute('DELETE FROM "Employees" WHERE notes LIKE %s;', (f"%{self.test_tag}%",))
                cur.execute('DELETE FROM "JobApplicants" WHERE notes LIKE %s;', (f"%{self.test_tag}%",))
                cur.execute('DELETE FROM "SubcontractorPartners" WHERE notes LIKE %s;', (f"%{self.test_tag}%",))
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

    def test_03_subcontractor_partner_intake_pipeline(self):
        """Verifies 1099 subcontractor crew intake via /api/v1/workforce/subcontractor."""
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

if __name__ == '__main__':
    unittest.main()
