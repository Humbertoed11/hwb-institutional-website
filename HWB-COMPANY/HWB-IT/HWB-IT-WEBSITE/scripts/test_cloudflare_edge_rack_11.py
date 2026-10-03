#!/usr/bin/env python3
"""
⚡ SIGMAFIDELITY™ RACK 11: CLOUDFLARE EDGE TELEMETRY & WAF THREAT RADAR VERIFICATION SUITE
Standard: SO-COM-001-DIR-07 / HWB-QMS-11.2 / ARCH-013 Enterprise Command Hub
Lead Systems Architect: George Bytes (Tactical Builder & Lead Software Engineer)
"""

import os
import sys
import time
import unittest
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Ensure application paths are in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hwbdev:hwbpassword@127.0.0.1:5432/hwb_dev_db")
if "localhost" in DB_URL:
    DB_URL = DB_URL.replace("localhost", "127.0.0.1")


def get_db_connection():
    return psycopg2.connect(DB_URL)


class Rack11CloudflareEdgeTestSuite(unittest.TestCase):
    """
    Empirical Test Suite for Rack 11: Cloudflare Edge Telemetry & WAF Threat Radar.
    Verifies edge telemetry computation, 11-rack snapshot persistence, SQL integrity,
    and REST API delivery.
    """

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 80)
        print("⚡ SIGMAFIDELITY™ RACK 11: CLOUDFLARE EDGE & WAF THREAT RADAR TEST SUITE")
        print("   Mission Order: SO-COM-001-DIR-07 | Command Hub ARCH-013")
        print("=" * 80)

    def test_01_cloudflare_edge_telemetry_computation(self):
        """Verifies get_cloudflare_edge_telemetry returns 100% composite score and Grade A+."""
        from core.services.self_healing_engine import get_cloudflare_edge_telemetry

        telemetry = get_cloudflare_edge_telemetry(DB_URL)
        self.assertIsInstance(telemetry, dict)
        self.assertEqual(telemetry.get("status"), "HEALTHY")
        self.assertEqual(telemetry.get("status_tag"), "NOMINAL")
        self.assertEqual(telemetry.get("composite_score"), 100.0)
        self.assertEqual(telemetry.get("letter_grade"), "A+")
        self.assertEqual(telemetry.get("zone_name"), "hwbcleaning.com")

        # Edge Probe assertions
        edge_probe = telemetry.get("edge_probe", {})
        self.assertEqual(edge_probe.get("status_code"), 200)
        self.assertTrue(edge_probe.get("edge_healthy"))
        self.assertEqual(edge_probe.get("server"), "cloudflare")
        self.assertEqual(edge_probe.get("pop"), "DFW")
        self.assertGreater(telemetry.get("edge_latency_ms", 0), 0)

        # Origin Isolation Probe assertions
        origin_probe = telemetry.get("origin_isolation_probe", {})
        self.assertEqual(origin_probe.get("status_code"), 403)
        self.assertTrue(origin_probe.get("origin_blocked"))
        self.assertTrue(origin_probe.get("shield_active"))

        # Edge Settings assertions
        settings = telemetry.get("edge_settings", {})
        self.assertEqual(settings.get("ssl_mode"), "strict")
        self.assertEqual(settings.get("always_use_https"), "on")
        self.assertEqual(settings.get("browser_check"), "on")

        # Five Pillars assertions
        pillars = telemetry.get("five_pillars", {})
        self.assertIn("104.21.70.180", pillars.get("anycast_ip", ""))
        self.assertEqual(pillars.get("datacenter_pop"), "DFW")
        self.assertEqual(pillars.get("origin_firewall_cidrs"), 15)
        self.assertIn("BLOCKED (403)", pillars.get("direct_bypass_status", ""))
        print(" ✓ Test 01: Edge Telemetry computation verified (100% Score, Grade A+, PoP DFW).")

    def test_02_record_rack_telemetry_snapshot_11_racks(self):
        """Verifies record_rack_telemetry_snapshot ingests all 11 racks into RackTelemetryHistory."""
        from core.services.self_healing_engine import record_rack_telemetry_snapshot

        test_session_id = f"DIR-07-VERIFY-{int(time.time())}"
        result = record_rack_telemetry_snapshot(
            session_id=test_session_id,
            db_url=DB_URL,
            operator="George Bytes (Lead Engineer)"
        )
        self.assertEqual(result.get("status"), "success")
        self.assertEqual(result.get("racks_logged"), 11)
        self.assertEqual(result.get("session_id"), test_session_id)

        # Inspect database records
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT rack_number, rack_name, metric_category, score_value, secondary_value, status_tag, details_json
                FROM "RackTelemetryHistory"
                WHERE session_id = %s
                ORDER BY rack_number ASC;
            """, (test_session_id,))
            rows = cur.fetchall()

            self.assertEqual(len(rows), 11, f"Expected 11 racks, found {len(rows)}")
            rack_numbers = [r["rack_number"] for r in rows]
            self.assertEqual(rack_numbers, list(range(1, 12)), f"Sequence mismatch: {rack_numbers}")

            # Verify Rack 11 specifically
            rack_11 = rows[10]
            self.assertEqual(rack_11["rack_number"], 11)
            self.assertEqual(rack_11["rack_name"], "Cloudflare Edge Telemetry & WAF Threat Radar")
            self.assertEqual(rack_11["metric_category"], "EDGE_CLOUDFLARE")
            self.assertEqual(float(rack_11["score_value"]), 100.0)
            self.assertEqual(rack_11["status_tag"], "NOMINAL")
            self.assertIsInstance(rack_11["details_json"], dict)

        conn.close()
        print(f" ✓ Test 02: 11-Rack snapshot successfully committed to RackTelemetryHistory (Session: {test_session_id}).")

    def test_03_rack_11_sql_persistence_and_payload_integrity(self):
        """Verifies Rack 11 details_json payload contains complete edge, origin, and pillar data."""
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, session_id, rack_number, score_value, status_tag, details_json
                FROM "RackTelemetryHistory"
                WHERE rack_number = 11
                ORDER BY id DESC
                LIMIT 1;
            """)
            row = cur.fetchone()
            self.assertIsNotNone(row, "No Rack 11 record found in RackTelemetryHistory")
            self.assertEqual(row["rack_number"], 11)
            self.assertEqual(row["status_tag"], "NOMINAL")

            details = row["details_json"]
            self.assertIn("edge_probe", details)
            self.assertIn("origin_isolation_probe", details)
            self.assertIn("five_pillars", details)
            self.assertIn("edge_settings", details)

            self.assertEqual(details["edge_probe"]["status_code"], 200)
            self.assertEqual(details["origin_isolation_probe"]["status_code"], 403)
            self.assertTrue(details["origin_isolation_probe"]["shield_active"])

        conn.close()
        print(" ✓ Test 03: SQL payload integrity verified for Rack 11.")

    def test_04_rest_api_endpoint_cloudflare_telemetry(self):
        """Verifies GET /api/v1/it/telemetry/cloudflare returns valid JSON with 200 OK."""
        try:
            from main_app import app
            client = app.test_client()
            resp = client.get("/api/v1/it/telemetry/cloudflare")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data.get("status"), "success")
            self.assertIn("telemetry", data)
            t = data["telemetry"]
            self.assertEqual(t.get("composite_score"), 100.0)
            self.assertEqual(t.get("letter_grade"), "A+")
            self.assertEqual(t.get("status_tag"), "NOMINAL")
            print(" ✓ Test 04: REST API /api/v1/it/telemetry/cloudflare verified (HTTP 200 OK).")
        except Exception as e:
            # Fallback direct probe via local web container
            import requests
            r = requests.get("http://127.0.0.1:5000/api/v1/it/telemetry/cloudflare", timeout=5)
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data.get("status"), "success")
            self.assertEqual(data.get("telemetry", {}).get("composite_score"), 100.0)
            print(" ✓ Test 04: REST API verified via HTTP request (HTTP 200 OK).")


if __name__ == "__main__":
    unittest.main()
