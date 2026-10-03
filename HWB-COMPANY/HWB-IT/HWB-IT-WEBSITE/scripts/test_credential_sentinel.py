#!/usr/bin/env python3
"""
⚡ SIGMAFIDELITY™ CREDENTIAL & SECRET EXPIRY SENTINEL VERIFICATION SUITE
Standard: SO-COM-001-DIR-09 / Mandate 12
Rack 4: Azure & Cloud Gateway Infrastructure
Lead Software Engineer: George Bytes (Tactical Builder)
Reporting to: Super George & CEO Humberto Dominguez

Empirical Test Suite for Credential & Secret Expiry Sentinel:
1. Full 8-credential inventory completeness
2. Health score and fleet metric accuracy (87.5% Grade B+)
3. Integration with Rack 4 telemetry in self_healing_engine
4. CLI standalone tool execution and JSON payload delivery
5. Expired key detection and remediation alert verification
"""

import os
import sys
import subprocess
import json
import unittest

# Ensure application paths are in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if os.path.exists("/app/core/services/credential_sentinel.py") and "/app" not in sys.path:
    sys.path.insert(0, "/app")

from core.services.credential_sentinel import audit_all_credentials
from core.services.self_healing_engine import get_cloud_gateway_telemetry


class CredentialSentinelTestSuite(unittest.TestCase):
    """
    Empirical Test Suite for SO-COM-001-DIR-09 Credential Expiry Sentinel.
    """

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 80)
        print("⚡ SIGMAFIDELITY™ CREDENTIAL & SECRET EXPIRY SENTINEL TEST SUITE")
        print("   Mission Order: SO-COM-001-DIR-09 | Rack 4: Azure & Cloud Gateway")
        print("=" * 80)

    def test_01_credential_inventory_completeness(self):
        """Verifies audit_all_credentials monitors all 8 external credentials with required schema."""
        results = audit_all_credentials()
        self.assertIsInstance(results, dict)
        self.assertEqual(results.get("status"), "success")
        self.assertIn("timestamp", results)

        creds = results.get("credentials", [])
        self.assertEqual(len(creds), 8, f"Expected 8 credentials, found {len(creds)}")

        expected_names = {
            "Microsoft Graph Secret",
            "Cloudflare API Token",
            "Telegram Bot Token",
            "Edge SSL Certificate",
            "GitHub Access Token",
            "Google Maps API Key",
            "Gemini AI API Key",
            "LinkedIn OAuth Secret"
        }
        found_names = {c.get("name") for c in creds}
        self.assertEqual(found_names, expected_names, "Mismatch in expected credential names")

        for c in creds:
            for required_field in ["name", "service", "type", "configured", "expiry_date", "days_remaining", "status", "badge", "action_required", "notes"]:
                self.assertIn(required_field, c, f"Credential {c.get('name')} missing field {required_field}")

        print("  ✓ Test 01 Passed: All 8 external credentials audited with complete schema.")

    def test_02_health_score_and_metrics_calculation(self):
        """Verifies fleet health score calculation (7 healthy / 8 monitored = 87.5% Grade B+)."""
        results = audit_all_credentials()
        self.assertEqual(results.get("credentials_monitored_count"), 8)
        self.assertEqual(results.get("credentials_healthy_count"), 7)
        self.assertEqual(results.get("credentials_action_required"), 1)
        self.assertEqual(results.get("health_score"), 87.5)
        self.assertEqual(results.get("letter_grade"), "B+")
        print("  ✓ Test 02 Passed: Fleet metrics correctly computed (87.5% Grade B+, 7 healthy, 1 action required).")

    def test_03_rack_4_integration(self):
        """Verifies get_cloud_gateway_telemetry embeds credential sentinel telemetry in Rack 4."""
        gateway = get_cloud_gateway_telemetry()
        self.assertIsInstance(gateway, dict)
        self.assertIn("credential_sentinel", gateway)
        self.assertIn("credential_health_score", gateway)
        self.assertIn("credentials_monitored_count", gateway)
        self.assertIn("credentials_healthy_count", gateway)
        self.assertIn("credentials_action_required", gateway)

        self.assertEqual(gateway.get("credentials_monitored_count"), 8)
        self.assertEqual(gateway.get("credentials_healthy_count"), 7)
        self.assertEqual(gateway.get("credentials_action_required"), 1)
        self.assertEqual(gateway.get("credential_health_score"), 87.5)
        self.assertEqual(gateway.get("credential_letter_grade"), "B+")
        print("  ✓ Test 03 Passed: Rack 4 Cloud Gateway correctly integrates Credential Sentinel telemetry.")

    def test_04_cli_tool_execution(self):
        """Verifies CLI tool scripts/check_credential_expiry.py --json executes and returns valid JSON."""
        cli_path = os.path.join(BASE_DIR, "scripts", "check_credential_expiry.py")
        if not os.path.exists(cli_path):
            cli_path = "/app/scripts/check_credential_expiry.py"

        result = subprocess.run([sys.executable, cli_path, "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"CLI exited with error: {result.stderr}")

        cli_json = json.loads(result.stdout)
        self.assertEqual(cli_json.get("credentials_monitored_count"), 8)
        self.assertEqual(cli_json.get("health_score"), 87.5)
        self.assertEqual(len(cli_json.get("credentials", [])), 8)
        print("  ✓ Test 04 Passed: CLI tool scripts/check_credential_expiry.py --json passed verification.")

    def test_05_expired_key_identification_and_alerting(self):
        """Verifies expired/revoked key (GitHub Personal Access Token) is identified with action_required=True."""
        results = audit_all_credentials()
        creds = results.get("credentials", [])
        action_creds = [c for c in creds if c.get("action_required")]

        self.assertEqual(len(action_creds), 1, "Expected exactly 1 credential requiring action")
        github_cred = action_creds[0]
        self.assertEqual(github_cred.get("name"), "GitHub Access Token")
        self.assertEqual(github_cred.get("status"), "EXPIRED_OR_REVOKED")
        self.assertIn("Action Required", github_cred.get("badge"))
        self.assertIn("HTTP 401", github_cred.get("notes"))
        print("  ✓ Test 05 Passed: Expired GitHub token accurately identified for remediation alert.")


if __name__ == "__main__":
    unittest.main()
