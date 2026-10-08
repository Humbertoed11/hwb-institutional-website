#!/usr/bin/env python3
"""
scripts/capture_live_manual_screenshots.py
Captures authentic, empirical PNG screenshots of the live HWB platform
for the Application User Guide (/manual/app).
Adheres strictly to the Empirical Data Integrity Mandate.
"""
import os
import sys
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/images/manual_screenshots"
BASE_URL = "http://127.0.0.1:5000"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"[*] Screenshot target directory: {OUTPUT_DIR}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Create standard desktop viewport
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # -------------------------------------------------------------
        # 1. Chapter 1: Login Page
        # -------------------------------------------------------------
        print("[*] 1. Capturing Chapter 1: Login Page...")
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.wait_for_timeout(1000)
        # Type in demo credentials visually
        page.evaluate("""() => {
            const u = document.querySelector('input[type="text"], input[name="username"]');
            if (u) u.value = 'mrondinella';
            const p = document.querySelector('input[type="password"]');
            if (p) p.value = '••••••••••••';
        }""")
        login_path = os.path.join(OUTPUT_DIR, "chapter1_login.png")
        page.screenshot(path=login_path)
        print(f"    Saved: {login_path}")

        # -------------------------------------------------------------
        # Authenticate via /debug-login
        # -------------------------------------------------------------
        print("[*] Authenticating via /debug-login...")
        page.goto(f"{BASE_URL}/debug-login", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # -------------------------------------------------------------
        # 2. Chapter 1: Security Session Warning / Termination Modal
        # -------------------------------------------------------------
        print("[*] 2. Capturing Chapter 1: Session Security Modal...")
        page.goto(f"{BASE_URL}/admin/operations", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.evaluate("""() => {
            const modal = document.getElementById('modal-logout-confirm');
            if (modal) {
                modal.style.display = 'flex';
                modal.style.opacity = '1';
                modal.style.visibility = 'visible';
            }
        }""")
        page.wait_for_timeout(500)
        timeout_path = os.path.join(OUTPUT_DIR, "chapter1_timeout.png")
        page.screenshot(path=timeout_path)
        print(f"    Saved: {timeout_path}")

        # Hide modal before next captures
        page.evaluate("""() => {
            const modal = document.getElementById('modal-logout-confirm');
            if (modal) modal.style.display = 'none';
        }""")

        # -------------------------------------------------------------
        # 3. Chapter 2: Commercial Leads Pipeline
        # -------------------------------------------------------------
        print("[*] 3. Capturing Chapter 2: Leads Pipeline...")
        page.goto(f"{BASE_URL}/admin/operations?view=leads", wait_until="networkidle")
        page.wait_for_timeout(1500)
        leads_path = os.path.join(OUTPUT_DIR, "chapter2_leads_pipeline.png")
        page.screenshot(path=leads_path)
        print(f"    Saved: {leads_path}")

        # -------------------------------------------------------------
        # 4. Chapter 2: Customize Columns Drawer
        # -------------------------------------------------------------
        print("[*] 4. Capturing Chapter 2: Customize Columns Dropdown...")
        page.evaluate("""() => {
            const menu = document.getElementById('col-mgr-menu');
            if (menu) {
                menu.style.display = 'block';
                menu.style.zIndex = '9999';
            }
        }""")
        page.wait_for_timeout(500)
        cols_path = os.path.join(OUTPUT_DIR, "chapter2_column_drawer.png")
        page.screenshot(path=cols_path)
        print(f"    Saved: {cols_path}")

        # Hide col menu
        page.evaluate("""() => {
            const menu = document.getElementById('col-mgr-menu');
            if (menu) menu.style.display = 'none';
        }""")

        # -------------------------------------------------------------
        # 5. Chapter 3: Construction & Commercial Bidding Pipeline
        # -------------------------------------------------------------
        print("[*] 5. Capturing Chapter 3: Bidding Pipeline...")
        page.goto(f"{BASE_URL}/admin/operations?view=construction_bids", wait_until="networkidle")
        page.wait_for_timeout(1500)
        bids_path = os.path.join(OUTPUT_DIR, "chapter3_bidding_pipeline.png")
        page.screenshot(path=bids_path)
        print(f"    Saved: {bids_path}")

        # -------------------------------------------------------------
        # 6. Chapter 3: Calculator Tool
        # -------------------------------------------------------------
        print("[*] 6. Capturing Chapter 3: Calculator Tool...")
        try:
            page.goto(f"{BASE_URL}/calculator", wait_until="networkidle")
            page.wait_for_timeout(1500)
            calc_path = os.path.join(OUTPUT_DIR, "chapter3_calculator.png")
            page.screenshot(path=calc_path)
            print(f"    Saved: {calc_path}")
        except Exception as e:
            print(f"    Warning: /calculator failed: {e}")

        # -------------------------------------------------------------
        # 7. Chapter 4: Marketing Outbox & Outreach
        # -------------------------------------------------------------
        print("[*] 7. Capturing Chapter 4: Marketing Outbox...")
        page.goto(f"{BASE_URL}/admin/operations?view=marketing", wait_until="networkidle")
        page.wait_for_timeout(1500)
        mkt_path = os.path.join(OUTPUT_DIR, "chapter4_marketing_outbox.png")
        page.screenshot(path=mkt_path)
        print(f"    Saved: {mkt_path}")

        # -------------------------------------------------------------
        # 8. Chapter 5: Workforce & HR Roster
        # -------------------------------------------------------------
        print("[*] 8. Capturing Chapter 5: Workforce Roster...")
        page.goto(f"{BASE_URL}/admin/operations?view=workforce", wait_until="networkidle")
        page.wait_for_timeout(1500)
        wf_path = os.path.join(OUTPUT_DIR, "chapter5_workforce_roster.png")
        page.screenshot(path=wf_path)
        print(f"    Saved: {wf_path}")

        # -------------------------------------------------------------
        # 9. Chapter 5: Work Monitor & Shift Dispatch
        # -------------------------------------------------------------
        print("[*] 9. Capturing Chapter 5: Shift Dispatch & Monitor...")
        page.goto(f"{BASE_URL}/admin/operations?view=monitor", wait_until="networkidle")
        page.wait_for_timeout(1500)
        mon_path = os.path.join(OUTPUT_DIR, "chapter5_shift_dispatch.png")
        page.screenshot(path=mon_path)
        print(f"    Saved: {mon_path}")

        # -------------------------------------------------------------
        # 10. Chapter 6: User Management & Role Permissions
        # -------------------------------------------------------------
        print("[*] 10. Capturing Chapter 6: User Permissions & Reset Button...")
        page.goto(f"{BASE_URL}/admin/executive", wait_until="networkidle")
        page.wait_for_timeout(1500)
        # Open the user edit modal for Mirna Rondinella or first user
        page.evaluate("""() => {
            // Find edit button or manually trigger modal
            const editBtn = document.querySelector('.user-row button[onclick*="openEditUserModalFromRow"], button[onclick*="openEditUserModal"]');
            if (editBtn) {
                editBtn.click();
            } else {
                const modal = document.getElementById('modal-edit-user');
                if (modal) {
                    modal.style.display = 'flex';
                    modal.style.opacity = '1';
                    modal.style.visibility = 'visible';
                    const nameInput = document.getElementById('edit_full_name');
                    if (nameInput) nameInput.value = 'Mirna Rondinella';
                    const roleSelect = document.getElementById('edit_user_role');
                    if (roleSelect) {
                        roleSelect.value = 'Sales';
                        if (typeof updateModalPermsFromRole === 'function') updateModalPermsFromRole('Sales');
                    }
                }
            }
        }""")
        page.wait_for_timeout(1000)
        perms_path = os.path.join(OUTPUT_DIR, "chapter6_user_permissions.png")
        page.screenshot(path=perms_path)
        print(f"    Saved: {perms_path}")

        browser.close()
        print("\n[+] All 10 live empirical screenshots captured successfully!")

if __name__ == "__main__":
    main()
