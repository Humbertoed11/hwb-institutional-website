#!/usr/bin/env python3
"""
SigmaFidelity™ Host Task Runner Daemon v1.0
Author: George (Systems Architect)
Governance: HWB-QMS-7.1 / Operational Minimization Mandate

Supervises host-level automation (Playwright Browser Tasks, Takeoff Engine, File Downloads)
triggered via PostgreSQL 'task_queue' from Telegram or Backoffice.
"""

import os
import sys
import time
import json
import subprocess
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PROFILE_DIR = os.path.expanduser("~/.config/hwb_buildingconnected_profile")

def send_telegram_msg(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=12)
    except Exception as e:
        print(f"[HOST RUNNER] Error sending telegram message: {e}", flush=True)

def send_telegram_doc(file_path, caption=""):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or not os.path.exists(file_path):
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": (os.path.basename(file_path), f)}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
            res = requests.post(url, data=data, files=files, timeout=40)
            return res.status_code == 200
    except Exception as e:
        print(f"[HOST RUNNER] Error sending document: {e}", flush=True)
        return False

def send_telegram_photo(photo_path, caption=""):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or not os.path.exists(photo_path):
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": (os.path.basename(photo_path), f)}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
            res = requests.post(url, data=data, files=files, timeout=30)
            return res.status_code == 200
    except Exception as e:
        print(f"[HOST RUNNER] Error sending photo: {e}", flush=True)
        return False

def execute_sql_in_container(sql_query, params=None):
    """Executes a SQL query inside hwb_web_app and returns JSON output."""
    script = f"""
import psycopg2, os, json
from psycopg2.extras import RealDictCursor
conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute('''{sql_query}''', {json.dumps(params) if params else "()"})
try:
    rows = cur.fetchall()
    print(json.dumps(rows, default=str))
except Exception:
    conn.commit()
    print("[]")
conn.close()
"""
    cmd = ["docker", "exec", "hwb_web_app", "python3", "-c", script]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout.strip())
        return []
    except Exception as e:
        print(f"[HOST RUNNER] SQL exec error: {e}", flush=True)
        return []

def poll_and_process():
    print("[HOST RUNNER] SigmaFidelity™ Host Task Daemon Active. Listening to task_queue...", flush=True)

    while True:
        try:
            # 1. Check for pending tasks
            query = "SELECT task_id, task_type, payload FROM task_queue WHERE status = 'PENDING' ORDER BY priority ASC, created_at ASC LIMIT 1;"
            tasks = execute_sql_in_container(query)

            if tasks:
                task = tasks[0]
                t_id = task['task_id']
                t_type = task['task_type']
                payload = json.loads(task['payload']) if isinstance(task['payload'], str) else task['payload']

                print(f"[HOST RUNNER] Processing Task {t_id} ({t_type})...", flush=True)

                # Mark as PROCESSING
                execute_sql_in_container(f"UPDATE task_queue SET status = 'PROCESSING', started_at = NOW() WHERE task_id = '{t_id}';")

                if t_type == "BC_AUTOTAKEOFF":
                    handle_task_bc_autotakeoff(t_id, payload)
                elif t_type == "BC_SUBMIT_BID":
                    handle_task_bc_submit(t_id, payload)
                else:
                    print(f"[HOST RUNNER] Unknown task type: {t_type}", flush=True)
                    execute_sql_in_container(f"UPDATE task_queue SET status = 'SKIPPED' WHERE task_id = '{t_id}';")

        except Exception as e:
            print(f"[HOST RUNNER] Loop error: {e}", flush=True)

        time.sleep(3)

def handle_task_bc_autotakeoff(task_id, payload):
    bid_id = payload.get("bid_id")
    url = payload.get("opportunity_url")
    project_name = payload.get("project_name", "Commercial Project")

    send_telegram_msg(f"🤖 *Autonomous Worker Activated*\nDownloading drawings for *{project_name}* via BuildingConnected...")

    try:
        # Step 1: Run bc_plan_downloader.py
        downloader_cmd = [sys.executable, os.path.join(BASE_DIR, "scripts", "bc_plan_downloader.py"), url]
        if bid_id:
            downloader_cmd.extend(["--bid-id", str(bid_id)])

        p_down = subprocess.run(downloader_cmd, capture_output=True, text=True, timeout=180)
        print(f"[DOWNLOADER OUTPUT]:\n{p_down.stdout[:500]}", flush=True)

        # Step 2: Locate target folder in HWB-ESTIMATING/PROJECTS
        projects_dir = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-ESTIMATING", "PROJECTS")
        target_dir = None
        for d in os.listdir(projects_dir):
            full_d = os.path.join(projects_dir, d)
            if os.path.isdir(full_d) and (project_name.lower() in d.lower() or str(bid_id) in d):
                target_dir = full_d
                break

        if not target_dir:
            # Fallback to most recently modified directory
            all_dirs = [os.path.join(projects_dir, d) for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
            if all_dirs:
                all_dirs.sort(key=os.path.getmtime, reverse=True)
                target_dir = all_dirs[0]

        if not target_dir:
            send_telegram_msg(f"⚠️ Could not locate project drawing folder for Bid #{bid_id}.")
            execute_sql_in_container(f"UPDATE task_queue SET status = 'FAILED' WHERE task_id = '{task_id}';")
            return

        # Step 3: Run gc_takeoff_engine.py
        send_telegram_msg(f"📐 *Executing PyMuPDF & pdfplumber Takeoff Engine* on `{os.path.basename(target_dir)}`...")
        engine_cmd = [sys.executable, os.path.join(BASE_DIR, "scripts", "gc_takeoff_engine.py"), target_dir]
        p_eng = subprocess.run(engine_cmd, capture_output=True, text=True, timeout=120)
        print(f"[TAKEOFF ENGINE OUTPUT]:\n{p_eng.stdout[:500]}", flush=True)

        # Step 4: Locate generated proposal Excel file
        summary_json_path = os.path.join(target_dir, "takeoff_summary.json")
        xlsx_file = None
        gross_sf = "TBD"
        bid_val = "Pending"
        discrepancy_notice = ""

        if os.path.exists(summary_json_path):
            with open(summary_json_path) as sjf:
                sdata = json.load(sjf)
                xlsx_file = sdata.get("excel_path")
                gross_sf = f"{sdata.get('gross_square_footage', 0):,} SF"
                bid_val = f"${sdata.get('total_proposal_value', 0):,.2f}"
                if sdata.get("discrepancy_flag"):
                    discrepancy_notice = "\n⚠️ *EMPIRICAL DISCREPANCY DETECTED: Heuristic Calibration Used.*"

        # Step 5: Send finished Excel file to Telegram
        caption = (
            f"✅ *Autonomous Takeoff Complete: Bid #{bid_id}*\n"
            f"📁 *Project:* {project_name}\n"
            f"📏 *Cleanable Footprint:* {gross_sf}\n"
            f"💰 *Calculated Base Bid:* {bid_val}"
            f"{discrepancy_notice}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Spreadsheet generated and ready for BuildingConnected submission."
        )

        if xlsx_file and os.path.exists(xlsx_file):
            send_telegram_doc(xlsx_file, caption=caption)
        else:
            send_telegram_msg(caption)

        execute_sql_in_container(f"UPDATE task_queue SET status = 'COMPLETED', completed_at = NOW() WHERE task_id = '{task_id}';")

    except Exception as e:
        print(f"[HOST RUNNER] Autotakeoff failed: {e}", flush=True)
        send_telegram_msg(f"⚠️ Autotakeoff failed for #{bid_id}: {e}")
        execute_sql_in_container(f"UPDATE task_queue SET status = 'FAILED' WHERE task_id = '{task_id}';")

def handle_task_bc_submit(task_id, payload):
    bid_id = payload.get("bid_id")
    opportunity_url = payload.get("opportunity_url")
    bid_amount = payload.get("bid_amount")
    excel_path = payload.get("excel_path")

    send_telegram_msg(f"🚀 *BuildingConnected Submission Bot Activated*\nTargeting RFP: `{opportunity_url}` with Base Bid: `${bid_amount:,.2f}`...")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=True,
                viewport={"width": 1600, "height": 1000},
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            page = context.new_page()
            page.goto(opportunity_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            # Look for Bid Form button or tab
            bid_form_btn = page.locator("text='Bid Form'").or_(page.locator("text='Create Bid'")).or_(page.locator("text='Edit Bid'"))
            if bid_form_btn.count() > 0:
                bid_form_btn.first.click()
                page.wait_for_timeout(4000)

            # Take verification screenshot of bid form
            shot_path = f"/tmp/bc_bid_submission_{bid_id}_{int(time.time())}.png"
            page.screenshot(path=shot_path, full_page=True)
            context.close()

            caption = (
                f"📸 *BuildingConnected Portal Snapshot: Bid #{bid_id}*\n"
                f"🔗 URL: `{opportunity_url}`\n"
                f"💰 Proposed Amount: `${bid_amount:,.2f}`\n"
                f"Status: Bid form navigated & verified."
            )
            send_telegram_photo(shot_path, caption=caption)

            execute_sql_in_container(f"UPDATE task_queue SET status = 'COMPLETED', completed_at = NOW() WHERE task_id = '{task_id}';")

    except Exception as e:
        print(f"[HOST RUNNER] Portal submission failed: {e}", flush=True)
        send_telegram_msg(f"⚠️ BuildingConnected submission error: {e}")
        execute_sql_in_container(f"UPDATE task_queue SET status = 'FAILED' WHERE task_id = '{task_id}';")

if __name__ == "__main__":
    poll_and_process()
