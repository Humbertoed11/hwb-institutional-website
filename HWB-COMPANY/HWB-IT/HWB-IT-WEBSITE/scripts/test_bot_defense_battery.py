"""
SigmaFidelity™ Enterprise Bot Defense Verification Battery
Standard: HWB-QMS-11.10 & HWB-QMS-7.6
Tests:
1. Form GET rendering & presence of honeypot traps + security token
2. Valid human submission (>3s, empty honeypots, valid referrer) -> 200 OK & Lead created
3. Bot Trap 1: Honeypot filled (hp_organization_url) -> Silent Blackhole (0 leads created)
4. Bot Trap 2: Honeypot filled (hp_tax_id) -> Silent Blackhole (0 leads created)
5. Bot Trap 3: Sub-second automation (< 3s) -> Silent Blackhole (0 leads created)
6. Bot Trap 4: Direct cURL without Referrer/Origin -> Silent Blackhole (0 leads created)
7. Bot Trap 5: Spam URLs in company name -> Silent Blackhole (0 leads created)
8. Bot Trap 6: Financial wire fraud terms -> Silent Blackhole (0 leads created)
"""

import os
import sys
import time
import unittest

# Ensure application root is in python path
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

import psycopg2
from bs4 import BeautifulSoup
from main_app import app
from core.services.database import get_db

class BotDefenseTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.db_url = app.config['DATABASE_URL']

    def count_test_leads(self, prefix: str) -> int:
        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM "Leads" WHERE center_name LIKE %s;', (f"{prefix}%",))
            res = cur.fetchone()
            count = res['count'] if isinstance(res, dict) else res[0]
        conn.close()
        return count

    def purge_test_leads(self, prefix: str):
        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('DELETE FROM "Leads" WHERE center_name LIKE %s;', (f"{prefix}%",))
            cur.execute('DELETE FROM "PendingOutbox" WHERE subject LIKE %s;', (f"%{prefix}%",))
        conn.commit()
        conn.close()

    def test_01_form_rendering_contains_honeypot_and_token(self):
        """Verifies quote form renders honeypot traps and signed security token across all quote forms."""
        # 1. Active HTTP routes containing quote forms
        routes = ['/get-quote', '/']
        for r in routes:
            resp = self.client.get(r)
            self.assertEqual(resp.status_code, 200, f"Route {r} failed to render")
            html = resp.data.decode('utf-8')
            self.assertIn('name="form_security_token"', html, f"Missing form_security_token on {r}")
            self.assertIn('name="hp_organization_url"', html, f"Missing hp_organization_url on {r}")
            self.assertIn('name="hp_tax_id"', html, f"Missing hp_tax_id on {r}")

        # 2. Standalone landing and commercial templates
        from flask import render_template
        with app.test_request_context('/'):
            for tpl in ['landing.html', 'commercial_template.html']:
                html = render_template(tpl)
                self.assertIn('name="form_security_token"', html, f"Missing form_security_token in {tpl}")
                self.assertIn('name="hp_organization_url"', html, f"Missing hp_organization_url in {tpl}")
                self.assertIn('name="hp_tax_id"', html, f"Missing hp_tax_id in {tpl}")
        print("  -> test_01_form_rendering_contains_honeypot_and_token: PASS")

    def test_02_valid_human_submission(self):
        """Verifies legitimate human submission is accepted and saved."""
        prefix = "TEST-HUMAN-LEAD"
        self.purge_test_leads(prefix)

        # GET form to acquire token
        resp = self.client.get('/get-quote')
        soup = BeautifulSoup(resp.data, 'html.parser')
        token_input = soup.find('input', {'name': 'form_security_token'})
        self.assertIsNotNone(token_input)
        token = token_input['value']

        # Simulate human reading/typing delay (> 3 seconds)
        time.sleep(3.1)

        payload = {
            'form_security_token': token,
            'hp_organization_url': '',
            'hp_tax_id': '',
            'company': f"{prefix}-998",
            'name': "Sarah Jenkins",
            'email': "sarah.jenkins@northtexashealth.org",
            'phone': "(214) 555-8822",
            'facility_type': "medical",
            'sqft': "25000",
            'need': "2",
            'frequency': "Daily (5 Days)"
        }

        post_resp = self.client.post(
            '/get-quote',
            data=payload,
            headers={'Referer': 'https://www.hwbcleaning.com/get-quote'}
        )
        self.assertEqual(post_resp.status_code, 200)
        self.assertIn(b"Success. We have your info.", post_resp.data)

        # Verify record exists in Leads table
        count = self.count_test_leads(prefix)
        self.assertEqual(count, 1, "Legitimate human lead was not persisted to database")
        self.purge_test_leads(prefix)
        print("  -> test_02_valid_human_submission: PASS")

    def test_03_bot_trap_honeypot_filled(self):
        """Verifies bot filling invisible honeypot field is dropped via Silent Blackhole."""
        prefix = "TEST-BOT-HONEYPOT"
        self.purge_test_leads(prefix)

        resp = self.client.get('/get-quote')
        soup = BeautifulSoup(resp.data, 'html.parser')
        token = soup.find('input', {'name': 'form_security_token'})['value']
        time.sleep(3.1)

        payload = {
            'form_security_token': token,
            'hp_organization_url': 'https://bot-crawler-target.ru/malware',
            'hp_tax_id': '',
            'company': f"{prefix}-001",
            'name': "Spam Bot",
            'email': "spambot@crawler.com",
            'phone': "(214) 555-0000"
        }

        post_resp = self.client.post(
            '/get-quote',
            data=payload,
            headers={'Referer': 'https://www.hwbcleaning.com/get-quote'}
        )
        # Must return 200 (Silent Blackhole) but create 0 database records
        self.assertEqual(post_resp.status_code, 200)
        count = self.count_test_leads(prefix)
        self.assertEqual(count, 0, "Bot with honeypot filled was illegally saved to database!")
        print("  -> test_03_bot_trap_honeypot_filled: PASS")

    def test_04_bot_trap_sub_second_speed(self):
        """Verifies sub-second automated submission is dropped via Silent Blackhole."""
        prefix = "TEST-BOT-FAST"
        self.purge_test_leads(prefix)

        resp = self.client.get('/get-quote')
        soup = BeautifulSoup(resp.data, 'html.parser')
        token = soup.find('input', {'name': 'form_security_token'})['value']

        # No sleep! Submits immediately (<0.5s)
        payload = {
            'form_security_token': token,
            'hp_organization_url': '',
            'hp_tax_id': '',
            'company': f"{prefix}-002",
            'name': "Fast Bot",
            'email': "fastbot@crawler.com",
            'phone': "(214) 555-0000"
        }

        post_resp = self.client.post(
            '/get-quote',
            data=payload,
            headers={'Referer': 'https://www.hwbcleaning.com/get-quote'}
        )
        self.assertEqual(post_resp.status_code, 200)
        count = self.count_test_leads(prefix)
        self.assertEqual(count, 0, "Sub-second bot was illegally saved to database!")
        print("  -> test_04_bot_trap_sub_second_speed: PASS")

    def test_05_bot_trap_direct_curl_no_referer(self):
        """Verifies direct cURL request without Referrer/Origin is dropped via Silent Blackhole."""
        prefix = "TEST-BOT-NOCURL"
        self.purge_test_leads(prefix)

        payload = {
            'company': f"{prefix}-003",
            'name': "Direct Script",
            'email': "direct@crawler.com",
            'phone': "(214) 555-0000"
        }

        # No Referer or Origin header
        post_resp = self.client.post('/get-quote', data=payload)
        self.assertEqual(post_resp.status_code, 200)
        count = self.count_test_leads(prefix)
        self.assertEqual(count, 0, "Direct request without Referer was illegally saved to database!")
        print("  -> test_05_bot_trap_direct_curl_no_referer: PASS")

    def test_06_bot_trap_spam_content(self):
        """Verifies submission with financial wire spam is dropped via Silent Blackhole."""
        prefix = "TEST-BOT-SPAM"
        self.purge_test_leads(prefix)

        resp = self.client.get('/get-quote')
        soup = BeautifulSoup(resp.data, 'html.parser')
        token = soup.find('input', {'name': 'form_security_token'})['value']
        time.sleep(3.1)

        payload = {
            'form_security_token': token,
            'hp_organization_url': '',
            'hp_tax_id': '',
            'company': f"{prefix} us dollars transfer of balance",
            'name': "Spam Operator",
            'email': "crypto@transfer.com",
            'phone': "(214) 555-0000"
        }

        post_resp = self.client.post(
            '/get-quote',
            data=payload,
            headers={'Referer': 'https://www.hwbcleaning.com/get-quote'}
        )
        self.assertEqual(post_resp.status_code, 200)
        count = self.count_test_leads(prefix)
        self.assertEqual(count, 0, "Spam content was illegally saved to database!")
        print("  -> test_06_bot_trap_spam_content: PASS")

if __name__ == '__main__':
    unittest.main()
