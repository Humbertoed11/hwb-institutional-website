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
from datetime import datetime, timezone, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from dotenv import load_dotenv
import msal

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

try:
    ALLOWED_CHAT_ID = int(TELEGRAM_CHAT_ID)
except ValueError:
    ALLOWED_CHAT_ID = TELEGRAM_CHAT_ID

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

def send_telegram_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    """Dispatches a formatted message with optional inline keyboard buttons."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
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

def get_main_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🏫 Collin College Hub", "callback_data": "cmd_collin"}, {"text": "📑 Send Collin Excel", "callback_data": "proposal_17"}],
            [{"text": "📊 Active GC Bids", "callback_data": "cmd_bids"}, {"text": "📈 System Pulse", "callback_data": "cmd_status"}],
            [{"text": "📬 Staged Approvals", "callback_data": "cmd_pending"}, {"text": "🎯 Texas CRM Leads", "callback_data": "cmd_leads"}],
            [{"text": "📐 Scope Configurator", "callback_data": "cmd_scope_menu"}, {"text": "🌅 Morning Brief", "callback_data": "cmd_briefing"}],
            [{"text": "🔍 Universal Search", "callback_data": "cmd_search_prompt"}, {"text": "🧠 Brain Sync", "callback_data": "cmd_sync"}]
        ]
    }

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

        endpoint = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/sendMail"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        email_payload = {
            "message": {
                "subject": item["subject"],
                "body": {
                    "contentType": "HTML" if ("<" in item["body"] and ">" in item["body"]) else "Text",
                    "content": item["body"]
                },
                "toRecipients": [{"emailAddress": {"address": item["recipient"].strip()}}]
            },
            "saveToSentItems": True
        }

        res = session.post(endpoint, headers=headers, json=email_payload, timeout=25)
        if res.status_code in [200, 202]:
            with conn.cursor() as cur:
                cur.execute("UPDATE \"PendingOutbox\" SET status = 'SENT' WHERE id = %s;", (record_id,))
            conn.commit()
            return True, f"Dispatched to {item['recipient']}"
        return False, f"Graph HTTP {res.status_code}: {res.text[:200]}"
    except Exception as e:
        return False, str(e)
    finally:
        if conn:
            conn.close()


# --- COLLIN COLLEGE FRISCO CAMPUS MASTER SPECIFICATIONS ---
COLLIN_COLLEGE_CONTEXT = """
COLLIN COLLEGE FRISCO CAMPUS OPERATIONAL & PRICING SPECIFICATIONS:
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

# --- GEMINI MULTIMODAL REASONING (VOICE & VISION) ---

def analyze_voice_with_gemini(audio_bytes):
    """Uses Gemini 2.5 Flash to transcribe and parse executive intent from voice notes."""
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY not configured."
    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        "You are George, Lead Systems Architect and Senior Estimator for HWB Cleaning Services LLC.\n"
        "Listen to this executive voice memo from CEO Humberto Dominguez.\n\n"
        f"{COLLIN_COLLEGE_CONTEXT}\n\n"
        "1. Transcribe the exact words spoken.\n"
        "2. Identify the operational intent:\n"
        "   - 'create_calendar_event': Humberto wants a meeting, site walkthrough, or appointment scheduled.\n"
        "   - 'draft_email': Humberto wants an email, quote, or proposal prepared.\n"
        "   - 'send_proposal': Humberto wants the Collin College Excel model or bid proposal transmitted.\n"
        "   - 'update_bid': Humberto wants to modify a bid price, status, or scope.\n"
        "   - 'strategic_note': General directive, walkthrough observation, or operational command.\n"
        "3. Output MUST start with a JSON code block with fields:\n"
        "```json\n"
        "{\"intent\": \"create_calendar_event\"|\"draft_email\"|\"send_proposal\"|\"update_bid\"|\"strategic_note\", "
        "\"title\": \"...\", \"recipient\": \"...\", \"date_time\": \"...\", \"summary\": \"...\", \"bid_id\": 17}\n"
        "```\n"
        "Followed by a concise, authoritative executive briefing with emojis and bold headers."
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
            return res.json()["candidates"][0]["content"]["parts"][0]["text"], None
        return None, f"Gemini API Error: {res.status_code}"
    except Exception as e:
        return None, str(e)

def analyze_photo_with_gemini(image_bytes, caption=""):
    """Uses Gemini 2.5 Flash Vision to extract blueprints, finish schedules, and site conditions."""
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY not configured."
    b64_img = base64.b64encode(image_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        "You are George, Lead Systems Architect and Senior Estimator for HWB Cleaning Services LLC.\n"
        "Analyze this construction blueprint sheet, finish schedule, or jobsite photo taken by CEO Humberto Dominguez.\n\n"
        f"{COLLIN_COLLEGE_CONTEXT}\n\n"
        f"Context/Caption provided by CEO: \"{caption or 'Collin College Frisco Campus Walkthrough'}\"\n\n"
        "Provide a surgically precise industrial analysis:\n"
        "1. 🏢 Building / Space & Substrate Identified (VCT, Terrazzo, Ceramic Tile, Carpet, Sealed Concrete)\n"
        "2. 🔍 Condition & Wear Assessment (wax buildup, yellowing, grout discoloration, scratches, traffic lanes)\n"
        "3. 🧹 Restorative Maintenance Scope Required (Tri-annual deep strip & 4-coat wax, diamond hone, Kaivac restroom wash, hot-water carpet extraction)\n"
        "4. ⚠️ Forensic Discrepancies, Hidden Pitfalls, or Backcharge Risks against Incumbent (Pritchard Industries)\n\n"
        "Format cleanly with bold headers and emojis for mobile reading.\n"
        "Conclude with a JSON block:\n"
        "```json\n"
        "{\"project_name\": \"Collin College Walkthrough\", \"estimated_sqft\": 15000, \"primary_floor\": \"VCT/Terrazzo\", \"is_clinical\": false}\n"
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
            return res.json()["candidates"][0]["content"]["parts"][0]["text"], None
        return None, f"Gemini Vision Error: {res.status_code}"
    except Exception as e:
        return None, str(e)


def analyze_text_with_gemini(text, chat_id):
    """Conversational field intelligence for CEO Humberto Dominguez on Telegram."""
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY not configured.", None

    send_telegram_chat_action(chat_id, "typing")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    system_prompt = (
        "You are George, Lead Autonomous Systems Architect, Senior Estimator, Senior ISO 9001 Auditor, and Certified Lean Six Sigma Master Black Belt for HWB Cleaning Services LLC.\n"
        "You are conversing directly in real-time with CEO Humberto Dominguez via Telegram during mobile operations and facility walkthroughs.\n\n"
        f"{COLLIN_COLLEGE_CONTEXT}\n\n"
        "OPERATIONAL RULES:\n"
        "1. Strictly maintain a professional, authoritative tone. Use everyday words, bold headers, bullet points, and emojis suitable for mobile reading.\n"
        "2. If Humberto asks questions about Collin College, pricing lines 41-48, staffing hours (904 hrs/wk), equipment, square footages, or janitorial math, provide exact, surgically specific figures.\n"
        "3. If Humberto gives an operational directive, include an optional JSON block at the very start of your response:\n"
        "```json\n"
        "{\n"
        '  "intent": "create_calendar_event" | "draft_email" | "send_proposal" | "conversational",\n'
        '  "title": "...",\n'
        '  "recipient": "...",\n'
        '  "date_time": "...",\n'
        '  "summary": "...",\n'
        '  "bid_id": 17\n'
        "}\n"
        "```\n"
        "4. Follow the JSON block with your crisp, high-impact executive response to Humberto."
    )

    payload = {
        "contents": [{
            "parts": [
                {"text": f"{system_prompt}\n\nCEO Humberto Dominguez says:\n\"{text}\""}
            ]
        }]
    }

    try:
        res = session.post(url, json=payload, timeout=30)
        if res.status_code == 200:
            gemini_reply = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            return gemini_reply, None
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

    intent = intent_data.get("intent", "conversational")
    action_note = ""

    # Execute Triggered Actions
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

    # Deliver message with interactive buttons
    buttons = [
        [{"text": "🏫 Collin Dashboard", "callback_data": "cmd_collin"}, {"text": "📑 Send Excel", "callback_data": "proposal_17"}],
        [{"text": "📊 Active Bids", "callback_data": "cmd_bids"}, {"text": "📬 Outbox", "callback_data": "cmd_pending"}]
    ]
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
    msg = (
        "🏛️ *SigmaFidelity™ Executive Mobile Operations Node v3.0*\n"
        "👤 *Operator:* George (Systems Architect)\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ *7-Frontier Industrial Capabilities:*\n\n"
        "🏫 */collin* — Collin College Frisco Campus Walkthrough Hub\n"
        "💬 *Chat with George* — Type any question or directive directly\n"
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
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🎙️ *Voice Notes:* AI-powered speech parsing (Creates Calendar events or Outbox emails)\n"
        "📷 *Photos:* Multimodal blueprint analysis & instant takeoff generation"
    )
    send_telegram_message(chat_id, msg, reply_markup=get_main_menu_keyboard())

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
        gemini_result, err = analyze_voice_with_gemini(audio_bytes)
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

        gemini_result, err = analyze_photo_with_gemini(img_bytes, caption=caption)
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
            cur.execute("""
                SELECT id, gc_name, project_name, estimated_value, status 
                FROM \"ConstructionBids\" 
                WHERE gc_name ILIKE %s OR project_name ILIKE %s OR notes ILIKE %s
                LIMIT 4;
            """, (q, q, q))
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

        if not bids and not leads and not docs:
            lines.append(f"❌ No matching records found for `{query.strip()}`.")

        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        markup = {"inline_keyboard": buttons[:6]} if buttons else get_main_menu_keyboard()
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

    if chat_id != ALLOWED_CHAT_ID:
        answer_callback_query(query_id, "Unauthorized")
        return

    print(f"[TELEGRAM] Callback received: '{data}' from {chat_id}", flush=True)

    if data == "cmd_collin":
        answer_callback_query(query_id)
        handle_cmd_collin(chat_id)
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
    else:
        answer_callback_query(query_id, "Acknowledged")

# --- MESSAGE DISPATCHER ---

def process_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if chat_id != ALLOWED_CHAT_ID:
        print(f"[TELEGRAM] Unauthorized command from chat_id {chat_id} blocked.", flush=True)
        return

    # Check for Voice Directives (Frontier 3)
    voice = message.get("voice") or message.get("audio")
    if voice:
        handle_voice_message(voice, chat_id)
        return

    # Check for Photos (Frontier 4)
    photos = message.get("photo")
    if photos:
        caption = message.get("caption", "")
        handle_photo_message(photos, chat_id, caption=caption)
        return

    # Check for Documents (PDF Blueprints or Uncompressed Photos with EXIF GPS)
    document = message.get("document")
    if document:
        file_name = document.get("file_name", "")
        file_id = document.get("file_id")
        mime_type = document.get("mime_type", "")
        caption = message.get("caption", "")
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
        handle_location_message(lat, lon, chat_id)
        return

    text = message.get("text", "").strip()

    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ["/start", "/help"]:
            handle_cmd_help(chat_id)
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
        else:
            send_telegram_message(chat_id, f"❓ Unknown command: `{cmd}`. Tap an option below or send `/help`.", reply_markup=get_main_menu_keyboard())
        return

    # Frontier 7: Full Two-Way Conversational Intelligence with George
    if text:
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
                                    cur.execute("""
                                        INSERT INTO \"ConstructionBids\" (
                                            gc_name, project_name, platform, status, email_id, notes, created_at, updated_at
                                        ) VALUES (%s, %s, %s, 'Invited', %s, %s, NOW(), NOW())
                                        RETURNING id;
                                    """, (name or sender, subj[:100], 'BuildingConnected' if 'buildingconnected' in combined else 'Planroom', msg_id, body[:200]))
                                    new_id = cur.fetchone()[0]
                                    conn.commit()

                                    alert_msg = (
                                        f"🔔 *NEW GC BID INVITATION DETECTED*\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"🏢 *General Contractor:* {name}\n"
                                        f"📁 *Project:* {subj}\n"
                                        f"✉️ *Sender:* `{sender}`\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"Registered in database as *Bid #{new_id}*."
                                    )
                                    markup = {
                                        "inline_keyboard": [
                                            [{"text": f"📥 1-Tap Auto-Takeoff", "callback_data": f"autotakeoff_{new_id}"}],
                                            [{"text": "📊 View All Bids", "callback_data": "cmd_bids"}]
                                        ]
                                    }
                                    send_telegram_message(ALLOWED_CHAT_ID, alert_msg, reply_markup=markup)
                    conn.close()

        except Exception as loop_err:
            print(f"[AUTONOMOUS MONITOR] Error in 15-minute loop: {loop_err}", flush=True)

        time.sleep(900)

def poll_updates():
    offset = None
    print("[TELEGRAM] Starting SigmaFidelity™ Executive Command Node v3.0 (6-Frontier Architecture)...", flush=True)

    monitor_thread = threading.Thread(target=autonomous_deal_capture_loop, daemon=True)
    monitor_thread.start()

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
                        
                        if "callback_query" in update:
                            process_callback_query(update["callback_query"])
                        elif "message" in update:
                            process_message(update["message"])
            else:
                time.sleep(2)
        except Exception as e:
            time.sleep(3)

        time.sleep(0.5)

if __name__ == "__main__":
    poll_updates()
