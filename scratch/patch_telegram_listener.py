import re
import sys

with open("scripts/telegram_listener.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add send_telegram_chat_action
chat_action_code = '''
def send_telegram_chat_action(chat_id, action="typing"):
    """Displays typing or document upload status in the Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendChatAction"
    try:
        session.post(url, json={"chat_id": chat_id, "action": action}, timeout=5)
    except Exception:
        pass
'''

if "def send_telegram_chat_action" not in content:
    target_pos = content.find("def send_telegram_document(")
    if target_pos != -1:
        content = content[:target_pos] + chat_action_code + "\n" + content[target_pos:]
        print("Added send_telegram_chat_action")

# 2. Update get_main_menu_keyboard
old_menu = '''def get_main_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📊 Active GC Bids", "callback_data": "cmd_bids"}, {"text": "📈 System Pulse", "callback_data": "cmd_status"}],'''

new_menu = '''def get_main_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🏫 Collin College Hub", "callback_data": "cmd_collin"}, {"text": "📑 Send Collin Excel", "callback_data": "proposal_17"}],
            [{"text": "📊 Active GC Bids", "callback_data": "cmd_bids"}, {"text": "📈 System Pulse", "callback_data": "cmd_status"}],'''

if old_menu in content:
    content = content.replace(old_menu, new_menu, 1)
    print("Updated get_main_menu_keyboard")

# 3. Update find_proposal_file to support Collin College
old_find = '''    combined = (str(project_name) + " " + str(gc_name)).lower()
    if "utsw" in combined or "microbiology" in combined:'''

new_find = '''    combined = (str(project_name) + " " + str(gc_name)).lower()
    if "collin" in combined or "frisco" in combined or "bosanna" in combined or str(bid_id) == "17":
        keywords = ["collin", "frisco", "bid-model"]
    elif "utsw" in combined or "microbiology" in combined:'''

if old_find in content:
    content = content.replace(old_find, new_find, 1)
    print("Updated find_proposal_file keywords")

# Also add fallback check in find_proposal_file
old_find_end = '''            for f in os.listdir(sdir):
                fl = f.lower()
                if any(k in fl for k in keywords) and fl.endswith(".xlsx"):
                    return os.path.join(sdir, f)
        except Exception:
            pass
    return None'''

new_find_end = '''            for f in os.listdir(sdir):
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
    return None'''

if old_find_end in content:
    content = content.replace(old_find_end, new_find_end, 1)
    print("Updated find_proposal_file end with explicit Collin fallback")

# 4. Inject COLLIN_COLLEGE_CONTEXT and Conversational AI
collin_context_block = '''
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
'''

if "COLLIN_COLLEGE_CONTEXT" not in content:
    target_pos = content.find("# --- GEMINI MULTIMODAL REASONING (VOICE & VISION) ---")
    if target_pos != -1:
        content = content[:target_pos] + collin_context_block + "\n" + content[target_pos:]
        print("Injected COLLIN_COLLEGE_CONTEXT")

# 5. Update analyze_voice_with_gemini
old_voice_prompt = '''    prompt = (
        "You are George, Systems Architect for HWB Cleaning Services LLC.\\n"
        "Listen to this executive voice memo from CEO Humberto Dominguez.\\n"
        "1. Transcribe the exact words spoken.\\n"
        "2. Identify the operational intent:\\n"
        "   - 'create_calendar_event': Humberto wants a meeting, site walkthrough, or appointment scheduled.\\n"
        "   - 'draft_email': Humberto wants an email, quote, or proposal prepared.\\n"
        "   - 'update_bid': Humberto wants to modify a bid price, status, or scope.\\n"
        "   - 'strategic_note': General directive, observation, or operational command.\\n"
        "3. Output MUST start with a JSON code block with fields:\\n"
        "```json\\n"
        "{\\"intent\\": \\"create_calendar_event\\"|\\"draft_email\\"|\\"update_bid\\"|\\"strategic_note\\", "
        "\\"title\\": \\"...\\", \\"recipient\\": \\"...\\", \\"date_time\\": \\"...\\", \\"summary\\": \\"...\\"}\\n"
        "```\\n"
        "Followed by a concise, authoritative executive briefing."
    )'''

new_voice_prompt = '''    prompt = (
        "You are George, Lead Systems Architect and Senior Estimator for HWB Cleaning Services LLC.\\n"
        "Listen to this executive voice memo from CEO Humberto Dominguez.\\n\\n"
        f"{COLLIN_COLLEGE_CONTEXT}\\n\\n"
        "1. Transcribe the exact words spoken.\\n"
        "2. Identify the operational intent:\\n"
        "   - 'create_calendar_event': Humberto wants a meeting, site walkthrough, or appointment scheduled.\\n"
        "   - 'draft_email': Humberto wants an email, quote, or proposal prepared.\\n"
        "   - 'send_proposal': Humberto wants the Collin College Excel model or bid proposal transmitted.\\n"
        "   - 'update_bid': Humberto wants to modify a bid price, status, or scope.\\n"
        "   - 'strategic_note': General directive, walkthrough observation, or operational command.\\n"
        "3. Output MUST start with a JSON code block with fields:\\n"
        "```json\\n"
        "{\\"intent\\": \\"create_calendar_event\\"|\\"draft_email\\"|\\"send_proposal\\"|\\"update_bid\\"|\\"strategic_note\\", "
        "\\"title\\": \\"...\\", \\"recipient\\": \\"...\\", \\"date_time\\": \\"...\\", \\"summary\\": \\"...\\", \\"bid_id\\": 17}\\n"
        "```\\n"
        "Followed by a concise, authoritative executive briefing with emojis and bold headers."
    )'''

if old_voice_prompt in content:
    content = content.replace(old_voice_prompt, new_voice_prompt, 1)
    print("Updated analyze_voice_with_gemini prompt")

# 6. Update analyze_photo_with_gemini
old_photo_func = '''def analyze_photo_with_gemini(image_bytes):
    """Uses Gemini 2.5 Flash Vision to extract blueprints, finish schedules, and site conditions."""
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY not configured."
    b64_img = base64.b64encode(image_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        "You are George, Senior Estimator and Systems Architect for HWB Cleaning Services LLC.\\n"
        "Analyze this construction blueprint sheet, finish schedule, or jobsite photo with industrial precision.\\n"
        "Extract:\\n"
        "1. 🏢 Document / Sheet Title & Project Name\\n"
        "2. 📏 Cleanable Footprint / Dimensions (Square Footage estimate)\\n"
        "3. 🧱 Floor Finish Breakdown (Sealed Concrete, VCT, Resinous Epoxy, Ceramic Tile, etc.)\\n"
        "4. 🧹 Construction Cleaning Scope (Rough clean, Final detail clean, debris level)\\n"
        "5. ⚠️ Empirical Discrepancies or ambiguities noticed\\n\\n"
        "Format your answer cleanly with bold headers for mobile display.\\n"
        "Include a final JSON code block at the bottom:\\n"
        "```json\\n"
        "{\\"project_name\\": \\"...\\", \\"estimated_sqft\\": 12000, \\"primary_floor\\": \\"...\\", \\"is_clinical\\": false}\\n"
        "```"
    )'''

new_photo_func = '''def analyze_photo_with_gemini(image_bytes, caption=""):
    """Uses Gemini 2.5 Flash Vision to extract blueprints, finish schedules, and site conditions."""
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY not configured."
    b64_img = base64.b64encode(image_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        "You are George, Lead Systems Architect and Senior Estimator for HWB Cleaning Services LLC.\\n"
        "Analyze this construction blueprint sheet, finish schedule, or jobsite photo taken by CEO Humberto Dominguez.\\n\\n"
        f"{COLLIN_COLLEGE_CONTEXT}\\n\\n"
        f"Context/Caption provided by CEO: \\"{caption or 'Collin College Frisco Campus Walkthrough'}\\"\\n\\n"
        "Provide a surgically precise industrial analysis:\\n"
        "1. 🏢 Building / Space & Substrate Identified (VCT, Terrazzo, Ceramic Tile, Carpet, Sealed Concrete)\\n"
        "2. 🔍 Condition & Wear Assessment (wax buildup, yellowing, grout discoloration, scratches, traffic lanes)\\n"
        "3. 🧹 Restorative Maintenance Scope Required (Tri-annual deep strip & 4-coat wax, diamond hone, Kaivac restroom wash, hot-water carpet extraction)\\n"
        "4. ⚠️ Forensic Discrepancies, Hidden Pitfalls, or Backcharge Risks against Incumbent (Pritchard Industries)\\n\\n"
        "Format cleanly with bold headers and emojis for mobile reading.\\n"
        "Conclude with a JSON block:\\n"
        "```json\\n"
        "{\\"project_name\\": \\"Collin College Walkthrough\\", \\"estimated_sqft\\": 15000, \\"primary_floor\\": \\"VCT/Terrazzo\\", \\"is_clinical\\": false}\\n"
        "```"
    )'''

if old_photo_func in content:
    content = content.replace(old_photo_func, new_photo_func, 1)
    print("Updated analyze_photo_with_gemini")

# 7. Add analyze_text_with_gemini function
text_analyzer_code = '''
def analyze_text_with_gemini(text, chat_id):
    """Conversational field intelligence for CEO Humberto Dominguez on Telegram."""
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY not configured.", None

    send_telegram_chat_action(chat_id, "typing")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    system_prompt = (
        "You are George, Lead Autonomous Systems Architect, Senior Estimator, Senior ISO 9001 Auditor, and Certified Lean Six Sigma Master Black Belt for HWB Cleaning Services LLC.\\n"
        "You are conversing directly in real-time with CEO Humberto Dominguez via Telegram during mobile operations and facility walkthroughs.\\n\\n"
        f"{COLLIN_COLLEGE_CONTEXT}\\n\\n"
        "OPERATIONAL RULES:\\n"
        "1. Strictly maintain a professional, authoritative tone. Use everyday words, bold headers, bullet points, and emojis suitable for mobile reading.\\n"
        "2. If Humberto asks questions about Collin College, pricing lines 41-48, staffing hours (904 hrs/wk), equipment, square footages, or janitorial math, provide exact, surgically specific figures.\\n"
        "3. If Humberto gives an operational directive, include an optional JSON block at the very start of your response:\\n"
        "```json\\n"
        "{\\n"
        '  "intent": "create_calendar_event" | "draft_email" | "send_proposal" | "conversational",\\n'
        '  "title": "...",\\n'
        '  "recipient": "...",\\n'
        '  "date_time": "...",\\n'
        '  "summary": "...",\\n'
        '  "bid_id": 17\\n'
        "}\\n"
        "```\\n"
        "4. Follow the JSON block with your crisp, high-impact executive response to Humberto."
    )

    payload = {
        "contents": [{
            "parts": [
                {"text": f"{system_prompt}\\n\\nCEO Humberto Dominguez says:\\n\\\"{text}\\\""}
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
    json_match = re.search(r'```json\\s*(\\{[\\s\\S]*?\\})\\s*```', gemini_reply)
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
        action_note = f"\\n\\n📅 *Outlook Action:* {msg}"
    elif intent == "draft_email":
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO \\"PendingOutbox\\" (recipient, subject, body, status, created_at)
                VALUES (%s, %s, %s, 'PENDING', NOW()) RETURNING id;
            """, (intent_data.get("recipient", "partner@domain.com"), intent_data.get("title", "Commercial Communication"), intent_data.get("summary", clean_reply)))
            new_out_id = cur.fetchone()[0]
            conn.commit()
        conn.close()
        action_note = f"\\n\\n📬 *Staged in Outbox:* Proposal #{new_out_id} created for 1-tap dispatch."
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
            """, (doc_id, f"USER: {text}\\nGEORGE: {clean_reply}", Json({"source": "Telegram Field Conversation", "chat_id": chat_id, "timestamp": datetime.now().isoformat()})))
        conn.commit()
        conn.close()
    except Exception as db_e:
        print(f"[TELEGRAM] Warning logging to sigma_kb: {db_e}", flush=True)

    # Deliver message with interactive buttons
    buttons = [
        [{"text": "🏫 Collin Dashboard", "callback_data": "cmd_collin"}, {"text": "📑 Send Excel", "callback_data": "proposal_17"}],
        [{"text": "📊 Active Bids", "callback_data": "cmd_bids"}, {"text": "📬 Outbox", "callback_data": "cmd_pending"}]
    ]
    full_msg = f"🏛️ *George (Systems Architect):*\\n━━━━━━━━━━━━━━━━━━━━━\\n{clean_reply}{action_note}"
    send_telegram_message(chat_id, full_msg, reply_markup={"inline_keyboard": buttons})
'''

if "def analyze_text_with_gemini" not in content:
    target_pos = content.find("# --- FRONTIER COMMAND & INTERACTION HANDLERS ---")
    if target_pos != -1:
        content = content[:target_pos] + text_analyzer_code + "\n" + content[target_pos:]
        print("Injected analyze_text_with_gemini and handle_text_conversation")

# 8. Add Collin College Hub Handlers
collin_hub_handlers = '''
def handle_cmd_collin(chat_id):
    """Collin College Frisco Campus Walkthrough Command Hub."""
    msg = (
        "🏫 *Collin College Frisco Campus — Master Operations Hub*\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        "🏢 *Footprint:* 10 Buildings | *478,418 Cleanable SF*\\n"
        "🕒 *Staffing:* 904.0 hrs/week (22.6 FTEs: 4 Porters M-F, 2 Sat, 12 Night, 1 Sup)\\n"
        "💼 *Subcontract Base:* *$104,518.00/mo* ($1,254,216.00/yr wholesale)\\n"
        "🏛️ *District Proposal:* *$124,426.19/mo* ($1,493,114.28/yr = $3.12/SF)\\n"
        "💰 *HWB Profit:* *$18,891.58/mo* Gross (18.1%) | *$14,291.58/mo* Net EBITDA\\n"
        "🤝 *Prime Partner:* Bosanna LLC (15% Prime Fee = $223,967.14/yr profit)\\n"
        "⏱️ *Audit:* Biometric Fingerprint Clock + Police Desk Sign-In Mandate\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        "Select a module below for instant field takeoff specs:"
    )
    buttons = [
        [{"text": "🏢 10 Building Takeoff", "callback_data": "collin_buildings"}, {"text": "🕒 Staffing & Shifts", "callback_data": "collin_staffing"}],
        [{"text": "🚜 Equipment Matrix", "callback_data": "collin_equipment"}, {"text": "💰 Pricing & Line Items", "callback_data": "collin_pricing"}],
        [{"text": "📑 Download Excel Model", "callback_data": "proposal_17"}, {"text": "📊 View All Bids", "callback_data": "cmd_bids"}]
    ]
    send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})

def handle_collin_buildings(chat_id):
    msg = (
        "🏢 *Collin College Frisco Campus — 10 Building Physical Takeoff*\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        "• *Founders Hall (F):* 92,105 SF | VCT/Terrazzo/Carpet | 32 Cls / 45 Off / 8 Rest (36 Fixt) | Porters 1 & 2\\n"
        "• *University Hall (U):* 84,320 SF | VCT/Carpet/Ceramic | 28 Cls / 50 Off / 7 Rest (32 Fixt) | Porters 1 & 2\\n"
        "• *Heritage Hall (H):* 78,450 SF | Terrazzo/VCT | 24 Cls / 40 Off / 6 Rest (28 Fixt) | Porter 3\\n"
        "• *Library & LRC (L):* 62,180 SF | 85% Carpet/VCT | 8 Cls / 25 Off / 4 Rest (18 Fixt) | Porter 4\\n"
        "• *Lawler Hall (J):* 48,260 SF | VCT/Carpet | 20 Cls / 18 Off / 4 Rest (18 Fixt) | Porter 4\\n"
        "• *Alumni Hall & PE (A):* 38,940 SF | Ceramic/Concrete | 4 Cls / 12 Off / 4 Rest (24 Fixt, 16 Showers, 180 Lockers) | Porter 4\\n"
        "• *Student Center (C):* 32,150 SF | Terrazzo/VCT | 6 Cls / 15 Off / 4 Rest (16 Fixt, Dining) | Porter 3\\n"
        "• *IT Infrastructure (IT):* 18,420 SF | Raised Tile/Carpet | 6 Cls / 10 Off / 2 Rest (8 Fixt) | Porter 3\\n"
        "• *Facilities Maint. (M):* 14,200 SF | Concrete | 4 Shops / 8 Off / 1 Rest (4 Fixt) | Rover\\n"
        "• *Campus Safety (S):* 9,393 SF | VCT/Carpet | 4 Off / 1 Rest (4 Fixt) | Police Desk & Clock\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
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
        "🕒 *Collin College Frisco Campus — Staffing & Shift Logistics*\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        "⏱️ *Mandated Staffing:* *904.0 Hours/Week* (22.6 FTEs | 23-25 Badged Personnel)\\n\\n"
        "☀️ *Day Porter Shifts (8:00 AM - 4:30 PM):*\\n"
        "• *Mon - Fri (4 Dedicated Porters):*\\n"
        "  - Porters 1 & 2: Founders + University (176k SF)\\n"
        "  - Porter 3: Heritage + Student Center + IT (129k SF)\\n"
        "  - Porter 4: Library + Lawler + Alumni Hall (173k SF)\\n"
        "• *Saturday (2 Dedicated Porters):* Campus-wide dual patrol (8:00 AM - 4:30 PM)\\n\\n"
        "🌙 *Night Production Shift (10:00 PM - 6:30 AM, 7 Nights/Wk):*\\n"
        "• *12 Dedicated Night Custodians:* Heavy production (136 classrooms/labs, 41 restroom banks deep sanitized, auto-scrubbers running).\\n"
        "• *1 Non-Cleaning Shift Supervisor:* Full-time quality control, audit logs, and walkthrough sweeps.\\n\\n"
        "🔒 *Security & Punch Audit Protocol:*\\n"
        "• Biometric cellular fingerprint time-clock at Central Staging.\\n"
        "• Mandatory physical sign-in & sign-out at Collin College Police desk (Bldg S).\\n"
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
        "🚜 *Collin College Frisco Campus — Dedicated Equipment Matrix*\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        "• *Founders Hall (F):* 28\\\" Riding Auto-Scrubber + 2000 RPM Burnisher (Stationed in F-102)\\n"
        "• *Heritage Hall (H):* 28\\\" Riding Auto-Scrubber + 2000 RPM Burnisher (Covers Student Hub & Concourse)\\n"
        "• *University Hall (U):* 20\\\" Walk-Behind Auto-Scrubber + 175 RPM Machine\\n"
        "• *Library & LRC (L):* Commercial Hot-Water Carpet Extractor + Backpack HEPA Vacs (Stationed in L-114)\\n"
        "• *Lawler Hall (J):* 20\\\" Walk-Behind Auto-Scrubber + Burnisher\\n"
        "• *Alumni Hall & PE (A):* Kaivac Touchless Restroom Cleaning Unit + 175 RPM Scrub Machine & Wet-Vac\\n"
        "• *Student Center (C):* 20\\\" Walk-Behind Scrubber + Heavy Degreasing Pads\\n"
        "• *IT Building (IT):* Anti-Static Cleanroom HEPA Canister Vac + Microfiber System\\n"
        "• *Facilities (M):* 20\\\" Walk-Behind Scrubber + Stripping Brushes; Central Compactor Station\\n"
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
        "💰 *Collin College Frisco Campus — Financial Underwriting & Rates*\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        "📊 *Base Scheduled Contract (Scenario A):*\\n"
        "• *Line 41 (Scheduled Labor - 904 hrs/wk):*\\n"
        "  - HWB Wholesale: *$96,943.00/mo* ($1,163,316.00/yr)\\n"
        "  - District Submittal: *$115,405.69/mo* ($1,384,868.28/yr)\\n"
        "• *Line 42 (Consumable Supplies Passthrough):*\\n"
        "  - HWB Wholesale: *$7,575.00/mo* ($90,900.00/yr)\\n"
        "  - District Submittal: *$9,020.50/mo* ($108,246.00/yr)\\n"
        "━━━━━━━━━━━━━━━━━━━━━\\n"
        "💼 *TOTAL HWB WHOLESALE:* *$104,518.00/mo* (*$1,254,216.00/yr*)\\n"
        "🤝 *Bosanna Prime Margin (15%):* *$18,663.93/mo* (*$223,967.14/yr*)\\n"
        "🏛️ *TOTAL DISTRICT PROPOSAL:* *$124,426.19/mo* (*$1,493,114.28/yr* = *$3.12/SF*)\\n"
        "💵 *HWB Net EBITDA Profit:* *$14,291.58/mo* (*$171,498.91/yr* = 13.67%)\\n\\n"
        "⚡ *Unscheduled Hourly & Restorative Rates:*\\n"
        "• Line 43 (M-F Unscheduled): *$28.50/hr* wholesale ($33.94 submittal)\\n"
        "• Line 44 (Saturday Unscheduled): *$32.00/hr* wholesale ($38.10 submittal)\\n"
        "• Line 45 (Sunday/Holidays): *$38.00/hr* wholesale ($45.24 submittal)\\n"
        "• Line 46 (Tile Strip & Wax): *$0.25/SF* wholesale ($0.298/SF submittal)\\n"
        "• Line 47 (Carpet Hot-Water Extract): *$0.28/SF* wholesale ($0.333/SF submittal)\\n"
        "• Line 48 (Add/Deduct Rate): *$2.62/SF/yr* wholesale ($3.120/SF/yr submittal)"
    )
    buttons = [
        [{"text": "🏢 10 Buildings", "callback_data": "collin_buildings"}, {"text": "🕒 Staffing & Shifts", "callback_data": "collin_staffing"}],
        [{"text": "🚜 Equipment", "callback_data": "collin_equipment"}, {"text": "📑 Send Excel", "callback_data": "proposal_17"}],
        [{"text": "⬅️ Back to Collin Hub", "callback_data": "cmd_collin"}]
    ]
    send_telegram_message(chat_id, msg, reply_markup={"inline_keyboard": buttons})
'''

if "def handle_cmd_collin" not in content:
    target_pos = content.find("def handle_cmd_help(chat_id):")
    if target_pos != -1:
        content = content[:target_pos] + collin_hub_handlers + "\n" + content[target_pos:]
        print("Injected Collin Hub Handlers")

# 9. Update handle_cmd_help
old_help_desc = '''        "⚡ *6-Frontier Industrial Capabilities:*\\n\\n"
        "📊 */bids* — Active GC bids, takeoffs & live pipeline\\n"'''

new_help_desc = '''        "⚡ *7-Frontier Industrial Capabilities:*\\n\\n"
        "🏫 */collin* — Collin College Frisco Campus Walkthrough Hub\\n"
        "💬 *Chat with George* — Type any question or directive directly\\n"
        "📊 */bids* — Active GC bids, takeoffs & live pipeline\\n"'''

if old_help_desc in content:
    content = content.replace(old_help_desc, new_help_desc, 1)
    print("Updated handle_cmd_help")

# 10. Update handle_photo_message to accept caption
old_photo_msg_head = '''def handle_photo_message(photo_list, chat_id):
    """Frontier 4: Multimodal Blueprint & Jobsite Photo Computer Vision."""
    best_photo = photo_list[-1]
    file_id = best_photo.get("file_id")

    send_telegram_message(chat_id, "📷 *Analyzing Drawing / Jobsite Photo with Gemini 2.5 Flash Vision*...")'''

new_photo_msg_head = '''def handle_photo_message(photo_list, chat_id, caption=""):
    """Frontier 4: Multimodal Blueprint & Jobsite Photo Computer Vision."""
    best_photo = photo_list[-1]
    file_id = best_photo.get("file_id")

    send_telegram_chat_action(chat_id, "typing")
    send_telegram_message(chat_id, "📷 *Analyzing Jobsite Photo with Gemini 2.5 Flash Vision*...")'''

if old_photo_msg_head in content:
    content = content.replace(old_photo_msg_head, new_photo_msg_head, 1)
    print("Updated handle_photo_message header")

# Update photo saving logic inside handle_photo_message
old_photo_save = '''        # Save incoming photo archive to disk
        try:
            photo_dir = "/app/logs/incoming_photos" if os.path.exists("/.dockerenv") else os.path.join(BASE_DIR, "logs", "incoming_photos")
            os.makedirs(photo_dir, exist_ok=True)
            t_str = datetime.now().strftime("%Y%m%d-%H%M%S")
            fname = f"photo_{t_str}_{os.path.basename(file_path or 'image.jpg')}"
            with open(os.path.join(photo_dir, fname), "wb") as pf:
                pf.write(img_bytes)

            quote_dir = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-QUOTES/BOSANNA-COLLIN-COLLEGE"
            if os.path.exists(quote_dir):
                with open(os.path.join(quote_dir, f"telegram_upload_{t_str}.jpg"), "wb") as qf:
                    qf.write(img_bytes)
        except Exception as save_err:
            print(f"[TELEGRAM] Warning saving photo: {save_err}", flush=True)

        gemini_result, err = analyze_photo_with_gemini(img_bytes)'''

new_photo_save = '''        # Extract building tag from caption if present
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

        gemini_result, err = analyze_photo_with_gemini(img_bytes, caption=caption)'''

if old_photo_save in content:
    content = content.replace(old_photo_save, new_photo_save, 1)
    print("Updated photo saving logic")

# 11. Update process_callback_query to handle Collin callbacks
old_cb_start = '''    if data == "cmd_bids":
        answer_callback_query(query_id)
        handle_cmd_bids(chat_id)'''

new_cb_start = '''    if data == "cmd_collin":
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
    elif data == "proposal_17":
        handle_action_send_proposal(chat_id, 17, callback_id=query_id)
    elif data == "cmd_bids":
        answer_callback_query(query_id)
        handle_cmd_bids(chat_id)'''

if old_cb_start in content:
    content = content.replace(old_cb_start, new_cb_start, 1)
    print("Updated process_callback_query")

# 12. Update process_message for /collin, photo caption, and text conversation
old_msg_photos = '''    # Check for Photos (Frontier 4)
    photos = message.get("photo")
    if photos:
        handle_photo_message(photos, chat_id)
        return'''

new_msg_photos = '''    # Check for Photos (Frontier 4)
    photos = message.get("photo")
    if photos:
        caption = message.get("caption", "")
        handle_photo_message(photos, chat_id, caption=caption)
        return'''

if old_msg_photos in content:
    content = content.replace(old_msg_photos, new_msg_photos, 1)
    print("Updated process_message photos caption")

old_cmd_routing = '''        if cmd in ["/start", "/help"]:
            handle_cmd_help(chat_id)'''

new_cmd_routing = '''        if cmd in ["/start", "/help"]:
            handle_cmd_help(chat_id)
        elif cmd in ["/collin", "/walkthrough", "/frisco"]:
            handle_cmd_collin(chat_id)'''

if old_cmd_routing in content:
    content = content.replace(old_cmd_routing, new_cmd_routing, 1)
    print("Updated cmd routing for /collin")

# Replace plain text handler with conversational AI
old_text_block = '''    # Plain text strategic note
    if text:
        send_telegram_message(chat_id, "George: Storing executive strategic note in SQL brain...")
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        doc_id = f"telegram-note-{timestamp_str}"
        metadata = {"source": "Telegram Text Note", "chat_id": chat_id, "timestamp": datetime.now().isoformat()}
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sigma_kb (doc_id, content, metadata)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET content = EXCLUDED.content, metadata = EXCLUDED.metadata;
                """, (doc_id, text, Json(metadata)))
            conn.commit()
            conn.close()
            send_telegram_message(chat_id, f"George: Note successfully stored in brain. Doc ID: `{doc_id}`", reply_markup=get_main_menu_keyboard())
        except Exception as e:
            send_telegram_message(chat_id, f"George: Note ingestion error: {e}")'''

new_text_block = '''    # Frontier 7: Full Two-Way Conversational Intelligence with George
    if text:
        handle_text_conversation(text, chat_id)'''

if old_text_block in content:
    content = content.replace(old_text_block, new_text_block, 1)
    print("Replaced static text note with handle_text_conversation")

with open("scripts/telegram_listener.py", "w", encoding="utf-8") as f:
    f.write(content)

print("SUCCESS: scripts/telegram_listener.py upgraded.")
