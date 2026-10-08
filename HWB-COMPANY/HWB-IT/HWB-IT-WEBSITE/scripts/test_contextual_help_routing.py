#!/usr/bin/env python3
"""
Automated Test Suite for Contextual In-App Help Routing (Deep-Link Workspace Routing)
Mandates: HWB-QMS-11.2 / HWB-QMS-11.6
Tests verification of workspace detection, deep-linking, referrer routing, and template highlights.
"""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBSITE_DIR = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE")
sys.path.insert(0, WEBSITE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, "/app")

from main_app import app
from core.models.user import User
from core.services.database import get_db


class ContextualHelpRoutingTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.client = cls.app.test_client()

    def get_auth_client(self, username="mrondinella"):
        """Helper to get an authenticated session for an employee."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            # In database seed: user 2 is admin/executive, user 3 is mrondinella
            if username == "admin":
                sess['_user_id'] = '2'
            else:
                sess['_user_id'] = '3'
            sess['_fresh'] = True
        return client

    def test_01_direct_access_all_chapters(self):
        """Verify accessing /manual/app without query parameters loads full manual."""
        client = self.get_auth_client("mrondinella")
        res = client.get('/manual/app')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('HWB Application Operating Manual', html)
        self.assertIn('id="chapter-1"', html)
        self.assertIn('id="chapter-2"', html)
        self.assertIn('id="chapter-3"', html)
        self.assertIn('id="chapter-4"', html)
        self.assertIn('id="chapter-5"', html)
        self.assertIn('id="chapter-6"', html)
        print("[TEST 01] PASS: Direct manual access loads all 6 chapters.")

    def test_02_query_topic_leads_routing(self):
        """Verify ?topic=leads sets Chapter 2 and contextual banner."""
        client = self.get_auth_client("mrondinella")
        res = client.get('/manual/app?topic=leads')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Showing help for:', html)
        self.assertIn('Commercial Leads &amp; CRM', html)
        self.assertIn("targetId = 'chapter-2'", html)
        print("[TEST 02] PASS: ?topic=leads routes to Chapter 2.")

    def test_03_query_view_construction_bids_routing(self):
        """Verify ?view=construction_bids sets Chapter 3 and contextual banner."""
        client = self.get_auth_client("mrondinella")
        res = client.get('/manual/app?view=construction_bids')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Showing help for:', html)
        self.assertIn('Commercial Construction Bids', html)
        self.assertIn("targetId = 'chapter-3'", html)
        print("[TEST 03] PASS: ?view=construction_bids routes to Chapter 3.")

    def test_04_query_topic_cleaning_workforce_routing(self):
        """Verify ?from_view=workforce sets Chapter 5 (Cleaning photos & field)."""
        client = self.get_auth_client("mrondinella")
        res = client.get('/manual/app?from_view=workforce')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Showing help for:', html)
        self.assertIn('Workforce &amp; Field Operations', html)
        self.assertIn("targetId = 'chapter-5'", html)
        print("[TEST 04] PASS: ?from_view=workforce routes to Chapter 5.")

    def test_05_referrer_detection_construction_bids(self):
        """Verify clicking App Manual from construction bids referrer redirects to Chapter 3."""
        client = self.get_auth_client("mrondinella")
        headers = {'Referer': 'http://localhost:5000/admin/operations?view=construction_bids'}
        res = client.get('/manual/app', headers=headers)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/manual/app?topic=bids#chapter-3', res.headers.get('Location', ''))
        
        # Follow redirect
        res_followed = client.get(res.headers['Location'])
        self.assertEqual(res_followed.status_code, 200)
        html = res_followed.data.decode('utf-8')
        self.assertIn('Bidding &amp; Price Estimating', html)
        print("[TEST 05] PASS: Referrer detection for construction bids redirects to Chapter 3.")

    def test_06_referrer_detection_sales_desk(self):
        """Verify clicking App Manual from sales desk referrer redirects to Chapter 2."""
        client = self.get_auth_client("mrondinella")
        headers = {'Referer': 'http://localhost:5000/sales-desk'}
        res = client.get('/manual/app', headers=headers)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/manual/app?topic=leads#chapter-2', res.headers.get('Location', ''))
        print("[TEST 06] PASS: Referrer detection for sales desk redirects to Chapter 2.")

    def test_07_referrer_detection_executive_admin(self):
        """Verify clicking App Manual from admin executive referrer redirects to Chapter 6."""
        client = self.get_auth_client("admin")
        headers = {'Referer': 'http://localhost:5000/admin/executive'}
        res = client.get('/manual/app', headers=headers)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/manual/app?topic=users#chapter-6', res.headers.get('Location', ''))
        print("[TEST 07] PASS: Referrer detection for executive redirects to Chapter 6.")

    def test_08_admin_operations_button_links_rendered_with_context(self):
        """Verify admin operations page renders App Manual link with active view context."""
        client = self.get_auth_client("admin")
        # Leads view
        res = client.get('/admin/operations?view=leads')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('topic=leads', html)
        self.assertIn('chapter-2', html)

        # Construction bids view
        res = client.get('/admin/operations?view=construction_bids')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('topic=bids', html)
        self.assertIn('chapter-3', html)
        print("[TEST 08] PASS: Admin operations renders contextual App Manual button links.")


if __name__ == '__main__':
    unittest.main()
