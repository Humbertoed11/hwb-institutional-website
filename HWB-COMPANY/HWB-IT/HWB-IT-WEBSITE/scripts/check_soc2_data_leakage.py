#!/usr/bin/env python3
"""
SigmaFidelity™ Automated SOC 2 Data Leakage & Blueprint Infiltration Sentinel
Standard: SOC 2 Type II / ISO 27001 A.8.10 / HWB-QMS-11.2
Approved: Executive Leadership
Architect: George (Systems Architect)

Objective:
Continuous automated auditing of application ingress, route classification,
authenticated boundaries, role-based document segregation, and zero-leakage
assurance across all public-facing endpoints.
"""

import os
import sys
import re
import unittest
from typing import Dict, Any, List

# Ensure application paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if "/app" not in sys.path and os.path.exists("/app/main_app.py"):
    sys.path.insert(0, "/app")

from main_app import app

FORBIDDEN_PATTERNS = [
    (r"SECRET_KEY\s*=", "SECRET_KEY variable leak"),
    (r"AZURE_CLIENT_SECRET\s*=", "Azure Client Secret leak"),
    (r"MICROSOFT_GRAPH_CLIENT_SECRET\s*=", "Microsoft Graph Secret leak"),
    (r"TELEGRAM_BOT_TOKEN\s*=", "Telegram Bot Token leak"),
    (r"postgres(?:ql)?://[^\s\"'<>]+:[^\s\"'<>]+@", "Database connection string with credentials"),
    (r"-----BEGIN (?:RSA )?PRIVATE KEY-----", "Private key certificate leak"),
    (r"\$2[aby]\$\d{2}\$[A-Za-z0-9./]{53}", "Bcrypt password hash leak"),
    (r"Traceback \(most recent call last\):", "Python stack trace leak"),
    (r"psycopg2\.(?:OperationalError|ProgrammingError|DatabaseError)", "Raw database exception leak"),
]

PUBLIC_ROUTES_TO_CRAWL = [
    "/",
    "/about",
    "/services/janitorial",
    "/services/commercial",
    "/services/industrial",
    "/services/construction",
    "/compliance",
    "/ehsq",
    "/methodology",
    "/privacy-policy",
    "/terms",
    "/trust-center",
    "/work-with-us",
    "/careers",
    "/get-quote",
    "/capability",
]

def run_soc2_leakage_audit(test_app=None) -> Dict[str, Any]:
    """
    Executes comprehensive SOC 2 Data Leakage & Route Isolation audit.
    Returns audit summary dictionary.
    """
    target_app = test_app or app
    client = target_app.test_client()
    failures = []
    checks_passed = 0

    print("\n" + "=" * 80)
    print("🛡️  SIGMAFIDELITY™ SOC 2 DATA LEAKAGE & ROUTE ISOLATION SENTINEL")
    print("   Standard: SOC 2 Type II / NIST SP 800-63B / HWB-QMS-11.2")
    print("=" * 80)

    # 1. Unauthenticated Route Boundary Check
    print("\n[CHECK 1] Testing Unauthenticated Route Isolation on Internal Manuals...")
    unauth_endpoints = [
        ("/manual", "Manual Index"),
        ("/manual/hwb-qms-1.1_institutional_dictionary_and_architectural_lexicon.html", "General QMS SOP"),
        ("/manual/hwb-acc-001_accounting_management_sop.html", "Accounting SOP"),
        ("/manual/hwb-acc-2026-03-13-azure-service-cost-forecast.html", "Azure Cost Forecast"),
        ("/my-signature", "Executive Signature Vault"),
        ("/admin/operations", "Operations Command Center"),
        ("/admin/operations?view=gc_bids", "Bidding Pipeline Desk"),
    ]

    for url, desc in unauth_endpoints:
        res = client.get(url)
        if res.status_code not in [302, 401, 403]:
            failures.append(f"Unauthenticated leak: {desc} ({url}) returned HTTP {res.status_code}, expected redirect/denial")
            print(f"  ❌ FAIL: {desc} ({url}) -> HTTP {res.status_code}")
        else:
            checks_passed += 1
            loc = res.headers.get("Location", "")
            print(f"  ✅ PASS: {desc} ({url}) blocked -> HTTP {res.status_code} (Redirect: {loc[:40]}...)")

    # 2. Path Traversal & Infiltration Attack Defense
    print("\n[CHECK 2] Testing Path Traversal Defense...")
    traversal_urls = [
        "/manual/../main_app.py",
        "/manual/../../etc/passwd",
        "/manual/%2e%2e%2fmain_app.py",
    ]
    for t_url in traversal_urls:
        res = client.get(t_url)
        # Must not return 200 with code
        if res.status_code == 200 and ("Flask(" in res.data.decode('utf-8', errors='ignore') or "root:" in res.data.decode('utf-8', errors='ignore')):
            failures.append(f"Path traversal breach: {t_url} leaked file content!")
            print(f"  ❌ FAIL: {t_url} leaked file content!")
        else:
            checks_passed += 1
            print(f"  ✅ PASS: Path traversal rejected: {t_url} -> HTTP {res.status_code}")

    # 3. Role-Based Access Control (RBAC) Department Partitioning
    print("\n[CHECK 3] Testing Role Partitioning (Standard Operator vs. Executive vs. Custom Role)...")
    # Standard Operator session (user_id=9 is operator_standard, role='Operator')
    with client.session_transaction() as sess:
        sess['_user_id'] = '9'

    res_op_acc = client.get('/manual/hwb-acc-001_accounting_management_sop.html')
    if res_op_acc.status_code != 403:
        failures.append(f"RBAC breach: Operator accessed Accounting SOP! Status: {res_op_acc.status_code}")
        print(f"  ❌ FAIL: Operator accessed Accounting SOP -> HTTP {res_op_acc.status_code} (Expected 403)")
    else:
        checks_passed += 1
        print(f"  ✅ PASS: Standard Operator blocked from Accounting SOP -> HTTP 403 Forbidden")

    res_op_qms = client.get('/manual/hwb-qms-1.1_institutional_dictionary_and_architectural_lexicon.html')
    if res_op_qms.status_code != 200:
        failures.append(f"RBAC false positive: Standard Operator could not access general QMS SOP! Status: {res_op_qms.status_code}")
        print(f"  ❌ FAIL: Standard Operator blocked from Staff QMS SOP -> HTTP {res_op_qms.status_code}")
    else:
        checks_passed += 1
        print(f"  ✅ PASS: Standard Operator granted access to Staff QMS SOP -> HTTP 200 OK")

    res_op_manual = client.get('/manual')
    if res_op_manual.status_code != 200:
        failures.append(f"RBAC false positive: Standard Operator blocked from manual index! Status: {res_op_manual.status_code}")
        print(f"  ❌ FAIL: Standard Operator blocked from manual index -> HTTP {res_op_manual.status_code}")
    else:
        checks_passed += 1
        print(f"  ✅ PASS: Standard Operator granted access to Manual Index -> HTTP 200 OK")

    # Executive session (user_id=2, role='Executive')
    with client.session_transaction() as sess:
        sess['_user_id'] = '2'

    res_exec_acc = client.get('/manual/hwb-acc-001_accounting_management_sop.html')
    if res_exec_acc.status_code != 200:
        failures.append(f"RBAC false positive: Executive could not access Accounting SOP! Status: {res_exec_acc.status_code}")
        print(f"  ❌ FAIL: Executive denied Accounting SOP -> HTTP {res_exec_acc.status_code}")
    else:
        checks_passed += 1
        print(f"  ✅ PASS: Executive granted access to Accounting SOP -> HTTP 200 OK")

    # Custom Role session (user_id=3 is mrondinella, role='Custom', qms: view=false)
    with client.session_transaction() as sess:
        sess['_user_id'] = '3'

    res_custom_manual = client.get('/manual')
    if res_custom_manual.status_code != 403:
        failures.append(f"Zero-Trust Custom role breach: Custom user accessed /manual! Status: {res_custom_manual.status_code}")
        print(f"  ❌ FAIL: Custom user accessed /manual -> HTTP {res_custom_manual.status_code} (Expected 403)")
    else:
        checks_passed += 1
        print(f"  ✅ PASS: Custom user (qms: view=false) blocked from /manual -> HTTP 403 Forbidden")
        manual_html = res_custom_manual.data.decode('utf-8', errors='ignore')
        if "Access Restricted" in manual_html and "You do not have permission to view this section" in manual_html:
            checks_passed += 1
            print(f"  ✅ PASS: Official HWB 403 page rendered with Everyday Words security explanation")
        else:
            failures.append("Official HWB 403 page missing expected security explanation")
            print(f"  ❌ FAIL: 403 response missing official HWB page content!")

    res_custom_sop = client.get('/manual/hwb-qms-1.1_institutional_dictionary_and_architectural_lexicon.html')
    if res_custom_sop.status_code != 403:
        failures.append(f"Zero-Trust Custom role breach: Custom user accessed QMS SOP! Status: {res_custom_sop.status_code}")
        print(f"  ❌ FAIL: Custom user accessed QMS SOP -> HTTP {res_custom_sop.status_code} (Expected 403)")
    else:
        checks_passed += 1
        print(f"  ✅ PASS: Custom user (qms: view=false) blocked from QMS SOP -> HTTP 403 Forbidden")

    # Clear session for public scanning
    client = target_app.test_client()

    # 4. Sensitive Secret Scanning on Public Endpoints
    print("\n[CHECK 4] Scanning Public Endpoints for Sensitive Secret Leaks...")
    for route in PUBLIC_ROUTES_TO_CRAWL:
        res = client.get(route)
        if res.status_code != 200:
            # Skip non-existent routes if redirect
            if res.status_code in [301, 302]:
                continue
            failures.append(f"Public route unavailable: {route} returned HTTP {res.status_code}")
            print(f"  ⚠️  WARN: Public route {route} returned HTTP {res.status_code}")
            continue

        body = res.data.decode('utf-8', errors='ignore')
        leaks_found = []
        for pattern, desc in FORBIDDEN_PATTERNS:
            if re.search(pattern, body):
                leaks_found.append(desc)

        if leaks_found:
            failures.append(f"Data leak on {route}: {', '.join(leaks_found)}")
            print(f"  ❌ FAIL: {route} leaked: {leaks_found}")
        else:
            checks_passed += 1
            print(f"  ✅ PASS: {route:30} -> Clean (0 secrets detected)")

    # 5. Public Trust Center Integrity Check
    print("\n[CHECK 5] Testing Public Trust Center (/trust-center)...")
    res_trust = client.get('/trust-center')
    if res_trust.status_code != 200:
        failures.append(f"Trust Center unavailable: HTTP {res_trust.status_code}")
        print(f"  ❌ FAIL: /trust-center returned HTTP {res_trust.status_code}")
    else:
        trust_body = res_trust.data.decode('utf-8', errors='ignore')
        checks = [
            ("ISO 9001", "ISO 9001 Compliance status"),
            (".43", "0.43 Experience Modification Rate"),
            ("2,000,000", "$2,000,000 General Liability coverage"),
            ("802920409", "Texas Secretary of State Charter"),
        ]
        missing_trust = []
        for needle, label in checks:
            if needle not in trust_body:
                missing_trust.append(label)
        
        if missing_trust:
            failures.append(f"Trust Center missing credentials: {missing_trust}")
            print(f"  ❌ FAIL: Trust Center missing credentials: {missing_trust}")
        else:
            checks_passed += 1
            print(f"  ✅ PASS: /trust-center verified with all 4 public compliance credentials")

    # 6. Granular ABAC & Custom Permissions Dynamic Query Enforcement
    print("\n[CHECK 6] Testing Granular ABAC Custom Permissions Enforcement on Views...")

    # Establish Operator session with custom permissions (user_id=3 is mrondinella, restricted to leads view only)
    client = target_app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = '3'

    # 6A: Authorized View Verification
    res_leads = client.get('/admin/operations?view=leads')
    if res_leads.status_code != 200:
        failures.append(f"ABAC false positive: Restricted user blocked from authorized 'leads' view! Status: {res_leads.status_code}")
        print(f"  ❌ FAIL: Authorized 'leads' view returned HTTP {res_leads.status_code} (Expected 200)")
    else:
        checks_passed += 1
        print(f"  ✅ PASS: Authorized 'leads' view accessible -> HTTP 200 OK")

        # 6B: Navigation DOM Ribbon Hygiene Check
        leads_html = res_leads.data.decode('utf-8', errors='ignore')
        if 'id="tab-leads-container"' not in leads_html:
            failures.append("DOM hygiene failure: '#tab-leads-container' missing for user with leads permission")
            print("  ❌ FAIL: '#tab-leads-container' missing from navigation ribbon")
        else:
            checks_passed += 1
            print("  ✅ PASS: Navigation ribbon displays authorized '#tab-leads-container'")

        forbidden_tab_markers = [
            ('id="tab-accounts-container"', "Accounts Tab"),
            ('id="tab-gcbids-container"', "Construction Bids Tab"),
            ('id="tab-instbids-container"', "Institutions Tab"),
            ('id="tab-programs-container"', "Certifications Tab"),
            ('id="tab-marketing-btn"', "Marketing Button"),
            ('id="tab-workforce-container"', "Workforce Tab"),
            ('id="tab-dispatch-container"', "Dispatch Tab"),
            ('id="tab-execit-container"', "Executive Command Tab"),
            ('id="header-qms-manual-btn"', "Header QMS Manual Button"),
            ('id="utility-qms-manual-btn"', "Utility Bar QMS Manual Button"),
        ]
        for marker, tab_name in forbidden_tab_markers:
            if marker in leads_html:
                failures.append(f"Visual privilege leak: {tab_name} ({marker}) rendered for restricted user!")
                print(f"  ❌ FAIL: Visual privilege leak: {tab_name} ({marker}) present in DOM!")
            else:
                checks_passed += 1
                print(f"  ✅ PASS: Visual boundary enforced: {tab_name} physically omitted from DOM")

    # 6C: Unauthorized Dynamic Query-Parameter Bypass Attempts (CWE-285 Prevention)
    unauthorized_views = [
        ("accounts", "Clients / Accounts Hub"),
        ("construction_bids", "Construction Bids Pipeline"),
        ("institutional_bids", "Public Institutional Solicitations"),
        ("general_contractors", "General Contractors Directory"),
        ("programs", "Government Programs Desk"),
        ("marketing", "Marketing Campaigns Engine"),
        ("workforce", "Personnel & Roster System"),
        ("safety", "Safety & EHSQ Module"),
        ("monitor", "Field Operations & Shift Monitor"),
        ("dispatch", "Shift Dispatch Engine"),
        ("scope", "Scopes Matrix Engine"),
        ("it_department", "IT Department & Systems Hub"),
    ]

    for view_param, view_desc in unauthorized_views:
        res_view = client.get(f'/admin/operations?view={view_param}')
        if res_view.status_code != 403:
            failures.append(f"ABAC authorization bypass (CWE-285): Restricted user accessed unauthorized view '{view_param}' ({view_desc})! Status: {res_view.status_code}")
            print(f"  ❌ FAIL: View '{view_param}' ({view_desc}) -> HTTP {res_view.status_code} (Expected 403 Forbidden)")
        else:
            checks_passed += 1
            print(f"  ✅ PASS: View '{view_param}' ({view_desc}) blocked -> HTTP 403 Forbidden")

    # 6D: Sales Desk & Manual Route Access Control
    res_sales_desk = client.get('/sales-desk')
    if res_sales_desk.status_code != 403:
        failures.append(f"ABAC bypass on /sales-desk: Status {res_sales_desk.status_code} (Expected 403)")
        print(f"  ❌ FAIL: /sales-desk accessible to restricted operator -> HTTP {res_sales_desk.status_code}")
    else:
        checks_passed += 1
        print(f"  ✅ PASS: /sales-desk blocked for restricted operator -> HTTP 403 Forbidden")

    res_custom_manual_6d = client.get('/manual')
    if res_custom_manual_6d.status_code != 403:
        failures.append(f"Zero-Trust Custom role bypass: Restricted user accessed /manual! Status: {res_custom_manual_6d.status_code}")
        print(f"  ❌ FAIL: /manual accessible to restricted custom user -> HTTP {res_custom_manual_6d.status_code}")
    else:
        checks_passed += 1
        print(f"  ✅ PASS: /manual blocked for restricted custom operator -> HTTP 403 Forbidden")

    # 6E: Executive Unhindered View Verification (user_id=2, role='Executive')
    client = target_app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = '2'

    exec_views = ['accounts', 'construction_bids', 'marketing', 'workforce', 'monitor']
    for ev in exec_views:
        res_ev = client.get(f'/admin/operations?view={ev}')
        if res_ev.status_code != 200:
            failures.append(f"ABAC false positive: Executive denied '{ev}' view! Status: {res_ev.status_code}")
            print(f"  ❌ FAIL: Executive denied '{ev}' view -> HTTP {res_ev.status_code}")
        else:
            checks_passed += 1
            print(f"  ✅ PASS: Executive granted full access to '{ev}' -> HTTP 200 OK")

    # -------------------------------------------------------------
    # [CHECK 7] REST API ABAC & Mutation Gating (Yamamoto Moto Battery)
    # -------------------------------------------------------------
    print("\n[CHECK 7] Testing Asynchronous REST API ABAC & Mutation Gating (Yamamoto Battery)...")
    client = target_app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = '3'  # mrondinella (Custom: leads view=True, edit=False, delete=False; accounts all False)

    api_mutation_probes = [
        ("LEADS", "PUT", "/api/v1/leads/83574", {"notes": "Tamper Test"}, True),
        ("LEADS", "PATCH", "/api/v1/leads/83574", {"status": "Qualified"}, True),
        ("LEADS", "POST", "/api/v1/leads/83574/cadence-save", {"decision_maker": "Tamper Test"}, True),
        ("LEADS", "POST", "/api/v1/leads/83574/contacts", {"full_name": "Tamper"}, True),
        ("LEADS", "POST", "/api/v1/leads/batch-action", {"action": "update_status", "lead_ids": [83574]}, True),
        ("LEADS", "POST", "/api/v1/leads/batch-action", {"action": "delete", "lead_ids": [99999999]}, True),
        ("LEADS", "DELETE", "/api/v1/leads/99999999", None, False),
        ("ACCOUNTS", "GET", "/api/v1/accounts/1", None, False),
        ("ACCOUNTS", "PUT", "/api/v1/accounts/1", {"notes": "Tamper"}, True),
        ("ACCOUNTS", "POST", "/api/v1/accounts/1/contacts", {"full_name": "Tamper"}, True),
        ("ACCOUNTS", "DELETE", "/api/v1/accounts/99999999", None, False),
    ]

    for mod, mth, ep, payload, is_json in api_mutation_probes:
        if mth == "GET":
            res = client.get(ep)
        elif mth == "POST":
            res = client.post(ep, json=payload if is_json else None)
        elif mth == "PUT":
            res = client.put(ep, json=payload if is_json else None)
        elif mth == "PATCH":
            res = client.patch(ep, json=payload if is_json else None)
        elif mth == "DELETE":
            res = client.delete(ep)

        if res.status_code != 403:
            failures.append(f"REST API ABAC Breach: Restricted user {mth} {ep} returned HTTP {res.status_code} (Expected 403 Forbidden)")
            print(f"  ❌ FAIL: {mod} {mth} {ep} allowed -> HTTP {res.status_code} (Expected 403)")
        else:
            checks_passed += 1
            print(f"  ✅ PASS: {mod} {mth} {ep} defended -> HTTP 403 Forbidden")

    print("\n" + "=" * 80)
    if not failures:
        print(f"🏆 AUDIT RESULT: PASSED ({checks_passed} checks verified clean)")
        print("   Zero unauthenticated data leaks. Technical manual isolation enforced.")
        print("=" * 80 + "\n")
        return {"status": "PASS", "checks_passed": checks_passed, "failures": []}
    else:
        print(f"🚨 AUDIT RESULT: FAILED ({len(failures)} violations detected)")
        for f in failures:
            print(f"   - {f}")
        print("=" * 80 + "\n")
        return {"status": "FAIL", "checks_passed": checks_passed, "failures": failures}


class SOC2DataLeakageTestCase(unittest.TestCase):
    def test_audit(self):
        result = run_soc2_leakage_audit(app)
        self.assertEqual(result.get("status"), "PASS", f"Violations: {result.get('failures')}")

if __name__ == "__main__":
    result = run_soc2_leakage_audit()
    sys.exit(0 if result["status"] == "PASS" else 1)
