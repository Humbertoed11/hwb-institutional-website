#!/usr/bin/env python3
"""
Test Suite: Phone Number Standardization (BUG-066 / HWB-QMS-11.2)
Standard: HWB-QMS-11.2 / SOC 2 Type II
Author: Systems Architect George
"""

import os
import sys
import unittest
import psycopg2
import re

sys.path.insert(0, '/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE')
from main_app import app, format_phone_filter, parse_advanced_search

class TestPhoneStandardization(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_jinja_filter_formatting(self):
        """Verify format_phone template filter on all variations."""
        self.assertEqual(format_phone_filter('8174606130'), '(817)-460-6130')
        self.assertEqual(format_phone_filter('(817) 460-6130'), '(817)-460-6130')
        self.assertEqual(format_phone_filter('(817)-460-6130'), '(817)-460-6130')
        self.assertEqual(format_phone_filter('817-460-6130'), '(817)-460-6130')
        self.assertEqual(format_phone_filter('1-817-460-6130'), '(817)-460-6130')
        self.assertEqual(format_phone_filter('817-460-6130 ext. 101'), '(817)-460-6130 ext. 101')
        self.assertEqual(format_phone_filter(None), '--')
        self.assertEqual(format_phone_filter(''), '--')
        self.assertEqual(format_phone_filter('--'), '--')

    def test_02_database_lead_phones_normalized(self):
        """Verify PostgreSQL database tables have 100% normalized phone numbers."""
        db_url = os.environ.get('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db')
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        pat = re.compile(r'^\(\d{3}\)-\d{3}-\d{4}(?:\s+ext\.\s+\d+)?$')

        # Check Leads: verify all valid 10-digit phones are formatted
        cur.execute('SELECT phone FROM "Leads" WHERE phone IS NOT NULL AND phone != \'\' AND phone != \'--\';')
        lead_phones = [r[0] for r in cur.fetchall()]
        valid_10_digit_leads = [p for p in lead_phones if len(re.sub(r'\D', '', p.split('ext')[0])) == 10]
        formatted_leads = sum(1 for p in valid_10_digit_leads if pat.match(p.strip()))
        self.assertGreater(len(valid_10_digit_leads), 20000)
        self.assertEqual(formatted_leads, len(valid_10_digit_leads))

        # Check Customers
        cur.execute('SELECT phone FROM "Customers" WHERE phone IS NOT NULL AND phone != \'\';')
        cust_phones = [r[0] for r in cur.fetchall()]
        formatted_cust = sum(1 for p in cust_phones if pat.match(p.strip()))
        self.assertEqual(formatted_cust, len(cust_phones))

        # Check ConstructionBids
        cur.execute('SELECT estimator_phone FROM "ConstructionBids" WHERE estimator_phone IS NOT NULL AND estimator_phone != \'\';')
        bid_phones = [r[0] for r in cur.fetchall()]
        formatted_bids = sum(1 for p in bid_phones if pat.match(p.strip()))
        self.assertEqual(formatted_bids, len(bid_phones))

        conn.close()

    def test_03_advanced_search_phone_resilience(self):
        """Verify phone queries match seamlessly with digits or formatted phone."""
        # 1. Search with raw 10 digits
        c1, p1 = parse_advanced_search('phone:8174606130', 'leads')
        self.assertIn('%8174606130%', p1)

        # 2. Search with formatted phone
        c2, p2 = parse_advanced_search('phone:(817)-460-6130', 'leads')
        self.assertIn('%(817)-460-6130%', p2)
        self.assertIn('%8174606130%', p2)

        # 3. Test execution against real database
        db_url = os.environ.get('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db')
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        sql = f'SELECT COUNT(*) FROM "Leads" WHERE {" AND ".join(c1)}'
        cur.execute(sql, tuple(p1))
        self.assertGreaterEqual(cur.fetchone()[0], 1)
        conn.close()

    def test_04_live_http_rendering_formatted_phone(self):
        """Verify backoffice operations HTML renders formatted phone numbers."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = '2'
            sess['role'] = 'Executive'

        # Leads View with phone column requested
        res = self.client.get('/admin/operations?view=leads&cols=company,phone')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        # Ensure regex (###)-###-#### matches inside HTML anchor tags
        self.assertTrue(re.search(r'>\(\d{3}\)-\d{3}-\d{4}</a>', html))

        # Accounts View initial load (phone is in default columns)
        res_acc = self.client.get('/admin/operations?view=accounts&cols=company,phone')
        self.assertEqual(res_acc.status_code, 200)
        html_acc = res_acc.data.decode('utf-8')
        self.assertTrue(re.search(r'>\(\d{3}\)-\d{3}-\d{4}</a>', html_acc))

if __name__ == '__main__':
    unittest.main()
