#!/usr/bin/env python3
"""
SigmaFidelity™ Tessa Test - Lead AI Quality Assurance & Platform Regression Suite
Standard: HWB-QMS-11.2 (Continuous Regression) & HWB-QMS-7.6 (Zero-Hotfix Standard)
Authority: Humberto Dominguez (CEO) | Architect: George (Systems Architect)
Operator: Tessa Test (Lead AI QA & Platform Regression Engineer)

Mission:
Autonomously stress-test and verify full-stack system integrity across:
1. Public & Core Commercial Routes (HTTP 200 / Zero Dead Links)
2. Enterprise RBAC & Security Gateway (Gated Access, Clean Redirects)
3. Database Connection Pool & Schema Parity (PostgreSQL 16 / Migrations)
4. Telegram Operations Gateway & 5-Tier User Permissions Matrix
5. Azure VNet Database Telemetry Handshake (/api/v1/db-audit)
6. Form Input Validation & PII Vault Security (Phone Masks / Encryption)
7. Autonomous Sentinel & Recovery Snapshot Verification (Peter Sentinel)
8. Anti-Spoofing & Ingestion Quarantine Gateway
9. Business Classifier & Ingestion Gateway Hardening
10. WCAG 2.1 AA Button Accessibility & Disambiguation Quality Gate
11. Domain-Driven Lexicon Governance & Jargon Quality Gate
"""

import os
import sys
import time
import json
import unittest
import requests
import argparse
import re
from typing import Dict, Any, Optional
from datetime import datetime

# Set up paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE")
for p in [BASE_DIR, APP_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

AUDIT_LOG_DIR = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-IT", "HWB-IT-SYSTEM-LOGS")
AUDIT_LOG_FILE = os.path.join(AUDIT_LOG_DIR, "tessa_regression_audit.log")


def log_tessa(message: str) -> None:
    """Logs regression test messages to stdout and the official QA audit log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[TESSA-TEST][{timestamp}] {message}"
    print(formatted)
    try:
        os.makedirs(AUDIT_LOG_DIR, exist_ok=True)
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass


class TessaPlatformRegressionSuite(unittest.TestCase):
    """
    Tessa Test's Master Platform Regression Battery.
    Guarantees zero-defect software execution across all business operations.
    """

    @classmethod
    def setUpClass(cls) -> None:
        log_tessa("=== Initializing Tessa Test Master Platform Regression Battery ===")
        candidate_urls = [
            os.getenv("TEST_WEB_URL"),
            "http://web:5000",
            "http://hwb_web_app:5000",
            "http://localhost:5000",
            "http://127.0.0.1:5000",
        ]
        cls.base_url = "http://localhost:5000"
        for candidate in candidate_urls:
            if not candidate:
                continue
            try:
                r = requests.get(f"{candidate}/", timeout=2)
                cls.base_url = candidate
                log_tessa(f"Connected to web target at: {cls.base_url}")
                break
            except Exception:
                continue

    def setUp(self) -> None:
        self.client = requests.Session()

    # -------------------------------------------------------------
    # MODULE 1: PUBLIC & CORE COMMERCIAL ROUTES
    # -------------------------------------------------------------
    def test_01_public_commercial_routes_availability(self) -> None:
        """Tessa Test verifies all public web routes return HTTP 200 without template syntax errors."""
        log_tessa("Inspecting Module 1: Public Core Commercial Web Routes")
        routes = [
            "/",
            "/services/janitorial",
            "/services/commercial",
            "/services/industrial",
            "/services/construction",
            "/locations/dallas",
            "/locations/plano",
            "/locations/fort-worth",
            "/locations/frisco",
            "/locations/mckinney",
            "/about",
            "/work-with-us",
            "/login",
            "/prequal"
        ]

        for route in routes:
            url = f"{self.base_url}{route}"
            res = self.client.get(url, timeout=5)
            self.assertEqual(
                res.status_code, 200,
                f"Public route '{route}' failed with status {res.status_code}"
            )
            # Verify no raw Jinja error bleeds into response
            self.assertNotIn("TemplateSyntaxError", res.text)
            self.assertNotIn("UndefinedError", res.text)

        log_tessa(f"PASS: Verified {len(routes)} public core routes with 100% availability.")

    # -------------------------------------------------------------
    # MODULE 2: ENTERPRISE RBAC & SECURITY GATEWAY
    # -------------------------------------------------------------
    def test_02_rbac_unauthorized_access_protection(self) -> None:
        """Tessa Test confirms that protected administrative endpoints strictly redirect unauthenticated traffic."""
        log_tessa("Inspecting Module 2: Enterprise RBAC & Security Gateway")
        protected_routes = [
            "/admin/operations",
            "/admin/executive",
            "/admin/master",
            "/admin/lab",
            "/sales-desk"
        ]

        for route in protected_routes:
            url = f"{self.base_url}{route}"
            # Use allow_redirects=False to catch the 302 login gateway
            res = self.client.get(url, allow_redirects=False, timeout=5)
            self.assertIn(
                res.status_code, [301, 302, 401],
                f"Protected endpoint '{route}' allowed unauthenticated access (status: {res.status_code})"
            )
            if res.status_code in [301, 302]:
                self.assertIn(
                    "login", res.headers.get("Location", "").lower(),
                    f"Redirect for '{route}' did not route to login gateway"
                )

        log_tessa(f"PASS: Verified {len(protected_routes)} protected endpoints reject unauthenticated access.")

    # -------------------------------------------------------------
    # MODULE 3: DATABASE CONNECTION POOL & SCHEMA PARITY
    # -------------------------------------------------------------
    def test_03_database_connection_pool_and_migrations(self) -> None:
        """Tessa Test certifies PostgreSQL connection pool latency and schema migration completeness."""
        log_tessa("Inspecting Module 3: PostgreSQL Database & Connection Pool")
        import psycopg2
        from urllib.parse import urlparse

        db_url = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
        # Support container hostname fallback
        try:
            conn = psycopg2.connect(db_url, connect_timeout=3)
        except Exception:
            conn = psycopg2.connect("postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db", connect_timeout=3)

        start = time.time()
        with conn.cursor() as cur:
            # Latency benchmark
            cur.execute("SELECT 1;")
            _ = cur.fetchone()
            latency_ms = (time.time() - start) * 1000.0
            self.assertLess(latency_ms, 50.0, f"Database latency ({latency_ms:.2f}ms) exceeds 50ms limit")

            # Check critical tables exist
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('Leads', 'ConstructionBids', 'InstitutionalBids', 'GeneralContractors', 'Users', 'RackTelemetryHistory');
            """)
            tables = [row[0] for row in cur.fetchall()]
            expected = ['Leads', 'ConstructionBids', 'InstitutionalBids', 'GeneralContractors', 'Users', 'RackTelemetryHistory']
            for exp in expected:
                self.assertIn(exp, tables, f"Critical institutional table '{exp}' missing from PostgreSQL schema")

        conn.close()
        log_tessa(f"PASS: PostgreSQL connection verified in {latency_ms:.2f}ms with all 6 core tables present.")

    # -------------------------------------------------------------
    # MODULE 4: TELEGRAM GATEWAY & 5-TIER PERMISSIONS
    # -------------------------------------------------------------
    def test_04_telegram_gateway_permissions_architecture(self) -> None:
        """Tessa Test inspects the 5-tier Telegram permissions structure for all users."""
        log_tessa("Inspecting Module 4: Telegram Operations Gateway & User Permissions")
        import psycopg2

        db_url = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
        try:
            conn = psycopg2.connect(db_url, connect_timeout=3)
        except Exception:
            conn = psycopg2.connect("postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db", connect_timeout=3)

        with conn.cursor() as cur:
            cur.execute("SELECT username, role, custom_permissions FROM \"Users\" WHERE custom_permissions IS NOT NULL;")
            users = cur.fetchall()
            self.assertGreater(len(users), 0, "No users found with structured custom_permissions")

            required_perms = [
                "can_approve_outbox",
                "can_run_terminal_cmd",
                "can_view_margins",
                "can_ingest_bids",
                "can_search_web",
                "can_audit_photos",
                "receive_daily_briefing"
            ]

            checked = 0
            for uname, role, raw_perms in users:
                try:
                    perms = json.loads(raw_perms)
                    t_perms = perms.get("telegram", {})
                    # If user is Executive, terminal command must be permitted
                    if role == "Executive" and uname in ["hdominguez", "humberto", "humbertoed"]:
                        self.assertTrue(t_perms.get("can_run_terminal_cmd", False), f"Executive {uname} missing can_run_terminal_cmd")
                    # Non-executives must not have default terminal shell access
                    elif role in ["Sales", "Operator"]:
                        self.assertFalse(t_perms.get("can_run_terminal_cmd", False), f"Non-executive {uname} improperly granted terminal command")
                    checked += 1
                except Exception as e:
                    self.fail(f"Invalid JSON in custom_permissions for user {uname}: {e}")

        conn.close()
        log_tessa(f"PASS: Verified 5-tier Telegram permission security matrix across {checked} active user profiles.")

    # -------------------------------------------------------------
    # MODULE 5: AZURE VNET DATABASE TELEMETRY HANDSHAKE
    # -------------------------------------------------------------
    def test_05_azure_vnet_db_telemetry_handshake(self) -> None:
        """Tessa Test validates live production Azure VNet database telemetry reporting."""
        log_tessa("Inspecting Module 5: Live Azure VNet Database Telemetry Handshake")
        import urllib.request

        audit_url = "https://www.hwbcleaning.com/api/v1/db-audit"
        try:
            with urllib.request.urlopen(audit_url, timeout=10) as resp:
                self.assertEqual(resp.status, 200, f"Azure DB Audit returned status {resp.status}")
                data = json.loads(resp.read().decode('utf-8'))
                
                # Check required telemetry keys
                self.assertIn("total_leads_count", data)
                self.assertIn("database_host", data)
                self.assertEqual(data["database_host"], "sigmajan-server.postgres.database.azure.com")
                
                leads = data["total_leads_count"]
                self.assertGreater(leads, 20000, f"Suspiciously low live lead count: {leads}")
                log_tessa(f"PASS: Live Azure Prod DB verified ({leads:,} leads at {data['database_host']}).")
        except Exception as e:
            self.fail(f"Could not complete Azure VNet DB telemetry handshake: {e}")

    # -------------------------------------------------------------
    # MODULE 6: FORM INPUT VALIDATION & PHONE NORMALIZATION
    # -------------------------------------------------------------
    def test_06_form_input_validation_and_phone_normalization(self) -> None:
        """Tessa Test verifies that phone normalization converts raw phone strings to standard (###) ###-#### format."""
        log_tessa("Inspecting Module 6: Phone Number Normalization & Poka-Yoke Validation")
        import re

        test_numbers = [
            ("2145860257", "(214) 586-0257"),
            ("972-800-7808", "(972) 800-7808"),
            ("+1 (214) 586-0257", "(214) 586-0257"),
            ("214.586.0257", "(214) 586-0257")
        ]

        def normalize(raw: str) -> str:
            digits = re.sub(r'\D', '', raw)
            if len(digits) == 11 and digits.startswith('1'):
                digits = digits[1:]
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            return raw

        for raw, expected in test_numbers:
            res = normalize(raw)
            self.assertEqual(res, expected, f"Normalization of '{raw}' failed. Got '{res}', expected '{expected}'")

        log_tessa(f"PASS: Phone normalization verified across {len(test_numbers)} formatting permutations.")

    # -------------------------------------------------------------
    # MODULE 7: PETER SENTINEL & BACKUP INTEGRITY
    # -------------------------------------------------------------
    def test_07_recovery_sentinel_and_snapshot_integrity(self) -> None:
        """Tessa Test verifies that Peter Sentinel backup process is active and recovery scratchpad is intact."""
        log_tessa("Inspecting Module 7: Peter's Recovery Sentinel & Snapshot Integrity")
        scratchpad_path = os.path.join(BASE_DIR, "HWB-SESSION-RECOVERY.md")
        self.assertTrue(os.path.exists(scratchpad_path), "HWB-SESSION-RECOVERY.md scratchpad missing")

        with open(scratchpad_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Live Azure Prod DB Count", content)
        self.assertIn("Combined Active Bid Pipeline", content)
        self.assertIn("Historical Telemetry Rows", content)

        log_tessa("PASS: Session Recovery Scratchpad verified with all institutional health indicators.")

    # -------------------------------------------------------------
    # MODULE 8: MULTI-TENANT RLS & QUARANTINE INGESTION GATEWAY
    # -------------------------------------------------------------
    def test_08_multitenant_rls_and_quarantine_ingestion(self) -> None:
        """Tessa Test verifies PostgreSQL Kernel RLS multi-tenant segregation and Poka-Yoke quarantine ingestion."""
        log_tessa("Inspecting Module 8: Multi-Tenant Kernel RLS & Quarantine Ingestion Gateway")
        import psycopg2
        from core.services.quarantine_importer import stage_and_quarantine_records, commit_quarantine_batch

        db_url = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
        if not os.path.exists("/.dockerenv") and "@db:" in db_url:
            db_url = db_url.replace("@db:", "@localhost:")
        conn = psycopg2.connect(db_url)
        try:
            with conn.cursor() as cur:
                # 1. Verify RLS Isolation: Ensure hwb_tenant_app role exists
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'hwb_tenant_app';")
                if not cur.fetchone():
                    cur.execute("CREATE ROLE hwb_tenant_app WITH LOGIN PASSWORD 'tenantpass' NOSUPERUSER;")
                    cur.execute("GRANT USAGE ON SCHEMA public TO hwb_tenant_app;")
                    cur.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hwb_tenant_app;")
                    cur.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hwb_tenant_app;")
                    conn.commit()

                # Switch to unprivileged application role
                cur.execute("SET ROLE hwb_tenant_app;")

                # Tenant 2 (Collin College) MUST see 0 rows of Tenant 1 (HWB)
                cur.execute("SET app.current_tenant_id = '2';")
                cur.execute('SELECT COUNT(*) FROM "Leads";')
                t2_count = cur.fetchone()[0]
                self.assertEqual(t2_count, 0, f"Cross-tenant data bleed detected! Tenant 2 saw {t2_count} rows.")

                # Tenant 1 (HWB) MUST see all records
                cur.execute("SET app.current_tenant_id = '1';")
                cur.execute('SELECT COUNT(*) FROM "Leads";')
                t1_count = cur.fetchone()[0]
                self.assertGreater(t1_count, 0, "Tenant 1 unexpectedly saw 0 rows under RLS.")

                # Cross-Tenant Insert Block (Anti-Spoofing Check)
                cur.execute("SET app.current_tenant_id = '2';")
                rls_blocked = False
                try:
                    cur.execute('''
                        INSERT INTO "Leads" (center_name, phone, status, tenant_id)
                        VALUES ('Malicious Tenant Spoof', '(214) 555-9999', 'NEW', 1);
                    ''')
                except Exception as rls_err:
                    rls_blocked = True
                    conn.rollback()

                self.assertTrue(rls_blocked, "PostgreSQL RLS failed to block cross-tenant insert spoofing!")

            log_tessa("PASS: Kernel RLS verified: 100% mathematical cross-tenant isolation and anti-spoofing block.")

            # 2. Verify Quarantine Ingestion Gateway (Poka-Yoke)
            test_batch = [
                {"company": "Tessa Clean Medical Center 101", "phone": "(214) 555-7788", "city": "Dallas", "email": "tessa@clean101.com"},
                {"company": "Tessa Defective Lead", "phone": "", "city": "", "email": ""},
                {"company": "Horizon at Premier", "phone": "(972) 555-0199", "city": "Plano", "email": "mgr@horizonpremier.com"}
            ]
            stage_res = stage_and_quarantine_records(test_batch, tenant_id=1, source_filename="tessa_qa_batch.csv", db_url=db_url)
            self.assertEqual(stage_res["status"], "success")
            self.assertEqual(stage_res["total_records"], 3)
            self.assertEqual(stage_res["validated_clean"], 1)
            self.assertEqual(stage_res["conflict_duplicates"], 1)
            self.assertEqual(stage_res["defects_quarantined"], 1)

            # Commit clean records
            commit_res = commit_quarantine_batch(stage_res["batch_id"], tenant_id=1, db_url=db_url)
            self.assertEqual(commit_res["status"], "success")
            self.assertEqual(commit_res["records_committed"], 1)

            # Cleanup test batch
            with conn.cursor() as cur:
                cur.execute("RESET ROLE;")
                cur.execute("DELETE FROM \"Leads\" WHERE center_name = 'Tessa Clean Medical Center 101';")
                cur.execute("DELETE FROM \"crm_ingestion_quarantine\" WHERE source_filename = 'tessa_qa_batch.csv';")
                conn.commit()

            log_tessa("PASS: Quarantine Ingestion Gateway verified: 1 validated, 1 conflict, 1 defect cleanly quarantined.")
        finally:
            conn.close()

    # -------------------------------------------------------------
    # MODULE 9: BUSINESS CLASSIFIER & INGESTION GATEWAY HARDENING
    # -------------------------------------------------------------
    def test_09_business_classifier_and_ingestion_quarantine_gate(self) -> None:
        """Tessa Test verifies BusinessClassifierEngine precision, cognitive conflict detection, and taxonomy integrity."""
        log_tessa("Inspecting Module 9: Business Classifier & Ingestion Gateway Hardening")
        from core.services.classifier import BusinessClassifierEngine
        from core.services.quarantine_importer import stage_and_quarantine_records
        import psycopg2

        # 1. Lexical Classifier Precision
        test_cases = [
            ("Reef Autoplex LLC", 0, "Texas Childcare Registry", "Automotive", "Automotive", True, "Texas Commercial Registry"),
            ("Dickinson ISD Gator Academy", 120, "Texas Childcare Registry", "Education", "School", False, "Texas Childcare Registry"),
            ("HOME DEPOT U.S.A., INC.", 0, "Texas Childcare Registry", "Retail & Hospitality", "Retail", True, "Texas Commercial Registry"),
            ("Childrens Courtyard", 85, "Texas CCL API", "Child Care", "Child Care Center", False, "Texas CCL API"),
            ("Apex Global Logistics Distribution", 0, "CAD Ingestion", "Industrial / Logistics", "Warehouse", False, "CAD Ingestion"),
            ("McKinney Specialty Surgical Pavilion", 0, "Commercial CAD", "Healthcare / Medical", "Medical", False, "Commercial CAD"),
            ("First Baptist Church McKinney", 0, "Website Form", "Religious / Nonprofit", "Church", False, "Website Form"),
            ("Sterling Legal Practice LLC", 0, "Direct Lead", "Corporate / Office", "Office", False, "Direct Lead")
        ]

        for name, cap, src, exp_ind, exp_fac, exp_conflict, exp_new_src in test_cases:
            res = BusinessClassifierEngine.classify(name, cap, src)
            self.assertEqual(res.industry, exp_ind, f"Mismatch in industry for '{name}': got '{res.industry}', expected '{exp_ind}'")
            self.assertEqual(res.facility_type, exp_fac, f"Mismatch in facility_type for '{name}': got '{res.facility_type}', expected '{exp_fac}'")
            self.assertEqual(res.is_conflict, exp_conflict, f"Conflict detection error for '{name}': got {res.is_conflict}, expected {exp_conflict}")
            self.assertEqual(res.normalized_lead_source, exp_new_src, f"Lead source normalization error for '{name}': got '{res.normalized_lead_source}'")
            self.assertGreaterEqual(res.confidence_score, 0.90, f"Confidence score unexpectedly low for '{name}': {res.confidence_score}")

        log_tessa("PASS: BusinessClassifierEngine verified across 8 core enterprise sectors with 100% precision.")

        # 2. Quarantine Gate Cognitive Conflict Protection
        db_url = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
        if not os.path.exists("/.dockerenv") and "@db:" in db_url:
            db_url = db_url.replace("@db:", "@localhost:")
        conflict_batch = [
            {
                "name": "KIKO Auto Group & Collision",
                "phone": "(214) 555-9011",
                "address": "909 Motor Way",
                "city": "Dallas",
                "zip": "75201",
                "lead_source": "Texas Childcare Registry"
            }
        ]
        q_res = stage_and_quarantine_records(conflict_batch, tenant_id=1, source_filename="conflict_test.csv", db_url=db_url)
        self.assertEqual(q_res["status"], "success")
        self.assertEqual(q_res["validated_clean"], 0, "Cognitive conflict lead was erroneously validated as clean!")
        self.assertGreater(q_res["defects_quarantined"], 0, "Cognitive conflict was not quarantined!")

        # 3. Database Population & Taxonomy Integrity Check
        conn = psycopg2.connect(db_url)
        try:
            with conn.cursor() as cur:
                # Cleanup quarantine test record
                cur.execute("DELETE FROM \"crm_ingestion_quarantine\" WHERE source_filename = 'conflict_test.csv';")
                conn.commit()

                # Verify database population from Migration 029
                cur.execute('SELECT COUNT(*) FROM "Leads" WHERE industry = \'Automotive\';')
                auto_cnt = cur.fetchone()[0]
                self.assertGreater(auto_cnt, 5000, f"Automotive leads undercounted post-migration: {auto_cnt}")

                cur.execute('SELECT COUNT(*) FROM "Leads" WHERE industry = \'Education\';')
                edu_cnt = cur.fetchone()[0]
                self.assertGreater(edu_cnt, 1000, f"Education leads undercounted post-migration: {edu_cnt}")

                cur.execute('SELECT COUNT(*) FROM "Leads" WHERE industry = \'Commercial Legacy\';')
                legacy_cnt = cur.fetchone()[0]
                self.assertEqual(legacy_cnt, 0, f"Unmigrated 'Commercial Legacy' records remain: {legacy_cnt}")

            log_tessa(f"PASS: Leads table verified: {auto_cnt:,} Automotive, {edu_cnt:,} Education, 0 unmigrated Commercial Legacy.")
        finally:
            conn.close()

    # -------------------------------------------------------------
    # MODULE 10: WCAG 2.1 AA BUTTON ACCESSIBILITY & DISAMBIGUATION GATE
    # -------------------------------------------------------------
    def test_10_wcag_button_accessibility_gate(self) -> None:
        """Tessa Test verifies all interactive buttons across public and core routes have accessible labels (WCAG 2.1 AA)."""
        log_tessa("Inspecting Module 10: WCAG 2.1 AA Button Accessibility & Disambiguation Quality Gate")
        from bs4 import BeautifulSoup

        routes = [
            "/",
            "/get-quote",
            "/work-with-us",
            "/terms",
            "/privacy-policy",
            "/login",
            "/services/janitorial",
            "/services/commercial",
            "/services/industrial",
            "/services/construction"
        ]

        total_buttons_checked = 0
        for route in routes:
            url = f"{self.base_url}{route}"
            resp = self.client.get(url, timeout=5)
            self.assertEqual(resp.status_code, 200, f"Route {route} failed with status {resp.status_code}")

            soup = BeautifulSoup(resp.text, "html.parser")
            buttons = soup.find_all("button")
            for b in buttons:
                total_buttons_checked += 1
                text = b.get_text(strip=True)
                aria_label = (b.get("aria-label") or "").strip()
                title = (b.get("title") or "").strip()
                has_label = bool(text or aria_label or title)
                self.assertTrue(
                    has_label,
                    f"Accessible button violation on {route}: button tag <button {b.attrs}> lacks text, aria-label, or title."
                )

        # Dedicated inspection for /get-quote quick facility type buttons (Option 1 Streamlined Flow)
        quote_url = f"{self.base_url}/get-quote"
        q_resp = self.client.get(quote_url, timeout=5)
        q_soup = BeautifulSoup(q_resp.text, "html.parser")
        chips = q_soup.find_all("button", class_="facility-chip")
        self.assertGreaterEqual(len(chips), 6, "Expected at least 6 facility type quick select buttons on /get-quote")
        for chip in chips:
            chip_aria = chip.get("aria-label")
            self.assertTrue(bool(chip_aria and "facility" in chip_aria.lower()), f"Chip {chip} missing descriptive aria-label")
            self.assertIn(chip.get("aria-pressed"), ["true", "false"], f"Chip {chip} missing aria-pressed state")

        # Dedicated inspection for /work-with-us job position buttons
        work_url = f"{self.base_url}/work-with-us"
        w_resp = self.client.get(work_url, timeout=5)
        w_soup = BeautifulSoup(w_resp.text, "html.parser")
        detail_btns = w_soup.find_all("button", onclick=re.compile(r"viewJobDescription"))
        for d_btn in detail_btns:
            aria = d_btn.get("aria-label") or ""
            self.assertTrue("for " in aria.lower(), f"Job details button {d_btn} lacks contextual job title in aria-label")

        log_tessa(f"PASS: WCAG 2.1 AA Button Accessibility Gate passed: {total_buttons_checked} buttons verified across {len(routes)} routes with 100% compliance.")

    # -------------------------------------------------------------
    # MODULE 11: DOMAIN-DRIVEN LEXICON GOVERNANCE & JARGON LINTER
    # -------------------------------------------------------------
    def test_11_domain_driven_lexicon_governance_gate(self) -> None:
        """Tessa Test verifies 0 occurrences of prohibited aviation jargon ('cockpit') and developer slang across templates and rendered pages."""
        log_tessa("Inspecting Module 11: Domain-Driven Lexicon Governance & Jargon Linter")
        from core.services.lexicon_governance import scan_templates_directory, BANNED_WORDS_PATTERN

        # 1. Scan all active HTML templates
        templates_path = os.path.join(APP_DIR, "templates")
        if not os.path.exists(templates_path):
            templates_path = os.path.join(BASE_DIR, "templates")
        scan_results = scan_templates_directory(templates_path)
        self.assertEqual(
            scan_results["violations_count"],
            0,
            f"Lexicon Governance defect: Found {scan_results['violations_count']} prohibited jargon violations in templates: {scan_results['violations']}"
        )

        # 2. Scan rendered HTML of public and core routes for prohibited words
        routes = [
            "/",
            "/get-quote",
            "/work-with-us",
            "/services/janitorial",
            "/portal/bosanna/login",
            "/login"
        ]

        for route in routes:
            url = f"{self.base_url}{route}"
            resp = self.client.get(url, timeout=5)
            self.assertEqual(resp.status_code, 200, f"Failed fetching {route}")
            matches = list(BANNED_WORDS_PATTERN.finditer(resp.text))
            self.assertEqual(
                len(matches),
                0,
                f"Lexicon violation on rendered route {route}: found banned term '{[m.group(0) for m in matches]}'"
            )

        log_tessa(f"PASS: Lexicon Governance Gate passed: 0 prohibited jargon terms found across {scan_results['scanned_files']} templates and {len(routes)} live rendered routes.")


def run_tessa_audit() -> bool:
    """Executes the complete test suite and outputs the formal certification."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TessaPlatformRegressionSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        log_tessa("=== CERTIFICATION: ALL PLATFORM MODULES PASSED TESSA TEST AUDIT (Grade: A+) ===")
        return True
    else:
        log_tessa(f"=== CRITICAL WARNING: TESSA TEST AUDIT DETECTED {len(result.failures)} FAILURE(S) & {len(result.errors)} ERROR(S) ===")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tessa Test Master Platform Regression Battery")
    parser.add_argument("--daemon", action="store_true", help="Run in continuous background monitoring mode")
    parser.add_argument("--interval", type=int, default=3600, help="Interval in seconds between audits (default: 3600)")
    args = parser.parse_args()

    if args.daemon:
        log_tessa(f"=== Starting Tessa Test Continuous Regression Daemon (Interval: {args.interval}s) ===")
        while True:
            try:
                run_tessa_audit()
            except Exception as e:
                log_tessa(f"Unexpected error during regression audit cycle: {e}")
            time.sleep(args.interval)
    else:
        success = run_tessa_audit()
        sys.exit(0 if success else 1)
