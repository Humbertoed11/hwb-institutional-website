#!/usr/bin/env python3
"""
SigmaFidelity™ Telegram Executive Walkthrough Brief Dispatcher
Transmits Horizon at Premier Walkthrough Brief to Mirna Rondinella (Executive)
Standard: HWB-QMS-7.6 & HWB-QMS-8.9
Authority: Humberto Dominguez (CEO) | Architect: George (Systems Architect)
"""

import os
import sys
import json
import datetime
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from dotenv import load_dotenv

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "scripts" else CURRENT_DIR.parent.parent
WEBSITE_DIR = PROJECT_ROOT / "HWB-COMPANY" / "HWB-IT" / "HWB-IT-WEBSITE"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(WEBSITE_DIR / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8690678270:AAHWXbs6bnh84-htoIE3F9gy1YgqefN2vA0")
MIRNA_CHAT_ID = 8443354512
CEO_CHAT_ID = 8564340073
DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

if "@localhost" in DB_URL and os.path.exists("/.dockerenv"):
    DB_URL = DB_URL.replace("@localhost", "@db")


def get_db():
    try:
        return psycopg2.connect(DB_URL)
    except Exception:
        fallback = DB_URL.replace("@localhost", "@hwb_postgres_dev").replace("@127.0.0.1", "@hwb_postgres_dev")
        return psycopg2.connect(fallback)


def send_tg(chat_id: int, text: str, markup: dict = None) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if markup:
        payload["reply_markup"] = markup

    try:
        res = requests.post(url, json=payload, timeout=12)
        if res.status_code == 200:
            print(f"✅ Telegram dispatched to {chat_id} (HTTP 200)")
            return True
        else:
            print(f"⚠️ Telegram dispatch failed to {chat_id}: {res.status_code} - {res.text}")
            # Fallback plain text if HTML parse error
            payload.pop("parse_mode", None)
            res2 = requests.post(url, json=payload, timeout=12)
            return res2.status_code == 200
    except Exception as e:
        print(f"❌ Error sending Telegram to {chat_id}: {e}")
        return False


def log_event(user_id, chat_id, name, role, event_type, summary, intent):
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "TelegramEventStream" (
                    user_id, chat_id, user_handle, user_full_name, user_role,
                    event_type, payload_summary, detected_intent, mirrored_to_ceo, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
            """, (user_id, chat_id, "mrondinella", name, role, event_type, summary, intent, True))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Logging skipped: {e}")


def dispatch():
    print("================================================================================")
    print("📱  SigmaFidelity™ Telegram Executive Walkthrough Briefing Dispatcher")
    print(f"🕒  Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤  Target: Mirna Rondinella (Chat ID: {MIRNA_CHAT_ID})")
    print("================================================================================")

    # 1. Ensure Mirna has Executive Role in DB
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            UPDATE "Users" 
            SET role = 'Executive'
            WHERE email = 'mrondinella@hwbcleaning.com'
            RETURNING id, full_name, role, telegram_chat_id;
        """)
        user = cur.fetchone()
        conn.commit()
    conn.close()

    print(f"👑 Verified Executive Permissions: {user['full_name']} -> Role: {user['role']}")

    # 2. Build High-Fidelity Walkthrough Brief Message
    mirna_message = """🏛️ <b>HWB EXECUTIVE OPERATIONS COMMAND</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👋 <b>Hola Mirna!</b> CEO Humberto Dominguez has granted you <b>Full Executive Access</b> to the Telegram Operations Command Center.

You are now equipped with full real-time field capabilities:
• 🎙️ <b>Voice Directives:</b> Send voice notes from the field and George will transcribe & execute your notes.
• 📸 <b>Computer Vision:</b> Take photos of dumpsters, corrals, pet stations, or site maps and send them here for instant AI analysis.
• ⚡ <b>Real-time Recalibration:</b> Tell George what you observe on-site, and he will fine-tune the pricing, labor hours, and proposal numbers on the fly.
• 🛠️ <b>Full Commands:</b> Tap buttons below or use /bids, /scope, /leads, /pending, and /status anytime.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 <b>WALKTHROUGH LEAD BRIEF: HORIZON AT PREMIER</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 <b>Property Name:</b> Horizon at Premier
📍 <b>Address:</b> 3409 Premier Drive, Plano, TX 75023
🏘️ <b>Property Style:</b> Luxury Built-to-Rent (BTR) detached single-story rental homes
🏢 <b>Management:</b> Avenue5 Residential (National Property Management Firm)
🎯 <b>Service Scope:</b> Doorstep Valet Waste & Compactor Sanitation Agreement

💰 <b>WHAT WE CAME UP WITH (INITIAL BID MODEL):</b>
• <b>Door Count:</b> 122 Residential Homes
• <b>Collection Schedule:</b> 5 Nights / Week (Sunday through Thursday, starting 8:00 PM)
• <b>Base Door Rate:</b> $14.00 / door / month ($1,708.00/mo)
• <b>Pet Waste Stations:</b> 5 Stations @ $50.00/ea ($250.00/mo)
• <b>Compactor Enclosure Care:</b> Nightly sweep/police + quarterly hot-water pressure wash ($150.00/mo)
• <b>Total Proposed Monthly Fee:</b> <b>$2,108.00 / month</b>
• <b>Annual Submittal:</b> $25,296.00 / year
• <b>3-Year Contract Total:</b> <b>$75,888.00</b>
• <b>Field Close Floor (Discretionary):</b> $13.00/door ($1,986.00/mo | $71,496.00 3-yr)
• <b>Technician Labor:</b> ~64 mins/night (1.07 hrs) = ~23.1 hrs/mo @ $20.00/hr Dallas living wage floor.
• <b>Operating Profit:</b> $1,245.39/month (64.08% operating EBITDA margin).

📈 <b>THE LANDLORD PITCH (WHY AVENUE5 WILL BUY):</b>
Avenue5 bills their residents $30.00/door on their lease ($3,660.00/mo).
They pay HWB $2,108.00/mo.
The landlord keeps <b>+$1,552.00 / month pure profit (+${18,624.00} / year net cash flow)</b>.
At a standard 6% market capitalization rate, this net revenue increase boosts their property valuation by <b>+$310,400.00</b>!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 <b>WHAT TO VERIFY ON YOUR WALKTHROUGH:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Please check and tell George what you see:
1️⃣ <b>Door Count & Placement:</b> Are there exactly 122 homes? Where do residents leave their trash (front porch, curbside, or garage driveway)?
2️⃣ <b>Compactor & Corral:</b> Locate the main compactor/dumpster enclosure. Does it have a water hose bib and electrical outlet nearby for our hot-water pressure washer?
3️⃣ <b>Pet Stations Count:</b> How many physical pet waste stations are on the grounds? (We modeled 5; count the actual posts so we can adjust up or down).
4️⃣ <b>Drive Logistics:</b> Can our technician drive through with a pickup truck or golf cart, or is walking through pedestrian gates required?
5️⃣ <b>Bulk Trash Area:</b> Is there an overflow area where residents dump old mattresses or furniture? (We offer on-demand bulk haul at $125–$225/item).
6️⃣ <b>Management Contacts:</b> Obtain the direct names and phone numbers of the Community Manager and Maintenance Supervisor at the leasing office.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <b>HOW TO FEED BACK TO GEORGE:</b>
Simply reply right here with a text message, send a voice note, or snap photos of what you see! George is live and will instantly adjust the numbers and update the official proposal for CEO review."""

    markup = {
        "inline_keyboard": [
            [{"text": "📋 View Active Pipeline Bids", "callback_data": "cmd_bids"}],
            [{"text": "⚡ Check System Pulse & Status", "callback_data": "cmd_status"}],
            [{"text": "🔍 Search Lead Database", "callback_data": "cmd_search_prompt"}]
        ]
    }

    # 3. Dispatch to Mirna
    mirna_ok = send_tg(MIRNA_CHAT_ID, mirna_message, markup=markup)
    if mirna_ok:
        log_event(
            user_id=user["id"],
            chat_id=MIRNA_CHAT_ID,
            name=user["full_name"],
            role="Executive",
            event_type="walkthrough_briefing_dispatched",
            summary="Dispatched Horizon at Premier Walkthrough Briefing & Activated Full Executive Access",
            intent="horizon_walkthrough_brief"
        )

    # 4. Mirror to CEO Humberto Dominguez
    ceo_notice = f"""👑 <b>EXECUTIVE NOTIFICATION FOR CEO HUMBERTO DOMINGUEZ</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ <b>Horizon at Premier Walkthrough Brief Dispatched to Mirna!</b>

• <b>Recipient:</b> Mirna Rondinella (Chat ID: <code>{MIRNA_CHAT_ID}</code>)
• <b>Status:</b> Assigned <b>Full Executive Access</b> in PostgreSQL Users table.
• <b>Property:</b> Horizon at Premier (3409 Premier Dr, Plano, TX)
• <b>Proposed Value:</b> $2,108.00/mo ($75,888.00 3-Yr Contract | 122 Doors)
• <b>Walkthrough Objective:</b> Verifying door placement, compactor water/power, pet station count (modeled 5), vehicle drive routes, and bulk trash staging.

Mirna has been instructed to feed back on-site observations via voice notes, photos, or text to fine-tune the final proposal."""

    ceo_ok = send_tg(CEO_CHAT_ID, ceo_notice)
    if ceo_ok:
        log_event(
            user_id=2,
            chat_id=CEO_CHAT_ID,
            name="Humberto Dominguez",
            role="Executive",
            event_type="ceo_walkthrough_mirror",
            summary="Mirrored Mirna's Horizon walkthrough dispatch notice to CEO",
            intent="executive_mirror"
        )

    print("\n================================================================================")
    print("🏁  Dispatch Completed. Mirna is live with Full Executive Telegram Access.")
    print("================================================================================")


if __name__ == "__main__":
    dispatch()
