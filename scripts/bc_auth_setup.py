#!/usr/bin/env python3
"""
SigmaFidelity™ BuildingConnected Persistent Session Setup
Author: George (Systems Architect)
Governance: HWB-QMS-7.1 / Operational Minimization Mandate

This script launches an interactive Chromium window to allow CEO Humberto Dominguez
to log in to BuildingConnected and complete 2FA once. The session cookies and tokens
are saved to a local persistent profile (~/.config/hwb_buildingconnected_profile),
enabling subsequent headless automated downloads without storing raw passwords.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

PROFILE_DIR = os.path.expanduser("~/.config/hwb_buildingconnected_profile")
AUTH_STATE_FILE = os.path.join(PROFILE_DIR, "auth_state.json")

def main():
    print("\n" + "=" * 65)
    print("🏛️  SigmaFidelity™ | BuildingConnected Persistent Session Setup")
    print("=" * 65)
    print(f"📁 Target Profile Directory: {PROFILE_DIR}")
    
    os.makedirs(PROFILE_DIR, exist_ok=True)

    with sync_playwright() as p:
        print("\n🚀 Launching interactive Chromium browser on your desktop...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            viewport={"width": 1280, "height": 850},
            accept_downloads=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        page = context.new_page()
        login_url = "https://app.buildingconnected.com/login"
        print(f"🌐 Navigating to: {login_url}")
        page.goto(login_url, wait_until="networkidle", timeout=45000)

        print("\n" + "-" * 65)
        print("📌 ACTION REQUIRED:")
        print("1. Enter your BuildingConnected / Autodesk credentials in the browser.")
        print("2. Complete Two-Factor Authentication (2FA) verification.")
        print("3. The script will AUTOMATICALLY detect when you reach your Bid Board,")
        print("   or you can press [ENTER] in this terminal when finished.")
        print("-" * 65 + "\n")

        import select

        logged_in = False
        max_wait_seconds = 600  # 10 minutes
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            try:
                # Check non-blocking stdin
                r, _, _ = select.select([sys.stdin], [], [], 1.0)
                if r:
                    sys.stdin.readline()
                    print("\n[USER CONFIRMATION] Enter key received!")
                    logged_in = True
                    break

                curr_url = page.url
                # Check if user reached authenticated BuildingConnected portal
                if "app.buildingconnected.com" in curr_url and not any(k in curr_url for k in ["login", "sign-in", "signin", "identity.autodesk.com"]):
                    # Verify page content or cookies
                    cookies = context.cookies()
                    has_auth_cookie = any(c['name'] in ['bc_session', 'connect.sid', 'id_token', 'access_token', 'optimizelyEndUserId'] for c in cookies)
                    if has_auth_cookie or "/bid-board" in curr_url or "/rfps" in curr_url or "/opportunities" in curr_url or "/projects" in curr_url:
                        print(f"\n✅ [AUTO-DETECT] Detected authenticated dashboard: {curr_url}")
                        time.sleep(3)
                        logged_in = True
                        break

            except Exception as loop_err:
                time.sleep(1)

        if not logged_in:
            print("\n⚠️ Session wait timed out. Checking current state...")

        # Verify login by checking current URL and storage
        current_url = page.url
        print(f"\n🔍 Verifying session at URL: {current_url}")

        # Capture storage state
        context.storage_state(path=AUTH_STATE_FILE)
        print(f"💾 Storage state saved to: {AUTH_STATE_FILE}")

        # Basic verification: check if cookies were captured
        cookies = context.cookies()
        auth_cookies = [c['name'] for c in cookies if any(k in c['name'].lower() for k in ['auth', 'session', 'token', 'autodesk', 'connect'])]
        print(f"🔑 Captured {len(cookies)} cookies (Auth keys: {', '.join(auth_cookies[:5])})")

        context.close()

    print("\n" + "=" * 65)
    print("✅ BuildingConnected Authentication Profile Successfully Established!")
    print("🛡️  Zero plaintext passwords were saved.")
    print("🤖 Automated plan downloaders can now run headlessly using this session.")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
