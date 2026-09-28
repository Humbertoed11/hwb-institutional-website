#!/usr/bin/env python3
"""
SigmaFidelity™ Telegram Executive Operations Command Center v3.0
Author: George (Systems Architect)
Governance: HWB-QMS-7.1 / Operational Minimization Mandate / Empirical Integrity Mandate

Full 6-Frontier Architecture:
1. Frontier 1: 1-Tap BuildingConnected Autonomous Planroom Ingestion & Takeoff Dispatch
2. Frontier 2: Interactive Scope Configurator (Telegram Mini App + In-Chat Live Sliders)
3. Frontier 3: Multimodal Voice-to-Action Directive Engine (Gemini 2.5 Flash -> Graph API Calendar/Outbox)
4. Frontier 4: Jobsite Camera & Blueprint Photo Computer Vision (Gemini 2.5 Flash Vision -> Instant Bid)
5. Frontier 5: 1-Tap BuildingConnected Portal Bid Submitter (Playwright Automation via task_queue)
6. Frontier 6: Autonomous 7:00 AM Daily Executive Briefing & Telemetry Pulse (/briefing)
"""

import os
import re
import sys
import time
import json
import base64
import tempfile
import threading
import subprocess
import concurrent.futures
from datetime import datetime, timezone, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from dotenv import load_dotenv
import msal
from bs4 import BeautifulSoup
from dateutil import parser as dt_parser

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

CID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TID = os.getenv("GRAPH_API_PROD_TENANT_ID")
USER_EMAIL = "hdominguez@hwbcleaning.com"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Container context DB route
if "@localhost" in DB_URL and os.path.exists("/.dockerenv"):
    DB_URL = DB_URL.replace("@localhost", "@db")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("[TELEGRAM] CRITICAL: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing from .env", flush=True)
    sys.exit(1)

def get_ceo_chat_id() -> int:
    """Returns the primary CEO Telegram Chat ID safely regardless of comma-separated configs."""
    raw = os.getenv("TELEGRAM_CHAT_ID", "8564340073")
    try:
        first_id = raw.split(",")[0].strip()
        return int(first_id)
    except Exception:
        return 8564340073

def get_allowed_chat_ids() -> list:
    """Returns a list of all integer chat IDs configured in .env."""
    raw = os.getenv("TELEGRAM_CHAT_ID", "8564340073")
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids or [8564340073]

ALLOWED_CHAT_ID = get_ceo_chat_id()

# Resilient HTTP session
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

def get_db_connection():
    """Returns an active connection to PostgreSQL with container fallback."""
    try:
        return psycopg2.connect(DB_URL)
    except Exception:
        fallback_url = DB_URL.replace("@localhost", "@db").replace("@127.0.0.1", "@db")
        return psycopg2.connect(fallback_url)

def get_authorized_chat_map():
    """
    Returns a dict mapping chat_id (as str and int) to user info dict:
    {
        8564340073: {"user_id": 2, "username": "hdominguez", "name": "Humberto Dominguez", "role": "Executive", "email": "hdominguez@hwbcleaning.com"},
        ...
    }
    """
    auth_map = {}
    ceo_perms = {
        "enabled": True,
        "can_approve_outbox": True,
        "can_run_terminal_cmd": True,
        "can_view_margins": True,
        "can_ingest_bids": True,
        "can_search_web": True,
        "can_audit_photos": True,
        "receive_daily_briefing": True
    }
    # 1. Add from .env TELEGRAM_CHAT_ID (supports comma-separated list)
    env_cids = os.getenv("TELEGRAM_CHAT_ID", "8564340073").split(",")
    for cid in env_cids:
        cid = cid.strip()
        if not cid:
            continue
        try:
            int_cid = int(cid)
            auth_map[int_cid] = {"username": "ceo", "name": "Humberto Dominguez", "role": "Executive", "email": "hdominguez@hwbcleaning.com", "telegram_perms": ceo_perms}
            auth_map[str(int_cid)] = auth_map[int_cid]
        except ValueError:
            auth_map[cid] = {"username": "ceo", "name": "Humberto Dominguez", "role": "Executive", "email": "hdominguez@hwbcleaning.com", "telegram_perms": ceo_perms}

    # 2. Add from PostgreSQL Users table where telegram_chat_id IS NOT NULL and status = 'Active'
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT id, username, full_name, email, role, telegram_chat_id, custom_permissions FROM "Users" WHERE status = \'Active\' AND telegram_chat_id IS NOT NULL AND telegram_chat_id != \'\' ORDER BY (CASE WHEN username = \'admin\' THEN 2 ELSE 1 END), id ASC;')
            for u in cur.fetchall():
                t_id = str(u.get("telegram_chat_id") or "").strip()
                if not t_id:
                    continue

                c_perms_raw = u.get("custom_permissions")
                c_perms = {}
                if c_perms_raw:
                    try:
                        c_perms = json.loads(c_perms_raw) if isinstance(c_perms_raw, str) else c_perms_raw
                    except Exception:
                        c_perms = {}

                tg_cfg = c_perms.get("telegram", {})
                is_exec = (u["role"] in ["Executive", "Admin"]) or (t_id in env_cids)
                is_estimator = (u["role"] == "Estimator")

                default_tg_perms = {
                    "enabled": True,
                    "can_approve_outbox": is_exec,
                    "can_run_terminal_cmd": is_exec,
                    "can_view_margins": is_exec or is_estimator,
                    "can_ingest_bids": is_exec or is_estimator,
                    "can_search_web": True,
                    "can_audit_photos": True,
                    "receive_daily_briefing": is_exec
                }

                effective_tg = {**default_tg_perms, **tg_cfg}
                if effective_tg.get("enabled") is False:
                    continue

                user_info = {
                    "user_id": u["id"],
                    "username": u["username"],
                    "name": u["full_name"] or u["username"],
                    "email": u["email"],
                    "role": u["role"],
                    "telegram_perms": effective_tg
                }
                try:
                    int_t = int(t_id)
                    # Poka-Yoke: Do not let generic 'admin' overwrite a named executive profile
                    existing = auth_map.get(int_t) or auth_map.get(str(int_t))
                    if existing and u["username"] == "admin" and existing.get("username") != "admin":
                        continue
                    auth_map[int_t] = user_info
                    auth_map[str(int_t)] = user_info
                except ValueError:
                    existing = auth_map.get(t_id)
                    if existing and u["username"] == "admin" and existing.get("username") != "admin":
                        continue
                    auth_map[t_id] = user_info
        conn.close()
    except Exception as e:
        pass

    return auth_map

def is_chat_authorized(chat_id):
    auth_map = get_authorized_chat_map()
    return (chat_id in auth_map) or (str(chat_id) in auth_map)

def get_user_for_chat(chat_id):
    auth_map = get_authorized_chat_map()
    return auth_map.get(chat_id) or auth_map.get(str(chat_id))

def welcome_unregistered_user(chat_id, from_user):
    sender_name = from_user.get("first_name", "Team Member")
    msg = (
        f"👋 *Welcome to HWB Cleaning Operations*, {sender_name}!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"This is the automated Operations Command Center for **HWB Cleaning Services LLC**.\n\n"
        f"📱 Your Telegram Chat ID is: `{chat_id}`\n\n"
        f"To link your account, reply:\n"
        f"`/register mrondinella@hwbcleaning.com` (or your company email)\n\n"
        f"Or send this Chat ID to CEO Humberto Dominguez to activate your access."
    )
    send_telegram_message(chat_id, msg)

def handle_user_registration(chat_id, text, from_user):
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(
            chat_id,
            "⚠️ *Registration Usage:*\n"
            "Please provide your HWB company email or username:\n"
            "Example: `/register mrondinella@hwbcleaning.com`"
        )
        return

    identifier = parts[1].strip()
    sender_name = from_user.get("first_name", "Team Member")
    username_tg = from_user.get("username", "")

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT id, username, full_name, email, role, status, telegram_chat_id 
                FROM "Users" 
                WHERE LOWER(email) = LOWER(%s) OR LOWER(username) = LOWER(%s);
            ''', (identifier, identifier))
            user = cur.fetchone()

            if not user:
                conn.close()
                send_telegram_message(
                    chat_id,
                    f"❌ *Account Not Found*\n"
                    f"No active HWB user profile matching `{identifier}` was found.\n"
                    f"Please check with management for your company email."
                )
                return

            if user["status"] != "Active":
                conn.close()
                send_telegram_message(
                    chat_id,
                    f"⚠️ *Account Inactive*\n"
                    f"The profile for `{identifier}` is currently inactive."
                )
                return

            # Update telegram_chat_id
            cur.execute('''
                UPDATE "Users" 
                SET telegram_chat_id = %s 
                WHERE id = %s;
            ''', (str(chat_id), user["id"]))
            conn.commit()
            conn.close()

            user_name = user["full_name"] or user["username"]
            role = user["role"]

            send_telegram_message(
                chat_id,
                f"✅ *Welcome {user_name}!*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Your Telegram account has been linked to **HWB Cleaning Operations**.\n\n"
                f"👤 *Role:* {role}\n"
                f"🆔 *Chat ID:* `{chat_id}`\n"
                f"✉️ *Email:* {user['email']}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"You are now registered to receive real-time operational notifications and alerts.\n"
                f"Tap `/help` to view available commands."
            )

            # Alert CEO
            try:
                ceo_chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "8564340073").split(",")[0].strip())
                if str(ceo_chat_id) != str(chat_id):
                    send_telegram_message(
                        ceo_chat_id,
                        f"🔔 *Team Member Linked to Telegram*\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"👤 *Name:* {user_name}\n"
                        f"💼 *Role:* {role} ({user['email']})\n"
                        f"📱 *Telegram Chat ID:* `{chat_id}`\n"
                        f"✈️ *Telegram User:* @{username_tg or sender_name}\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"User has been authenticated and can now receive operations alerts."
                    )
            except Exception:
                pass
            print(f"[TELEGRAM] User {user_name} successfully linked to chat_id {chat_id}", flush=True)

    except Exception as e:
        print(f"[TELEGRAM ERROR] Registration failed: {e}", flush=True)
        send_telegram_message(chat_id, f"⚠️ Error linking account: {e}")

def handle_magic_link_auth(chat_id, token, from_user):
    token = token.strip()
    if not token:
        welcome_unregistered_user(chat_id, from_user)
        return

    sender_name = from_user.get("first_name", "Team Member")
    username_tg = from_user.get("username", "")

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT id, username, full_name, email, role, status, custom_permissions, telegram_chat_id FROM "Users";')
            users = cur.fetchall()

            target_user = None
            for u in users:
                c_perms = u.get("custom_permissions")
                if c_perms:
                    try:
                        p_dict = json.loads(c_perms) if isinstance(c_perms, str) else c_perms
                        tg_cfg = p_dict.get("telegram", {})
                        if tg_cfg.get("auth_token") == token:
                            target_user = (u, p_dict)
                            break
                    except Exception:
                        pass

            if not target_user:
                conn.close()
                send_telegram_message(
                    chat_id,
                    "❌ *Invalid or Expired Onboarding Link*\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "This magic link is either invalid, already used, or expired.\n\n"
                    "Please contact CEO Humberto Dominguez or log in to the SigmaFidelity™ Executive Backoffice to request a fresh onboarding link."
                )
                return

            u_record, p_dict = target_user
            if u_record["status"] != "Active":
                conn.close()
                send_telegram_message(
                    chat_id,
                    "⚠️ *Account Inactive*\n"
                    f"The account for @{u_record['username']} is currently suspended."
                )
                return

            tg_cfg = p_dict.get("telegram", {})
            tg_cfg["enabled"] = True
            tg_cfg.pop("auth_token", None)
            tg_cfg["linked_at"] = datetime.now().isoformat()
            p_dict["telegram"] = tg_cfg

            cur.execute('UPDATE "Users" SET telegram_chat_id = %s, custom_permissions = %s WHERE id = %s;', 
                        (str(chat_id), json.dumps(p_dict), u_record["id"]))
            conn.commit()
            conn.close()

            u_name = u_record["full_name"] or u_record["username"]
            u_role = u_record["role"]

            send_telegram_message(
                chat_id,
                f"🚀 *Welcome to SigmaFidelity™ Operations Control*, {u_name}!\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"Your Telegram profile has been successfully linked to your company account.\n\n"
                f"👤 *Username:* @{u_record['username']}\n"
                f"💼 *System Role:* {u_role}\n"
                f"🆔 *Chat ID:* `{chat_id}`\n"
                f"✉️ *Email:* {u_record['email']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"You can now receive operational notifications, facility walkthrough alerts, and communicate with George.\n\n"
                f"Send `/help` or tap an option below to get started.",
                reply_markup=get_main_menu_keyboard(chat_id)
            )

            # Alert CEO
            try:
                ceo_chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "8564340073").split(",")[0].strip())
                if str(ceo_chat_id) != str(chat_id):
                    send_telegram_message(
                        ceo_chat_id,
                        f"🔔 *Team Member Onboarded via Magic Link*\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 *Name:* {u_name} (@{u_record['username']})\n"
                        f"💼 *Role:* {u_role} ({u_record['email']})\n"
                        f"📱 *Telegram Chat ID:* `{chat_id}`\n"
                        f"✈️ *Telegram Handle:* @{username_tg or sender_name}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Authentication token consumed. User is live in operations."
                    )
            except Exception:
                pass
            print(f"[TELEGRAM] User {u_name} successfully linked via magic link to chat_id {chat_id}", flush=True)
    except Exception as e:
        print(f"[TELEGRAM ERROR] Magic link authentication failed: {e}", flush=True)
        send_telegram_message(chat_id, f"⚠️ Error linking account: {e}")

def handle_cmd_terminal(chat_id, command_str):
    auth_user = get_user_for_chat(chat_id)
    perms = auth_user.get("telegram_perms", {}) if auth_user else {}
    if not perms.get("can_run_terminal_cmd"):
        send_telegram_message(
            chat_id,
            "🚫 *Permission Denied*\n"
            "Your user profile does not have authorization for Terminal Shell Execution (`can_run_terminal_cmd`).\n"
            "This capability is restricted to CEO and System Administrators."
        )
        return

    cmd = command_str.strip()
    if not cmd:
        send_telegram_message(
            chat_id,
            "⚡ *SigmaFidelity™ Terminal Shell Gateway*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Execute Linux shell commands directly from your mobile device:\n\n"
            "Usage: `/cmd <bash command>`\n\n"
            "Examples:\n"
            "• `/cmd docker ps`\n"
            "• `/cmd git status`\n"
            "• `/cmd df -h`"
        )
        return

    send_telegram_chat_action(chat_id, "typing")
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=35,
            cwd="/home/humbertoed/gemini_projects"
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        ret_code = proc.returncode

        status_badge = "✅ *SUCCESS (0)*" if ret_code == 0 else f"❌ *EXIT CODE ({ret_code})*"

        combined_output = ""
        if stdout:
            combined_output += stdout
        if stderr:
            if combined_output:
                combined_output += "\n--- STDERR ---\n"
            combined_output += stderr

        if not combined_output:
            combined_output = "(No output produced)"

        if len(combined_output) > 3500:
            combined_output = combined_output[:3500] + "\n... [OUTPUT TRUNCATED]"

        msg = (
            f"⚡ *Terminal Command:* `{cmd}`\n"
            f"📊 Status: {status_badge}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"```bash\n{combined_output}\n```"
        )
        send_telegram_message(chat_id, msg)
    except subprocess.TimeoutExpired:
        send_telegram_message(chat_id, "⚠️ *Execution Timed Out* (>35s). For long background tasks, launch asynchronously.")
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ *Execution Error:* {e}")

def handle_cmd_adduser(chat_id, arg):
    parts = arg.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "⚠️ Usage: `/adduser <username/email> <chat_id>`\nExample: `/adduser mrondinella 123456789`")
        return
    identifier, target_chat_id = parts[0], parts[1]
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT id, username, full_name, email, role FROM "Users" WHERE LOWER(email) = LOWER(%s) OR LOWER(username) = LOWER(%s);', (identifier, identifier))
            u = cur.fetchone()
            if not u:
                conn.close()
                send_telegram_message(chat_id, f"❌ User `{identifier}` not found in database.")
                return
            cur.execute('UPDATE "Users" SET telegram_chat_id = %s WHERE id = %s;', (str(target_chat_id), u["id"]))
            conn.commit()
            conn.close()
            send_telegram_message(chat_id, f"✅ Linked *{u['full_name'] or u['username']}* ({u['role']}) to Telegram Chat ID `{target_chat_id}`.")
            try:
                send_telegram_message(int(target_chat_id), f"✅ *Account Activated!*\nCEO Humberto Dominguez has linked your Telegram account to HWB Operations Control. Welcome!")
            except Exception:
                pass
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error linking user: {e}")

def handle_cmd_users(chat_id):
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT id, username, full_name, role, status, telegram_chat_id FROM "Users" ORDER BY id ASC;')
            rows = cur.fetchall()
            conn.close()
            lines = ["👥 *HWB Operations Team Members:*"]
            for r in rows:
                status_icon = "🟢" if r["telegram_chat_id"] else "⚪"
                cid_display = f"`{r['telegram_chat_id']}`" if r["telegram_chat_id"] else "_Not Linked_"
                lines.append(f"{status_icon} *{r['full_name'] or r['username']}* ({r['role']})\n   Telegram: {cid_display}")
            send_telegram_message(chat_id, "\n".join(lines))
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error fetching team: {e}")

def send_telegram_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    """Dispatches a formatted message with optional inline keyboard buttons. Auto-chunks if >4000 chars."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    if len(text) > 4000:
        chunks = []
        current = text
        while len(current) > 4000:
            split_idx = current.rfind("\n\n", 0, 4000)
            if split_idx == -1:
                split_idx = current.rfind("\n", 0, 4000)
            if split_idx == -1:
                split_idx = 4000
            chunks.append(current[:split_idx])
            current = current[split_idx:].lstrip()
        if current:
            chunks.append(current)

        for i, chunk in enumerate(chunks):
            chunk_markup = reply_markup if i == len(chunks) - 1 else None
            payload = {"chat_id": chat_id, "text": chunk}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            if chunk_markup:
                payload["reply_markup"] = chunk_markup
            try:
                res = session.post(url, json=payload, timeout=15)
                if res.status_code != 200 and parse_mode:
                    payload.pop("parse_mode", None)
                    session.post(url, json=payload, timeout=15)
            except Exception as e:
                print(f"[TELEGRAM] Error sending chunk: {e}", flush=True)
        return

    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        res = session.post(url, json=payload, timeout=15)
        if res.status_code != 200 and parse_mode:
            payload.pop("parse_mode", None)
            session.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"[TELEGRAM] Error sending message: {e}", flush=True)

def edit_telegram_message(chat_id, message_id, text, reply_markup=None, parse_mode="Markdown"):
    """Updates an existing message in-place for seamless slider/recalculation UX."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        res = session.post(url, json=payload, timeout=12)
        if res.status_code != 200 and parse_mode:
            payload.pop("parse_mode", None)
            session.post(url, json=payload, timeout=12)
    except Exception as e:
        print(f"[TELEGRAM] Error editing message: {e}", flush=True)


def send_telegram_chat_action(chat_id, action="typing"):
    """Displays typing or document upload status in the Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendChatAction"
    try:
        session.post(url, json={"chat_id": chat_id, "action": action}, timeout=5)
    except Exception:
        pass

def send_telegram_document(chat_id, file_path, caption="", reply_markup=None):
    """Sends a local file (.xlsx, .pdf, etc.) directly into Telegram."""
    if not os.path.exists(file_path):
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": (os.path.basename(file_path), f)}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
            res = session.post(url, data=data, files=files, timeout=40)
            if res.status_code != 200:
                data.pop("parse_mode", None)
                f.seek(0)
                res = session.post(url, data=data, files=files, timeout=40)
            return res.status_code == 200
    except Exception as e:
        print(f"[TELEGRAM] Error sending document: {e}", flush=True)
        return False

def answer_callback_query(callback_id, text=None):
    """Acknowledges an inline button click to dismiss the loading indicator."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    try:
        session.post(url, json=payload, timeout=8)
    except Exception as e:
        print(f"[TELEGRAM] Error answering callback: {e}", flush=True)

# --- TELEGRAM BEHAVIORAL TELEMETRY & EXECUTIVE MIRRORING SYSTEM ---

def log_telegram_event(user_id, chat_id, user_handle, user_full_name, user_role, event_type, payload_summary, detected_intent=None, friction_flag=False, latency_ms=0, mirrored=False):
    """
    Persists granular interaction telemetry into PostgreSQL 'TelegramEventStream'
    and updates the active interaction metrics on 'UserBehavioralProfiles'.
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "TelegramEventStream" (
                    user_id, chat_id, user_handle, user_full_name, user_role,
                    event_type, payload_summary, detected_intent, friction_flag,
                    latency_ms, mirrored_to_ceo, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id;
            """, (
                user_id, chat_id, user_handle, user_full_name, user_role,
                event_type, payload_summary[:1000] if payload_summary else "",
                detected_intent, friction_flag, latency_ms, mirrored
            ))
            event_id = cur.fetchone()[0]

            if user_id:
                cur.execute("""
                    UPDATE "UserBehavioralProfiles"
                    SET total_interactions = total_interactions + 1,
                        last_active_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s;
                """, (user_id,))
            conn.commit()
        conn.close()
        return event_id
    except Exception as e:
        print(f"[TELEMETRY ERROR] Failed to log Telegram event: {e}", flush=True)
        return None

def mirror_activity_to_ceo(actor_user, chat_id, from_user, event_type, payload_summary, detected_intent=None, friction_flag=False):
    """
    Real-time activity mirroring to CEO Humberto Dominguez (chat_id: 8564340073).
    Mirrors critical user actions, queries, button clicks, voice notes, and uploads
    performed by any team member or incoming contact.
    Enterprise Fault-Tolerant: Failures in mirroring will NEVER crash the caller.
    """
    try:
        ceo_chat_id = get_ceo_chat_id()
        
        # Do not mirror CEO's own direct actions back to his own chat window
        if str(chat_id) == str(ceo_chat_id):
            return False

        actor_name = actor_user.get("name") if actor_user else None
        if not actor_name and from_user:
            f_name = f"{from_user.get('first_name', '')} {from_user.get('last_name', '')}".strip()
            actor_name = f_name or from_user.get("username") or f"Contact #{chat_id}"
        elif not actor_name:
            actor_name = f"Contact #{chat_id}"

        actor_role = actor_user.get("role", "Unregistered") if actor_user else "External Contact"
        handle_str = f"@{from_user.get('username')}" if from_user and from_user.get("username") else (f"@{actor_user.get('username')}" if actor_user and actor_user.get("username") else f"ID `{chat_id}`")
        
        timestamp = datetime.now().strftime("%I:%M:%S %p CST")
        
        alert_icon = "⚠️" if friction_flag else "📡"
        mirror_msg = (
            f"{alert_icon} *[TELEGRAM ACTIVITY MIRROR]*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Actor:* {actor_name} ({actor_role})\n"
            f"🏷️ *Handle:* {handle_str} | Chat `{chat_id}`\n"
            f"⚡ *Event:* `{event_type.upper()}`\n"
            f"🎯 *Intent:* `{detected_intent or 'General'}`\n"
            f"📝 *Details:* {payload_summary}\n"
            f"⏰ *Time:* {timestamp}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧠 _Logged to TelegramEventStream for behavioral profiling._"
        )

        send_telegram_message(ceo_chat_id, mirror_msg)
        return True
    except Exception as e:
        print(f"[MIRROR ERROR] Failed to mirror Telegram activity to CEO: {e}", flush=True)
        return False

def record_and_mirror_activity(chat_id, from_user, event_type, payload_summary, detected_intent=None, friction_flag=False, latency_ms=0):
    """
    Unified entry point to both record to database stream and mirror to CEO.
    Hardened with Poka-Yoke exception isolation so telemetry failures NEVER abort processing.
    """
    actor_user = get_user_for_chat(chat_id)
    user_id = actor_user.get("user_id") if actor_user else None
    user_handle = from_user.get("username") if from_user else (actor_user.get("username") if actor_user else None)
    user_full_name = actor_user.get("name") if actor_user else (f"{from_user.get('first_name', '')} {from_user.get('last_name', '')}".strip() if from_user else None)
    user_role = actor_user.get("role") if actor_user else "Unregistered"

    # Mirror to CEO if not CEO himself
    mirrored = False
    try:
        mirrored = mirror_activity_to_ceo(actor_user, chat_id, from_user, event_type, payload_summary, detected_intent, friction_flag)
    except Exception as me:
        print(f"[MIRROR ERROR] Non-fatal mirror failure: {me}", flush=True)

    # Log to PostgreSQL
    event_id = None
    try:
        event_id = log_telegram_event(
            user_id=user_id,
            chat_id=chat_id,
            user_handle=user_handle,
            user_full_name=user_full_name,
            user_role=user_role,
            event_type=event_type,
            payload_summary=payload_summary,
            detected_intent=detected_intent,
            friction_flag=friction_flag,
            latency_ms=latency_ms,
            mirrored=mirrored
        )
    except Exception as le:
        print(f"[TELEMETRY ERROR] Non-fatal logging failure: {le}", flush=True)

    return event_id

def handle_cmd_mirror(chat_id, arg=""):
    """Displays real-time mirroring telemetry and team activity feed."""
    ceo_chat_id = get_ceo_chat_id()
    conn = get_db_connection()
    stats = {}
    recent = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT COUNT(*) as total_events,
                       COUNT(CASE WHEN mirrored_to_ceo THEN 1 END) as total_mirrored,
                       COUNT(CASE WHEN created_at >= CURRENT_DATE THEN 1 END) as today_events
                FROM "TelegramEventStream";
            """)
            stats = cur.fetchone() or {}
            cur.execute("""
                SELECT user_full_name, user_role, event_type, payload_summary, created_at
                FROM "TelegramEventStream"
                WHERE chat_id != %s
                ORDER BY created_at DESC
                LIMIT 5;
            """, (ceo_chat_id,))
            recent = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"[MIRROR STATUS ERROR] {e}", flush=True)

    report = (
        f"📡 *[EXECUTIVE TELEGRAM MIRROR STATUS]*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 *Executive Target:* Chat ID `{ceo_chat_id}` (Active & Armed)\n"
        f"📊 *Stream Telemetry:* {stats.get('total_events', 0)} total events ({stats.get('today_events', 0)} today)\n"
        f"🪞 *Activity Mirrored to CEO:* {stats.get('total_mirrored', 0)} events\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Recent Mirrored Team Activities:*\n"
    )
    if recent:
        for r in recent:
            t = r['created_at'].strftime('%I:%M %p') if r.get('created_at') else '--'
            report += f"• `{t}` *{r.get('user_full_name') or 'User'}* ({r.get('user_role', 'Team')}): {r.get('payload_summary', '')[:50]}\n"
    else:
        report += "• _No external user activities logged yet today._\n"

    send_telegram_message(chat_id, report)

def handle_cmd_behavioral_insights(chat_id):
    """Synthesizes and displays live behavioral profiles for team members."""
    send_telegram_chat_action(chat_id, "typing")
    try:
        from scripts.telegram_behavioral_engine import analyze_all_user_behaviors
        profiles = analyze_all_user_behaviors()
        
        msg = "🧠 *[SIGMAFIDELITY™ USER BEHAVIORAL PROFILES]*\n━━━━━━━━━━━━━━━━━━━━━\n"
        for p in profiles:
            msg += f"👤 *{p['full_name']}* (`{p['role']}`)\n"
            msg += f"📊 *Total Events:* {p['total_events']}\n"
            msg += f"📝 *Insight:* {p['qualitative_summary']}\n"
            if p.get('friction_summary') and 'Zero' not in p['friction_summary'] and 'Heuristic' not in p['friction_summary']:
                msg += f"⚠️ *Friction:* {p['friction_summary']}\n"
            msg += "─────────────────────\n"
        
        send_telegram_message(chat_id, msg)
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error generating behavioral insights: {e}")

def get_main_menu_keyboard(chat_id=None):
    custom_rows = []
    if chat_id:
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT adaptive_preferences FROM "UserBehavioralProfiles" WHERE chat_id = %s;', (chat_id,))
                prof = cur.fetchone()
                if prof and prof.get("adaptive_preferences"):
                    rec_btns = prof["adaptive_preferences"].get("recommended_home_buttons", [])
                    if rec_btns:
                        row = []
                        for b in rec_btns[:4]:
                            row.append({"text": f"⭐ {b['text']}", "callback_data": b['callback_data']})
                            if len(row) == 2:
                                custom_rows.append(row)
                                row = []
                        if row:
                            custom_rows.append(row)
            conn.close()
        except Exception:
            pass

    default_keyboard = [
        [{"text": "🏫 Collin College Hub", "callback_data": "cmd_collin"}, {"text": "📑 Send Collin Excel", "callback_data": "proposal_17"}],
        [{"text": "📊 Active GC Bids", "callback_data": "cmd_bids"}, {"text": "📈 System Pulse", "callback_data": "cmd_status"}],
        [{"text": "📬 Staged Approvals", "callback_data": "cmd_pending"}, {"text": "🎯 Texas CRM Leads", "callback_data": "cmd_leads"}],
        [{"text": "📐 Scope Configurator", "callback_data": "cmd_scope_menu"}, {"text": "🌅 Morning Brief", "callback_data": "cmd_briefing"}],
        [{"text": "🧠 Behavioral Insights", "callback_data": "cmd_behavior"}, {"text": "📡 Mirror Status", "callback_data": "cmd_mirror"}],
        [{"text": "🔍 Universal Search", "callback_data": "cmd_search_prompt"}, {"text": "🧠 Brain Sync", "callback_data": "cmd_sync"}]
    ]
    return {"inline_keyboard": custom_rows + default_keyboard}

def clean_html_content(html_text):
    if not html_text:
        return ""
    html_text = re.sub(r'<(script|style)\b[^>]*>([\s\S]*?)</\1>', '', html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'<!--[\s\S]*?-->', '', html_text)
    clean_text = re.sub(r'<br\s*/?>', '\n', html_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'</p>', '\n\n', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'</div>', '\n', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
    return re.sub(r'[ \t]+', ' ', clean_text).strip()

def enqueue_task(task_type, payload):
    """Enqueues an asynchronous automation task into PostgreSQL task_queue."""
    task_id = f"task_{int(time.time())}_{task_type.lower()}"
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO task_queue (task_id, task_type, priority, payload, status, created_at)
                VALUES (%s, %s, 1, %s, 'PENDING', NOW());
            """, (task_id, task_type, json.dumps(payload)))
        conn.commit()
        return task_id
    except Exception as e:
        print(f"[TASK QUEUE] Error enqueuing task {task_type}: {e}", flush=True)
        return None
    finally:
        if conn:
            conn.close()

def find_proposal_file(bid_id, project_name="", gc_name=""):
    search_dirs = [
        "/app/static/proposals",
        os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE", "static", "proposals"),
        os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-ESTIMATING", "PROPOSALS")
    ]
    keywords = []
    combined = (str(project_name) + " " + str(gc_name)).lower()
    if "collin" in combined or "frisco" in combined or "bosanna" in combined or str(bid_id) == "17":
        keywords = ["collin", "frisco", "bid-model"]
    elif "utsw" in combined or "microbiology" in combined:
        keywords = ["utsw", "microbiology"]
    elif "mycon" in combined or "hillside" in combined:
        keywords = ["mycon", "hillside"]
    elif "weekes" in combined or "barnes" in combined:
        keywords = ["weekes", "barnes"]
    elif "novel" in combined or "stacked" in combined:
        keywords = ["novel", "stacked"]

    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        try:
            for f in os.listdir(sdir):
                fl = f.lower()
                if any(k in fl for k in keywords) and fl.endswith(".xlsx"):
                    return os.path.join(sdir, f)
        except Exception:
            pass
    # Explicit check for Collin College master model
    if str(bid_id) == "17" or "collin" in combined:
        candidates = [
            "/app/static/proposals/COLLIN-COLLEGE-FRISCO-BID-MODEL.xlsx",
            os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE", "static", "proposals", "COLLIN-COLLEGE-FRISCO-BID-MODEL.xlsx"),
            os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-QUOTES", "BOSANNA-COLLIN-COLLEGE", "COLLIN-COLLEGE-FRISCO-BID-MODEL.xlsx")
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
    return None

def get_graph_token():
    if not CID or not SECRET or not TID:
        return None
    try:
        authority = f"https://login.microsoftonline.com/{TID}"
        app = msal.ConfidentialClientApplication(CID, authority=authority, client_credential=SECRET)
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        return result.get("access_token")
    except Exception as e:
        print(f"[GRAPH API] Token acquisition error: {e}", flush=True)
        return None

def create_graph_calendar_event(subject, start_iso=None, end_iso=None, body=""):
    """Creates a calendar event on hdominguez@hwbcleaning.com Outlook calendar."""
    token = get_graph_token()
    if not token:
        return False, "Failed to acquire Microsoft Graph token"

    endpoint = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/events"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    if not start_iso:
        tomorrow = datetime.now() + timedelta(days=1)
        start_iso = tomorrow.strftime("%Y-%m-%dT09:00:00")
        end_iso = tomorrow.strftime("%Y-%m-%dT10:00:00")
    elif not end_iso:
        end_iso = start_iso

    event_payload = {
        "subject": subject,
        "body": {
            "contentType": "HTML",
            "content": f"<p>{body}</p><br><p><em>Scheduled via SigmaFidelity™ Telegram Voice Directive.</em></p>"
        },
        "start": {
            "dateTime": start_iso,
            "timeZone": "Central Standard Time"
        },
        "end": {
            "dateTime": end_iso,
            "timeZone": "Central Standard Time"
        }
    }

    try:
        res = session.post(endpoint, headers=headers, json=event_payload, timeout=20)
        if res.status_code in [200, 201]:
            return True, "Event scheduled successfully on Outlook calendar."
        return False, f"Graph HTTP {res.status_code}: {res.text[:150]}"
    except Exception as e:
        return False, str(e)

def dispatch_graph_email(record_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, recipient, subject, body FROM \"PendingOutbox\" WHERE id = %s;", (record_id,))
            item = cur.fetchone()

        if not item:
            return False, "Record not found"

        token = get_graph_token()
        if not token:
            return False, "Failed to acquire Microsoft Graph token"

        recipient_addr = item["recipient"].strip()
        if "@" not in recipient_addr:
            # Auto-resolve employee name from Users table
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT email, full_name FROM "Users"
                    WHERE LOWER(full_name) = LOWER(%s)
                       OR LOWER(username) = LOWER(%s)
                       OR LOWER(full_name) ILIKE %s
                    LIMIT 1;
                """, (recipient_addr, recipient_addr, f"%{recipient_addr}%"))
                resolved_user = cur.fetchone()
                if resolved_user and resolved_user.get("email"):
                    recipient_addr = resolved_user["email"]
                    print(f"[DISPATCH RESOLVER] Auto-resolved '{item['recipient']}' to '{recipient_addr}'", flush=True)
                else:
                    return False, f"Invalid recipient: '{item['recipient']}' is not a valid email address and could not be resolved to a registered user."

        endpoint = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/sendMail"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Check for brand asset / logo attachments
        attachments = []
        if any(w in item["subject"].lower() or w in item["body"].lower() for w in ["logo", "brand asset", "branding"]):
            logo_candidates = [
                "/app/static/1-hwb-cleaning-services-llc-logo-plano-tx.png",
                os.path.join(BASE_DIR, "static", "1-hwb-cleaning-services-llc-logo-plano-tx.png")
            ]
            for lpath in logo_candidates:
                if os.path.exists(lpath):
                    with open(lpath, "rb") as lf:
                        attachments.append({
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": "1-hwb-cleaning-services-llc-logo-plano-tx.png",
                            "contentType": "image/png",
                            "contentBytes": base64.b64encode(lf.read()).decode("utf-8")
                        })
                    break

        email_payload = {
            "message": {
                "subject": item["subject"],
                "body": {
                    "contentType": "HTML" if ("<" in item["body"] and ">" in item["body"]) else "Text",
                    "content": item["body"]
                },
                "toRecipients": [{"emailAddress": {"address": recipient_addr}}]
            },
            "saveToSentItems": True
        }

        if attachments:
            email_payload["message"]["attachments"] = attachments

        res = session.post(endpoint, headers=headers, json=email_payload, timeout=25)
        if res.status_code in [200, 202]:
            with conn.cursor() as cur:
                cur.execute("UPDATE \"PendingOutbox\" SET status = 'SENT', recipient = %s WHERE id = %s;", (recipient_addr, record_id))
            conn.commit()
            return True, f"Dispatched to {recipient_addr}"
        return False, f"Graph HTTP {res.status_code}: {res.text[:200]}"
    except Exception as e:
        return False, str(e)
    finally:
        if conn:
            conn.close()


# --- MICROSOFT GRAPH MESSAGE SEARCH, BID PARSING & INGESTION ---

def parse_email_bid_details(subject, text, sender_name="", sender_email="", recv_dt=None):
    """
    Extracts project name, location, bid dates, and contacts from solicitation email content.
    Prevents generic email subjects like 'COMPETITIVE SEALED PROPOSAL' from masking the real project name.
    """
    # 1. Project Name
    project_name = ""
    m = re.search(r"(?:Project Name|Project):\s*(.*?)(?=\s*(?:Description|Location|Contact|Prebid|Bid Date|$))", text, re.IGNORECASE)
    if m and len(m.group(1).strip()) > 3:
        project_name = m.group(1).strip()
    if not project_name:
        generic_subjects = ["COMPETITIVE SEALED PROPOSAL", "INVITATION TO BID", "BID INVITE", "CURRENTLY BIDDING", "NEW BID OPPORTUNITY"]
        if not any(g in subject.upper() for g in generic_subjects):
            project_name = subject.strip()
        else:
            code_match = re.search(r"((?:FWISD|TEA|RFP|CSP|ISD)\s*[0-9A-Z\s-]+)", text)
            if code_match and len(code_match.group(1).strip()) > 5:
                project_name = code_match.group(1).strip()
            else:
                project_name = subject.strip()

    # 2. Location
    address = ""
    city = "Fort Worth" if "FORT WORTH" in text.upper() else "Texas"
    state = "TX"
    zipcode = ""
    loc_match = re.search(r"(?:Location|Address):\s*(.*?)(?=\s*(?:Contact|Prebid|Bid Date|Description|$))", text, re.IGNORECASE)
    if loc_match:
        loc_str = loc_match.group(1).strip()
        address = loc_str
        parts = [p.strip() for p in loc_str.split(",")]
        if len(parts) >= 2:
            address = parts[0]
            city = parts[1]
        if len(parts) >= 3:
            st_zip = parts[2].split()
            if len(st_zip) >= 1:
                state = st_zip[0]
            if len(st_zip) >= 2:
                zipcode = st_zip[1]

    # 3. Dates
    bid_date = None
    bid_match = re.search(r"(?<!pre)(?<!sub)bid date:\s*([0-9\/\-:\sapmAPM]+)", text, re.IGNORECASE)
    if bid_match:
        try:
            bid_date = dt_parser.parse(bid_match.group(1).strip())
        except Exception:
            pass

    prebid_date_str = ""
    prebid_match = re.search(r"prebid date:\s*([0-9\/\-:\sapmAPM]+)", text, re.IGNORECASE)
    if prebid_match:
        prebid_date_str = prebid_match.group(1).strip()

    # 4. Description
    desc_str = ""
    desc_match = re.search(r"description:\s*(.*?)(?=\s*(?:Location|Contact|Prebid|Bid Date|$))", text, re.IGNORECASE)
    if desc_match:
        desc_str = desc_match.group(1).strip()

    # 5. Contact
    estimator_name = sender_name
    estimator_email = sender_email
    estimator_phone = ""
    contact_match = re.search(r"contact:\s*(.*?)(?=\s*(?:Prebid|Bid Date|Location|Description|$))", text, re.IGNORECASE)
    if contact_match:
        c_str = contact_match.group(1).strip()
        estimator_name = c_str
        phone_match = re.search(r"(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4})", c_str)
        if phone_match:
            estimator_phone = phone_match.group(1)
        email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", c_str)
        if email_match:
            estimator_email = email_match.group(1)

    # 6. Planroom / RFP URL
    plan_url = None
    url_matches = re.findall(r"https?://[^\s\"'<>]+", text)
    for u in url_matches:
        if any(dom in u.lower() for dom in ["fwisdplanroom.com", "reproconnect.com", "buildingconnected.com", "planhub.com", "isqft.com"]):
            if "unsubscribe" not in u.lower():
                plan_url = u
                break

    return {
        "project_name": project_name,
        "address": address,
        "city": city,
        "state": state,
        "zipcode": zipcode,
        "bid_due_date": bid_date,
        "prebid_date_str": prebid_date_str,
        "description": desc_str,
        "estimator_name": estimator_name,
        "estimator_email": estimator_email,
        "estimator_phone": estimator_phone,
        "plan_url": plan_url
    }

def search_graph_messages(query, top=5):
    """Searches Microsoft Graph API messages in hdominguez@hwbcleaning.com mailbox."""
    token = get_graph_token()
    if not token:
        return []
    try:
        clean_q = re.sub(r'["\']', '', query).strip()
        if not clean_q:
            return []
        url = f'https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/messages?$search="{clean_q}"&$top={top}&$select=id,subject,from,receivedDateTime,bodyPreview,body'
        headers = {'Authorization': f'Bearer {token}'}
        res = session.get(url, headers=headers, timeout=20)
        if res.status_code != 200:
            print(f"[GRAPH SEARCH] HTTP {res.status_code}: {res.text[:200]}", flush=True)
            return []
        data = res.json().get('value', [])
        results = []
        for m in data:
            sender_obj = m.get('from', {}).get('emailAddress', {})
            raw_body = m.get('body', {}).get('content', '')
            clean_body = re.sub(r'<[^>]+>', ' ', raw_body)
            clean_body = re.sub(r'\s+', ' ', clean_body).strip()
            
            details = parse_email_bid_details(m.get('subject', ''), clean_body, sender_obj.get('name', ''), sender_obj.get('address', ''))
            
            results.append({
                "id": m.get('id'),
                "subject": m.get('subject', 'No Subject'),
                "sender_name": sender_obj.get('name', ''),
                "sender_email": sender_obj.get('address', ''),
                "received_date": (m.get('receivedDateTime') or '')[:10],
                "preview": m.get('bodyPreview', ''),
                "body_text": clean_body,
                "parsed_details": details
            })
        return results
    except Exception as e:
        print(f"[GRAPH SEARCH ERROR] {e}", flush=True)
        return []

def ingest_bid_from_email_id(message_id):
    """Ingests or updates a ConstructionBid directly from an Outlook message ID."""
    token = get_graph_token()
    if not token:
        return False, "Failed to acquire Microsoft Graph token", None

    try:
        url = f'https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/messages/{message_id}'
        headers = {'Authorization': f'Bearer {token}'}
        res = session.get(url, headers=headers, timeout=20)
        if res.status_code != 200:
            return False, f"Failed to retrieve email: HTTP {res.status_code}", None

        msg = res.json()
        subject = msg.get('subject', 'Inbound Solicitation')
        sender_obj = msg.get('from', {}).get('emailAddress', {})
        sender_name = sender_obj.get('name', '')
        sender_email = sender_obj.get('address', '')
        raw_body = msg.get('body', {}).get('content', '')
        clean_body = re.sub(r'<[^>]+>', ' ', raw_body)
        clean_body = re.sub(r'\s+', ' ', clean_body).strip()

        details = parse_email_bid_details(subject, clean_body, sender_name, sender_email)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM "ConstructionBids" WHERE email_id = %s;', (message_id,))
            existing = cur.fetchone()
            if existing:
                bid_id = existing[0]
                cur.execute('''
                    UPDATE "ConstructionBids"
                    SET project_name = %s,
                        project_address = COALESCE(%s, project_address),
                        city = COALESCE(%s, city),
                        state = COALESCE(%s, state),
                        zipcode = COALESCE(%s, zipcode),
                        bid_due_date = COALESCE(%s, bid_due_date),
                        plan_url = COALESCE(%s, plan_url),
                        rfp_url = COALESCE(%s, rfp_url),
                        estimator_name = COALESCE(%s, estimator_name),
                        estimator_email = COALESCE(%s, estimator_email),
                        estimator_phone = COALESCE(%s, estimator_phone),
                        special_requirements = COALESCE(%s, special_requirements),
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id;
                ''', (
                    details["project_name"],
                    details["address"] or None,
                    details["city"] or None,
                    details["state"] or None,
                    details["zipcode"] or None,
                    details["bid_due_date"],
                    details["plan_url"],
                    details["plan_url"],
                    details["estimator_name"] or None,
                    details["estimator_email"] or None,
                    details["estimator_phone"] or None,
                    f"Prebid: {details['prebid_date_str']}. {details['description']}",
                    bid_id
                ))
            else:
                cur.execute('''
                    INSERT INTO "ConstructionBids" (
                        gc_name, project_name, project_address, city, state, zipcode,
                        bid_due_date, plan_url, rfp_url, estimator_name, estimator_email, estimator_phone,
                        platform, status, email_id, special_requirements, notes, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        'Planroom', 'Invited', %s, %s, %s, NOW(), NOW()
                    ) RETURNING id;
                ''', (
                    sender_name or "General Contractor",
                    details["project_name"],
                    details["address"] or None,
                    details["city"] or None,
                    details["state"] or None,
                    details["zipcode"] or None,
                    details["bid_due_date"],
                    details["plan_url"],
                    details["plan_url"],
                    details["estimator_name"] or None,
                    details["estimator_email"] or None,
                    details["estimator_phone"] or None,
                    message_id,
                    f"Prebid: {details['prebid_date_str']}. {details['description']}",
                    f"Inbound solicitation email: {subject}. {clean_body[:300]}"
                ))
                bid_id = cur.fetchone()[0]

            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, 'ConstructionBid', 'Email Ingested via Telegram', %s);
            ''', (bid_id, f"Solicitation ingested from email: {details['project_name']}"))
            conn.commit()
        conn.close()
        return True, f"Bid #{bid_id} ({details['project_name']}) registered in Commercial GC Pipeline.", bid_id
    except Exception as e:
        return False, f"Ingestion error: {e}", None

def get_recent_conversation_history(chat_id, limit=6):
    """Retrieves the last N conversation turns from sigma_kb to preserve multi-turn context."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT content, metadata
                FROM sigma_kb
                WHERE doc_id LIKE %s
                  AND (metadata->>'chat_id' = %s OR metadata->>'chat_id' IS NULL)
                ORDER BY doc_id DESC
                LIMIT %s;
            """, ("telegram-convo%", str(chat_id), limit))
            rows = cur.fetchall()
        if not rows:
            return "No previous conversation turns recorded."
        turns = []
        for content, meta in reversed(rows):
            clean_content = content.strip()
            if len(clean_content) > 500:
                clean_content = clean_content[:500] + "... [truncated]"
            turns.append(clean_content)
        return "\n---\n".join(turns)
    except Exception as e:
        print(f"[CONVERSATION MEMORY ERROR] {e}", flush=True)
        return "Conversation history unavailable."
    finally:
        if conn:
            conn.close()


# --- MASTER SPECIFICATIONS & DYNAMIC RESOLVER CAPSULES ---
COLLIN_COLLEGE_CONTEXT = """
ACTIVE PROJECT: COLLIN COLLEGE FRISCO CAMPUS OPERATIONAL & PRICING SPECIFICATIONS:
- Project: Collin College Frisco Campus Custodial Replacement (RFP # FY2024-RFP-005 Replacement).
- Prime Partner: Bosanna LLC (Attn: Angelica Hudgins). TIPS Contracts: #260103 / #260102.
- Total Footprint: 478,418 Cleanable SF across 10 Campus Buildings.
- Cleaning Standard: APPA Level 2 ("Ordinary Tidiness" guaranteed).
- Total Staffing: 904.0 Hours/Week (22.6 FTEs; 23-25 Badged Personnel).
  * Day Porters (M-F 8:00 AM - 4:30 PM): 4 Dedicated Porters.
    - Sector Alpha (Spine): 2 Porters covering Founders Hall (92,105 SF) & University Hall (84,320 SF).
    - Sector Bravo (Hub): 1 Porter covering Heritage Hall (78,450 SF), Student Center (32,150 SF), IT (18,420 SF).
    - Sector Charlie (Specialty): 1 Porter covering Library LRC (62,180 SF), Lawler Hall (48,260 SF), Alumni Hall (38,940 SF), Safety (9,393 SF).
  * Saturday Day Porters: 2 Porters Saturday (8:00 AM - 4:30 PM) campus-wide.
  * Night Custodians (7 Nights/Week 10:00 PM - 6:30 AM): 12 Full-Time Cleaners.
  * Night Supervisor (7 Nights/Week 10:00 PM - 6:30 AM): 1 Non-Cleaning Shift Supervisor.
- Timekeeping & Security Audit Mandate:
  * Dual biometric cellular fingerprint time-clock at Central Staging.
  * Mandatory physical sign-in & sign-out at Collin College Police desk in Building S.
  * Digital punch printout attached to monthly billing.
- Subcontract Financial Architecture (Scenario A - Recommended):
  * Line 41 (Scheduled Labor - 904 hrs/wk): $96,943.00/mo wholesale ($1,163,316.00/yr). District: $115,405.69/mo ($1,384,868.28/yr).
  * Line 42 (Consumable Supplies Passthrough): $7,575.00/mo wholesale ($90,900.00/yr). District: $9,020.50/mo ($108,246.00/yr).
  * Total HWB Wholesale Subcontract: $104,518.00/month ($1,254,216.00/year).
  * TIPS Co-op Fee 1.0%: $1,244.26/mo ($14,931.14/yr).
  * Bosanna Prime Fee 15.0%: $18,663.93/mo ($223,967.14/year profit to Bosanna with 0 field labor).
  * Total Proposal Submittal to Collin College: $124,426.19/month ($1,493,114.28/year = $3.12/SF).
  * Direct Monthly COGS: $85,626.42 ($63,284.52 base wages + $12,656.90 20% burden + $6,675 supplies + $900 chemicals + $1,400 equipment amortization + $710 badging/fingerprints).
  * HWB Gross Profit: $18,891.58/month ($226,693.91/year = 18.07% Gross Margin).
  * HWB Net Operating Profit (EBITDA): $14,291.58/month ($171,498.91/year = 13.67% Net Margin).
- Unscheduled Rates:
  * Line 43 (M-F Unscheduled): $28.50/hr wholesale ($33.94 submittal).
  * Line 44 (Saturday Unscheduled): $32.00/hr wholesale ($38.10 submittal).
  * Line 45 (Sunday/Holidays): $38.00/hr wholesale ($45.24 submittal).
  * Line 46 (Tile Strip & Wax): $0.25/SF wholesale ($0.298/SF submittal).
  * Line 47 (Carpet Extraction): $0.28/SF wholesale ($0.333/SF submittal).
  * Line 48 (Add/Deduct Rate): $2.62/SF/yr wholesale ($3.120/SF/yr submittal).
- 10 Campus Buildings & Assigned Equipment:
  1. Founders Hall (F): 92,105 SF (32 class, 45 off, 8 rest / 36 fix). Equip: 28" Riding Auto-Scrubber + 2000 RPM Burnisher in F-102.
  2. University Hall (U): 84,320 SF (28 class, 50 off, 7 rest / 32 fix). Equip: 20" Walk-Behind Scrubber + 175 RPM Machine.
  3. Heritage Hall (H): 78,450 SF (24 class, 40 off, 6 rest / 28 fix). Equip: 28" Riding Scrubber + 2000 RPM Burnisher.
  4. Library LRC (L): 62,180 SF (8 class, 25 off, 4 rest / 18 fix, 85% carpet). Equip: Commercial Extractor + HEPA Backpack Vacs in L-114.
  5. Lawler Hall (J): 48,260 SF (20 class, 18 off, 4 rest / 18 fix). Equip: 20" Walk-Behind Scrubber + Burnisher.
  6. Alumni Hall & PE (A): 38,940 SF (4 class, 12 off, 4 rest / 24 fix, 16 showers, 180 lockers). Equip: Kaivac Touchless Unit + Wet-Vac.
  7. Student Center (C): 32,150 SF (6 class, 15 off, 4 rest / 16 fix). Equip: 20" Walk-Behind Scrubber + Degreaser pads.
  8. IT Infrastructure (IT): 18,420 SF (6 class, 10 off, 2 rest / 8 fix). Equip: Anti-Static HEPA Canister + Microfiber.
  9. Facilities Operations (M): 14,200 SF (4 shops, 8 off, 1 rest / 4 fix). Equip: 20" Scrubber + Stripping brush; Central compactor.
  10. Campus Safety (S): 9,393 SF (4 off, 1 rest / 4 fix). 24/7 Police desk logbook & staging.
- Incumbent Intelligence:
  * Pritchard Industries Southwest defaulted under RFP # FY2024-RFP-005 ($14.5M 3-yr / $4.95M annual district-wide contract) due to chronic staffing shortages and supervisory failure. Collin College T&C § 41 allows District to backcharge replacement costs.
"""

HORIZON_PREMIER_CONTEXT = """
ACTIVE PROJECT: HORIZON AT PREMIER (PLANO, TX)
- Facility: Horizon at Premier (Multi-Family Townhome Community).
- Address: 3409 Premier Dr, Plano, TX 75023.
- Community Size: 122 Homes / Multi-Family Townhome Doors.
- Primary Scope: Doorstep Valet Trash & Recycling Removal.
- Schedule / Frequency: 7 Nights a Week (Daily evening collection between 7:00 PM - 9:00 PM).
- Collection Workflow: Nightly collection from resident doorstep receptacles directly to community dumpsters/compactors.
- Benchmarks & Financial Formulas:
  * Benchmark Door Rate: $20.00 - $25.00 / door / month.
  * Recommended Base Submittal: $22.50 / door / month ($2,745.00/mo | $32,940.00/yr).
  * Conservative Tier: $18.00 / door / month ($2,196.00/mo | $26,352.00/yr).
  * Premium 7-Night Tier: $25.00 / door / month ($3,050.00/mo | $36,600.00/yr).
  * Direct Labor Requirement: 1 Porter, 1.5 - 2.0 hrs/night @ $20.00/hr = ~$900 - $1,200/mo labor COGS.
  * Gross Margin: ~55% - 65% for valet waste management.
- Database Record: Lead #82474 (Status: Walkthrough Completed by Mirna Rondinella).
- Operational Directives:
  * Validate compactor access, gate remotes, and collection protocol.
  * Confirm that CEO Humberto Dominguez holds approval authority for the final client proposal.
"""

def get_dynamic_session_context(chat_id, incoming_text="", caption=""):
    """
    Dynamic Project & Problem Resolver:
    1. Identifies topic pivots from message content or user directives.
    2. Updates and retrieves session context in UserBehavioralProfiles per user.
    3. Dynamically queries PostgreSQL for live Commercial GC Bids, Institutional Bids, or Leads.
    4. Seamlessly adapts system prompts without rigid hardcoded lockouts.
    5. Falls back to Microsoft Graph API email search if the project was received via inbound email.
    """
    combined_query = f"{incoming_text} {caption}".lower()

    new_context = None
    if any(k in combined_query for k in ["horizon", "premier", "3409 premier", "valet trash", "trash pickup", "waste management", "122 home", "122 unit"]):
        new_context = "HORIZON_PREMIER"
    elif any(k in combined_query for k in ["collin college", "frisco campus", "rfp-005", "pritchard", "heritage hall", "founders hall"]):
        new_context = "COLLIN_COLLEGE"
    elif any(k in combined_query for k in ["stop", "reset", "clear project", "different project", "new project"]) and not any(k in combined_query for k in ["horizon", "collin"]):
        new_context = "GENERAL"

    active_context = None
    extra_db_context = ""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if new_context:
                cur.execute("""
                    UPDATE "UserBehavioralProfiles"
                    SET active_project_context = %s
                    WHERE chat_id = %s;
                """, (new_context, chat_id))
                conn.commit()
                active_context = new_context
            else:
                cur.execute("""
                    SELECT active_project_context FROM "UserBehavioralProfiles"
                    WHERE chat_id = %s;
                """, (chat_id,))
                row = cur.fetchone()
                active_context = row[0] if row and row[0] else None

            # Dynamic database lookup across Bids and Leads
            ignore_words = {"project", "clean", "about", "there", "their", "please", "george", "hello", "trash", "pickup", "frisco", "plano", "college", "horizon", "what", "have", "check", "email", "emails", "domain", "from", "with", "that", "this", "some"}
            words = [w for w in re.findall(r'[A-Za-z0-9]{4,}', combined_query) if w not in ignore_words]
            
            matched = False
            for w in words[:3]:
                search_term = f"%{w}%"
                
                # 1. Search Commercial GC Bids (ConstructionBids)
                try:
                    cur.execute("""
                        SELECT id, gc_name, project_name, project_address, city, state, zipcode,
                               estimated_value, cleanable_sqft, bid_due_date, special_requirements, notes,
                               rfp_url, plan_url, estimator_name, estimator_email, status,
                               word_similarity(%s, project_name) as sim
                        FROM "ConstructionBids"
                        WHERE project_name ILIKE %s
                           OR notes ILIKE %s
                           OR word_similarity(%s, project_name) > 0.3
                        ORDER BY sim DESC NULLS LAST
                        LIMIT 1;
                    """, (w, search_term, search_term, w))
                    bid_match = cur.fetchone()
                    if bid_match:
                        b_id, b_gc, b_proj, b_addr, b_city, b_st, b_zip, b_val, b_sqft, b_due, b_spec, b_notes, b_rfp, b_plan, b_est_name, b_est_email, b_stat, _ = bid_match
                        due_str = b_due.strftime("%m/%d/%Y at %I:%M %p") if b_due else "Pending"
                        val_str = f"${float(b_val):,.2f}" if b_val else "$0.00"
                        sqft_str = f"{int(b_sqft):,} SF" if b_sqft else "Pending"
                        extra_db_context += (
                            f"\n\nDATABASE MATCH FOUND (Commercial GC Bid #{b_id}):\n"
                            f"- Project: {b_proj}\n"
                            f"- General Contractor / Client: {b_gc}\n"
                            f"- Location: {b_addr or ''}, {b_city or ''}, {b_st or ''} {b_zip or ''}\n"
                            f"- Bid Due Date: {due_str}\n"
                            f"- Cleanable Footprint / Estimated Value: {sqft_str} | {val_str}\n"
                            f"- Scope / Special Requirements: {b_spec or b_notes or 'Standard CSI Division 01 Clean'}\n"
                            f"- Estimator / Contact: {b_est_name or 'N/A'} ({b_est_email or 'N/A'})\n"
                            f"- Planroom Access / URL: {b_plan or b_rfp or 'Pending'}\n"
                            f"- Pipeline Status: {b_stat}\n"
                        )
                        matched = True
                        break
                except Exception:
                    pass

                # 2. Search Institutional Bids
                if not matched:
                    try:
                        cur.execute("""
                            SELECT id, agency_name, title, solicitation_number, hwb_bid_total, cleanable_sqft, bid_due_date, status
                            FROM "InstitutionalBids"
                            WHERE agency_name ILIKE %s OR title ILIKE %s OR solicitation_number ILIKE %s
                            LIMIT 1;
                        """, (search_term, search_term, search_term))
                        ib_match = cur.fetchone()
                        if ib_match:
                            ib_due_str = ib_match[6].strftime("%m/%d/%Y at %I:%M %p") if ib_match[6] else "Pending"
                            extra_db_context += (
                                f"\n\nDATABASE MATCH FOUND (Institutional Bid #{ib_match[0]}):\n"
                                f"- Agency: {ib_match[1]} | Title: {ib_match[2]} (Solicitation: {ib_match[3]})\n"
                                f"- Footprint: {ib_match[5] or 'N/A'} SF | Value: ${ib_match[4] or 0:,.2f}\n"
                                f"- Deadline: {ib_due_str} | Status: {ib_match[7]}\n"
                            )
                            matched = True
                            break
                    except Exception:
                        pass

                # 3. Search CRM Leads
                if not matched:
                    cur.execute("""
                        SELECT id, center_name, address, city, notes, estimated_annual_value
                        FROM "Leads"
                        WHERE center_name ILIKE %s OR address ILIKE %s
                        ORDER BY id DESC LIMIT 1;
                    """, (search_term, search_term))
                    lead_match = cur.fetchone()
                    if lead_match:
                        extra_db_context += (
                            f"\n\nDATABASE MATCH FOUND (Lead #{lead_match[0]}):\n"
                            f"- Facility: {lead_match[1]}\n"
                            f"- Address: {lead_match[2]}, {lead_match[3]}\n"
                            f"- Estimated Value: ${lead_match[5] or 0:,.2f}\n"
                            f"- Recorded Notes: {lead_match[4] or 'None'}\n"
                        )
                        matched = True
                        break
        conn.close()

        # 4. Fallback search via Microsoft Graph API if no DB match or user explicitly inquiries about email/domain
        if not matched and (any(k in combined_query for k in ["email", "domain", "reproconnect", "inbox", "sent", "solicitation"]) or words):
            lookup_kw = "reproconnect" if "reproconnect" in combined_query else (words[0] if words else "")
            if lookup_kw:
                found_emails = search_graph_messages(lookup_kw, top=2)
                if found_emails:
                    extra_db_context += "\n\nOUTLOOK INBOX MATCHES FOUND (Incoming Email Solicitations):\n"
                    for fe in found_emails:
                        pd = fe["parsed_details"]
                        due_fmt = pd['bid_due_date'].strftime('%m/%d/%Y %I:%M %p') if pd['bid_due_date'] else 'Pending'
                        extra_db_context += (
                            f"- Project: {pd['project_name']}\n"
                            f"  * From: {fe['sender_name']} <{fe['sender_email']}> | Date: {fe['received_date']}\n"
                            f"  * Location: {pd['address']}, {pd['city']} {pd['state']}\n"
                            f"  * Bid Due: {due_fmt} | Prebid: {pd['prebid_date_str'] or 'None'}\n"
                            f"  * Scope: {pd['description'][:200]}\n"
                            f"  * Planroom Link: {pd['plan_url'] or 'N/A'}\n"
                        )

    except Exception as e:
        print(f"[DYNAMIC RESOLVER ERROR] {e}", flush=True)
        active_context = new_context or "GENERAL"
        extra_db_context = ""

    if active_context == "HORIZON_PREMIER":
        return HORIZON_PREMIER_CONTEXT + extra_db_context
    elif active_context == "COLLIN_COLLEGE":
        return COLLIN_COLLEGE_CONTEXT + extra_db_context
    else:
        return """
ACTIVE OPERATIONAL CONTEXT (GENERAL PIPELINE):
- You have unrestricted access to all active operations, leads, and bids for HWB Cleaning Services LLC.
- Active Focus Areas:
  * FWISD TEA 048 - Polytech Pyramid Middle School Consolidation (1101 Nashville Ave, Fort Worth - Bid #42)
  * FWISD TEA 044 - Northside Pyramid Middle School (709 NW 21st St, Fort Worth - Bid #43)
  * Horizon at Premier (3409 Premier Dr, Plano - 122 units, 7 days/wk valet waste removal - Lead #82474)
  * Collin College Frisco Campus Custodial Replacement (478,418 SF, 10 buildings, RFP # FY2024-RFP-005 Replacement - Bid #17)
  * North Texas Daycare & Commercial Pipeline (10,000+ facilities in DFW)
- OPERATIONAL DIRECTIVE: Listen carefully to the user's project, location, or walk-through observations. Do not force them into an unrelated project. Acknowledge their exact numbers (units, square footage, frequencies, addresses), record their findings, and assist with immediate estimation and operational execution.
""" + extra_db_context


# --- GEMINI MULTIMODAL REASONING (VOICE & VISION) ---

def analyze_voice_with_gemini(audio_bytes, chat_id=None):
    """Uses Gemini 2.5 Flash to transcribe and parse executive intent from voice notes."""
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY not configured."
    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    actor_user = get_user_for_chat(chat_id) if chat_id else None
    actor_name = actor_user.get("name", "CEO Humberto Dominguez") if actor_user else "Team Member"
    dynamic_context = get_dynamic_session_context(chat_id) if chat_id else COLLIN_COLLEGE_CONTEXT

    prompt = (
        "You are George, Lead Systems Architect and Senior Estimator for HWB Cleaning Services LLC.\n"
        f"Listen to this field voice memo from {actor_name}.\n\n"
        f"{dynamic_context}\n\n"
        "1. Transcribe the exact words spoken.\n"
        "2. Identify the operational intent:\n"
        "   - 'create_calendar_event': Wants a meeting, site walkthrough, or appointment scheduled.\n"
        "   - 'draft_email': Wants an email, quote, or proposal prepared.\n"
        "   - 'send_proposal': Wants a bid proposal or model transmitted.\n"
        "   - 'update_bid': Wants to modify a bid price, status, or scope.\n"
        "   - 'strategic_note': General directive, walkthrough observation, or operational command.\n"
        "3. Output MUST start with a JSON code block with fields:\n"
        "```json\n"
        "{\"intent\": \"create_calendar_event\"|\"draft_email\"|\"send_proposal\"|\"update_bid\"|\"strategic_note\", "
        "\"title\": \"...\", \"recipient\": \"...\", \"date_time\": \"...\", \"summary\": \"...\", \"bid_id\": 17}\n"
        "```\n"
        "Followed by a concise, authoritative field briefing with emojis and bold headers."
    )
    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "audio/ogg", "data": b64_audio}},
                {"text": prompt}
            ]
        }]
    }
    try:
        res = session.post(url, json=payload, timeout=35)
        if res.status_code == 200:
            candidates = res.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text_content = "\n\n".join(p.get("text", "") for p in parts if p.get("text")).strip()
                return text_content, None
            return None, "Empty candidates returned by Gemini Speech AI"
        return None, f"Gemini API Error: {res.status_code}"
    except Exception as e:
        return None, str(e)

def analyze_photo_with_gemini(image_bytes, caption="", chat_id=None):
    """Uses Gemini 2.5 Flash Vision to extract blueprints, finish schedules, and site conditions."""
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY not configured."
    b64_img = base64.b64encode(image_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    actor_user = get_user_for_chat(chat_id) if chat_id else None
    actor_name = actor_user.get("name", "CEO Humberto Dominguez") if actor_user else "Team Member"
    dynamic_context = get_dynamic_session_context(chat_id, caption=caption) if chat_id else COLLIN_COLLEGE_CONTEXT

    prompt = (
        "You are George, Lead Systems Architect and Senior Estimator for HWB Cleaning Services LLC.\n"
        f"Analyze this construction blueprint sheet, finish schedule, or jobsite photo taken by {actor_name}.\n\n"
        f"{dynamic_context}\n\n"
        f"Context/Caption provided: \"{caption or 'Facility Walkthrough'}\"\n\n"
        "Provide a surgically precise industrial analysis:\n"
        "1. 🏢 Building / Space & Substrate Identified (VCT, Terrazzo, Ceramic Tile, Carpet, Sealed Concrete, Waste Areas)\n"
        "2. 🔍 Condition & Wear Assessment (wax buildup, yellowing, grout discoloration, scratches, traffic lanes, trash accumulation)\n"
        "3. 🧹 Restorative Maintenance Scope Required (Tri-annual deep strip & 4-coat wax, Kaivac wash, hot-water extraction, waste staging)\n"
        "4. ⚠️ Forensic Discrepancies, Hidden Pitfalls, or Backcharge Risks\n\n"
        "Format cleanly with bold headers and emojis for mobile reading.\n"
        "Conclude with a JSON block:\n"
        "```json\n"
        "{\"project_name\": \"Site Walkthrough\", \"estimated_sqft\": 15000, \"primary_floor\": \"VCT/Terrazzo\", \"is_clinical\": false}\n"
        "```"
    )
    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}},
                {"text": prompt}
            ]
        }]
    }
    try:
        res = session.post(url, json=payload, timeout=40)
        if res.status_code == 200:
            candidates = res.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text_content = "\n\n".join(p.get("text", "") for p in parts if p.get("text")).strip()
                return text_content, None
            return None, "Empty candidates returned by Gemini Vision AI"
        return None, f"Gemini Vision Error: {res.status_code}"
    except Exception as e:
        return None, str(e)


def analyze_text_with_gemini(text, chat_id):
    """Conversational field intelligence for team members on Telegram with Dynamic Resolver & Episodic Memory."""
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY not configured.", None

    send_telegram_chat_action(chat_id, "typing")

    actor_user = get_user_for_chat(chat_id)
    actor_name = actor_user.get("name", "CEO Humberto Dominguez") if actor_user else "Team Member"
    actor_role = actor_user.get("role", "Executive") if actor_user else "Team Member"

    # Multi-turn episodic conversation memory (eliminates amnesia)
    recent_history = get_recent_conversation_history(chat_id, limit=6)

    # Dynamic Resolver Context Capsule
    dynamic_context = get_dynamic_session_context(chat_id, incoming_text=text)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    system_prompt = (
        "You are George, Lead Autonomous Systems Architect, Senior Estimator, Senior ISO 9001 Auditor, and Certified Lean Six Sigma Master Black Belt for HWB Cleaning Services LLC.\n"
        f"You are conversing directly in real-time with {actor_name} ({actor_role}) via Telegram during mobile operations and facility walkthroughs.\n\n"
        f"EPISODIC DIALOGUE MEMORY (Recent conversation turns with {actor_name}):\n"
        f"{recent_history}\n\n"
        f"{dynamic_context}\n\n"
        "OPERATIONAL RULES:\n"
        "1. Strictly maintain a professional, authoritative tone. Use everyday words, bold headers, bullet points, and emojis suitable for mobile reading.\n"
        f"2. Tailor your responses to {actor_name}'s role ({actor_role}). For executives, provide exact financial figures, margins, and operational approvals. For operators, provide clear workflows, candidate details, and task schedules.\n"
        "3. Never force the user back into an unrelated project if they state they are working on a different lead, location, or facility.\n"
        "4. CONTINUITY MANDATE: If the user refers to previous context (e.g. 'that domain', 'that project', 'I just gave it to you', 'check emails for it'), RESOLVE IT IMMEDIATELY using the EPISODIC DIALOGUE MEMORY above. Never ask the user to repeat what they previously stated.\n"
        "5. If the user gives an operational directive, asks about emails, or references a project, include a JSON block at the very start of your response:\n"
        "```json\n"
        "{\n"
        '  "intent": "search_emails" | "ingest_bid" | "create_calendar_event" | "draft_email" | "send_proposal" | "conversational",\n'
        '  "query": "search query or domain (e.g. reproconnect.com, polytech pyramid, etc.)",\n'
        '  "title": "...",\n'
        '  "recipient": "...",\n'
        '  "date_time": "...",\n'
        '  "summary": "...",\n'
        '  "bid_id": 42\n'
        "}\n"
        "```\n"
        f"6. MANDATORY COMPLETE BRIEFING: You MUST ALWAYS follow the JSON block with your full, thorough, detailed, high-impact operational response, strategic analysis, and executive reasoning to {actor_name}. NEVER output only a JSON block. Always provide your complete analytical findings."
    )

    payload = {
        "contents": [{
            "parts": [
                {"text": f"{system_prompt}\n\n{actor_name} ({actor_role}) says:\n\"{text}\""}
            ]
        }]
    }

    actor_perms = actor_user.get("telegram_perms", {}) if actor_user else {}
    if actor_perms.get("can_search_web", True):
        payload["tools"] = [{"google_search": {}}]

    try:
        res = session.post(url, json=payload, timeout=35)
        if res.status_code == 200:
            candidates = res.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                gemini_reply = "\n\n".join(p.get("text", "") for p in parts if p.get("text")).strip()
                return gemini_reply, None
            return "⚠️ Empty response generated by Gemini.", None
        return f"⚠️ Gemini API returned HTTP {res.status_code}", None
    except Exception as e:
        return f"⚠️ Error communicating with Gemini: {e}", None

def handle_text_conversation(text, chat_id):
    """Frontier 7: Two-Way Real-Time Conversational AI with George."""
    send_telegram_chat_action(chat_id, "typing")
    gemini_reply, err = analyze_text_with_gemini(text, chat_id)
    if err or not gemini_reply:
        send_telegram_message(chat_id, f"⚠️ Error: {err or 'Empty response'}")
        return

    # Parse JSON intent if present
    json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', gemini_reply)
    intent_data = {}
    clean_reply = gemini_reply
    if json_match:
        try:
            intent_data = json.loads(json_match.group(1))
            clean_reply = gemini_reply.replace(json_match.group(0), '').strip()
        except Exception:
            pass

    # Direct query: List last messages
    if any(k in text.lower() for k in ["last 5 message", "last messages", "recent message", "my message"]):
        conn = get_db_connection()
        history_lines = ["📜 *Recent Telegram Operational Interactions:*", "━━━━━━━━━━━━━━━━━━━━━"]
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id, event_type, payload_summary, created_at FROM "TelegramEventStream" WHERE chat_id = %s ORDER BY id DESC LIMIT 5;', (chat_id,))
                for row in cur.fetchall():
                    ev_time = row[3].strftime("%I:%M:%S %p CST") if row[3] else "Recent"
                    history_lines.append(f"• *#{row[0]}* ({ev_time})\n  `{row[1]}`: {row[2]}")
            conn.close()
            history_lines.append("━━━━━━━━━━━━━━━━━━━━━")
            full_msg = "\n".join(history_lines)
            send_telegram_message(chat_id, full_msg, reply_markup=get_main_menu_keyboard(chat_id))
            return
        except Exception as he:
            if conn:
                conn.close()

    # Guarantee clean_reply is never empty if Gemini only returned JSON
    if not clean_reply:
        summary_text = intent_data.get("summary") or intent_data.get("query")
        if summary_text:
            clean_reply = f"Acknowledged: **{summary_text}**.\n\nDirective registered in operational stream. Standing by for next command."
        else:
            clean_reply = "Directive registered in operational stream. Standing by for next command."

    intent = intent_data.get("intent", "conversational")
    action_note = ""

    # 1. Email Search Intent Execution (Pillar 2)
    is_email_query = (intent == "search_emails") or (
        ("email" in text.lower() or "inbox" in text.lower() or "domain" in text.lower() or "reproconnect" in text.lower()) and
        any(k in text.lower() for k in ["check", "find", "search", "what", "any", "look", "from", "for"])
    )
    if is_email_query:
        query_term = intent_data.get("query") or ""
        if not query_term or query_term.lower() in ["that domain", "the domain", "email", "emails"]:
            if "reproconnect" in text.lower() or "reproconnect" in clean_reply.lower():
                query_term = "reproconnect"
            else:
                m_dom = re.search(r'([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', gemini_reply + " " + text)
                query_term = m_dom.group(1) if m_dom else "reproconnect"

        send_telegram_chat_action(chat_id, "typing")
        results = search_graph_messages(query_term, top=3)
        if results:
            msg_lines = [
                f"📬 *Inbound Email Solicitations in Outlook:*",
                f"🔎 *Search Filter:* `{query_term}`",
                "━━━━━━━━━━━━━━━━━━━━━"
            ]
            action_buttons = []
            conn = get_db_connection()
            for idx, r in enumerate(results, 1):
                pd = r["parsed_details"]
                p_title = pd["project_name"] or r["subject"]
                msg_lines.append(f"*{idx}. {p_title}*")
                msg_lines.append(f"  • *Sender:* `{r['sender_email']}` | *Date:* {r['received_date']}")
                if pd["address"]:
                    msg_lines.append(f"  • *Location:* {pd['address']}, {pd['city']} {pd['state']}")
                if pd["bid_due_date"]:
                    msg_lines.append(f"  • *Bid Date:* {pd['bid_due_date'].strftime('%m/%d/%Y %I:%M %p')}")
                if pd["prebid_date_str"]:
                    msg_lines.append(f"  • *Prebid:* {pd['prebid_date_str']}")
                msg_lines.append("")

                with conn.cursor() as cur:
                    cur.execute('SELECT id FROM "ConstructionBids" WHERE email_id = %s OR project_name ILIKE %s LIMIT 1;', (r['id'], f"%{p_title[:25]}%"))
                    eb = cur.fetchone()
                if eb:
                    action_buttons.append([{"text": f"📐 Inspect Bid #{eb[0]} ({p_title[:20]}...)", "callback_data": f"takeoff_{eb[0]}"}])
                else:
                    action_buttons.append([{"text": f"📥 Ingest {p_title[:25]}...", "callback_data": f"ingest_msg_{r['id']}"}])
            conn.close()

            action_buttons.append([{"text": "📊 Active GC Bids", "callback_data": "cmd_bids"}, {"text": "📬 Outbox", "callback_data": "cmd_pending"}])
            full_msg = "\n".join(msg_lines)
            send_telegram_message(chat_id, full_msg, reply_markup={"inline_keyboard": action_buttons})
            return

    # 2. GC Ingestion Intent Execution
    if intent == "ingest_bid" and intent_data.get("query"):
        found = search_graph_messages(intent_data["query"], top=1)
        if found:
            ok, imsg, n_bid_id = ingest_bid_from_email_id(found[0]["id"])
            if ok and n_bid_id:
                action_note = f"\n\n📥 *GC Pipeline Ingestion:* Registered as Bid #{n_bid_id}."

    # 3. Calendar & Proposal Actions
    if intent == "create_calendar_event":
        subj = intent_data.get("title") or "Executive Appointment"
        dt = intent_data.get("date_time")
        body = intent_data.get("summary") or clean_reply
        ok, msg = create_graph_calendar_event(subj, start_iso=dt, body=body)
        action_note = f"\n\n📅 *Outlook Action:* {msg}"
    elif intent == "draft_email":
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO \"PendingOutbox\" (recipient, subject, body, status, created_at)
                VALUES (%s, %s, %s, 'PENDING', NOW()) RETURNING id;
            """, (intent_data.get("recipient", "partner@domain.com"), intent_data.get("title", "Commercial Communication"), intent_data.get("summary", clean_reply)))
            new_out_id = cur.fetchone()[0]
            conn.commit()
        conn.close()
        action_note = f"\n\n📬 *Staged in Outbox:* Proposal #{new_out_id} created for 1-tap dispatch."
    elif intent == "send_proposal" or ("send" in text.lower() and any(k in text.lower() for k in ["excel", "proposal", "quote", "model", "collin"])):
        bid_id = intent_data.get("bid_id", 17)
        handle_action_send_proposal(chat_id, bid_id)

    # Store interaction in sigma_kb
    timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
    doc_id = f"telegram-convo-{timestamp_str}"
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sigma_kb (doc_id, content, metadata)
                VALUES (%s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET content = EXCLUDED.content, metadata = EXCLUDED.metadata;
            """, (doc_id, f"USER: {text}\nGEORGE: {clean_reply}", Json({"source": "Telegram Field Conversation", "chat_id": chat_id, "timestamp": datetime.now().isoformat()})))
        conn.commit()
        conn.close()
    except Exception as db_e:
        print(f"[TELEGRAM] Warning logging to sigma_kb: {db_e}", flush=True)

    # Mirror George's reply to the CEO if talking to another team member
    ceo_chat_id = get_ceo_chat_id()
    if str(chat_id) != str(ceo_chat_id):
        actor_user = get_user_for_chat(chat_id)
        actor_name = actor_user.get("name", "Team Member") if actor_user else f"Contact {chat_id}"
        actor_role = actor_user.get("role", "Operations") if actor_user else "Unregistered"
        mirror_reply = (
            f"🤖 *[GEORGE REPLY MIRROR]*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Replying to:* {actor_name} ({actor_role})\n"
            f"💬 *Their Query:* \"{text}\"\n"
            f"🏛️ *George Response:*\n{clean_reply[:500]}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        try:
            send_telegram_message(ceo_chat_id, mirror_reply)
        except Exception:
            pass

    # Dynamic contextual buttons
    buttons = []
    target_bid_id = intent_data.get("bid_id")
    if not target_bid_id:
        m_bid = re.search(r'bid\s*#?(\d+)', clean_reply + " " + text, re.IGNORECASE)
        if m_bid:
            target_bid_id = int(m_bid.group(1))

    if target_bid_id:
        buttons.append([{"text": f"📐 Inspect Bid #{target_bid_id}", "callback_data": f"takeoff_{target_bid_id}"}])
    elif any(k in clean_reply.lower() for k in ["polytech", "politech"]):
        buttons.append([{"text": "📐 Inspect Polytech Bid #42", "callback_data": "takeoff_42"}])
    elif "northside" in clean_reply.lower():
        buttons.append([{"text": "📐 Inspect Northside Bid #43", "callback_data": "takeoff_43"}])
    elif "collin" in clean_reply.lower():
        buttons.append([{"text": "🏫 Collin Dashboard", "callback_data": "cmd_collin"}, {"text": "📑 Send Excel", "callback_data": "proposal_17"}])

    buttons.append([
        {"text": "📊 Active Bids", "callback_data": "cmd_bids"},
        {"text": "📬 Outbox", "callback_data": "cmd_pending"}
    ])

    full_msg = f"🏛️ *George (Systems Architect):*\n━━━━━━━━━━━━━━━━━━━━━\n{clean_reply}{action_note}"
    send_telegram_message(chat_id, full_msg, reply_markup={"inline_keyboard": buttons})

# --- FRONTIER COMMAND & INTERACTION HANDLERS ---


def handle_cmd_collin(chat_id):
    """Collin College Frisco Campus Walkthrough Command Hub."""
    msg = (
        "🏫 *Collin College Frisco Campus — Master Operations Hub*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🏢 *Footprint:* 10 Buildings | *478,418 Cleanable SF*\n"
        "🕒 *Staffing:* 904.0 hrs/week (22.6 FTEs: 4 Porters M-F, 2 Sat, 12 Night, 1 Sup)\n"
        "💼 *Subcontract Base:* *$104,518.00/mo* ($1,254,216.00/yr wholesale)\n"
        "🏛️ *District Proposal:* *$124,426.19/mo* ($1,493,114.28/yr = $3.12/SF)\n"
        "💰 *HWB Profit:* *$18,891.58/mo* Gross (18.1%) | *$14,291.58/mo* Net EBITDA\n"
        "🤝 *Prime Partner:* Bosanna LLC (15% Prime Fee = $223,967.14/yr profit)\n"
        "⏱️ *Audit:* Biometric Fingerprint Clock + Police Desk Sign-In Mandate\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Select a module below for instant field takeoff specs:"
    )
    buttons = [
        [{"text": "🏢 10 Building Takeoff", "callback_data": "collin_buildings"}, {"text": "🕒 Staffing & Shifts", "callback_data": "collin_staffing"}],
        [{"text": "🚜 Equipment Matrix", "callback_data": "collin_equipment"}, {"text": "💰 Pricing & Line Items", "callback_data": "collin_pricing"}],
        [{"text": "🗺️ Exterior Trash Map", "callback_data": "collin_trashmap"}, {"text": "📑 Download Excel Model", "callback_data": "proposal_17"}],
        [{"text": "📊 View All Bids", "callback_data": "cmd_bids"}]
    ]
    send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})

def handle_collin_trashmap(chat_id):
    """Sends the latest GPS-georeferenced trashcan plot map."""
    plot_path = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-QUOTES", "BOSANNA-COLLIN-COLLEGE", "frisco_campus_trashcan_plot.png")
    if not os.path.exists(plot_path):
        try:
            import subprocess
            subprocess.run(["python3", os.path.join(BASE_DIR, "scripts", "plot_walkthrough_gps.py")], check=True)
        except Exception as e:
            print(f"[TRASHMAP] Generator error: {e}", flush=True)

    caption = (
        "🗺️ *Collin College Frisco Campus — Exterior Trashcan Audit Map*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📍 All exterior bins georeferenced from walkthrough photo EXIF GPS.\n"
        "💡 *Field Tip:* Send photos as *Files/Documents* in Telegram to preserve full GPS metadata!"
    )
    buttons = [
        [{"text": "🏢 10 Building Takeoff", "callback_data": "collin_buildings"}, {"text": "💰 Pricing", "callback_data": "collin_pricing"}],
        [{"text": "⬅️ Back to Collin Hub", "callback_data": "cmd_collin"}]
    ]
    send_telegram_document(chat_id, plot_path, caption=caption, reply_markup={"inline_keyboard": buttons})

def handle_collin_buildings(chat_id):
    msg = (
        "🏢 *Collin College Frisco Campus — 10 Building Physical Takeoff*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "• *Founders Hall (F):* 92,105 SF | VCT/Terrazzo/Carpet | 32 Cls / 45 Off / 8 Rest (36 Fixt) | Porters 1 & 2\n"
        "• *University Hall (U):* 84,320 SF | VCT/Carpet/Ceramic | 28 Cls / 50 Off / 7 Rest (32 Fixt) | Porters 1 & 2\n"
        "• *Heritage Hall (H):* 78,450 SF | Terrazzo/VCT | 24 Cls / 40 Off / 6 Rest (28 Fixt) | Porter 3\n"
        "• *Library & LRC (L):* 62,180 SF | 85% Carpet/VCT | 8 Cls / 25 Off / 4 Rest (18 Fixt) | Porter 4\n"
        "• *Lawler Hall (J):* 48,260 SF | VCT/Carpet | 20 Cls / 18 Off / 4 Rest (18 Fixt) | Porter 4\n"
        "• *Alumni Hall & PE (A):* 38,940 SF | Ceramic/Concrete | 4 Cls / 12 Off / 4 Rest (24 Fixt, 16 Showers, 180 Lockers) | Porter 4\n"
        "• *Student Center (C):* 32,150 SF | Terrazzo/VCT | 6 Cls / 15 Off / 4 Rest (16 Fixt, Dining) | Porter 3\n"
        "• *IT Infrastructure (IT):* 18,420 SF | Raised Tile/Carpet | 6 Cls / 10 Off / 2 Rest (8 Fixt) | Porter 3\n"
        "• *Facilities Maint. (M):* 14,200 SF | Concrete | 4 Shops / 8 Off / 1 Rest (4 Fixt) | Rover\n"
        "• *Campus Safety (S):* 9,393 SF | VCT/Carpet | 4 Off / 1 Rest (4 Fixt) | Police Desk & Clock\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🏛️ *Total Campus Footprint:* *478,418 Cleanable SF* | 136 Cls | 219 Off | 41 Rest (180 Fixtures)"
    )
    buttons = [
        [{"text": "🕒 Staffing & Shifts", "callback_data": "collin_staffing"}, {"text": "🚜 Equipment", "callback_data": "collin_equipment"}],
        [{"text": "💰 Pricing & Rates", "callback_data": "collin_pricing"}, {"text": "📑 Send Excel", "callback_data": "proposal_17"}],
        [{"text": "⬅️ Back to Collin Hub", "callback_data": "cmd_collin"}]
    ]
    send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})

def handle_collin_staffing(chat_id):
    msg = (
        "🕒 *Collin College Frisco Campus — Staffing & Shift Logistics*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⏱️ *Mandated Staffing:* *904.0 Hours/Week* (22.6 FTEs | 23-25 Badged Personnel)\n\n"
        "☀️ *Day Porter Shifts (8:00 AM - 4:30 PM):*\n"
        "• *Mon - Fri (4 Dedicated Porters):*\n"
        "  - Porters 1 & 2: Founders + University (176k SF)\n"
        "  - Porter 3: Heritage + Student Center + IT (129k SF)\n"
        "  - Porter 4: Library + Lawler + Alumni Hall (173k SF)\n"
        "• *Saturday (2 Dedicated Porters):* Campus-wide dual patrol (8:00 AM - 4:30 PM)\n\n"
        "🌙 *Night Production Shift (10:00 PM - 6:30 AM, 7 Nights/Wk):*\n"
        "• *12 Dedicated Night Custodians:* Heavy production (136 classrooms/labs, 41 restroom banks deep sanitized, auto-scrubbers running).\n"
        "• *1 Non-Cleaning Shift Supervisor:* Full-time quality control, audit logs, and walkthrough sweeps.\n\n"
        "🔒 *Security & Punch Audit Protocol:*\n"
        "• Biometric cellular fingerprint time-clock at Central Staging.\n"
        "• Mandatory physical sign-in & sign-out at Collin College Police desk (Bldg S).\n"
        "• Digital punch printouts attached to every monthly invoice."
    )
    buttons = [
        [{"text": "🏢 10 Buildings", "callback_data": "collin_buildings"}, {"text": "🚜 Equipment", "callback_data": "collin_equipment"}],
        [{"text": "💰 Pricing & Rates", "callback_data": "collin_pricing"}, {"text": "📑 Send Excel", "callback_data": "proposal_17"}],
        [{"text": "⬅️ Back to Collin Hub", "callback_data": "cmd_collin"}]
    ]
    send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})

def handle_collin_equipment(chat_id):
    msg = (
        "🚜 *Collin College Frisco Campus — Dedicated Equipment Matrix*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "• *Founders Hall (F):* 28\" Riding Auto-Scrubber + 2000 RPM Burnisher (Stationed in F-102)\n"
        "• *Heritage Hall (H):* 28\" Riding Auto-Scrubber + 2000 RPM Burnisher (Covers Student Hub & Concourse)\n"
        "• *University Hall (U):* 20\" Walk-Behind Auto-Scrubber + 175 RPM Machine\n"
        "• *Library & LRC (L):* Commercial Hot-Water Carpet Extractor + Backpack HEPA Vacs (Stationed in L-114)\n"
        "• *Lawler Hall (J):* 20\" Walk-Behind Auto-Scrubber + Burnisher\n"
        "• *Alumni Hall & PE (A):* Kaivac Touchless Restroom Cleaning Unit + 175 RPM Scrub Machine & Wet-Vac\n"
        "• *Student Center (C):* 20\" Walk-Behind Scrubber + Heavy Degreasing Pads\n"
        "• *IT Building (IT):* Anti-Static Cleanroom HEPA Canister Vac + Microfiber System\n"
        "• *Facilities (M):* 20\" Walk-Behind Scrubber + Stripping Brushes; Central Compactor Station\n"
        "• *Campus Safety (S):* Upright HEPA Vacs + Spot Floor Burnisher"
    )
    buttons = [
        [{"text": "🏢 10 Buildings", "callback_data": "collin_buildings"}, {"text": "🕒 Staffing & Shifts", "callback_data": "collin_staffing"}],
        [{"text": "💰 Pricing & Rates", "callback_data": "collin_pricing"}, {"text": "📑 Send Excel", "callback_data": "proposal_17"}],
        [{"text": "⬅️ Back to Collin Hub", "callback_data": "cmd_collin"}]
    ]
    send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})

def handle_collin_pricing(chat_id):
    msg = (
        "💰 *Collin College Frisco Campus — Financial Underwriting & Rates*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 *Base Scheduled Contract (Scenario A):*\n"
        "• *Line 41 (Scheduled Labor - 904 hrs/wk):*\n"
        "  - HWB Wholesale: *$96,943.00/mo* ($1,163,316.00/yr)\n"
        "  - District Submittal: *$115,405.69/mo* ($1,384,868.28/yr)\n"
        "• *Line 42 (Consumable Supplies Passthrough):*\n"
        "  - HWB Wholesale: *$7,575.00/mo* ($90,900.00/yr)\n"
        "  - District Submittal: *$9,020.50/mo* ($108,246.00/yr)\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💼 *TOTAL HWB WHOLESALE:* *$104,518.00/mo* (*$1,254,216.00/yr*)\n"
        "🤝 *Bosanna Prime Margin (15%):* *$18,663.93/mo* (*$223,967.14/yr*)\n"
        "🏛️ *TOTAL DISTRICT PROPOSAL:* *$124,426.19/mo* (*$1,493,114.28/yr* = *$3.12/SF*)\n"
        "💵 *HWB Net EBITDA Profit:* *$14,291.58/mo* (*$171,498.91/yr* = 13.67%)\n\n"
        "⚡ *Unscheduled Hourly & Restorative Rates:*\n"
        "• Line 43 (M-F Unscheduled): *$28.50/hr* wholesale ($33.94 submittal)\n"
        "• Line 44 (Saturday Unscheduled): *$32.00/hr* wholesale ($38.10 submittal)\n"
        "• Line 45 (Sunday/Holidays): *$38.00/hr* wholesale ($45.24 submittal)\n"
        "• Line 46 (Tile Strip & Wax): *$0.25/SF* wholesale ($0.298/SF submittal)\n"
        "• Line 47 (Carpet Hot-Water Extract): *$0.28/SF* wholesale ($0.333/SF submittal)\n"
        "• Line 48 (Add/Deduct Rate): *$2.62/SF/yr* wholesale ($3.120/SF/yr submittal)"
    )
    buttons = [
        [{"text": "🏢 10 Buildings", "callback_data": "collin_buildings"}, {"text": "🕒 Staffing & Shifts", "callback_data": "collin_staffing"}],
        [{"text": "🚜 Equipment", "callback_data": "collin_equipment"}, {"text": "📑 Send Excel", "callback_data": "proposal_17"}],
        [{"text": "⬅️ Back to Collin Hub", "callback_data": "cmd_collin"}]
    ]
    send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})

# -----------------------------------------------------------------------------
# 4.6 FRISCO CAMPUS GEOFENCED WALKTHROUGH ENGINE (FRONTIER 7)
# -----------------------------------------------------------------------------
FRISCO_BUILDINGS_GEOFENCE = [
    {
        "code": "F",
        "name": "Founders Hall",
        "sector": "Sector Alpha (Spine)",
        "sqft": 92105,
        "lat": 33.1303571,
        "lon": -96.7929494,
        "stats": "32 Classrooms/Labs | 45 Offices | 8 Restrooms (36 Fixtures)",
        "flooring": "Terrazzo atriums, VCT in labs, carpet tile in offices",
        "questions": [
            "1. In science/chemistry labs, are lab benchtops cleaned by custodial or faculty only?",
            "2. What equipment has historically been used to wash the 3-story interior slope glass?",
            "3. Are the wall-mounted chemical proportioners in janitor closets college-owned?"
        ],
        "red_flags": [
            "⚠️ Check atrium slope glass height (ladder vs scissor lift access)",
            "⚠️ Verify eyewash stations and biohazard boundaries in labs",
            "⚠️ Inspect 1st-floor main restrooms for flush-valve leaks"
        ]
    },
    {
        "code": "U",
        "name": "University Hall",
        "sector": "Sector Alpha (Spine)",
        "sqft": 84320,
        "lat": 33.1303573,
        "lon": -96.7918300,
        "stats": "28 Classrooms/Lecture Halls | 50 Offices | 7 Restrooms (32 Fixtures)",
        "flooring": "Porcelain corridors, VCT classrooms, carpeted tiered auditoriums",
        "questions": [
            "1. Are tiered lecture halls occupied for evening community events or cleared by 9:30 PM?",
            "2. Are whiteboard trays cleaned nightly with chemical solution or dry-erased only?",
            "3. Are secondary faculty office suites cleaned nightly if locked?"
        ],
        "red_flags": [
            "⚠️ Inspect under-seat trash and gum in tiered lecture halls",
            "⚠️ Check transition strips between tile corridors and carpet",
            "⚠️ Check drinking fountains for hard-water lime buildup"
        ]
    },
    {
        "code": "H",
        "name": "Heritage Hall",
        "sector": "Sector Bravo (Hub)",
        "sqft": 78450,
        "lat": 33.1314616,
        "lon": -96.7941169,
        "stats": "24 Classrooms | 40 Offices | 6 Restrooms (28 Fixtures)",
        "flooring": "Terrazzo/VCT corridors, carpet in student services & testing center",
        "questions": [
            "1. What are the operating hours and access restrictions for the Testing Center?",
            "2. Do floors 2 and 3 have dedicated hot-water slop sinks in the janitor closets?",
            "3. Are private faculty offices unlocked by security for evening cleaners?"
        ],
        "red_flags": [
            "⚠️ Check Testing Center restricted access & noise requirements",
            "⚠️ Inspect open stairwell bulkheads for dust cobwebs",
            "⚠️ Check elevator cab stainless steel and door tracks"
        ]
    },
    {
        "code": "L",
        "name": "Library & Learning Resource Center",
        "sector": "Sector Charlie (Special)",
        "sqft": 62180,
        "lat": 33.1317080,
        "lon": -96.7928631,
        "stats": "8 Multi-Media Rooms | 25 Offices | 4 Restrooms (18 Fixtures)",
        "flooring": "85% Commercial broadloom & carpet tile, VCT workrooms",
        "questions": [
            "1. Does the library maintain late-night student study hours past 10:00 PM?",
            "2. Is deep restorative HOST dry carpet cleaning scheduled exclusively during semester breaks?",
            "3. Are computer carrels dusted around cables or perimeter only?"
        ],
        "red_flags": [
            "⚠️ Inspect carpet traffic lanes for coffee stains and seam tears",
            "⚠️ Check vaulted ceiling beams and central skylight for dust",
            "⚠️ Confirm noise sensitivity limits (mandates quiet <65 dBA vacuums)"
        ]
    },
    {
        "code": "J",
        "name": "Lawler Hall (Building D)",
        "sector": "Sector Charlie (Special)",
        "sqft": 48260,
        "lat": 33.1306004,
        "lon": -96.7938961,
        "stats": "20 Classrooms | 18 Offices | 4 Restrooms (18 Fixtures)",
        "flooring": "Polished sealed concrete concourse, VCT, carpet tile",
        "questions": [
            "1. What diamond pad or burnishing chemical is required for sealed concrete (SOW § 170)?",
            "2. Are the executive seminar rooms used for daytime board meetings?",
            "3. Are walk-off mats provided and maintained by the District at entrances?"
        ],
        "red_flags": [
            "⚠️ Check concrete slab gloss (diamond-polished vs acrylic wax buildup)",
            "⚠️ Inspect exposed spiral HVAC ducts in tech classrooms for dust",
            "⚠️ Check entry doors for exterior water penetration"
        ]
    },
    {
        "code": "A",
        "name": "Alumni Hall & Physical Education",
        "sector": "Sector Charlie (Athletic)",
        "sqft": 38940,
        "lat": 33.1313951,
        "lon": -96.7918255,
        "stats": "Gymnasium | Fitness Center | Dance Studio | 4 Restroom/Locker Banks (24 Fixt, 16 Showers, 180 Lockers)",
        "flooring": "Specialized rubber flooring (fitness), hardwood gym/dance floors, ceramic showers",
        "questions": [
            "1. Who disconnects power and assists when commercial gym gear is moved 3×/year (SOW § 42)?",
            "2. Does the college supply the proprietary wood floor cleaner (Huntington or equiv)?",
            "3. Are locker room shower stalls acid descaled 3× per year by the vendor?"
        ],
        "red_flags": [
            "⚠️ Inspect weight room rubber floor seams and odor",
            "⚠️ Check hardwood gym floor finish for dulling or scratches",
            "⚠️ Inspect shower stalls for soap scum, mold, and floor drain backups",
            "⚠️ Look up at 32-ft gym bar joists and Big Ass Fans for dust blankets"
        ]
    },
    {
        "code": "C",
        "name": "Student Center & Cafeteria",
        "sector": "Sector Bravo (Hub)",
        "sqft": 32150,
        "lat": 33.1322189,
        "lon": -96.7941642,
        "stats": "Food Court Dining | Student Lounge | 4 Restroom Banks (16 Fixtures)",
        "flooring": "Porcelain tile, luxury vinyl, quarry tile in prep perimeter",
        "questions": [
            "1. Where does custodial scope end and food service vendor scope begin in the cafeteria?",
            "2. How often are dining hall trash cans pulled during the lunch rush?",
            "3. Are grease traps and kitchen drains maintained by college plumbing?"
        ],
        "red_flags": [
            "⚠️ Inspect dining floor for grease film / slipperiness",
            "⚠️ Check outdoor dining patio tables and trash can capacity",
            "⚠️ Check ceiling trusses and serving bulkheads for cooking film"
        ]
    },
    {
        "code": "IT",
        "name": "IT Infrastructure Building",
        "sector": "Sector Bravo (Hub)",
        "sqft": 18420,
        "lat": 33.1327534,
        "lon": -96.7931172,
        "stats": "Network Operations Center | Help Desk | 2 Restroom Banks (8 Fixtures)",
        "flooring": "Anti-static raised computer flooring, low-pile commercial carpet",
        "questions": [
            "1. Is the central server room (MDF) excluded from daily janitorial cleaning or escort-only?",
            "2. What is the access protocol for custodial badge entry into network closets?",
            "3. Are anti-static ESD-grounded vacuum protocols mandatory in all IT labs?"
        ],
        "red_flags": [
            "⚠️ Verify zero-liquid protocol around server racks and computer bays",
            "⚠️ Check overhead cable trays for dust accumulation",
            "⚠️ Ensure non-conductive fiberglass ladders are strictly specified"
        ]
    },
    {
        "code": "M",
        "name": "Facilities Operations & Maintenance",
        "sector": "Sector Delta",
        "sqft": 14200,
        "lat": 33.1305764,
        "lon": -96.7912365,
        "stats": "Central Receiving Dock | Trade Workshops | Custodial Storage Core | 1 Restroom Bank (4 Fixtures)",
        "flooring": "Sealed industrial concrete, trade shop slabs",
        "questions": [
            "1. Is this loading dock the designated drop-off point for monthly semi-truck deliveries of paper/chemicals?",
            "2. Is there secure, dedicated square footage here for our riding auto-scrubber charging stations?",
            "3. Does the college provide access to an on-site scissor lift for break projects?"
        ],
        "red_flags": [
            "⚠️ Verify 20A electrical outlets for heavy floor machine battery chargers",
            "⚠️ Inspect chemical storage staging area and eyewash station",
            "⚠️ Check loading dock height and pallet jack roll paths"
        ]
    },
    {
        "code": "S",
        "name": "Campus Safety & Central Plant",
        "sector": "Sector Delta",
        "sqft": 9393,
        "lat": 33.1305764,
        "lon": -96.7912365,
        "stats": "Police Substation | Dispatch Core | Mechanical Plant | 1 Restroom Bank (4 Fixtures)",
        "flooring": "Sealed concrete, vinyl composite tile",
        "questions": [
            "1. Is the custodial physical sign-in logbook kept at Police Dispatch (SOW § 202)?",
            "2. Do Collin College Police officers conduct random attendance checks during night shifts?",
            "3. Are holding cells or armory rooms completely off-limits to cleaners?"
        ],
        "red_flags": [
            "⚠️ Verify location of biometric fingerprint clock network jack & power",
            "⚠️ Confirm after-hours police badge-in protocols for night cleaners"
        ]
    },
    {
        "code": "PKG",
        "name": "Multi-Story Parking Garage",
        "sector": "Sector Delta / Grounds",
        "sqft": 0,
        "lat": 33.1332939,
        "lon": -96.7929573,
        "stats": "3 Concrete Stairwell Towers | 1 Elevator Shaft Core",
        "flooring": "Cast-in-place post-tensioned concrete, stainless steel cab",
        "questions": [
            "1. Is pressure washing of garage stairwells billed under base contract or as unscheduled work orders?",
            "2. Who is responsible for bird nest removal and swallow prevention on upper ceilings?"
        ],
        "red_flags": [
            "⚠️ Inspect concrete stair landings for cobwebs, windblown litter, and oil stains",
            "⚠️ Check elevator door tracks for gravel and dirt jams",
            "⚠️ Verify nearby water hose spigots for stairwell wash-downs"
        ]
    }
]

WALKTHROUGH_STATE_FILE = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-QUOTES", "BOSANNA-COLLIN-COLLEGE", "walkthrough_active_state.json")
WALKTHROUGH_LOG_FILE = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-QUOTES", "BOSANNA-COLLIN-COLLEGE", "WALKTHROUGH_FIELD_LOG.md")

def save_active_walkthrough_building(bldg_dict, lat=None, lon=None):
    os.makedirs(os.path.dirname(WALKTHROUGH_STATE_FILE), exist_ok=True)
    state = {
        "code": bldg_dict["code"],
        "name": bldg_dict["name"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lat": lat,
        "lon": lon
    }
    with open(WALKTHROUGH_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def get_active_walkthrough_building():
    if os.path.exists(WALKTHROUGH_STATE_FILE):
        try:
            with open(WALKTHROUGH_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def log_walkthrough_finding(bldg_name, note_text, photo_path=None):
    tstamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n### [{tstamp}] {bldg_name}\n- **Note:** {note_text}\n"
    if photo_path:
        entry += f"- **Photo Attached:** `{os.path.basename(photo_path)}`\n"
    target_paths = [
        WALKTHROUGH_LOG_FILE,
        "/app/static/proposals/WALKTHROUGH_FIELD_LOG.md",
        os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-QUOTES", "BOSANNA-COLLIN-COLLEGE", "WALKTHROUGH_FIELD_LOG.md"),
        "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-QUOTES/BOSANNA-COLLIN-COLLEGE/WALKTHROUGH_FIELD_LOG.md"
    ]
    for p in target_paths:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a") as f:
                f.write(entry)
        except Exception:
            pass

def send_building_field_card(chat_id, bldg, dist_ft=None):
    dist_str = f" (~{dist_ft} ft away)" if dist_ft is not None else ""
    sqft_str = f"{bldg['sqft']:,} Cleanable SF" if bldg['sqft'] > 0 else "Elevator & Stairways Core"
    
    q_text = "\n".join(bldg["questions"])
    rf_text = "\n".join(bldg["red_flags"])
    
    msg = (
        f"📍 *Building Detected:* *{bldg['name']} (Code {bldg['code']})*{dist_str}\n"
        f"🏛️ *Sector:* {bldg['sector']} | 📐 *Footprint:* {sqft_str}\n"
        f"🚻 *Takeoff:* {bldg['stats']}\n"
        f"🧼 *Flooring:* {bldg['flooring']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 *QUESTIONS TO ASK FACILITIES ON THE SPOT:*\n"
        f"{q_text}\n\n"
        f"🚨 *RED FLAGS TO INSPECT RIGHT NOW:*\n"
        f"{rf_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Reply with text, a voice note, or a photo to document findings for this building!*"
    )
    
    buttons = [
        [{"text": "🗺️ Exterior Trash Map", "callback_data": "collin_trashmap"}, {"text": "🏢 All Buildings Menu", "callback_data": "collin_all_buildings_menu"}],
        [{"text": "📑 Send Excel Model", "callback_data": "proposal_17"}, {"text": "⬅️ Back to Collin Hub", "callback_data": "cmd_collin"}]
    ]
    send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})

def handle_location_message(lat, lon, chat_id):
    """Triggered when CEO shares location from phone."""
    best_bldg = None
    min_dist_ft = float('inf')
    for b in FRISCO_BUILDINGS_GEOFENCE:
        dist_deg = ((lat - b['lat'])**2 + (lon - b['lon'])**2)**0.5
        dist_ft = round(dist_deg * 364000)
        if dist_ft < min_dist_ft:
            min_dist_ft = dist_ft
            best_bldg = b

    if best_bldg:
        save_active_walkthrough_building(best_bldg, lat=lat, lon=lon)
        send_building_field_card(chat_id, best_bldg, dist_ft=min_dist_ft)
    else:
        send_telegram_message(chat_id, f"📍 Location received ({lat:.5f}, {lon:.5f}), but outside Collin College Frisco campus boundaries.")

def handle_cmd_bldg(chat_id, query, callback_id=None):
    """Allows manual selection by code or name (e.g. /bldg F, /bldg gym)."""
    if callback_id:
        answer_callback_query(callback_id)
    query_clean = (query or "").strip().lower()
    target_bldg = None
    for b in FRISCO_BUILDINGS_GEOFENCE:
        if query_clean == b["code"].lower() or query_clean in b["name"].lower():
            target_bldg = b
            break
    
    if target_bldg:
        save_active_walkthrough_building(target_bldg)
        send_building_field_card(chat_id, target_bldg)
    else:
        send_all_buildings_menu(chat_id)

def send_all_buildings_menu(chat_id):
    msg = "🏢 *Select a Collin College Frisco Building to Inspect:*"
    keyboard = []
    row = []
    for b in FRISCO_BUILDINGS_GEOFENCE:
        row.append({"text": f"{b['code']} - {b['name']}", "callback_data": f"walkthrough_bldg_{b['code']}"})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([{"text": "⬅️ Back to Collin Hub", "callback_data": "cmd_collin"}])
    send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": keyboard})

def handle_cmd_help(chat_id):
    auth_user = get_user_for_chat(chat_id)
    actor_name = auth_user.get("name", "Team Member") if auth_user else "Team Member"
    actor_role = auth_user.get("role", "Operator") if auth_user else "Team Member"
    perms = auth_user.get("telegram_perms", {}) if auth_user else {}
    can_cmd = perms.get("can_run_terminal_cmd", False)
    
    cmd_line = "⚡ */cmd <command>* — Linux terminal shell execution\n" if can_cmd else ""
    msg = (
        f"🏛️ *SigmaFidelity™ Operations Command Node v3.0*\n"
        f"👤 *Logged In:* {actor_name} ({actor_role})\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ *Operations Commands:*\n\n"
        f"{cmd_line}"
        "🏫 */collin* — Collin College Frisco Campus Walkthrough Hub\n"
        "💬 *Chat with George* — Natural language directives, emails & research\n"
        "📊 */bids* — Active GC bids, takeoffs & live pipeline\n"
        "📥 */autotakeoff <ID>* — 1-Tap BuildingConnected planroom extraction\n"
        "📤 */submit_bid <ID>* — 1-Tap BuildingConnected portal bid submission\n"
        "📐 */scope <ID>* — In-chat interactive pricing sliders & scope tweaks\n"
        "🌅 */briefing* — Comprehensive 7:00 AM executive morning brief\n"
        "📬 */pending* — Staged client proposals awaiting CEO sign-off\n"
        "✅ */approve <ID>* — Release staged email for dispatch\n"
        "👁️ */preview <ID>* — Inspect staged email body & financials\n"
        "🚀 */dispatch <ID>* — Immediate Microsoft Graph API transmission\n"
        "🎯 */leads* — Real-time Texas CRM lead pipeline\n"
        "🔍 */search <query>* — Universal cross-table database search\n"
        "📑 */proposal <ID>* — Receive Excel proposal file directly in chat\n"
        "🧠 */sync* — Trigger neural persistence handshake\n"
        "👥 */users* — Team member Telegram roster & connection status\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🎙️ *Voice Notes:* Multimodal speech parsing to tasks/calendar\n"
        "📷 *Photos:* Computer vision inspection & GPS mapping"
    )
    send_telegram_message(chat_id, msg, reply_markup=get_main_menu_keyboard(chat_id))

def handle_cmd_briefing(chat_id):
    """Frontier 6: Dispatches the 7:00 AM Executive Morning Briefing."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM \"Leads\";")
            total_leads = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*), COALESCE(SUM(estimated_value), 0) FROM \"ConstructionBids\";")
            b_row = cur.fetchone()
            bids_cnt = b_row[0]
            pipeline_val = float(b_row[1])
            cur.execute("SELECT COUNT(*) FROM \"PendingOutbox\" WHERE status = 'PENDING';")
            pending_outbox = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM \"ConstructionBids\" WHERE status LIKE '%%Discrepancy%%';")
            discrepancy_cnt = cur.fetchone()[0]

        msg = (
            f"🌅 *SigmaFidelity™ Executive Morning Briefing*\n"
            f"📅 *Date:* {datetime.now().strftime('%A, %B %d, %Y')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏗️ *Commercial Pipeline:* {bids_cnt} active bids | *${pipeline_val:,.2f}*\n"
            f"📬 *Proposals Awaiting Approval:* {pending_outbox} pending in Outbox\n"
            f"⚠️ *Takeoffs Flagged for Discrepancy:* {discrepancy_cnt} heuristic records\n"
            f"🎯 *Texas CRM Lead Base:* {total_leads:,} statewide leads\n"
            f"🤖 *Host Task Runner Daemon:* Active (Playwright & Takeoff Engine)\n"
            f"✉️ *Microsoft Graph API:* Connected (`{USER_EMAIL}`)\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Tap below to review bids or approve staged client emails:"
        )
        buttons = [
            [{"text": "📬 Review Outbox Queue", "callback_data": "cmd_pending"}, {"text": "📊 Inspect Active Bids", "callback_data": "cmd_bids"}],
            [{"text": "📐 Open Scope Configurator", "callback_data": "cmd_scope_menu"}]
        ]
        send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error generating morning briefing: {e}")
    finally:
        if conn:
            conn.close()

def handle_cmd_bids(chat_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, gc_name, project_name, cleanable_sqft, estimated_value, status, rfp_url
                FROM \"ConstructionBids\" 
                ORDER BY id ASC;
            """)
            bids = cur.fetchall()

        if not bids:
            send_telegram_message(chat_id, "ℹ️ No active bids found in ConstructionBids database.")
            return

        lines = ["🏗️ *Active General Contractor Bidding Stream*", "━━━━━━━━━━━━━━━━━━━━━"]
        buttons = []
        for b in bids:
            sqft_str = f"{int(b['cleanable_sqft']):,} SF" if b['cleanable_sqft'] else "TBD"
            val_str = f"${float(b['estimated_value']):,.2f}" if b['estimated_value'] else "Pending"
            
            icon = "🟢" if "Complete" in b['status'] else "🟡"
            if "Discrepancy" in b['status']:
                icon = "⚠️"
                
            lines.append(
                f"{icon} *#{b['id']} | {b['gc_name']}*\n"
                f"   📁 *Project:* {b['project_name']}\n"
                f"   📐 *Footprint:* {sqft_str} | *Value:* {val_str}\n"
                f"   🏷️ *Status:* `{b['status']}`\n"
            )
            buttons.append([
                {"text": f"📐 Takeoff #{b['id']}", "callback_data": f"takeoff_{b['id']}"},
                {"text": f"📥 Auto-Takeoff", "callback_data": f"autotakeoff_{b['id']}"}
            ])

        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        markup = {"inline_keyboard": buttons[:8]}
        send_telegram_message(chat_id, "\n".join(lines), reply_markup=markup)
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error querying bids: {e}")
    finally:
        if conn:
            conn.close()

def handle_cmd_takeoff(chat_id, arg, callback_id=None):
    if not arg or not str(arg).strip().isdigit():
        send_telegram_message(chat_id, "⚠️ Usage: `/takeoff <BID_ID>`")
        return

    bid_id = int(str(arg).strip())
    if callback_id:
        answer_callback_query(callback_id, f"Loading Takeoff #{bid_id}...")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM \"ConstructionBids\" WHERE id = %s;", (bid_id,))
            bid = cur.fetchone()

        if not bid:
            send_telegram_message(chat_id, f"❌ Bid #{bid_id} not found.")
            return

        sqft = f"{int(bid['cleanable_sqft']):,} SF" if bid.get('cleanable_sqft') else "Pending"
        val = f"${float(bid['estimated_value']):,.2f}" if bid.get('estimated_value') else "Pending"
        
        status_icon = "🟢" if "Complete" in bid['status'] else "🟡"
        discrepancy_alert = ""
        if "Discrepancy" in bid['status']:
            status_icon = "⚠️"
            discrepancy_alert = "\n⚠️ *EMPIRICAL MANDATE NOTICE: Calibrated Footprint / Heuristic Estimate*\n"

        proposal_file = find_proposal_file(bid_id, bid['project_name'], bid['gc_name'])
        has_file = bool(proposal_file and os.path.exists(proposal_file))

        msg = (
            f"📐 *Takeoff Audit: Bid #{bid['id']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 *General Contractor:* {bid['gc_name']}\n"
            f"📁 *Project:* {bid['project_name']}\n"
            f"📍 *Location:* {bid.get('city') or 'Texas'}\n"
            f"📏 *Cleanable Footprint:* {sqft}\n"
            f"💰 *Calculated Base Bid:* {val}\n"
            f"{status_icon} *Status:* `{bid['status']}`"
            f"{discrepancy_alert}"
            f"📝 *Audit Notes:* {bid.get('notes') or 'None'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )

        buttons = []
        if has_file:
            buttons.append([
                {"text": f"📑 Send Excel Proposal", "callback_data": f"send_proposal_{bid['id']}"},
                {"text": f"📤 Submit to BC Portal", "callback_data": f"submit_bc_{bid['id']}"}
            ])
        else:
            buttons.append([{"text": f"📥 Run Auto-Takeoff", "callback_data": f"autotakeoff_{bid['id']}"}])

        buttons.append([
            {"text": f"🎛️ Adjust Scope / Margins", "callback_data": f"scope_edit_{bid['id']}"},
            {"text": "📊 All Bids", "callback_data": "cmd_bids"}
        ])

        send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error querying takeoff for #{bid_id}: {e}")
    finally:
        if conn:
            conn.close()

def handle_action_autotakeoff(chat_id, bid_id, callback_id=None):
    """Frontier 1: Triggers BuildingConnected automated download and takeoff execution."""
    if callback_id:
        answer_callback_query(callback_id, f"Enqueueing Auto-Takeoff #{bid_id}...")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, gc_name, project_name, rfp_url FROM \"ConstructionBids\" WHERE id = %s;", (bid_id,))
            bid = cur.fetchone()

        if not bid:
            send_telegram_message(chat_id, f"❌ Bid #{bid_id} not found.")
            return

        url = bid.get("rfp_url") or "https://app.buildingconnected.com/opportunities/pipeline"
        task_id = enqueue_task("BC_AUTOTAKEOFF", {
            "bid_id": bid['id'],
            "opportunity_url": url,
            "project_name": bid['project_name']
        })

        msg = (
            f"📥 *Autonomous Planroom Ingestion Triggered*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Bid #{bid['id']}* | {bid['gc_name']}\n"
            f"📁 *Project:* {bid['project_name']}\n"
            f"⚙️ *Task ID:* `{task_id}`\n"
            f"🤖 *Host Task Runner* is launching headless browser to download drawings and execute PyMuPDF takeoff.\n"
            f"You will receive the compiled proposal spreadsheet directly here upon completion."
        )
        send_telegram_message(chat_id, msg)
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error triggering auto-takeoff: {e}")
    finally:
        if conn:
            conn.close()

def handle_action_submit_bc(chat_id, bid_id, callback_id=None):
    """Frontier 5: Triggers Playwright to submit the bid to BuildingConnected portal."""
    if callback_id:
        answer_callback_query(callback_id, f"Enqueueing Portal Submission #{bid_id}...")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, gc_name, project_name, estimated_value, rfp_url FROM \"ConstructionBids\" WHERE id = %s;", (bid_id,))
            bid = cur.fetchone()

        if not bid:
            send_telegram_message(chat_id, f"❌ Bid #{bid_id} not found.")
            return

        proposal_file = find_proposal_file(bid_id, bid['project_name'], bid['gc_name'])
        val = float(bid['estimated_value']) if bid.get('estimated_value') else 0.0

        task_id = enqueue_task("BC_SUBMIT_BID", {
            "bid_id": bid['id'],
            "opportunity_url": bid.get('rfp_url') or "https://app.buildingconnected.com/opportunities/pipeline",
            "bid_amount": val,
            "excel_path": proposal_file
        })

        msg = (
            f"📤 *BuildingConnected Submission Bot Enqueued*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Bid #{bid['id']}* | {bid['gc_name']}\n"
            f"📁 *Project:* {bid['project_name']}\n"
            f"💰 *Base Bid:* ${val:,.2f}\n"
            f"⚙️ *Task ID:* `{task_id}`\n"
            f"The browser worker will navigate to the portal, verify the RFP form, attach the Excel proposal, and return a confirmation screenshot."
        )
        send_telegram_message(chat_id, msg)
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error enqueuing portal submission: {e}")
    finally:
        if conn:
            conn.close()

def handle_scope_adjust_ui(chat_id, bid_id, message_id=None, delta_sqft=0, delta_margin=0, toggle_clinical=False):
    """Frontier 2: In-chat interactive scope & pricing adjuster."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM \"ConstructionBids\" WHERE id = %s;", (bid_id,))
            bid = cur.fetchone()

            if not bid:
                send_telegram_message(chat_id, f"❌ Bid #{bid_id} not found.")
                return

            current_sqft = int(bid['cleanable_sqft'] or 15000)
            new_sqft = max(1000, current_sqft + delta_sqft)

            is_clinical = "Clinical" in (bid['special_requirements'] or "")
            if toggle_clinical:
                is_clinical = not is_clinical

            # Rate: 0.48/SF standard commercial, 0.75/SF clinical
            rate = 0.75 if is_clinical else 0.48
            new_val = round(new_sqft * rate, 2)
            special_req = "Clinical Biosafety Decontamination" if is_clinical else "Standard Commercial Scope"

            cur.execute("""
                UPDATE \"ConstructionBids\"
                SET cleanable_sqft = %s, estimated_value = %s, special_requirements = %s, updated_at = NOW()
                WHERE id = %s;
            """, (new_sqft, new_val, special_req, bid_id))
            conn.commit()

        msg = (
            f"🎛️ *Interactive Scope Configurator: Bid #{bid['id']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 *GC:* {bid['gc_name']} | *Project:* {bid['project_name']}\n"
            f"📏 *Cleanable Footprint:* *{new_sqft:,} SF*\n"
            f"🏥 *Classification:* *{special_req}*\n"
            f"💰 *Calculated Base Bid:* *${new_val:,.2f}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Tap adjustments below to update live in database:"
        )

        buttons = [
            [{"text": "➕ 5,000 SF", "callback_data": f"adj_sqft_p5000_{bid_id}"}, {"text": "➖ 5,000 SF", "callback_data": f"adj_sqft_m5000_{bid_id}"}],
            [{"text": "🏥 Toggle Clinical / Lab", "callback_data": f"adj_clinical_{bid_id}"}],
            [{"text": "📑 Send Updated Excel", "callback_data": f"send_proposal_{bid_id}"}, {"text": "🔙 Back to Takeoff", "callback_data": f"takeoff_{bid_id}"}]
        ]

        if message_id:
            edit_telegram_message(chat_id, message_id, msg, reply_markup={"inline_keyboard": buttons})
        else:
            send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})

    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error adjusting scope: {e}")
    finally:
        if conn:
            conn.close()

def handle_action_send_proposal(chat_id, bid_id, callback_id=None):
    if callback_id:
        answer_callback_query(callback_id, f"Transmitting Proposal #{bid_id}...")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, gc_name, project_name, cleanable_sqft, estimated_value FROM \"ConstructionBids\" WHERE id = %s;", (bid_id,))
            bid = cur.fetchone()

        if not bid:
            send_telegram_message(chat_id, f"❌ Bid #{bid_id} not found.")
            return

        file_path = find_proposal_file(bid['id'], bid['project_name'], bid['gc_name'])
        if not file_path or not os.path.exists(file_path):
            send_telegram_message(chat_id, f"⚠️ Excel proposal file not found on disk for Bid #{bid_id}.")
            return

        caption = (
            f"📑 *SigmaFidelity™ Takeoff Proposal Document*\n"
            f"🏢 *GC:* {bid['gc_name']}\n"
            f"📁 *Project:* {bid['project_name']}\n"
            f"💰 *Base Bid:* ${float(bid['estimated_value']):,.2f} ({int(bid['cleanable_sqft']):,} SF)"
        )
        markup = {"inline_keyboard": [[{"text": "📤 Submit to BuildingConnected", "callback_data": f"submit_bc_{bid['id']}"}, {"text": "📊 Back to Bids", "callback_data": "cmd_bids"}]]}
        send_telegram_document(chat_id, file_path, caption=caption, reply_markup=markup)
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error sending proposal document: {e}")
    finally:
        if conn:
            conn.close()

# --- VOICE & PHOTO MULTIMODAL PROCESSORS ---

def handle_voice_message(voice_obj, chat_id):
    """Frontier 3: Downloads CEO voice note and runs Gemini Speech AI reasoning."""
    file_id = voice_obj.get("file_id")
    duration = voice_obj.get("duration", 0)

    send_telegram_message(chat_id, f"🎙️ *Transcribing & Analyzing CEO Voice Directive* ({duration}s)...")
    try:
        get_file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
        res = session.get(get_file_url, params={"file_id": file_id}, timeout=15)
        file_path = res.json().get("result", {}).get("file_path")
        if not file_path:
            send_telegram_message(chat_id, "⚠️ Unable to download voice payload from Telegram.")
            return

        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        voice_res = session.get(download_url, timeout=30)
        audio_bytes = voice_res.content

        # Save archive
        save_dir = "/app/logs/voice_directives" if os.path.exists("/.dockerenv") else os.path.join(BASE_DIR, "logs", "voice_directives")
        os.makedirs(save_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        saved_filename = f"voice_directive_{timestamp_str}.ogg"
        with open(os.path.join(save_dir, saved_filename), "wb") as vf:
            vf.write(audio_bytes)

        # Gemini Multimodal Speech Reasoning
        gemini_result, err = analyze_voice_with_gemini(audio_bytes, chat_id=chat_id)
        if err:
            send_telegram_message(chat_id, f"⚠️ Voice analysis error: {err}")
            return

        # Parse JSON block if present
        json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', gemini_result)
        intent_data = {}
        if json_match:
            try:
                intent_data = json.loads(json_match.group(1))
            except Exception:
                pass

        intent = intent_data.get("intent", "strategic_note")
        action_status = ""

        # Execute automated action based on intent
        if intent == "create_calendar_event":
            subj = intent_data.get("title") or "Executive Appointment"
            dt = intent_data.get("date_time")
            details = intent_data.get("summary") or gemini_result
            ok, msg = create_graph_calendar_event(subj, start_iso=dt, body=details)
            action_status = f"\n📅 *Outlook Action:* {msg}"
        elif intent == "draft_email":
            # Stage proposal into PendingOutbox
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO \"PendingOutbox\" (recipient, subject, body, status, created_at)
                    VALUES (%s, %s, %s, 'PENDING', NOW()) RETURNING id;
                """, (intent_data.get("recipient", "client@domain.com"), intent_data.get("title", "Commercial Proposal"), intent_data.get("summary", gemini_result)))
                new_out_id = cur.fetchone()[0]
                conn.commit()
            conn.close()
            action_status = f"\n📬 *Staged Proposal:* Created Outbox Record #{new_out_id} (Awaiting 1-tap approval)."

        # Log directive to sigma_kb
        doc_id = f"voice-directive-{timestamp_str}"
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sigma_kb (doc_id, content, metadata)
                VALUES (%s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET content = EXCLUDED.content, metadata = EXCLUDED.metadata;
            """, (doc_id, gemini_result, Json({"source": "Telegram Voice Memo", "file": saved_filename, "timestamp": datetime.now().isoformat()})))
        conn.commit()
        conn.close()

        msg = (
            f"🎙️ *Executive Voice Directive Processed*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{gemini_result}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
            f"{action_status}"
        )
        send_telegram_message(chat_id, msg, reply_markup=get_main_menu_keyboard())

    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Voice ingestion error: {e}")

def handle_photo_message(photo_list, chat_id, caption=""):
    """Frontier 4: Multimodal Blueprint & Jobsite Photo Computer Vision."""
    best_photo = photo_list[-1]
    file_id = best_photo.get("file_id")

    send_telegram_chat_action(chat_id, "typing")
    send_telegram_message(chat_id, "📷 *Analyzing Jobsite Photo with Gemini 2.5 Flash Vision*...")
    try:
        get_file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
        res = session.get(get_file_url, params={"file_id": file_id}, timeout=15)
        file_path = res.json().get("result", {}).get("file_path")
        if not file_path:
            send_telegram_message(chat_id, "⚠️ Unable to download photo payload from Telegram.")
            return

        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        img_res = session.get(download_url, timeout=30)
        img_bytes = img_res.content

        # Extract building tag from caption if present
        bldg_tag = "general"
        clean_cap = (caption or "").lower()
        if "founder" in clean_cap: bldg_tag = "founders_hall"
        elif "heritage" in clean_cap: bldg_tag = "heritage_hall"
        elif "university" in clean_cap: bldg_tag = "university_hall"
        elif "library" in clean_cap or "lrc" in clean_cap: bldg_tag = "library_lrc"
        elif "lawler" in clean_cap: bldg_tag = "lawler_hall"
        elif "alumni" in clean_cap or "gym" in clean_cap: bldg_tag = "alumni_hall"
        elif "student" in clean_cap or "cafeteria" in clean_cap: bldg_tag = "student_center"
        elif "it" in clean_cap or "server" in clean_cap: bldg_tag = "it_bldg"
        elif "maint" in clean_cap or "facil" in clean_cap: bldg_tag = "facilities_bldg"
        elif "police" in clean_cap or "safety" in clean_cap: bldg_tag = "safety_bldg"

        t_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        fname = f"collin_frisco_{bldg_tag}_{t_str}.jpg"

        # Save incoming photo archive across container and host paths
        save_dirs = [
            "/app/logs/incoming_photos",
            "/app/static/walkthrough_photos",
            os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-QUOTES", "BOSANNA-COLLIN-COLLEGE", "walkthrough_photos"),
            os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE", "static", "walkthrough_photos"),
            os.path.join(BASE_DIR, "logs", "incoming_photos")
        ]
        for sdir in save_dirs:
            try:
                os.makedirs(sdir, exist_ok=True)
                with open(os.path.join(sdir, fname), "wb") as pf:
                    pf.write(img_bytes)
            except Exception:
                pass

        # Check for GPS metadata or trashcan keywords to update live site map
        has_gps = False
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            import io
            with Image.open(io.BytesIO(img_bytes)) as pil_img:
                exif = pil_img._getexif()
                if exif:
                    for k, v in exif.items():
                        if TAGS.get(k) == "GPSInfo" and v:
                            has_gps = True
                            break
        except Exception:
            pass

        if has_gps or any(w in clean_cap for w in ["trash", "can", "bin", "urn", "waste", "exterior", "grounds"]):
            try:
                import subprocess
                subprocess.run(["python3", os.path.join(BASE_DIR, "scripts", "plot_walkthrough_gps.py")], check=True)
                plot_path = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-QUOTES", "BOSANNA-COLLIN-COLLEGE", "frisco_campus_trashcan_plot.png")
                if os.path.exists(plot_path):
                    send_telegram_document(
                        chat_id, 
                        plot_path, 
                        caption=f"🗺️ *GPS Plotted to Frisco Campus Map!*\nLocation updated for {bldg_tag.replace('_', ' ').title()}."
                    )
            except Exception as pe:
                print(f"[GPS] Plotter error: {pe}", flush=True)

        gemini_result, err = analyze_photo_with_gemini(img_bytes, caption=caption, chat_id=chat_id)
        if err:
            send_telegram_message(chat_id, f"⚠️ Vision analysis error: {err}")
            return

        # Parse JSON block
        json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', gemini_result)
        bid_data = {}
        if json_match:
            try:
                bid_data = json.loads(json_match.group(1))
            except Exception:
                pass

        proj_name = bid_data.get("project_name") or "Field Photo Takeoff"
        sqft = bid_data.get("estimated_sqft") or 10000
        rate = 0.75 if bid_data.get("is_clinical") else 0.48
        val = round(sqft * rate, 2)

        # Create candidate bid record in ConstructionBids
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO \"ConstructionBids\" (
                    gc_name, project_name, cleanable_sqft, estimated_value, status, notes, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, 'Field Takeoff (Photo Extracted)', %s, NOW(), NOW())
                RETURNING id;
            """, ("Field Verification", proj_name, sqft, val, gemini_result[:400]))
            new_bid_id = cur.fetchone()[0]
            conn.commit()
        conn.close()

        msg = (
            f"📷 *Computer Vision Blueprint Takeoff Generated*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{gemini_result}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Registered in database as *Bid #{new_bid_id}* (${val:,.2f})."
        )
        buttons = [
            [{"text": f"📐 Inspect Bid #{new_bid_id}", "callback_data": f"takeoff_{new_bid_id}"}],
            [{"text": "📊 View All Bids", "callback_data": "cmd_bids"}]
        ]
        send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})

    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Photo processing error: {e}")

# --- OUTBOX & CRM HANDLERS ---

def handle_cmd_pending(chat_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, recipient, subject, status, created_at 
                FROM \"PendingOutbox\" 
                WHERE status = 'PENDING' 
                ORDER BY id DESC 
                LIMIT 5;
            """)
            items = cur.fetchall()

        if not items:
            send_telegram_message(chat_id, "✅ *Pending Outbox is clear!* No emails currently awaiting CEO approval.", reply_markup=get_main_menu_keyboard())
            return

        lines = ["📬 *Staged Outbox Emails (Awaiting CEO Approval)*", "━━━━━━━━━━━━━━━━━━━━━"]
        buttons = []
        for item in items:
            created_str = item['created_at'].strftime('%m/%d %H:%M') if item['created_at'] else "N/A"
            lines.append(
                f"🆔 *Record #{item['id']}*\n"
                f"👤 *To:* `{item['recipient']}`\n"
                f"📄 *Subject:* {item['subject']}\n"
                f"⏰ *Staged:* {created_str}\n"
            )
            buttons.append([
                {"text": f"✅ Approve #{item['id']}", "callback_data": f"approve_{item['id']}"},
                {"text": f"👁️ Preview #{item['id']}", "callback_data": f"preview_{item['id']}"},
                {"text": f"❌ Reject #{item['id']}", "callback_data": f"reject_{item['id']}"}
            ])

        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        lines.append("Tap an action button below:")
        send_telegram_message(chat_id, "\n".join(lines), reply_markup={"inline_keyboard": buttons})
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error querying pending outbox: {e}")
    finally:
        if conn:
            conn.close()

def handle_action_preview(chat_id, record_id, callback_id=None):
    if callback_id:
        answer_callback_query(callback_id, f"Loading Preview #{record_id}...")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, recipient, subject, body, status FROM \"PendingOutbox\" WHERE id = %s;", (record_id,))
            item = cur.fetchone()

        if not item:
            send_telegram_message(chat_id, f"❌ Outbox record #{record_id} not found.")
            return

        clean_body = clean_html_content(item['body'])
        if len(clean_body) > 1200:
            clean_body = clean_body[:1200] + "\n\n...[Preview truncated for mobile display]"

        msg = (
            f"👁️ *Staged Proposal Preview: #{item['id']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Recipient:* `{item['recipient']}`\n"
            f"📄 *Subject:* {item['subject']}\n"
            f"🏷️ *Status:* `{item['status']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{clean_body}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [{"text": f"✅ Approve #{item['id']}", "callback_data": f"approve_{item['id']}"}, {"text": f"❌ Reject #{item['id']}", "callback_data": f"reject_{item['id']}"}],
            [{"text": "📬 Back to Pending Queue", "callback_data": "cmd_pending"}]
        ]
        send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Preview error: {e}")
    finally:
        if conn:
            conn.close()

def handle_cmd_approve(chat_id, arg, callback_id=None):
    auth_user = get_user_for_chat(chat_id)
    perms = auth_user.get("telegram_perms", {}) if auth_user else {}
    if not perms.get("can_approve_outbox"):
        if callback_id:
            answer_callback_query(callback_id, "Unauthorized: Outbox approval requires Executive role.")
        send_telegram_message(
            chat_id,
            "🚫 *Permission Denied*\n"
            "Your profile is not authorized to approve outbound transmissions (`can_approve_outbox`).\n"
            "Outbox approvals require Executive authorization."
        )
        return

    if not arg or not str(arg).strip().isdigit():
        send_telegram_message(chat_id, "⚠️ Usage: `/approve <ID>`")
        return

    record_id = int(str(arg).strip())
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, recipient, subject FROM \"PendingOutbox\" WHERE id = %s;", (record_id,))
            item = cur.fetchone()

            if not item:
                if callback_id:
                    answer_callback_query(callback_id, f"Record #{record_id} not found.")
                send_telegram_message(chat_id, f"❌ Outbox record #{record_id} not found.")
                return

            cur.execute("UPDATE \"PendingOutbox\" SET status = 'APPROVED' WHERE id = %s;", (record_id,))
            conn.commit()

        if callback_id:
            answer_callback_query(callback_id, f"Approved Record #{record_id}!")

        msg = (
            f"✅ *Authorization Granted by CEO Humberto Dominguez*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Record #{record_id} Status:* `APPROVED`\n"
            f"👤 *Recipient:* `{item['recipient']}`\n"
            f"📄 *Subject:* {item['subject']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Choose an action:"
        )
        buttons = [
            [{"text": f"🚀 Dispatch via Graph API Now", "callback_data": f"dispatch_{record_id}"}],
            [{"text": "📬 Back to Pending Queue", "callback_data": "cmd_pending"}]
        ]
        send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error approving record #{record_id}: {e}")
    finally:
        if conn:
            conn.close()

def handle_action_dispatch(chat_id, record_id, callback_id=None):
    auth_user = get_user_for_chat(chat_id)
    perms = auth_user.get("telegram_perms", {}) if auth_user else {}
    if not perms.get("can_approve_outbox"):
        if callback_id:
            answer_callback_query(callback_id, "Unauthorized: Outbox dispatch requires Executive role.")
        send_telegram_message(
            chat_id,
            "🚫 *Permission Denied*\n"
            "Your profile is not authorized to dispatch outbound transmissions (`can_approve_outbox`)."
        )
        return

    if callback_id:
        answer_callback_query(callback_id, f"Dispatching #{record_id} via Microsoft Graph...")
    send_telegram_message(chat_id, f"🚀 Dispatching email #{record_id} via Microsoft Graph API ({USER_EMAIL})...")
    ok, details = dispatch_graph_email(record_id)
    if ok:
        msg = (
            f"🚀 *Email Dispatched Successfully!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Record:* #{record_id}\n"
            f"📡 *Gateway:* Microsoft Graph API (`{USER_EMAIL}`)\n"
            f"✅ *Status:* `SENT`\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        msg = f"⚠️ *Dispatch Failure for Record #{record_id}:*\n{details}"
    send_telegram_message(chat_id, msg, reply_markup=get_main_menu_keyboard())

def handle_action_reject(chat_id, record_id, callback_id=None):
    if callback_id:
        answer_callback_query(callback_id, f"Rejecting #{record_id}...")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE \"PendingOutbox\" SET status = 'REJECTED' WHERE id = %s;", (record_id,))
        conn.commit()
        msg = f"❌ *Proposal #{record_id} Rejected by CEO Humberto Dominguez.*\nStatus updated to `REJECTED`."
        send_telegram_message(chat_id, msg, reply_markup=get_main_menu_keyboard())
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Reject error: {e}")
    finally:
        if conn:
            conn.close()

def handle_cmd_status(chat_id):
    conn = None
    t0 = time.time()
    try:
        conn = get_db_connection()
        latency_ms = int((time.time() - t0) * 1000)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM \"Leads\";")
            total_leads = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*), COALESCE(SUM(estimated_value), 0) FROM \"ConstructionBids\";")
            bids_row = cur.fetchone()
            total_bids = bids_row[0]
            total_pipeline_val = float(bids_row[1])
            cur.execute("SELECT COUNT(*) FROM \"PendingOutbox\" WHERE status = 'PENDING';")
            pending_count = cur.fetchone()[0]

        token = get_graph_token()
        graph_status = "🟢 Active (Client Credentials)" if token else "🔴 Inactive"

        msg = (
            "⚙️ *SigmaFidelity™ Institutional Health Pulse*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 *PostgreSQL:* Connected (`hwb_dev_db` | {latency_ms}ms)\n"
            f"🎯 *Texas Leads Ingested:* {total_leads:,} records\n"
            f"🏗️ *Commercial GC Pipeline:* {total_bids} bids | ${total_pipeline_val:,.2f}\n"
            f"📬 *Pending Approvals:* {pending_count} awaiting CEO review\n"
            f"✉️ *Microsoft Graph API:* {graph_status}\n"
            f"🤖 *Host Task Runner:* Active (`task_queue` listener)\n"
            f"🧠 *Gemini Multimodal AI:* Active (Speech & Vision)\n"
            f"🛡️ *Takeoff Mandate:* Empirical Discrepancy Flagging Live\n"
            f"⏰ *Server Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "━━━━━━━━━━━━━━━━━━━━━"
        )
        send_telegram_message(chat_id, msg, reply_markup=get_main_menu_keyboard())
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error querying system health: {e}")
    finally:
        if conn:
            conn.close()

def handle_cmd_search(chat_id, query):
    if not query or len(query.strip()) < 2:
        send_telegram_message(chat_id, "🔍 *Usage:* `/search <keyword>` (e.g. `/search UTSW`, `/search Bosanna`, `/search Daycare`)")
        return
    
    q = f"%{query.strip()}%"
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            clean_term = query.strip()
            cur.execute("""
                SELECT id, gc_name, project_name, estimated_value, status,
                       similarity(project_name, %s) as sim
                FROM \"ConstructionBids\" 
                WHERE gc_name ILIKE %s OR project_name ILIKE %s OR notes ILIKE %s
                   OR similarity(project_name, %s) > 0.15
                   OR soundex(project_name) = soundex(%s)
                ORDER BY sim DESC NULLS LAST
                LIMIT 4;
            """, (clean_term, q, q, q, clean_term, clean_term))
            bids = cur.fetchall()

            cur.execute("""
                SELECT id, center_name, director, phone, city 
                FROM \"Leads\" 
                WHERE center_name ILIKE %s OR director ILIKE %s OR city ILIKE %s OR phone ILIKE %s
                LIMIT 4;
            """, (q, q, q, q))
            leads = cur.fetchall()

            cur.execute("""
                SELECT doc_id 
                FROM sigma_kb 
                WHERE doc_id ILIKE %s OR content ILIKE %s 
                LIMIT 3;
            """, (q, q))
            docs = cur.fetchall()

        buttons = []
        lines = [f"🔍 *Intelligence Search:* `{query.strip()}`", "━━━━━━━━━━━━━━━━━━━━━"]

        if bids:
            lines.append("🏗️ *Commercial GC Bids:*")
            for b in bids:
                lines.append(f"  • #{b['id']} | *{b['gc_name']}* - {b['project_name']} (`{b['status']}`)")
                buttons.append([{"text": f"📐 Inspect Bid #{b['id']}", "callback_data": f"takeoff_{b['id']}"}])

        if leads:
            lines.append("\n🎯 *CRM Leads:*")
            for l in leads:
                lines.append(f"  • #{l['id']} | *{l['center_name'] or 'Lead'}* ({l['city'] or 'TX'})")
                buttons.append([{"text": f"👤 Inspect Lead #{l['id']}", "callback_data": f"lead_{l['id']}"}])

        if docs:
            lines.append("\n🧠 *Knowledge Base Documents:*")
            for d in docs:
                lines.append(f"  • `{d['doc_id']}`")

        # Fallback search into Outlook emails if no bids found or explicit solicitation search
        found_emails = search_graph_messages(query.strip(), top=3)
        if found_emails:
            lines.append("\n📬 *Inbound Outlook Solicitations:*")
            for em in found_emails:
                p_title = em["parsed_details"]["project_name"] or em["subject"]
                lines.append(f"  • *{p_title}* (`{em['sender_email']}` - {em['received_date']})")
                buttons.append([{"text": f"📥 Ingest {p_title[:22]}...", "callback_data": f"ingest_msg_{em['id']}"}])

        if not bids and not leads and not docs and not found_emails:
            lines.append(f"❌ No matching records found for `{query.strip()}`.")

        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        markup = {"inline_keyboard": buttons[:8]} if buttons else get_main_menu_keyboard()
        send_telegram_message(chat_id, "\n".join(lines), reply_markup=markup)
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Search Error: {e}")
    finally:
        if conn:
            conn.close()

def handle_cmd_leads(chat_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM \"Leads\";")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM \"Leads\" WHERE priority_level = 'High';")
            high_pri = cur.fetchone()[0]
            cur.execute("SELECT lead_source, COUNT(*) FROM \"Leads\" GROUP BY lead_source ORDER BY 2 DESC LIMIT 4;")
            sources = cur.fetchall()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, center_name, director, city, phone FROM \"Leads\" WHERE priority_level = 'High' ORDER BY id DESC LIMIT 3;")
            recent_high = cur.fetchall()

        lines = [
            "🎯 *SigmaFidelity™ Texas Lead Pipeline*",
            "━━━━━━━━━━━━━━━━━━━━━",
            f"📊 *Total Ingested Leads:* {total:,} (Statewide Texas)",
            f"🔥 *High-Priority Targets:* {high_pri:,}",
            "\n*Top Ingestion Channels:*"
        ]
        for src, cnt in sources:
            lines.append(f"  • {src or 'Direct Discovery'}: {cnt:,}")

        buttons = []
        if recent_high:
            lines.append("\n*Latest High-Priority Leads:*")
            for l in recent_high:
                lines.append(f"  • #{l['id']} | *{l['center_name']}* ({l['city'] or 'TX'})")
                buttons.append([{"text": f"👤 Inspect Lead #{l['id']}", "callback_data": f"lead_{l['id']}"}])

        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        buttons.append([{"text": "🔍 Search Leads Pipeline", "callback_data": "cmd_search_prompt"}])
        send_telegram_message(chat_id, "\n".join(lines), reply_markup={"inline_keyboard": buttons})
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error querying leads: {e}")
    finally:
        if conn:
            conn.close()

def handle_cmd_lead_detail(chat_id, lead_id, callback_id=None):
    if callback_id:
        answer_callback_query(callback_id)
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, center_name, director, phone, email, address, city, county,
                       sqf, estimated_annual_value, priority_level, status, lead_source
                FROM \"Leads\" WHERE id = %s;
            """, (lead_id,))
            lead = cur.fetchone()

        if not lead:
            send_telegram_message(chat_id, f"❌ Lead #{lead_id} not found.")
            return

        sqf_str = f"{int(lead['sqf']):,} SF" if lead.get('sqf') else "TBD"
        val_str = f"${float(lead['estimated_annual_value']):,.2f}" if lead.get('estimated_annual_value') else "Pending"

        msg = (
            f"🎯 *Lead Dossier: #{lead['id']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 *Company/Center:* {lead['center_name'] or 'Target Facility'}\n"
            f"👤 *Contact Person:* {lead['director'] or 'General Manager'}\n"
            f"📞 *Phone:* `{lead['phone'] or 'Not on file'}`\n"
            f"✉️ *Email:* `{lead['email'] or 'Not on file'}`\n"
            f"📍 *Address:* {lead['address'] or ''}, {lead['city'] or ''}, {lead['county'] or 'TX'}\n"
            f"📏 *Estimated Footprint:* {sqf_str}\n"
            f"💰 *Annual Value:* {val_str}\n"
            f"🏷️ *Priority:* `{lead['priority_level'] or 'Standard'}` | *Status:* `{lead['status'] or 'New'}`\n"
            f"📡 *Source:* {lead['lead_source'] or 'Texas Discovery'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [{"text": "🎯 View Leads Pipeline", "callback_data": "cmd_leads"}, {"text": "🔍 Search System", "callback_data": "cmd_search_prompt"}]
        ]
        send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Error loading lead #{lead_id}: {e}")
    finally:
        if conn:
            conn.close()

def handle_cmd_sync(chat_id):
    send_telegram_message(chat_id, "🧠 *Initiating SigmaFidelity™ Neural Persistence Handshake...*")
    try:
        sync_script = "/app/scripts/sigma_sync.py" if os.path.exists("/app/scripts/sigma_sync.py") else os.path.join(BASE_DIR, "scripts", "sigma_sync.py")
        proc = subprocess.run(["python3", sync_script], capture_output=True, text=True, timeout=90)
        output_snippet = "\n".join(proc.stdout.strip().splitlines()[-5:])
        msg = (
            f"🧠 *Neural Persistence Synchronized*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"```\n{output_snippet}\n```\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Traceability 100% locked to PostgreSQL."
        )
        send_telegram_message(chat_id, msg, reply_markup=get_main_menu_keyboard())
    except Exception as e:
        send_telegram_message(chat_id, f"⚠️ Sync error: {e}")

# --- CALLBACK QUERY ROUTER ---

def process_callback_query(callback_query):
    query_id = callback_query.get("id")
    message = callback_query.get("message", {})
    message_id = message.get("message_id")
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    data = callback_query.get("data", "")
    from_user = callback_query.get("from", {})

    if not is_chat_authorized(chat_id):
        answer_callback_query(query_id, "Unauthorized")
        record_and_mirror_activity(chat_id, from_user, "unauthorized_callback", f"Unauthorized button attempt: `{data}`", friction_flag=True)
        return

    print(f"[TELEGRAM] Callback received: '{data}' from {chat_id}", flush=True)

    # Real-time Telemetry & Mirroring
    record_and_mirror_activity(
        chat_id=chat_id,
        from_user=from_user,
        event_type="callback_button",
        payload_summary=f"Tapped button action: `{data}`",
        detected_intent=data.split('_')[0] if '_' in data else data
    )

    if data == "cmd_collin":
        answer_callback_query(query_id)
        handle_cmd_collin(chat_id)
    elif data in ["cmd_behavior", "cmd_insights"]:
        answer_callback_query(query_id, "Synthesizing behavioral insights...")
        handle_cmd_behavioral_insights(chat_id)
    elif data == "cmd_mirror":
        answer_callback_query(query_id)
        handle_cmd_mirror(chat_id)
    elif data == "collin_buildings":
        answer_callback_query(query_id)
        handle_collin_buildings(chat_id)
    elif data == "collin_staffing":
        answer_callback_query(query_id)
        handle_collin_staffing(chat_id)
    elif data == "collin_equipment":
        answer_callback_query(query_id)
        handle_collin_equipment(chat_id)
    elif data == "collin_pricing":
        answer_callback_query(query_id)
        handle_collin_pricing(chat_id)
    elif data == "collin_trashmap":
        answer_callback_query(query_id)
        handle_collin_trashmap(chat_id)
    elif data == "collin_all_buildings_menu":
        answer_callback_query(query_id)
        send_all_buildings_menu(chat_id)
    elif data.startswith("walkthrough_bldg_"):
        b_code = data.replace("walkthrough_bldg_", "")
        handle_cmd_bldg(chat_id, b_code, callback_id=query_id)
    elif data == "proposal_17":
        handle_action_send_proposal(chat_id, 17, callback_id=query_id)
    elif data == "cmd_bids":
        answer_callback_query(query_id)
        handle_cmd_bids(chat_id)
    elif data == "cmd_status":
        answer_callback_query(query_id)
        handle_cmd_status(chat_id)
    elif data == "cmd_pending":
        answer_callback_query(query_id)
        handle_cmd_pending(chat_id)
    elif data == "cmd_leads":
        answer_callback_query(query_id)
        handle_cmd_leads(chat_id)
    elif data == "cmd_briefing":
        answer_callback_query(query_id, "Generating morning briefing...")
        handle_cmd_briefing(chat_id)
    elif data == "cmd_sync":
        answer_callback_query(query_id, "Starting sync...")
        handle_cmd_sync(chat_id)
    elif data == "cmd_scope_menu":
        answer_callback_query(query_id)
        # Select first active bid or prompt
        handle_scope_adjust_ui(chat_id, 4)
    elif data == "cmd_search_prompt":
        answer_callback_query(query_id)
        send_telegram_message(chat_id, "🔍 To search, type `/search <keyword>` (e.g. `/search UTSW` or `/search Bosanna`).")
    elif data.startswith("approve_"):
        handle_cmd_approve(chat_id, data.replace("approve_", ""), callback_id=query_id)
    elif data.startswith("preview_"):
        handle_action_preview(chat_id, data.replace("preview_", ""), callback_id=query_id)
    elif data.startswith("reject_"):
        handle_action_reject(chat_id, data.replace("reject_", ""), callback_id=query_id)
    elif data.startswith("dispatch_"):
        handle_action_dispatch(chat_id, data.replace("dispatch_", ""), callback_id=query_id)
    elif data.startswith("takeoff_"):
        handle_cmd_takeoff(chat_id, data.replace("takeoff_", ""), callback_id=query_id)
    elif data.startswith("send_proposal_"):
        handle_action_send_proposal(chat_id, int(data.replace("send_proposal_", "")), callback_id=query_id)
    elif data.startswith("autotakeoff_"):
        handle_action_autotakeoff(chat_id, int(data.replace("autotakeoff_", "")), callback_id=query_id)
    elif data.startswith("submit_bc_"):
        handle_action_submit_bc(chat_id, int(data.replace("submit_bc_", "")), callback_id=query_id)
    elif data.startswith("scope_edit_"):
        bid_id = int(data.replace("scope_edit_", ""))
        handle_scope_adjust_ui(chat_id, bid_id)
    elif data.startswith("adj_sqft_p5000_"):
        bid_id = int(data.replace("adj_sqft_p5000_", ""))
        answer_callback_query(query_id, "Adding 5,000 SF...")
        handle_scope_adjust_ui(chat_id, bid_id, message_id=message_id, delta_sqft=5000)
    elif data.startswith("adj_sqft_m5000_"):
        bid_id = int(data.replace("adj_sqft_m5000_", ""))
        answer_callback_query(query_id, "Subtracting 5,000 SF...")
        handle_scope_adjust_ui(chat_id, bid_id, message_id=message_id, delta_sqft=-5000)
    elif data.startswith("adj_clinical_"):
        bid_id = int(data.replace("adj_clinical_", ""))
        answer_callback_query(query_id, "Toggling Clinical Scope...")
        handle_scope_adjust_ui(chat_id, bid_id, message_id=message_id, toggle_clinical=True)
    elif data.startswith("lead_"):
        handle_cmd_lead_detail(chat_id, int(data.replace("lead_", "")), callback_id=query_id)
    elif data.startswith("link_user_"):
        parts = data.split("_")
        if len(parts) >= 4:
            target_username = parts[2]
            target_chat_id = parts[3]
            try:
                conn = get_db_connection()
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('UPDATE "Users" SET telegram_chat_id = %s WHERE LOWER(username) = LOWER(%s) RETURNING id, full_name, role;', (str(target_chat_id), target_username))
                    updated = cur.fetchone()
                    conn.commit()
                conn.close()
                if updated:
                    answer_callback_query(query_id, "User linked successfully!")
                    send_telegram_message(chat_id, f"✅ Successfully linked *{updated['full_name']}* ({updated['role']}) to Telegram Chat ID `{target_chat_id}`!\n\nShe is now live and will receive real-time operational notifications.")
                    try:
                        send_telegram_message(int(target_chat_id), f"✅ *Account Activated!*\nCEO Humberto Dominguez has connected your Telegram account to HWB Operations Control. Welcome aboard, {updated['full_name']}!")
                    except Exception:
                        pass
                else:
                    answer_callback_query(query_id, f"User {target_username} not found.")
            except Exception as e:
                answer_callback_query(query_id, f"Error: {e}")
    elif data.startswith("ingest_msg_"):
        msg_id = data.replace("ingest_msg_", "")
        answer_callback_query(query_id, "Ingesting solicitation into GC Pipeline...")
        ok, res_msg, bid_id = ingest_bid_from_email_id(msg_id)
        if ok and bid_id:
            btns = [
                [{"text": f"📐 Open Takeoff #{bid_id}", "callback_data": f"takeoff_{bid_id}"}],
                [{"text": "📊 View All Bids", "callback_data": "cmd_bids"}]
            ]
            send_telegram_message(chat_id, f"✅ *Successfully Ingested Bid #{bid_id}!*\n━━━━━━━━━━━━━━━━━━━━━\n{res_msg}", reply_markup={"inline_keyboard": btns})
        else:
            send_telegram_message(chat_id, f"⚠️ Ingestion Failed: {res_msg}")
    elif data.startswith("search_email_"):
        kw = data.replace("search_email_", "")
        answer_callback_query(query_id, f"Searching emails for '{kw}'...")
        handle_text_conversation(f"Check my emails for {kw}", chat_id)
    else:
        answer_callback_query(query_id, "Acknowledged")

# --- MESSAGE DISPATCHER ---

def process_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    auth_user = get_user_for_chat(chat_id)
    text = message.get("text", "").strip()

    from_user = message.get("from", {})
    print(f"[TELEGRAM] >>> INCOMING MESSAGE from chat_id={chat_id}, user={from_user.get('first_name')} (@{from_user.get('username')}): '{text}'", flush=True)

    # Check for Forwarded Messages (Effortless User & Group ID Detection)
    forward_from = message.get("forward_from")
    forward_from_chat = message.get("forward_from_chat")
    forward_sender_name = message.get("forward_sender_name")

    if forward_from:
        f_id = forward_from.get("id")
        f_first = forward_from.get("first_name", "")
        f_last = forward_from.get("last_name", "")
        f_name = f"{f_first} {f_last}".strip() or "Telegram User"
        f_user_handle = f"@{forward_from.get('username')}" if forward_from.get("username") else "No username"
        record_and_mirror_activity(chat_id, from_user, "forwarded_message", f"Forwarded user detected: {f_name} ({f_user_handle}, ID {f_id})", detected_intent="user_forward")
        msg = (
            f"🔍 *Detected User from Forwarded Message!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Name:* {f_name}\n"
            f"🏷️ *Handle:* {f_user_handle}\n"
            f"🆔 *Telegram Chat ID:* `{f_id}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Tap below to instantly link this Chat ID:"
        )
        markup = {
            "inline_keyboard": [
                [{"text": f"✅ Link to Mirna Rondinella", "callback_data": f"link_user_mrondinella_{f_id}"}],
                [{"text": "👥 View All Users", "callback_data": "cmd_users"}]
            ]
        }
        send_telegram_message(chat_id, msg, reply_markup=markup)
        return

    if forward_from_chat:
        f_id = forward_from_chat.get("id")
        f_title = forward_from_chat.get("title", "Group")
        record_and_mirror_activity(chat_id, from_user, "forwarded_group", f"Forwarded group detected: {f_title} (ID {f_id})", detected_intent="group_forward")
        msg = (
            f"🏢 *Detected Group/Channel from Forward!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ *Title:* {f_title}\n"
            f"🆔 *Telegram Chat ID:* `{f_id}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"This group's Telegram ID is `{f_id}`."
        )
        send_telegram_message(chat_id, msg)
        return

    if forward_sender_name:
        record_and_mirror_activity(chat_id, from_user, "forwarded_private", f"Forwarded from private sender: {forward_sender_name}", detected_intent="private_forward")
        msg = (
            f"🔒 *Forwarded Message Received from:* {forward_sender_name}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"This user has Telegram Forward Privacy enabled, which hides their numerical ID when messages are forwarded.\n\n"
            f"👉 Solution: Please ask {forward_sender_name} to search for **@Georgebytesbot** directly and tap **Start**!"
        )
        send_telegram_message(chat_id, msg)
        return

    # Check for Magic Link Onboarding Token
    if text.startswith("/start auth_") or text.startswith("auth_"):
        token = text.split("auth_")[1].strip()
        record_and_mirror_activity(chat_id, from_user, "magic_link_auth", f"Attempting magic link authentication", detected_intent="magic_link")
        handle_magic_link_auth(chat_id, token, from_user)
        return

    if not auth_user:
        chat_type = chat.get("type", "private")
        record_and_mirror_activity(chat_id, from_user, "unregistered_contact", f"Incoming text from unlinked account: \"{text}\"", friction_flag=True, detected_intent="onboarding")

        if chat_type in ["group", "supergroup"]:
            chat_title = chat.get("title", "Group")
            msg = (
                f"👋 *Hello {chat_title}!* I am George, your autonomous operations assistant.\n\n"
                f"🏢 *Group Chat ID:* `{chat_id}`\n\n"
                f"To register this group for real-time alerts, CEO Humberto Dominguez can link it using:\n"
                f"`/linkuser hdominguez {chat_id}`"
            )
            send_telegram_message(chat_id, msg)
            return

        if text.startswith("/register"):
            handle_user_registration(chat_id, text, from_user)
            return
        elif text in ["/start", "/id", "/myid", "/help"]:
            welcome_unregistered_user(chat_id, from_user)
            return
        else:
            print(f"[TELEGRAM] Unregistered message from chat_id {chat_id}, sending onboarding prompt.", flush=True)
            welcome_unregistered_user(chat_id, from_user)
            return

    # Check for Voice Directives (Frontier 3)
    voice = message.get("voice") or message.get("audio")
    if voice:
        record_and_mirror_activity(chat_id, from_user, "voice_directive", f"Voice directive duration: {voice.get('duration', 0)}s", detected_intent="multimodal_voice")
        handle_voice_message(voice, chat_id)
        return

    # Check for Photos (Frontier 4)
    photos = message.get("photo")
    if photos:
        caption = message.get("caption", "")
        record_and_mirror_activity(chat_id, from_user, "photo_upload", f"Photo uploaded with caption: '{caption}'", detected_intent="computer_vision")
        handle_photo_message(photos, chat_id, caption=caption)
        return

    # Check for Documents (PDF Blueprints or Uncompressed Photos with EXIF GPS)
    document = message.get("document")
    if document:
        file_name = document.get("file_name", "")
        file_id = document.get("file_id")
        mime_type = document.get("mime_type", "")
        caption = message.get("caption", "")
        record_and_mirror_activity(chat_id, from_user, "document_upload", f"Document uploaded: '{file_name}' ({mime_type})", detected_intent="document_ingestion")
        if file_id:
            if any(file_name.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".heic"]) or "image" in mime_type.lower():
                handle_photo_message([{"file_id": file_id}], chat_id, caption=caption)
                return
            elif file_name.lower().endswith(".pdf") or "pdf" in mime_type.lower():
                send_telegram_message(chat_id, f"George: Ingesting PDF blueprint '{file_name}'...")
                return
        return

    # Check for Location Shares (GPS Walkthrough Intelligence)
    location = message.get("location")
    if location:
        lat = location.get("latitude")
        lon = location.get("longitude")
        record_and_mirror_activity(chat_id, from_user, "location_share", f"GPS Pin shared: lat={lat}, lon={lon}", detected_intent="walkthrough_gps")
        handle_location_message(lat, lon, chat_id)
        return

    text = message.get("text", "").strip()

    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        record_and_mirror_activity(chat_id, from_user, "command", f"Command: {cmd} {arg}".strip(), detected_intent=cmd.replace('/', ''))

        if cmd in ["/cmd", "/bash", "/sh", "/terminal"]:
            handle_cmd_terminal(chat_id, arg)
        elif cmd in ["/start", "/help"]:
            handle_cmd_help(chat_id)
        elif cmd in ["/mirror"]:
            handle_cmd_mirror(chat_id, arg)
        elif cmd in ["/insights", "/behavior"]:
            handle_cmd_behavioral_insights(chat_id)
        elif cmd in ["/collin", "/walkthrough", "/frisco"]:
            handle_cmd_collin(chat_id)
        elif cmd in ["/bldg", "/building", "/locate"]:
            handle_cmd_bldg(chat_id, arg)
        elif cmd in ["/trashmap", "/trashcans", "/gpsmap"]:
            handle_collin_trashmap(chat_id)
        elif cmd in ["/briefing", "/morning"]:
            handle_cmd_briefing(chat_id)
        elif cmd in ["/status", "/pulse"]:
            handle_cmd_status(chat_id)
        elif cmd in ["/bids", "/projects"]:
            handle_cmd_bids(chat_id)
        elif cmd in ["/pending", "/outbox"]:
            handle_cmd_pending(chat_id)
        elif cmd in ["/approve", "/accept"]:
            handle_cmd_approve(chat_id, arg)
        elif cmd in ["/preview"]:
            if arg.isdigit():
                handle_action_preview(chat_id, int(arg))
            else:
                send_telegram_message(chat_id, "⚠️ Usage: `/preview <ID>`")
        elif cmd in ["/dispatch", "/send_email"]:
            if arg.isdigit():
                handle_action_dispatch(chat_id, int(arg))
            else:
                send_telegram_message(chat_id, "⚠️ Usage: `/dispatch <ID>`")
        elif cmd in ["/leads", "/crm"]:
            handle_cmd_leads(chat_id)
        elif cmd in ["/lead"]:
            if arg.isdigit():
                handle_cmd_lead_detail(chat_id, int(arg))
            else:
                send_telegram_message(chat_id, "⚠️ Usage: `/lead <ID>`")
        elif cmd in ["/takeoff", "/estimate"]:
            handle_cmd_takeoff(chat_id, arg)
        elif cmd in ["/autotakeoff"]:
            if arg.isdigit():
                handle_action_autotakeoff(chat_id, int(arg))
            else:
                send_telegram_message(chat_id, "⚠️ Usage: `/autotakeoff <BID_ID>`")
        elif cmd in ["/submit_bid"]:
            if arg.isdigit():
                handle_action_submit_bc(chat_id, int(arg))
            else:
                send_telegram_message(chat_id, "⚠️ Usage: `/submit_bid <BID_ID>`")
        elif cmd in ["/scope"]:
            bid_id = int(arg) if arg.isdigit() else 4
            handle_scope_adjust_ui(chat_id, bid_id)
        elif cmd in ["/proposal", "/send_proposal"]:
            if arg.isdigit():
                handle_action_send_proposal(chat_id, int(arg))
            else:
                send_telegram_message(chat_id, "⚠️ Usage: `/proposal <BID_ID>`")
        elif cmd in ["/search", "/find"]:
            handle_cmd_search(chat_id, arg)
        elif cmd in ["/sync"]:
            handle_cmd_sync(chat_id)
        elif cmd in ["/adduser", "/linkuser"]:
            handle_cmd_adduser(chat_id, arg)
        elif cmd in ["/users", "/team"]:
            handle_cmd_users(chat_id)
        else:
            send_telegram_message(chat_id, f"❓ Unknown command: `{cmd}`. Tap an option below or send `/help`.", reply_markup=get_main_menu_keyboard(chat_id))
        return

    # Frontier 7: Full Two-Way Conversational Intelligence with George
    if text:
        record_and_mirror_activity(chat_id, from_user, "text_chat", f"Query: \"{text}\"", detected_intent="conversational")
        active_bldg = get_active_walkthrough_building()
        if active_bldg and (text.lower().startswith("note:") or text.lower().startswith("log:") or text.lower().startswith("#") or any(w in text.lower() for w in ["facilities", "clean", "glass", "door", "floor", "key", "restroom", "dispenser", "dave"])):
            log_walkthrough_finding(f"{active_bldg['name']} (Code {active_bldg['code']})", text)
        handle_text_conversation(text, chat_id)

# --- AUTONOMOUS SCHEDULERS (DEAL CAPTURE & 7:00 AM BRIEFING) ---

def autonomous_deal_capture_loop():
    """Background daemon checking Graph API for GC bids & pending outbox every 15 minutes."""
    print("[AUTONOMOUS MONITOR] 15-Minute Deal-Capture Thread Initialized.", flush=True)
    last_notified_outbox_ids = set()
    last_briefing_date = None

    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            # Frontier 6: 7:00 AM Daily Briefing Trigger
            if now.hour == 7 and now.minute <= 15 and last_briefing_date != today_str:
                last_briefing_date = today_str
                print("[AUTONOMOUS MONITOR] Triggering 7:00 AM Daily Executive Briefing...", flush=True)
                handle_cmd_briefing(ALLOWED_CHAT_ID)

            # 1. Check for Pending Outbox Approvals
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, recipient, subject, created_at FROM \"PendingOutbox\" WHERE status = 'PENDING';")
                staged = cur.fetchall()

            for item in staged:
                if item['id'] not in last_notified_outbox_ids:
                    last_notified_outbox_ids.add(item['id'])
                    msg = (
                        f"🔔 *EXECUTIVE ACTION REQUIRED: Proposal Staged*\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🆔 *Record #{item['id']}*\n"
                        f"👤 *Recipient:* `{item['recipient']}`\n"
                        f"📄 *Subject:* {item['subject']}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Tap below to approve or preview:"
                    )
                    markup = {
                        "inline_keyboard": [
                            [{"text": f"✅ Approve #{item['id']}", "callback_data": f"approve_{item['id']}"}, {"text": f"👁️ Preview #{item['id']}", "callback_data": f"preview_{item['id']}"}],
                            [{"text": "📬 View Pending Queue", "callback_data": "cmd_pending"}]
                        ]
                    }
                    send_telegram_message(ALLOWED_CHAT_ID, msg, reply_markup=markup)
            conn.close()

            # 2. Check for Inbound GC Bid Solicitations via Graph API
            token = get_graph_token()
            if token:
                headers = {'Authorization': f'Bearer {token}'}
                url = f'https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/messages?$top=10&$select=id,subject,from,receivedDateTime,bodyPreview&$orderby=receivedDateTime desc'
                res = requests.get(url, headers=headers, timeout=20)
                if res.status_code == 200:
                    messages = res.json().get('value', [])
                    gc_terms = ['buildingconnected', 'planroom', 'reproconnect', 'final clean', 'rough clean', 'construction clean', 'invitation to bid', 'itb', 'bid due']
                    
                    conn = get_db_connection()
                    for m in messages:
                        subj = m.get('subject', '')
                        sender = m.get('from', {}).get('emailAddress', {}).get('address', '')
                        name = m.get('from', {}).get('emailAddress', {}).get('name', '')
                        body = m.get('bodyPreview', '')
                        msg_id = m.get('id')

                        combined = f"{subj} {sender} {name} {body}".lower()
                        if any(term in combined for term in gc_terms):
                            with conn.cursor() as cur:
                                cur.execute("SELECT id FROM \"ConstructionBids\" WHERE email_id = %s;", (msg_id,))
                                exists = cur.fetchone()
                                if not exists:
                                    parsed = parse_email_bid_details(subj, body, sender_name=name, sender_email=sender)
                                    real_proj = parsed["project_name"] or subj[:100]
                                    cur.execute("""
                                        INSERT INTO \"ConstructionBids\" (
                                            gc_name, project_name, project_address, city, state, zipcode,
                                            bid_due_date, plan_url, rfp_url, estimator_name, estimator_email, estimator_phone,
                                            platform, status, email_id, special_requirements, notes, created_at, updated_at
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Invited', %s, %s, %s, NOW(), NOW())
                                        RETURNING id;
                                    """, (
                                        name or sender,
                                        real_proj,
                                        parsed["address"] or None,
                                        parsed["city"] or None,
                                        parsed["state"] or None,
                                        parsed["zipcode"] or None,
                                        parsed["bid_due_date"],
                                        parsed["plan_url"],
                                        parsed["plan_url"],
                                        parsed["estimator_name"] or None,
                                        parsed["estimator_email"] or None,
                                        parsed["estimator_phone"] or None,
                                        'BuildingConnected' if 'buildingconnected' in combined else 'Planroom',
                                        msg_id,
                                        f"Prebid: {parsed['prebid_date_str']}. {parsed['description']}",
                                        body[:200]
                                    ))
                                    new_id = cur.fetchone()[0]
                                    conn.commit()

                                    alert_msg = (
                                        f"🔔 *NEW GC BID INVITATION DETECTED*\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"🏢 *General Contractor:* {name or sender}\n"
                                        f"📁 *Project:* {real_proj}\n"
                                        f"📍 *Location:* {parsed['city']}, {parsed['state']}\n"
                                        f"✉️ *Sender:* `{sender}`\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"Registered in database as *Bid #{new_id}*."
                                    )
                                    markup = {
                                        "inline_keyboard": [
                                            [{"text": f"📐 Takeoff #{new_id}", "callback_data": f"takeoff_{new_id}"}, {"text": f"📥 1-Tap Auto-Takeoff", "callback_data": f"autotakeoff_{new_id}"}],
                                            [{"text": "📊 View All Bids", "callback_data": "cmd_bids"}]
                                        ]
                                    }
                                    send_telegram_message(ALLOWED_CHAT_ID, alert_msg, reply_markup=markup)
                    conn.close()

        except Exception as loop_err:
            print(f"[AUTONOMOUS MONITOR] Error in 15-minute loop: {loop_err}", flush=True)

        time.sleep(900)

def safe_process_update(update: dict):
    """
    Enterprise worker task: processes a single update in an isolated thread.
    Catches all exceptions to prevent thread deaths and preserve loop integrity.
    """
    try:
        if "callback_query" in update:
            process_callback_query(update["callback_query"])
        elif "message" in update:
            process_message(update["message"])
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print(f"[TELEGRAM WORKER EXCEPTION]: {exc}\n{tb}", flush=True)

def poll_updates():
    offset = None
    print("[TELEGRAM] Starting SigmaFidelity™ Executive Command Node v3.1 (Enterprise Concurrency Engine)...", flush=True)

    monitor_thread = threading.Thread(target=autonomous_deal_capture_loop, daemon=True)
    monitor_thread.start()

    # Enterprise ThreadPool: 16 concurrent workers to ensure non-blocking polling and instant scaling
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=16, thread_name_prefix="tg_worker")

    while True:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"timeout": 15}
        if offset:
            params["offset"] = offset

        try:
            res = session.get(url, params=params, timeout=20)
            if res.status_code == 200:
                data = res.json()
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update.get("update_id") + 1
                        print(f"[TELEGRAM] >>> INCOMING UPDATE #{offset}: {update}", flush=True)
                        executor.submit(safe_process_update, update)
            else:
                print(f"[TELEGRAM POLLING WARNING] getUpdates returned HTTP {res.status_code}: {res.text}", flush=True)
                time.sleep(2)
        except Exception as e:
            print(f"[TELEGRAM POLLING EXCEPTION]: {e}", flush=True)
            time.sleep(3)

        time.sleep(0.5)

if __name__ == "__main__":
    poll_updates()
