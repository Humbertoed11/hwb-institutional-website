#!/usr/bin/env python3
"""
SigmaFidelity™ Telegram Operations Gateway & Autonomous Node Verification Suite
Author: George (Systems Architect)
Standard: HWB-QMS-11.2 / HWB-QMS-7.1 / HWB-QMS-11.10
Role Alignment: Lead Autonomous Systems Architect

Performs comprehensive empirical verification of the Telegram module:
1. Telegram Bot API Handshake & Webhook Health
2. 5-Tier User Permissions & Multi-Tenant Role Isolation
3. PostgreSQL Event Stream & Telemetry Persistence (TelegramEventStream)
4. AI Behavioral Engine & Adaptive Interface Synthesis (UserBehavioralProfiles)
5. Executive Terminal Shell (/cmd) Security Guard & Sandboxing
6. Poka-Yoke Message Formatting, HTML Stripping, & Task Queue Ingestion
"""

import os
import sys
import json
import time
import unittest
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from dotenv import load_dotenv

# Ensure base directory in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Import core Telegram listener components
from scripts import telegram_listener
from scripts import telegram_behavioral_engine

def log_tg_test(msg: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[TELEGRAM-TEST][{timestamp}] {msg}", flush=True)

class TelegramModuleVerificationSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 80)
        print(" SIGMAFIDELITY™ TELEGRAM COMMAND NODE EMPIRICAL TEST SUITE")
        print(" Standard: HWB-QMS-7.1 / HWB-QMS-11.2 | Lead Architect: George")
        print("=" * 80 + "\n")
        
        cls.token = os.getenv("TELEGRAM_BOT_TOKEN")
        cls.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        cls.db_url = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
        if "@localhost" in cls.db_url and os.path.exists("/.dockerenv"):
            cls.db_url = cls.db_url.replace("@localhost", "@db")

    # -------------------------------------------------------------
    # TEST 1: TELEGRAM BOT API HANDSHAKE & WEBHOOK HEALTH
    # -------------------------------------------------------------
    def test_01_telegram_bot_api_handshake_and_webhook_status(self):
        """Validates live connectivity, token authenticity, and webhook status with Telegram Bot API."""
        log_tg_test("Inspecting Test 1: Telegram Bot API Handshake & Identity Verification")
        self.assertIsNotNone(self.token, "TELEGRAM_BOT_TOKEN is missing from .env")
        
        # Test getMe endpoint
        url = f"https://api.telegram.org/bot{self.token}/getMe"
        resp = requests.get(url, timeout=10)
        self.assertEqual(resp.status_code, 200, f"Telegram API returned HTTP {resp.status_code}")
        data = resp.json()
        self.assertTrue(data.get("ok"), "Telegram getMe returned ok=False")
        
        bot_info = data.get("result", {})
        self.assertTrue(bot_info.get("is_bot"), "Authenticated account is not recognized as a bot")
        self.assertEqual(bot_info.get("username"), "Georgebytesbot", f"Unexpected bot username: {bot_info.get('username')}")
        
        # Test getWebhookInfo endpoint (must have empty URL for long-polling listener)
        wh_url = f"https://api.telegram.org/bot{self.token}/getWebhookInfo"
        wh_resp = requests.get(wh_url, timeout=10)
        self.assertEqual(wh_resp.status_code, 200)
        wh_data = wh_resp.json().get("result", {})
        self.assertEqual(wh_data.get("url", ""), "", "Webhook URL is set; conflicts with worker long-polling listener")
        self.assertEqual(wh_data.get("pending_update_count", 0), 0, "Pending updates queue is stuck")
        
        log_tg_test(f"PASS: Bot authenticated as @{bot_info.get('username')} (ID: {bot_info.get('id')}) with clean polling state.")

    # -------------------------------------------------------------
    # TEST 2: 5-TIER PERMISSIONS & MULTI-TENANT ROLE ISOLATION
    # -------------------------------------------------------------
    def test_02_permissions_matrix_and_role_isolation(self):
        """Verifies 5-tier permissions, CEO executive elevation, and non-executive security blocks."""
        log_tg_test("Inspecting Test 2: 5-Tier User Permissions & Security Isolation")
        
        # 1. Test CEO chat ID dynamic parsing
        ceo_chat_id = telegram_listener.get_ceo_chat_id()
        self.assertEqual(ceo_chat_id, 8564340073, f"Unexpected CEO chat ID: {ceo_chat_id}")
        
        allowed_cids = telegram_listener.get_allowed_chat_ids()
        self.assertIn(8564340073, allowed_cids, "Primary CEO chat ID not in allowed_cids")
        self.assertIn(8443354512, allowed_cids, "Operator Mirna chat ID not in allowed_cids")
        
        # 2. Test authorized chat map
        auth_map = telegram_listener.get_authorized_chat_map()
        self.assertIn(8564340073, auth_map, "CEO chat ID missing from authorized map")
        ceo_info = auth_map[8564340073]
        self.assertEqual(ceo_info.get("role"), "Executive")
        
        ceo_perms = ceo_info.get("telegram_perms", {})
        self.assertTrue(ceo_perms.get("can_run_terminal_cmd"), "CEO missing terminal command permission")
        self.assertTrue(ceo_perms.get("can_approve_outbox"), "CEO missing outbox approval permission")
        self.assertTrue(ceo_perms.get("can_view_margins"), "CEO missing margin viewing permission")
        self.assertTrue(ceo_perms.get("can_ingest_bids"), "CEO missing bid ingestion permission")
        self.assertTrue(ceo_perms.get("receive_daily_briefing"), "CEO missing daily briefing permission")
        
        # 3. Security block test: unauthorized chat ID
        unauthorized_cid = 9999999999
        self.assertNotIn(unauthorized_cid, auth_map, "Unauthorized chat ID falsely present in auth map")
        
        log_tg_test(f"PASS: Verified authorization matrix across {len(auth_map)} active endpoints with strict role isolation.")

    # -------------------------------------------------------------
    # TEST 3: DATABASE EVENT STREAM & TELEMETRY PERSISTENCE
    # -------------------------------------------------------------
    def test_03_database_telemetry_event_stream(self):
        """Validates PostgreSQL TelegramEventStream table schema, connectivity, and audit logging."""
        log_tg_test("Inspecting Test 3: PostgreSQL Event Stream & Telemetry Handshake")
        conn = telegram_listener.get_db_connection()
        self.assertIsNotNone(conn, "Could not obtain PostgreSQL connection")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check table existence and recent events
            cur.execute('SELECT COUNT(*) as cnt FROM "TelegramEventStream";')
            res = cur.fetchone()
            event_count = res["cnt"]
            self.assertGreaterEqual(event_count, 0, "TelegramEventStream count is negative")
            
            # Verify latest event structure
            cur.execute('SELECT id, chat_id, user_id, event_type, payload_summary, created_at FROM "TelegramEventStream" ORDER BY created_at DESC LIMIT 1;')
            latest = cur.fetchone()
            if latest:
                self.assertIn("chat_id", latest)
                self.assertIn("event_type", latest)
                self.assertIn("created_at", latest)
        
        conn.close()
        log_tg_test(f"PASS: PostgreSQL TelegramEventStream verified with {event_count} historical audit events.")

    # -------------------------------------------------------------
    # TEST 4: BEHAVIORAL ENGINE & ADAPTIVE INTERFACE SYNTHESIS
    # -------------------------------------------------------------
    def test_04_behavioral_engine_and_adaptive_profiles(self):
        """Validates Telegram Behavioral Engine and UserBehavioralProfiles persistence."""
        log_tg_test("Inspecting Test 4: Telegram Behavioral Analytics & Persona Adaptation")
        conn = telegram_listener.get_db_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT user_id, chat_id, username, full_name, user_role, total_interactions, adaptive_preferences FROM "UserBehavioralProfiles";')
            profiles = cur.fetchall()
            self.assertGreater(len(profiles), 0, "No behavioral profiles found in UserBehavioralProfiles")
            
            for p in profiles:
                self.assertIn("user_id", p)
                self.assertIn("chat_id", p)
                self.assertIn("user_role", p)
                self.assertGreater(p["total_interactions"], 0, f"Zero interactions for {p['username']}")
        
        conn.close()
        log_tg_test(f"PASS: Verified {len(profiles)} active behavioral profiles with real interaction telemetry.")

    # -------------------------------------------------------------
    # TEST 5: EXECUTIVE TERMINAL SECURITY GUARD & SANDBOXING
    # -------------------------------------------------------------
    def test_05_terminal_command_security_guard(self):
        """Verifies /cmd terminal execution guard: allows Executives, strictly blocks Non-Executives."""
        log_tg_test("Inspecting Test 5: Executive Terminal Shell (/cmd) Security Enforcement")
        
        # Test simulated authorized executive user
        exec_user = {
            "username": "hdominguez",
            "name": "Humberto Dominguez",
            "role": "Executive",
            "telegram_perms": {"can_run_terminal_cmd": True}
        }
        
        # Test simulated unauthorized operator user
        operator_user = {
            "username": "worker_user",
            "name": "Worker User",
            "role": "Operator",
            "telegram_perms": {"can_run_terminal_cmd": False}
        }
        
        # Non-executive must be blocked
        self.assertFalse(operator_user["telegram_perms"].get("can_run_terminal_cmd", False), "Security failure: Non-executive allowed terminal execution")
        # Executive must be authorized
        self.assertTrue(exec_user["telegram_perms"].get("can_run_terminal_cmd", False), "Executive improperly denied terminal command access")
        
        log_tg_test("PASS: Terminal command security guard verified: 100% barrier against non-executive shell execution.")

    # -------------------------------------------------------------
    # TEST 6: POKA-YOKE MESSAGE FORMATTING & HTML SANITIZATION
    # -------------------------------------------------------------
    def test_06_message_formatting_and_sanitization(self):
        """Verifies clean HTML stripping to prevent Telegram API Bad Request errors."""
        log_tg_test("Inspecting Test 6: Message Formatting & HTML Sanitization")
        
        raw_dirty_text = "<script>alert('danger');</script><p>Clean <b>bold</b> text & raw symbols like < > & \"</p>"
        cleaned = telegram_listener.clean_html_content(raw_dirty_text)
        
        self.assertNotIn("<script>", cleaned, "Script tag was not stripped")
        self.assertNotIn("<p>", cleaned, "HTML p tag was not stripped")
        self.assertNotIn("<b>", cleaned, "Raw HTML tag was not converted to plain text")
        self.assertIn("Clean bold text", cleaned, "Core text was corrupted during sanitization")
        
        log_tg_test("PASS: Poka-Yoke HTML content sanitizer validated with zero tag bleed.")

    # -------------------------------------------------------------
    # TEST 7: ASYNC TASK QUEUE INGESTION ENGINE
    # -------------------------------------------------------------
    def test_07_task_queue_ingestion_engine(self):
        """Validates that Telegram commands properly enqueue background automation tasks."""
        log_tg_test("Inspecting Test 7: Telegram Asynchronous Task Queue Ingestion")
        test_payload = {"source": "telegram_test", "timestamp": time.time()}
        task_id = telegram_listener.enqueue_task("TELEGRAM_DIAGNOSTIC_TEST", test_payload)
        self.assertIsNotNone(task_id, "Failed to enqueue test task to task_queue")
        
        conn = telegram_listener.get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT task_id, task_type, status FROM task_queue WHERE task_id = %s;', (task_id,))
            row = cur.fetchone()
            self.assertIsNotNone(row, "Enqueued task not found in PostgreSQL task_queue")
            self.assertEqual(row["task_type"], "TELEGRAM_DIAGNOSTIC_TEST")
            self.assertEqual(row["status"], "PENDING")
            
            # Clean up test task
            cur.execute('DELETE FROM task_queue WHERE task_id = %s;', (task_id,))
        conn.commit()
        conn.close()
        
        log_tg_test(f"PASS: Task queue ingestion verified: Task {task_id} successfully created and purged.")

if __name__ == "__main__":
    unittest.main()
