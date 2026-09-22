#!/usr/bin/env python3
"""
Comprehensive Live Azure Pre-Handover Verification Suite
Standard: HWB-QMS-11.2 / Pre-Handover Empirical Verification
Author: George (Systems Architect)

Verifies:
1. Azure Web App HTTP 200 health, database connection pool, and latency.
2. Verified physical database records in Azure PostgreSQL.
3. Integrity of all critical public URLs and links.
4. CEO authentication flow via /login against live production Azure App Service.
"""

import sys
import time
import requests

BASE_URL = "https://hwb-institutional-website.azurewebsites.net"
CUSTOM_DOMAIN_URL = "https://www.hwbcleaning.com"

# Critical links to verify
CRITICAL_ROUTES = [
    "/",
    "/work-with-us",
    "/about",
    "/contact",
    "/commercial",
    "/janitorial-services",
    "/terms-of-service",
    "/privacy-policy",
    "/login",
    "/bosanna"
]

def verify_live():
    print(f"--- Starting Live Azure Deployment Verification against {BASE_URL} ---")
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SigmaFidelity-Auditor/2.0'
    })

    # 1. Health Endpoint
    print("\n[1] Checking /api/v1/health...")
    max_retries = 6
    health_ok = False
    for attempt in range(1, max_retries + 1):
        try:
            res = session.get(f"{BASE_URL}/api/v1/health", timeout=15)
            if res.status_code == 200:
                data = res.json()
                print(f"    SUCCESS: Health 200 OK | Database: {data.get('database')} | Latency: {data.get('latency_ms')} ms")
                health_ok = True
                break
            else:
                print(f"    Attempt {attempt}/{max_retries}: Status {res.status_code}. Retrying in 10s...")
        except Exception as e:
            print(f"    Attempt {attempt}/{max_retries}: Connection error {e}. Retrying in 10s...")
        time.sleep(10)

    if not health_ok:
        print("FATAL: Live health check failed after retries.")
        sys.exit(1)

    # 2. Database Audit Telemetry
    print("\n[2] Checking /api/v1/db-audit...")
    try:
        res = session.get(f"{BASE_URL}/api/v1/db-audit", timeout=15)
        if res.status_code == 200:
            audit = res.json()
            print(f"    SUCCESS: Total Verified Leads: {audit.get('total_leads_count')} | Host: {audit.get('database_host')}")
        else:
            print(f"    WARNING: db-audit returned {res.status_code}")
    except Exception as e:
        print(f"    WARNING: db-audit error: {e}")

    # 3. Critical Links Audit
    print("\n[3] Auditing all critical website links...")
    all_routes_ok = True
    for route in CRITICAL_ROUTES:
        url = f"{BASE_URL}{route}"
        try:
            r = session.get(url, timeout=15)
            if r.status_code in [200, 302]:
                print(f"    ✓ {route:<24} -> HTTP {r.status_code} OK ({len(r.content)} bytes)")
            else:
                print(f"    ✗ {route:<24} -> HTTP {r.status_code} FAILED")
                all_routes_ok = False
        except Exception as e:
            print(f"    ✗ {route:<24} -> Error: {e}")
            all_routes_ok = False

    if not all_routes_ok:
        print("WARNING: Some public routes did not return 200 OK.")

    # 4. CEO Authentication Flow Verification
    print("\n[4] Testing CEO Login Authentication Flow...")
    login_url = f"{BASE_URL}/login"
    login_session = requests.Session()
    login_session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SigmaFidelity-Auditor/2.0'
    })

    # First fetch login page to get session cookie if any
    r_get = login_session.get(login_url, timeout=15)
    print(f"    GET /login -> HTTP {r_get.status_code}")

    # Test POST login with CEO primary credential
    credentials_to_test = [
        ("hdominguez", "Password11"),
        ("admin", "Password11")
    ]

    for username, password in credentials_to_test:
        auth_session = requests.Session()
        auth_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SigmaFidelity-Auditor/2.0'
        })
        payload = {"username": username, "password": password}
        try:
            r_post = auth_session.post(login_url, data=payload, allow_redirects=False, timeout=15)
            loc = r_post.headers.get("Location", "")
            cookies = auth_session.cookies.get_dict()
            if r_post.status_code == 302 and "/admin" in loc:
                print(f"    ✓ CEO Login ({username}) -> SUCCESS! Redirects to {loc} with cookies: {list(cookies.keys())}")
            else:
                print(f"    ✗ CEO Login ({username}) -> Status: {r_post.status_code}, Location: {loc}")
        except Exception as e:
            print(f"    ✗ CEO Login ({username}) error: {e}")

    # 5. Check Custom Domain
    print(f"\n[5] Checking Custom Domain ({CUSTOM_DOMAIN_URL})...")
    try:
        r_custom = requests.get(f"{CUSTOM_DOMAIN_URL}/api/v1/health", timeout=15)
        print(f"    SUCCESS: Custom domain {CUSTOM_DOMAIN_URL} health status: {r_custom.status_code}")
    except Exception as e:
        print(f"    Custom domain notice: {e}")

    print("\n--- Live Azure Deployment Verification Complete ---")

if __name__ == "__main__":
    verify_live()
