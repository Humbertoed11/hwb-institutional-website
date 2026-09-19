"""
SigmaFidelity™ Enterprise Modular Architecture Verification Suite (v3)
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
"""

import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE"))
sys.path.insert(0, BASE_DIR)

from main_app import app, parse_advanced_search, format_phone_filter
from core.services.sanitizer import clean_phone, clean_currency, clean_sqft, clean_zip, clean_email

def run_tests():
    print("=== [TEST SUITE] SigmaFidelity™ Modular Architecture & Blueprint Hub ===")
    
    # 1. Blueprint Architecture Audit
    print("\n--- 1. Testing Blueprint Hub Registration ---")
    expected_bps = ['telemetry', 'bids', 'auth', 'public', 'operations', 'crm_api']
    for bp_name in expected_bps:
        assert bp_name in app.blueprints, f"Blueprint {bp_name} not registered in app.blueprints!"
        print(f"✓ PASS: Blueprint '{bp_name}' successfully loaded and mounted.")

    # 2. Backward Compatibility & Endpoint Alias Verification
    print("\n--- 2. Testing Root URL Endpoint Alias Resolution ---")
    critical_endpoints = [
        ('login', '/login'),
        ('logout', '/logout'),
        ('index', '/'),
        ('about', '/about'),
        ('get_quote', '/get-quote'),
        ('prequal', '/prequal'),
        ('admin_operations', '/admin/operations'),
        ('sales_desk', '/admin/sales-desk'),
        ('admin_master', '/admin/master'),
        ('sigma_executive', '/admin/executive'),
    ]
    with app.test_request_context():
        for endpoint, expected_path in critical_endpoints:
            from flask import url_for
            resolved_url = url_for(endpoint)
            assert resolved_url == expected_path, f"url_for('{endpoint}') gave {resolved_url}, expected {expected_path}"
            print(f"✓ PASS: url_for('{endpoint}') resolves cleanly to '{resolved_url}'")

    # 3. Code Decoupling & Monolith Reduction Metric
    print("\n--- 3. Testing Monolith Size & Decoupling Metrics ---")
    main_app_path = os.path.join(BASE_DIR, "main_app.py")
    with open(main_app_path, "r") as f:
        line_count = len(f.readlines())
    print(f"✓ PASS: main_app.py line count is {line_count} lines (reduced by {(2992 - line_count) / 2992 * 100:.1f}% from 2,992 lines).")
    assert line_count < 400, f"main_app.py is {line_count} lines, expected < 400 lines!"

    # 4. End-to-End API Probing via Test Client
    print("\n--- 4. Testing Backoffice & CRM REST API Endpoints ---")
    client = app.test_client()

    # Login as Admin via debug-login
    login_res = client.get('/debug-login', follow_redirects=False)
    assert login_res.status_code == 302, f"Admin login failed: {login_res.status_code}"
    print("✓ PASS: Admin authentication and session generation successful.")

    # Probe Operations Backoffice
    ops_res = client.get('/admin/operations?view=leads')
    assert ops_res.status_code == 200, f"Operations leads view failed: {ops_res.status_code}"
    print("✓ PASS: Modular Operations Blueprint /admin/operations returned HTTP 200.")

    # Probe CRM Lead API
    lead_api_res = client.get('/api/v1/leads/60799')
    assert lead_api_res.status_code == 200, f"Lead API failed: {lead_api_res.status_code}"
    lead_data = lead_api_res.get_json()
    assert 'lead' in lead_data and lead_data['lead']['id'] == 60799, "Lead API JSON payload malformed"
    print(f"✓ PASS: Modular CRM API Blueprint /api/v1/leads/60799 returned valid record: {lead_data['lead']['center_name']}.")

    # Probe Cadence Save with phone sanitization
    cadence_res = client.post('/api/v1/leads/60799/cadence-save', json={
        'phone': '214 555 0199',
        'note': 'Automated enterprise test touchpoint.',
        'activity_type': 'Phone Call'
    })
    assert cadence_res.status_code == 200, f"Cadence save failed: {cadence_res.status_code}"
    print("✓ PASS: Modular CRM API Blueprint /api/v1/leads/<id>/cadence-save succeeded.")

    # Probe Telemetry Audit
    db_audit_res = client.get('/api/v1/db-audit')
    assert db_audit_res.status_code == 200, f"DB audit failed: {db_audit_res.status_code}"
    db_audit_data = db_audit_res.get_json()
    print(f"✓ PASS: Modular Telemetry Blueprint reports live database lead count: {db_audit_data.get('total_leads_count')} rows.")

    print("\n=============================================================")
    print("ALL MODULAR BLUEPRINT ARCHITECTURE TESTS PASSED (100% SUCCESS)")
    print("=============================================================\n")

if __name__ == '__main__':
    run_tests()
