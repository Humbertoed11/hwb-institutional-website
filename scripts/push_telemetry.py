import os
import json
import psycopg2
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load credentials
load_dotenv()
DB_URL = os.getenv('DATABASE_URL')

def push_telemetry(session_id, objective, last_action, next_step, heat_zone_files, technical_logic, operator="George"):
    """
    SigmaFidelity™ Tier 6 Tactical DB: Flight Data Recorder.
    """
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "SigmaTelemetry" 
                (session_id, objective, last_action, next_step, heat_zone_files, technical_logic, operator)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (session_id, objective, last_action, next_step, json.dumps(heat_zone_files), json.dumps(technical_logic), operator))
        conn.commit()
        conn.close()
        print(f"--- SigmaFidelity: Telemetry Pushed ({session_id}) ---")
    except Exception as e:
        print(f"--- SigmaFidelity: Telemetry FAILED: {e} ---")

def log_interaction(user_prompt, agent_explanation, tools_used, status="SUCCESS"):
    """
    SigmaFidelity™ Tier 6: High-Fidelity Interaction Logging.
    """
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "SigmaInteractionLog" 
                (user_prompt, agent_explanation, tools_used, status)
                VALUES (%s, %s, %s, %s)
            """, (user_prompt, agent_explanation, json.dumps(tools_used), status))
        conn.commit()
        conn.close()
        print("--- SigmaFidelity: Interaction Logged ---")
    except Exception as e:
        print(f"--- SigmaFidelity: Interaction Logging FAILED: {e} ---")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--log":
        # Usage: python push_telemetry.py --log "prompt" "explanation" '["tool1", "tool2"]'
        prompt = sys.argv[2] if len(sys.argv) > 2 else "N/A"
        expl = sys.argv[3] if len(sys.argv) > 3 else "N/A"
        tools = json.loads(sys.argv[4]) if len(sys.argv) > 4 else []
        log_interaction(prompt, expl, tools)
    else:
        # Default behavior: Push general telemetry
        push_telemetry(
            session_id="2026-05-20-LOGGING-ACTIVE",
            objective="Activate real-time CLI Interaction Logging.",
            last_action="Created SigmaInteractionLog table and updated push_telemetry utility.",
            next_step="Apply logging to every subsequent agent turn.",
            heat_zone_files=["scripts/push_telemetry.py"],
            technical_logic={"feature": "Interaction Persistence", "tier": 6}
        )
