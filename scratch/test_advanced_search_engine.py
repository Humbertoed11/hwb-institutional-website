#!/usr/bin/env python3
"""
Test Suite: Advanced Field Targeting & Query Engine (BUG-065 Verification)
Standard: HWB-QMS-11.2 / SOC 2 Type II
Author: Systems Architect George
"""

import os
import sys
import unittest

sys.path.insert(0, '/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE')
from main_app import app, parse_advanced_search

class TestAdvancedSearchEngine(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_unit_parser_field_targeting(self):
        """Verify field targeting extraction."""
        clauses, params = parse_advanced_search('city:Plano industry:Medical', 'leads')
        self.assertEqual(len(clauses), 2)
        self.assertIn('city ILIKE %s', clauses)
        self.assertIn('facility_type ILIKE %s', clauses)
        self.assertEqual(params, ['%Plano%', '%Medical%'])

    def test_02_unit_parser_numeric_comparisons(self):
        """Verify numeric comparison operators and ranges."""
        clauses, params = parse_advanced_search('sqf:>=10000 sqf:<20000', 'leads')
        self.assertEqual(len(clauses), 2)
        self.assertIn('sqf >= %s', clauses)
        self.assertIn('sqf < %s', clauses)
        self.assertEqual(params, [10000.0, 20000.0])

    def test_03_unit_parser_exclusions(self):
        """Verify negative exclusions with COALESCE."""
        clauses, params = parse_advanced_search('-Church', 'leads')
        self.assertEqual(len(clauses), 1)
        self.assertTrue(clauses[0].startswith('('))
        self.assertIn('COALESCE(center_name::text, \'\') NOT ILIKE %s', clauses[0])
        self.assertTrue(all(p == '%Church%' for p in params))

    def test_04_unit_parser_american_dates(self):
        """Verify American date MM/DD/YYYY to YYYY-MM-DD translation."""
        clauses, params = parse_advanced_search('04/10/2026', 'leads')
        self.assertEqual(len(clauses), 1)
        self.assertIn('%2026-04-10%', params)

    def test_05_unit_parser_rep_attribution(self):
        """Verify rep targeting by id and by name."""
        clauses_id, params_id = parse_advanced_search('rep:4', 'leads')
        self.assertEqual(clauses_id, ['owner_id = %s'])
        self.assertEqual(params_id, [4])

        clauses_name, params_name = parse_advanced_search('rep:Field', 'leads')
        self.assertEqual(len(clauses_name), 1)
        self.assertIn('owner_id IN (SELECT id FROM "Users"', clauses_name[0])
        self.assertEqual(params_name, ['%Field%', '%Field%'])

    def test_06_unit_parser_accounts_view(self):
        """Verify accounts view field targeting."""
        clauses, params = parse_advanced_search('city:Dallas revenue:>=50000 rep:4', 'accounts')
        self.assertEqual(len(clauses), 3)
        self.assertIn('city ILIKE %s', clauses)
        self.assertIn('annual_revenue >= %s', clauses)
        self.assertIn('c.assigned_rep_id = %s', clauses)
        self.assertIn(50000.0, params)
        self.assertIn(4, params)

    def test_07_unit_parser_construction_bids_view(self):
        """Verify construction bids view field targeting."""
        clauses, params = parse_advanced_search('city:Frisco gc:"Turner" sqf:>=50000', 'construction_bids')
        self.assertEqual(len(clauses), 3)
        self.assertIn('cb.city ILIKE %s', clauses)
        self.assertIn('cb.gc_name ILIKE %s', clauses)
        self.assertIn('cb.cleanable_sqft >= %s', clauses)
        self.assertIn('%Frisco%', params)
        self.assertIn('%Turner%', params)
        self.assertIn(50000.0, params)

    def test_08_integration_admin_operations_http(self):
        """Verify live HTTP GET requests through Flask application."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = '2'  # hdominguez (Executive)
            sess['role'] = 'Executive'

        # Leads: city:Plano
        res_leads = self.client.get('/admin/operations?view=leads&q=city:Plano')
        self.assertEqual(res_leads.status_code, 200)
        html = res_leads.data.decode('utf-8')
        self.assertIn('Plano', html)
        self.assertIn('108', html)

        # Leads: city:Plano sqf:>=10000
        res_leads_filtered = self.client.get('/admin/operations?view=leads&q=city:Plano+sqf:%3E=10000')
        self.assertEqual(res_leads_filtered.status_code, 200)
        html_filtered = res_leads_filtered.data.decode('utf-8')
        self.assertIn('34', html_filtered)

        # Accounts HTTP GET
        res_acc = self.client.get('/admin/operations?view=accounts&q=city:Plano')
        self.assertEqual(res_acc.status_code, 200)

        # Construction Bids HTTP GET
        res_bids = self.client.get('/admin/operations?view=construction_bids&q=city:Dallas')
        self.assertEqual(res_bids.status_code, 200)

        # Sales Desk HTTP GET
        res_sales = self.client.get('/admin/sales-desk?q=city:Plano')
        self.assertEqual(res_sales.status_code, 200)

if __name__ == '__main__':
    unittest.main()
