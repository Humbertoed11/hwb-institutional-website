#!/usr/bin/env python3
"""
Test Suite: Google Site Analytics & GA4 Conversion Tracking
Standard: HWB-QMS-8.2 / Extreme SEO & Digital Analytics
Author: Systems Architect George
"""

import sys
import os
import unittest
from dotenv import load_dotenv

sys.path.insert(0, '/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE')
load_dotenv('/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/.env')

from main_app import app

class TestGoogleSiteAnalytics(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_ga4_tag_in_head_no_duplicate(self):
        """Verify GA4 tag is present in <head> and not duplicated in <body>."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        # Check GA4 measurement ID
        self.assertIn('G-8BX5Q7THYR', html)
        self.assertIn('https://www.googletagmanager.com/gtag/js?id=G-8BX5Q7THYR', html)
        # Ensure it appears exactly once as a script source
        count = html.count('https://www.googletagmanager.com/gtag/js?id=G-8BX5Q7THYR')
        self.assertEqual(count, 1, f"Expected exactly 1 GA4 tag script load, found {count}")

    def test_02_click_to_call_event_listener(self):
        """Verify click-to-call Google Analytics event tracking is present on base template."""
        res = self.client.get('/')
        html = res.get_data(as_text=True)
        self.assertIn('click_to_call', html)
        self.assertIn('a[href^="tel:"]', html)

    def test_03_quote_success_conversion_event(self):
        """Verify quote_success.html fires GA4 generate_lead conversion event."""
        with self.app.test_request_context():
            from flask import render_template
            mock_data = {
                'name': 'CEO John Doe',
                'company': 'Apex Logistics Corp',
                'phone': '(214)-555-0199',
                'email': 'admin@apexcorp.com'
            }
            rendered = render_template('quote_success.html', data=mock_data)
            self.assertIn("gtag('event', 'generate_lead'", rendered)
            self.assertIn('Apex Logistics Corp', rendered)
            self.assertIn("'currency': 'USD'", rendered)
            self.assertIn("'value': 150.00", rendered)

    def test_04_site_audit_telemetry_endpoint(self):
        """Verify /api/v1/analytics/site-audit endpoint returns healthy status and metadata."""
        res = self.client.get('/api/v1/analytics/site-audit')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'HEALTHY')
        self.assertEqual(data['google_analytics']['measurement_id'], 'G-8BX5Q7THYR')
        self.assertEqual(data['google_analytics']['tag_status'], 'ACTIVE_CONFIGURED')
        self.assertEqual(len(data['google_analytics']['conversion_events']), 2)
        self.assertEqual(data['search_infrastructure']['sitemap_priority_pages'], 11)

    def test_05_staff_exclusion_guard(self):
        """Verify that authenticated staff do not trigger GA4 tag (internal traffic filter)."""
        with self.app.test_request_context():
            from flask_login import login_user
            from core.models.user import User
            staff_user = User(id=1, username="hdominguez", role="CEO")
            login_user(staff_user)
            from flask import render_template
            rendered = render_template('base.html')
            self.assertNotIn('https://www.googletagmanager.com/gtag/js', rendered)
            self.assertIn('Internal staff session active. Tracking paused', rendered)

if __name__ == '__main__':
    unittest.main()

