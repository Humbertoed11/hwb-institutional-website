#!/usr/bin/env python3
"""
SigmaFidelity™ Apple & WebKit Browser Compatibility Test Suite
Simulates requests across macOS Safari, iOS Mobile Safari, and iPadOS WebKit user agents.
Validates WebKit CSS vendor prefixes and HTML viewport properties.
"""

import sys
import os
import re

# Ensure app path is in path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
sys.path.insert(0, os.path.abspath(os.path.join(script_dir, '..')))
sys.path.insert(0, os.path.abspath(os.path.join(script_dir, '../HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE')))

from main_app import app, User
from flask_login import login_user
from unittest.mock import patch

APPLE_USER_AGENTS = {
    "macOS Safari 17.4": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "iPhone iOS Safari 17.4": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/605.1.15",
    "iPadOS Safari 17.4": "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/605.1.15"
}

ROUTES_TO_TEST = [
    "/admin/operations?view=leads",
    "/admin/operations?view=accounts",
    "/admin/operations?view=monitor",
    "/login"
]

def run_apple_compatibility_audit():
    print("=" * 70)
    print(" 🍎 SIGMAFIDELITY™ APPLE / WEBKIT BROWSER COMPLIANCE AUDIT")
    print("=" * 70)

    client = app.test_client()
    passed_tests = 0
    total_tests = 0

    # 1. Audit CSS Vendor Prefixes
    print("\n[CSS AUDIT] Verifying WebKit Vendor Prefixes...")
    base_template_path = os.path.join(script_dir, '../templates/backoffice_base.html')
    if not os.path.exists(base_template_path):
        base_template_path = os.path.join(script_dir, '../../templates/backoffice_base.html')
    if not os.path.exists(base_template_path):
        base_template_path = os.path.join(script_dir, '../HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/templates/backoffice_base.html')

    style_css_path = os.path.join(script_dir, '../static/HWB-WEB Style.css')
    if not os.path.exists(style_css_path):
        style_css_path = os.path.join(script_dir, '../../static/HWB-WEB Style.css')
    if not os.path.exists(style_css_path):
        style_css_path = os.path.join(script_dir, '../HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/HWB-WEB Style.css')

    with open(base_template_path, 'r', encoding='utf-8') as f:
        base_content = f.read()

    with open(style_css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()

    webkit_backdrop = "-webkit-backdrop-filter" in base_content and "-webkit-backdrop-filter" in css_content
    webkit_scrollbar = "::-webkit-scrollbar" in base_content or "::-webkit-scrollbar" in css_content

    total_tests += 2
    if webkit_backdrop:
        print("  ✓ [-webkit-backdrop-filter] Glassmorphism prefix present.")
        passed_tests += 1
    else:
        print("  ✗ [-webkit-backdrop-filter] Missing in base template or CSS.")

    if webkit_scrollbar:
        print("  ✓ [::-webkit-scrollbar] Custom WebKit scrollbars configured.")
        passed_tests += 1
    else:
        print("  ✗ [::-webkit-scrollbar] Missing WebKit scrollbar styling.")

    # 2. Audit Simulated Apple WebKit Requests
    print("\n[REQUEST AUDIT] Simulating Apple Safari & Mobile WebKit Devices...")
    mock_user = User(id=1, username="humberto", role="admin")

    with patch('flask_login.utils._get_user') as mock_get_user:
        mock_get_user.return_value = mock_user

        for device_name, ua_string in APPLE_USER_AGENTS.items():
            print(f"\n  📱 Testing Device: {device_name}")
            headers = {"User-Agent": ua_string}

            for route in ROUTES_TO_TEST:
                total_tests += 1
                res = client.get(route, headers=headers, follow_redirects=True)

                if res.status_code == 200:
                    html = res.get_data(as_text=True)
                    has_viewport = '<meta name="viewport"' in html
                    has_charset = '<meta charset=' in html or '<meta charset="' in html
                    
                    if has_viewport and has_charset:
                        print(f"    ✓ Route: {route:<35} | Status: 200 OK | Viewport: YES")
                        passed_tests += 1
                    else:
                        print(f"    ⚠️ Route: {route:<35} | Status: 200 OK | Viewport: MISSING")
                else:
                    print(f"    ✗ Route: {route:<35} | Status: {res.status_code}")

    print("\n" + "=" * 70)
    print(f" 📊 AUDIT RESULT: {passed_tests}/{total_tests} Tests Passed ({(passed_tests/total_tests)*100:.1f}%)")
    print("=" * 70)

    return passed_tests == total_tests

if __name__ == '__main__':
    success = run_apple_compatibility_audit()
    sys.exit(0 if success else 1)
