#!/usr/bin/env python3
"""
SigmaFidelity™ Telegram Behavioral Insight & Pattern Detection Engine v1.0
Author: George (Systems Architect)
Standard: HWB-QMS-7.6 / Operational Minimization Mandate / Empirical Integrity Mandate
Governance: Executive Directive 2026-09-19 (CEO Humberto Dominguez)

Analyzes user interaction streams from Telegram to:
1. Map individual operational rhythms, peak active hours, and intent clusters.
2. Detect systemic friction, repeated inquiries, and workflow bottlenecks.
3. Synthesize qualitative behavioral profiles using Gemini 2.5 Flash.
4. Adapt the Telegram interface (custom keyboard layouts, George's persona, priority shortcuts).
"""

import os
import sys
import json
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if "@localhost" in DB_URL and os.path.exists("/.dockerenv"):
    DB_URL = DB_URL.replace("@localhost", "@db")

session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

def get_db_connection():
    try:
        return psycopg2.connect(DB_URL)
    except Exception:
        fallback_url = DB_URL.replace("@localhost", "@db").replace("@127.0.0.1", "@db")
        return psycopg2.connect(fallback_url)

def synthesize_with_gemini(user_meta: dict, stats: dict, recent_samples: list) -> dict:
    """
    Sends aggregated behavioral telemetry to Gemini 2.5 Flash
    to extract qualitative insights and system evolution directives.
    """
    if not GEMINI_API_KEY:
        return fallback_rule_based_synthesis(user_meta, stats)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
You are the SigmaFidelity™ Behavioral Analytics Engine for HWB Cleaning Services LLC.
Analyze this user's operational activity from Telegram and generate behavioral insights and UI adaptation directives.

USER CONTEXT:
- Name: {user_meta.get('full_name')}
- Username: {user_meta.get('username')}
- Role: {user_meta.get('user_role')}
- Total Interactions Recorded: {stats.get('total_events')}

QUANTITATIVE TELEMETRY:
- Event Types: {json.dumps(stats.get('event_types', {}))}
- Intent Distribution: {json.dumps(stats.get('intent_distribution', {}))}
- Active Hours (CST): {json.dumps(stats.get('active_hours', {}))}
- Top Actions Tapped: {json.dumps(stats.get('top_actions', []))}
- Friction Events Count: {stats.get('friction_count', 0)}

RECENT INTERACTION SAMPLES:
{json.dumps(recent_samples, indent=2)}

TASK:
Output a strict JSON object with NO markdown or commentary outside the JSON block:
{{
  "qualitative_summary": "2-3 crisp sentences summarizing their active operational focus, behavioral habits, and primary value contribution.",
  "friction_summary": "1-2 sentences on any friction, confusion, or unanswered questions detected (or 'Zero operational friction detected' if smooth).",
  "priority_modules": ["primary_domain", "secondary_domain"],
  "adaptive_preferences": {{
    "suggested_verbosity": "high_fidelity_concise" or "detailed_contextual",
    "recommended_home_buttons": [
      {{"text": "Button Label", "callback_data": "callback_cmd"}},
      {{"text": "Button Label 2", "callback_data": "callback_cmd_2"}}
    ],
    "evolutionary_macro": "Description of any repetitive sequence that can be converted to 1-tap"
  }}
}}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        res = session.post(url, json=payload, timeout=25)
        if res.status_code == 200:
            text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Clean possible markdown block
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
    except Exception as e:
        print(f"[BEHAVIORAL ENGINE] Gemini synthesis error: {e}", flush=True)

    return fallback_rule_based_synthesis(user_meta, stats)

def fallback_rule_based_synthesis(user_meta: dict, stats: dict) -> dict:
    """Deterministic fallback synthesis when LLM is unavailable."""
    role = (user_meta.get("user_role") or "Operator").lower()
    intents = stats.get("intent_distribution", {})
    
    # Check dominant intent
    dominant_intent = max(intents.items(), key=lambda x: x[1])[0] if intents else "general"

    if "exec" in role or user_meta.get("username") == "hdominguez":
        summary = "Executive oversight focus. High priority on daily briefing, commercial bid pricing, and outbox approvals."
        buttons = [
            {"text": "📊 Active Bids", "callback_data": "cmd_bids"},
            {"text": "📬 Pending Outbox", "callback_data": "cmd_pending"},
            {"text": "🏫 Collin College", "callback_data": "cmd_collin"},
            {"text": "🌅 Morning Briefing", "callback_data": "cmd_briefing"}
        ]
    elif "workforce" in dominant_intent or "operator" in role:
        summary = "Operations & workforce management focus. Prioritizes candidate screening, trade partner compliance, and field tasks."
        buttons = [
            {"text": "👥 Candidates Roster", "callback_data": "cmd_workforce"},
            {"text": "🤝 Trade Partners", "callback_data": "cmd_subcontractors"},
            {"text": "📊 Operations Status", "callback_data": "cmd_status"},
            {"text": "🔍 Search Database", "callback_data": "cmd_search_prompt"}
        ]
    else:
        summary = "General operational engagement across backoffice and field inquiries."
        buttons = [
            {"text": "📊 Status Pulse", "callback_data": "cmd_status"},
            {"text": "🔍 Search", "callback_data": "cmd_search_prompt"},
            {"text": "👥 Team", "callback_data": "cmd_users"},
            {"text": "ℹ️ Help", "callback_data": "cmd_help"}
        ]

    return {
        "qualitative_summary": summary,
        "friction_summary": "Heuristic baseline generated via rule-based engine.",
        "priority_modules": [dominant_intent, "general"],
        "adaptive_preferences": {
            "suggested_verbosity": "high_fidelity_concise",
            "recommended_home_buttons": buttons,
            "evolutionary_macro": None
        }
    }

def analyze_user_behavior(user_id: int, chat_id: int) -> dict:
    """
    Analyzes interaction stream for a single user and updates UserBehavioralProfiles.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Fetch user metadata
            cur.execute('SELECT id, username, full_name, role FROM "Users" WHERE id = %s;', (user_id,))
            user = cur.fetchone()
            if not user:
                user = {
                    "id": user_id,
                    "username": f"user_{chat_id}",
                    "full_name": f"Telegram User {chat_id}",
                    "role": "Team Member"
                }

            # 2. Fetch interaction events from TelegramEventStream
            cur.execute('''
                SELECT event_type, payload_summary, detected_intent, friction_flag, latency_ms, created_at
                FROM "TelegramEventStream"
                WHERE chat_id = %s OR user_id = %s
                ORDER BY created_at DESC
                LIMIT 150;
            ''', (chat_id, user_id))
            events = cur.fetchall()

            total_events = len(events)
            event_types = {}
            intent_distribution = {}
            active_hours = {"Morning (06-12)": 0, "Afternoon (12-17)": 0, "Evening (17-22)": 0, "Night (22-06)": 0}
            actions_counter = {}
            friction_count = 0
            friction_items = []
            recent_samples = []

            for ev in events:
                # Count event types
                etype = ev["event_type"]
                event_types[etype] = event_types.get(etype, 0) + 1

                # Count intents
                intent = ev["detected_intent"] or "general"
                intent_distribution[intent] = intent_distribution.get(intent, 0) + 1

                # Count hours
                if ev["created_at"]:
                    hr = ev["created_at"].hour
                    if 6 <= hr < 12:
                        active_hours["Morning (06-12)"] += 1
                    elif 12 <= hr < 17:
                        active_hours["Afternoon (12-17)"] += 1
                    elif 17 <= hr < 22:
                        active_hours["Evening (17-22)"] += 1
                    else:
                        active_hours["Night (22-06)"] += 1

                # Action counter
                payload = ev["payload_summary"] or ""
                if payload:
                    actions_counter[payload] = actions_counter.get(payload, 0) + 1

                # Friction
                if ev["friction_flag"]:
                    friction_count += 1
                    if len(friction_items) < 5:
                        friction_items.append({
                            "time": ev["created_at"].isoformat() if ev["created_at"] else "",
                            "payload": payload,
                            "intent": intent
                        })

                # Samples
                if len(recent_samples) < 10 and payload:
                    recent_samples.append({
                        "type": etype,
                        "intent": intent,
                        "content": payload[:120]
                    })

            # Sort top actions
            top_actions = sorted(actions_counter.items(), key=lambda x: x[1], reverse=True)[:5]
            top_actions_list = [{"action": k, "count": v} for k, v in top_actions]

            stats = {
                "total_events": total_events,
                "event_types": event_types,
                "intent_distribution": intent_distribution,
                "active_hours": active_hours,
                "top_actions": top_actions_list,
                "friction_count": friction_count
            }

            user_meta = {
                "user_id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "user_role": user["role"]
            }

            # 3. Synthesize via Gemini 2.5 Flash
            synthesis = synthesize_with_gemini(user_meta, stats, recent_samples)

            # 4. Upsert into UserBehavioralProfiles
            cur.execute('''
                INSERT INTO "UserBehavioralProfiles" (
                    user_id, chat_id, username, full_name, user_role, total_interactions,
                    interaction_habits, intent_distribution, top_actions, friction_log,
                    adaptive_preferences, qualitative_summary, last_analyzed_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
                )
                ON CONFLICT (user_id) DO UPDATE SET
                    chat_id = EXCLUDED.chat_id,
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    user_role = EXCLUDED.user_role,
                    total_interactions = EXCLUDED.total_interactions,
                    interaction_habits = EXCLUDED.interaction_habits,
                    intent_distribution = EXCLUDED.intent_distribution,
                    top_actions = EXCLUDED.top_actions,
                    friction_log = EXCLUDED.friction_log,
                    adaptive_preferences = EXCLUDED.adaptive_preferences,
                    qualitative_summary = EXCLUDED.qualitative_summary,
                    last_analyzed_at = CURRENT_TIMESTAMP;
            ''', (
                user["id"],
                chat_id,
                user["username"],
                user["full_name"],
                user["role"],
                total_events,
                Json({"active_hours": active_hours, "event_types": event_types}),
                Json(intent_distribution),
                Json(top_actions_list),
                Json(friction_items),
                Json(synthesis.get("adaptive_preferences", {})),
                synthesis.get("qualitative_summary", "")
            ))
            conn.commit()

            return {
                "user_id": user["id"],
                "full_name": user["full_name"],
                "role": user["role"],
                "total_events": total_events,
                "qualitative_summary": synthesis.get("qualitative_summary"),
                "friction_summary": synthesis.get("friction_summary"),
                "adaptive_preferences": synthesis.get("adaptive_preferences")
            }
    finally:
        conn.close()

def analyze_all_user_behaviors() -> list:
    """
    Executes behavioral analysis across all registered users in UserBehavioralProfiles.
    """
    conn = get_db_connection()
    users_to_process = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT user_id, chat_id FROM "UserBehavioralProfiles";')
            users_to_process = cur.fetchall()
    finally:
        conn.close()

    results = []
    for u in users_to_process:
        res = analyze_user_behavior(u["user_id"], u["chat_id"])
        results.append(res)
        print(f"[BEHAVIORAL ENGINE] Analyzed user {res['full_name']} ({res['role']}): {res['total_events']} events.", flush=True)

    return results

if __name__ == "__main__":
    print("=== SigmaFidelity™ Telegram Behavioral Insight & Pattern Detection Engine ===", flush=True)
    profiles = analyze_all_user_behaviors()
    print(f"✓ Analysis complete for {len(profiles)} team member profiles.", flush=True)
    for p in profiles:
        print(f"\n--- [{p['role']}] {p['full_name']} ---")
        print(f"Summary: {p['qualitative_summary']}")
        print(f"Adaptive Buttons: {p['adaptive_preferences'].get('recommended_home_buttons')}")
