#!/usr/bin/env python3
"""
SigmaFidelity™ BuildingConnected Automated Plan Downloader
Author: George (Systems Architect)
Governance: HWB-QMS-7.1 / Operational Minimization Mandate

This script uses the persistent BuildingConnected session profile to automatically
access bid invitations, download architectural drawing packages / specifications,
and place them into the designated HWB-ESTIMATING project directories.
"""

import os
import sys
import time
import argparse
import zipfile
import re
import subprocess
from urllib.parse import urlparse, parse_qs, unquote
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESTIMATING_PROJECTS_DIR = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-ESTIMATING", "PROJECTS")
PROFILE_DIR = os.path.expanduser("~/.config/hwb_buildingconnected_profile")
AUTH_STATE_FILE = os.path.join(PROFILE_DIR, "auth_state.json")
LOG_FILE = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-IT", "HWB-IT-SYSTEM-LOGS", "bc_downloads.log")

def decode_proofpoint_url(url: str) -> str:
    """Decodes Proofpoint Defense URL wrappers if present."""
    if "urldefense.proofpoint.com" in url:
        match = re.search(r'[?&]u=([^&]+)', url)
        if match:
            u = match.group(1)
            u = u.replace('-3A__', '://').replace('https-3A__', 'https://').replace('http-3A__', 'http://')
            u = u.replace('_', '/')
            u = u.replace('-2D', '-')
            u = u.replace('-2E', '.')
            u = u.replace('-3F', '?').replace('-3D', '=').replace('-26', '&').replace('-23', '#')
            return unquote(u)
    return url

def log_event(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")

def update_bid_status_in_db(bid_id: int, status: str = "Plans Downloaded", plan_notes: str = ""):
    """Updates the ConstructionBids table inside the PostgreSQL container."""
    try:
        # Sanitize single quotes
        safe_notes = plan_notes.replace("'", "''")
        sql = f"""
        docker exec hwb_web_app python3 -c "
import psycopg2, os
conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
cur = conn.cursor()
cur.execute('''
    UPDATE \\\"ConstructionBids\\\"
    SET status = %s, plan_url = %s, updated_at = NOW()
    WHERE id = %s
''', ('{status}', '{safe_notes}', {bid_id}))
conn.commit()
conn.close()
"
        """
        subprocess.run(sql, shell=True, check=True)
        log_event(f"Updated database record #{bid_id} -> '{status}'")
    except Exception as e:
        log_event(f"Error updating database record #{bid_id}: {e}")

def sanitize_folder_name(name: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9_\- ]', '', name).strip()
    return clean.replace(' ', '-')

def download_rfp_plans(url: str, project_folder: str = None, bid_id: int = None, headful: bool = False):
    target_url = decode_proofpoint_url(url)
    log_event(f"Targeting BuildingConnected URL: {target_url}")

    if not os.path.exists(PROFILE_DIR):
        log_event("❌ Profile directory not found! Run 'python3 scripts/bc_auth_setup.py' first.")
        return False

    with sync_playwright() as p:
        log_event(f"Launching browser (Headless: {not headful})...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=not headful,
            viewport={"width": 1600, "height": 900},
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )

        page = context.new_page()
        page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)

        current_url = page.url
        log_event(f"Landed on: {current_url}")

        # Check if redirected to login
        if "login" in current_url.lower() or "auth" in current_url.lower():
            log_event("❌ Session expired or unauthenticated! Please run 'python3 scripts/bc_auth_setup.py' to refresh.")
            context.close()
            return False

        # Dismiss onboarding dialogs / modal backdrops
        page.evaluate("""() => {
            const buttons = Array.from(document.querySelectorAll('button, a'));
            const gotIt = buttons.find(b => b.textContent.includes('Got It!'));
            if (gotIt) gotIt.click();
            document.querySelectorAll('[class*="overlay"], [class*="backdrop"], [class*="modal"]').forEach(el => {
                if (!el.textContent.includes('Download All') && !el.textContent.includes('Drawings')) {
                    el.remove();
                }
            });
        }""")
        page.wait_for_timeout(2000)

        # Extract Project Name if not provided
        if not project_folder:
            try:
                title = page.title()
                if title and title != "BuildingConnected" and title != "--":
                    project_folder = sanitize_folder_name(title)
                else:
                    heading = page.query_selector("h1, h2, [data-qa='project-name']")
                    if heading:
                        project_folder = sanitize_folder_name(heading.inner_text().split('\n')[0])
            except Exception:
                project_folder = None
        
        if not project_folder:
            project_folder = f"BC-Project-{int(time.time())}"

        destination_dir = os.path.join(ESTIMATING_PROJECTS_DIR, project_folder)
        os.makedirs(destination_dir, exist_ok=True)
        log_event(f"Destination folder: {destination_dir}")

        # If on an opportunity page, navigate directly to /files
        if "/opportunities/" in page.url and not page.url.endswith("/files"):
            # strip sub-routes
            base_opp = re.sub(r'(/opportunities/[^/]+).*', r'\1', page.url)
            files_url = f"{base_opp}/files"
            log_event(f"Navigating to Files section: {files_url}")
            page.goto(files_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(6000)

        # Trigger download via JS click
        log_event("Attempting download trigger...")
        download_success = False

        try:
            with page.expect_download(timeout=120000) as download_info:
                has_clicked = page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const dlBtn = btns.find(b => b.textContent.trim().toLowerCase().includes('download all'));
                    if (dlBtn) {
                        dlBtn.click();
                        return true;
                    }
                    return false;
                }""")
                if not has_clicked:
                    # Fallback to any file download button
                    has_clicked = page.evaluate("""() => {
                        const dl = document.querySelector('button:has-text("Download"), a[download]');
                        if (dl) { dl.click(); return true; }
                        return false;
                    }""")

            download = download_info.value
            suggested_filename = download.suggested_filename
            save_path = os.path.join(destination_dir, suggested_filename)
            log_event(f"Downloading {suggested_filename} to {save_path}...")
            download.save_as(save_path)
            fsize = os.path.getsize(save_path)
            log_event(f"✅ Successfully downloaded: {suggested_filename} ({fsize:,} bytes)")

            # Extract if ZIP
            if suggested_filename.endswith(".zip"):
                log_event(f"Extracting ZIP archive {suggested_filename}...")
                with zipfile.ZipFile(save_path, 'r') as zip_ref:
                    zip_ref.extractall(destination_dir)
                log_event(f"✅ Extracted files into: {destination_dir}")

            download_success = True
        except Exception as e:
            log_event(f"Download trigger failed or timed out: {e}")

        # Update database if bid_id provided
        if download_success and bid_id:
            update_bid_status_in_db(bid_id, "Plans Downloaded", destination_dir)

        context.close()
        return download_success

def main():
    parser = argparse.ArgumentParser(description="BuildingConnected Automated Plan Downloader")
    parser.add_argument("--url", type=str, help="BuildingConnected RFP URL or Proofpoint wrapper")
    parser.add_argument("--project", type=str, help="Target folder name in HWB-ESTIMATING/PROJECTS")
    parser.add_argument("--bid-id", type=int, help="Optional ConstructionBids ID to update")
    parser.add_argument("--headful", action="store_true", help="Run browser visibly for debugging")
    args = parser.parse_args()

    if not args.url:
        print("Usage: python3 scripts/bc_plan_downloader.py --url <BuildingConnected_URL> [--project <FOLDER>] [--bid-id <ID>]")
        sys.exit(1)

    success = download_rfp_plans(args.url, args.project, args.bid_id, args.headful)
    if success:
        print("\n🎉 Plan download completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️ Plan download could not complete automatically. Check logs.")
        sys.exit(1)

if __name__ == "__main__":
    main()
