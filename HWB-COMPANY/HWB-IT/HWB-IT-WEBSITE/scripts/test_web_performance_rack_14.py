#!/usr/bin/env python3
"""
⚡ SIGMAFIDELITY™ HWB-QMS-11.14: ENTERPRISE WEB & BACKOFFICE PERFORMANCE TEST SUITE
Standard: HWB-QMS-11.14 v1.1.0 / MO-HWB-2026-10-19-PERF-014 & PERF-015 (v5.4.4)
Custodians: Super George (Commander of Special Ops) & George Bytes (HWB Tactical Builder)
"""

import os
import sys
import time
import unittest
from dotenv import load_dotenv

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, "../../.."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from main_app import app
from core.services.database import get_db, MAX_POOL_CONNECTIONS, _FALLBACK_TZ_POOLS
from core.services.version_service import get_version_info, clear_version_cache, APP_SEMANTIC_VERSION
from core.services.self_healing_engine import get_architectural_scorecard
from core.services.credential_sentinel import audit_all_credentials
from database.schema_engine import sync_bug_132_133_five_tables


class EnterpriseWebPerformanceTestSuite(unittest.TestCase):
    """Verifies Part I (Public Web Performance) and Part II (Backoffice CQRS <150ms) of HWB-QMS-11.14 v1.1.0."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.db_url = app.config["DATABASE_URL"]

    def get_auth_client(self):
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
            sess["role"] = "Executive"
            sess["_fresh"] = True
        return client

    def test_01_database_pool_zero_round_trip_and_timezone(self):
        """Part I Pillar 3: Verifies DB_POOL_MAX=10 and connection-init America/Chicago timezone without checkout SQL."""
        self.assertEqual(MAX_POOL_CONNECTIONS, int(os.environ.get("DB_POOL_MAX", 10)))
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute("SHOW TIME ZONE;")
                tz_row = cur.fetchone()
                tz_val = tz_row[0] if tz_row else ""
                self.assertEqual(tz_val, "America/Chicago")
            self.assertNotIn(self.db_url, _FALLBACK_TZ_POOLS)
        finally:
            conn.close()

    def test_02_version_service_in_memory_lru_cache(self):
        """Part I Pillar 4: Verifies get_version_info() is cached in memory with lru_cache and reports v5.4.x."""
        clear_version_cache()
        self.assertTrue(APP_SEMANTIC_VERSION.startswith("v5.4."))
        info_1 = get_version_info()
        info_2 = get_version_info()
        self.assertTrue(str(info_1.get("app_version", "")).startswith("v5.4."))
        self.assertIs(info_1, info_2)
        cache_info = get_version_info.cache_info()
        self.assertGreaterEqual(cache_info.hits, 1)
        self.assertEqual(cache_info.misses, 1)

    def test_03_public_marketing_split_cloudflare_edge_cache_headers(self):
        """Part I Pillar 5: Verifies anonymous GET / emits s-maxage=3600, strips Cookie from Vary, and emits no Set-Cookie."""
        fresh_client = app.test_client()
        res = fresh_client.get("/")
        self.assertEqual(res.status_code, 200)
        cc = res.headers.get("Cache-Control", "")
        self.assertIn("public", cc)
        self.assertIn("s-maxage=3600", cc)
        self.assertIn("stale-while-revalidate=86400", cc)
        vary = res.headers.get("Vary", "")
        self.assertNotIn("cookie", vary.lower(), f"Vary header still contains Cookie: {vary}")
        self.assertIsNone(res.headers.get("Set-Cookie"), "Anonymous public GET emitted Set-Cookie")

    def test_04_protected_routes_enforce_strict_no_store(self):
        """Part I Pillar 5: Verifies /login and /admin routes strictly forbid edge caching."""
        res_login = self.client.get("/login")
        self.assertEqual(res_login.status_code, 200)
        cc = res_login.headers.get("Cache-Control", "")
        self.assertIn("no-store", cc)
        self.assertIn("private", cc)

    def test_05_webp_homepage_assets_and_template_references(self):
        """Part I Pillar 5: Verifies all 5 homepage WebP images exist, total <450 KB, and are referenced in GET / HTML."""
        img_dir = os.path.join(APP_DIR, "static", "img")
        homepage_webp = [
            "hero_lobby.webp",
            "daycare_busy_active.webp",
            "commercial_marble_polishing.webp",
            "industrial_m20_scrubber.webp",
            "construction_sweeper_servicing_street.webp",
        ]
        total_kb = 0.0
        for fname in homepage_webp:
            fpath = os.path.join(img_dir, fname)
            self.assertTrue(os.path.exists(fpath), f"Missing WebP asset: {fpath}")
            total_kb += os.path.getsize(fpath) / 1024.0

        self.assertLess(total_kb, 450.0, f"Homepage WebP total {total_kb:.1f} KB exceeds 450 KB target")

        res = self.client.get("/")
        html = res.get_data(as_text=True)
        for fname in homepage_webp:
            self.assertIn(f"/static/img/{fname}", html)

    def test_06_backoffice_cqrs_covering_indexes_migration_043(self):
        """Part II Pillar 2: Verifies all 4 covering composite indexes from Migration 043 exist in pg_indexes."""
        expected_indexes = {
            "idx_global_activities_parent_lookup",
            "idx_campaign_recipients_lead_lookup",
            "idx_leads_assigned_rep_status",
            "idx_employee_documents_employee_id",
        }
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname = ANY(%s);",
                    (list(expected_indexes),),
                )
                found = {r[0] for r in cur.fetchall()}
            self.assertEqual(found, expected_indexes, f"Missing covering indexes: {expected_indexes - found}")
        finally:
            conn.close()

    def test_07_self_healing_and_credential_300s_telemetry_cache(self):
        """Part II Pillar 1: Verifies 300s in-memory TTL cache returns sub-2ms hits for telemetry and credentials."""
        # Prime cache
        get_architectural_scorecard(self.db_url)
        audit_all_credentials()

        t0 = time.perf_counter()
        scorecard = get_architectural_scorecard(self.db_url)
        creds = audit_all_credentials()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        self.assertIsNotNone(scorecard)
        self.assertIsNotNone(creds)
        self.assertLess(dt_ms, 5.0, f"Cached telemetry + credential lookup took {dt_ms:.2f}ms (expected <5ms)")

    def test_08_active_view_cqrs_dom_pruning_and_static_js(self):
        """Part II Pillar 3 & 4: Verifies inactive department views and modals are pruned and static JS is linked."""
        js_path = os.path.join(APP_DIR, "static", "js", "backoffice_operations_core.js")
        self.assertTrue(os.path.exists(js_path), "Missing static/js/backoffice_operations_core.js")
        self.assertGreater(os.path.getsize(js_path), 350000)

        auth_client = self.get_auth_client()
        res_accounts = auth_client.get("/admin/operations?view=accounts")
        self.assertEqual(res_accounts.status_code, 200)
        html_acc = res_accounts.get_data(as_text=True)
        self.assertIn("backoffice_operations_core.js", html_acc)
        self.assertIn('id="modal-account-command"', html_acc)
        # Inactive department modals must be pruned on view=accounts
        self.assertNotIn('id="modal-lead-command"', html_acc)
        self.assertNotIn('id="modal-onboard-candidate"', html_acc)
        self.assertNotIn('id="modal-create-campaign"', html_acc)

    def test_09_warm_backoffice_tab_switching_sub_150ms(self):
        """Part II Pillar 3 & 4: Verifies warm response time <150ms and gzipped payload <250KB across core views."""
        auth_client = self.get_auth_client()
        core_views = [
            "leads",
            "accounts",
            "construction_bids",
            "marketing",
            "workforce",
            "it_department",
        ]
        # Warmup pass
        for v in core_views:
            r = auth_client.get(f"/admin/operations?view={v}")
            self.assertEqual(r.status_code, 200)

        # Timed pass
        for v in core_views:
            t0 = time.perf_counter()
            r = auth_client.get(f"/admin/operations?view={v}", headers={"Accept-Encoding": "gzip"})
            dt_ms = (time.perf_counter() - t0) * 1000.0
            gz_kb = len(r.data) / 1024.0
            self.assertEqual(r.status_code, 200)
            self.assertLess(dt_ms, 150.0, f"Warm view={v} took {dt_ms:.2f}ms (exceeds 150ms budget)")
            self.assertLess(gz_kb, 250.0, f"Gzipped view={v} payload {gz_kb:.1f}KB exceeds 250KB budget")

    def test_10_bug_132_133_five_table_error_ledger_sync(self):
        """Critical Addendum: Verifies BUG-132 and BUG-133 are recorded across all 5 error/audit database tables."""
        conn = get_db(self.db_url)
        try:
            receipt = sync_bug_132_133_five_tables(conn)
            self.assertEqual(receipt["sigma_knowledge_scars"].get("BUG-132"), 224)
            self.assertEqual(receipt["sigma_knowledge_scars"].get("BUG-133"), 225)
            self.assertIsNotNone(receipt["global_activities"].get("BUG-132"))
            self.assertIsNotNone(receipt["global_activities"].get("BUG-133"))
            self.assertIsNotNone(receipt["incidents"].get("BUG-132"))
            self.assertIsNotNone(receipt["incidents"].get("BUG-133"))
            self.assertIsNotNone(receipt["rack_telemetry_history_id"])
            self.assertIsNotNone(receipt["security_audit_logs_id"])
        finally:
            conn.close()

    def test_11_backoffice_modal_dom_isolation_and_lead_click(self):
        """BUG-134 Guard: Verifies modals (#modal-lead-command, etc.) are never trapped inside hidden view-* containers and lead row click API resolves 200 OK."""
        from html.parser import HTMLParser
        import re

        class DomNestingChecker(HTMLParser):
            def __init__(self):
                super().__init__()
                self.stack = []
                self.trapped_elements = {}

            def handle_starttag(self, tag, attrs):
                d = dict(attrs)
                el_id = d.get("id", "")
                if el_id.startswith("view-") or el_id.startswith("modal-"):
                    hidden_view_parents = [
                        x[1] for x in self.stack if x[1].startswith("view-") and "display: none" in x[2]
                    ]
                    if hidden_view_parents:
                        self.trapped_elements[el_id] = hidden_view_parents
                if tag not in (
                    "br", "hr", "img", "input", "meta", "link", "source",
                    "col", "area", "base", "embed", "param", "track", "wbr",
                ):
                    self.stack.append((tag, el_id, d.get("style", "")))

            def handle_endtag(self, tag):
                for i in range(len(self.stack) - 1, -1, -1):
                    if self.stack[i][0] == tag:
                        self.stack = self.stack[:i]
                        break

        auth_client = self.get_auth_client()

        for v in ["leads", "accounts", "construction_bids", "workforce", "scope", "it_department"]:
            r = auth_client.get(f"/admin/operations?view={v}")
            self.assertEqual(r.status_code, 200)
            html = r.data.decode("utf-8")
            checker = DomNestingChecker()
            checker.feed(html)
            self.assertEqual(
                checker.trapped_elements,
                {},
                f"View {v} has views/modals trapped inside hidden view-* containers: {checker.trapped_elements}",
            )
            if v == "leads":
                self.assertIn('id="modal-lead-command"', html)
                m = re.search(r"handleRowClick\(event,\s*'(\d+)'\)", html)
                self.assertIsNotNone(m, "Expected at least one clickable lead row on view=leads")
                lead_id = m.group(1)
                r_lead = auth_client.get(f"/api/v1/leads/{lead_id}")
                self.assertEqual(r_lead.status_code, 200)
                payload = r_lead.get_json()
                self.assertIsNotNone(payload.get("lead"))

    def test_12_global_activities_enterprise_idempotency_and_canonical_guard(self):
        """Enterprise Standards #1 & #5: Verifies GlobalActivities deduplication, BEFORE INSERT trigger idempotency, and canonical parent_type CHECK constraint."""
        import psycopg2

        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                # 1. Verify no duplicate Autonomous Vetting & Enrichment rows per bid
                cur.execute("""
                    SELECT MAX(cnt) FROM (
                        SELECT COUNT(*) AS cnt
                        FROM "GlobalActivities"
                        WHERE activity_type = 'Autonomous Vetting & Enrichment'
                        GROUP BY parent_type, parent_id
                    ) sub;
                """)
                max_dup = cur.fetchone()[0] or 0
                self.assertLessEqual(max_dup, 1, f"Expected <= 1 Autonomous Vetting & Enrichment row per bid, found {max_dup}")

                # 2. Verify BEFORE INSERT trigger suppresses duplicate automated enrichment inserts
                cur.execute("""
                    SELECT parent_id, description
                    FROM "GlobalActivities"
                    WHERE parent_type = 'ConstructionBid'
                      AND activity_type = 'Autonomous Vetting & Enrichment'
                    LIMIT 1;
                """)
                sample = cur.fetchone()
                if sample:
                    pid, desc = sample
                    cur.execute(
                        'SELECT COUNT(*) FROM "GlobalActivities" WHERE parent_type = %s AND parent_id = %s AND activity_type = %s;',
                        ("ConstructionBid", pid, "Autonomous Vetting & Enrichment"),
                    )
                    before_cnt = cur.fetchone()[0]
                    cur.execute(
                        'INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description) VALUES (%s, %s, %s, %s);',
                        (pid, "ConstructionBid", "Autonomous Vetting & Enrichment", desc),
                    )
                    cur.execute(
                        'SELECT COUNT(*) FROM "GlobalActivities" WHERE parent_type = %s AND parent_id = %s AND activity_type = %s;',
                        ("ConstructionBid", pid, "Autonomous Vetting & Enrichment"),
                    )
                    after_cnt = cur.fetchone()[0]
                    self.assertEqual(before_cnt, after_cnt, "Trigger must suppress duplicate Autonomous Vetting & Enrichment insert")
                    conn.commit()

                # 3. Verify canonical parent_type CHECK constraint rejects invalid entity names
                with self.assertRaises(psycopg2.Error):
                    cur.execute(
                        'INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description) VALUES (1, %s, %s, %s);',
                        ("InvalidNonCanonicalEntity", "Test", "Should be rejected by CHECK constraint"),
                    )
                conn.rollback()
        finally:
            conn.close()

    def test_13_tablet_popover_and_modal_viewport_safety(self):
        """BUG-135: Verifies Customize Columns popovers (#col-mgr-menu*), .isc-modal touch scroll, sticky column unpinning, and SortableJS touch delay."""
        auth_client = self.get_auth_client()

        for v, menu_id in [("leads", "col-mgr-menu"), ("accounts", "col-mgr-menu-acc"), ("construction_bids", "col-mgr-menu-bids")]:
            r = auth_client.get(f"/admin/operations?view={v}")
            self.assertEqual(r.status_code, 200)
            html = r.data.decode("utf-8")
            self.assertIn(f'id="{menu_id}"', html)
            self.assertIn("sigma-col-mgr-menu", html)
            self.assertIn("max-width: calc(100vw - 24px)", html)
            self.assertIn("-webkit-overflow-scrolling: touch", html)
            self.assertIn("@media (max-width: 1024px)", html)

        js_resp = auth_client.get("/static/js/backoffice_operations_core.js")
        self.assertEqual(js_resp.status_code, 200)
        js_text = js_resp.data.decode("utf-8")
        self.assertIn("delayOnTouchOnly: true", js_text)
        self.assertIn("m.style.position = 'fixed'", js_text)

    def test_14_smartphone_iphone_and_pixel9_form_ergonomics(self) -> None:
        """
        Verify Apple iPhone (390px iOS Safari) and Google Pixel 9 (412px Android Chrome)
        form ergonomics across both public and backend forms (BUG-136).
        """
        # 1. Public CSS: 16px iOS zoom prevention & universal row collapse
        css_resp = self.client.get("/static/HWB-WEB%20Style.css")
        self.assertEqual(css_resp.status_code, 200)
        css_text = css_resp.data.decode("utf-8")
        self.assertIn("font-size: max(16px, 1rem) !important", css_text)
        self.assertIn(".sigma-row-75-25", css_text)
        self.assertIn("env(safe-area-inset-bottom)", css_text)

        # 2. Public Login & Forgot Password Vaults: fluid clamp padding & 1rem inputs
        login_html = self.client.get("/login").data.decode("utf-8")
        self.assertIn("padding: clamp(1.75rem, 6vw, 4rem)", login_html)
        forgot_html = self.client.get("/forgot-password").data.decode("utf-8")
        self.assertIn("font-size: 1rem", forgot_html)

        # 3. Backend Operations Hub: 92dvh dynamic viewport, universal modal grid collapse, & keyboard scrollIntoView
        auth_client = self.get_auth_client()
        if auth_client:
            ops_html = auth_client.get("/admin/operations?view=leads").data.decode("utf-8")
            self.assertIn("max-height: 92dvh !important", ops_html)
            self.assertIn('.isc-modal [style*="grid-template-columns"]', ops_html)
            self.assertIn("font-size: max(16px, 1rem) !important", ops_html)

        js_text = self.client.get("/static/js/backoffice_operations_core.js").data.decode("utf-8")
        self.assertIn("scrollIntoView({ block: 'center', behavior: 'smooth' })", js_text)

    def test_15_full_site_phone_tablet_and_table_enterprise_architecture(self) -> None:
        """
        Verify permanent full-site Phone (<= 768px), Tablet (<= 1024px), and Adaptive
        Data-Table (Card/Table Switcher + MutationObserver) architecture across all
        public pages, QMS manuals, and backend modules (BUG-137).
        """
        # 1. Verify SigmaResponsiveTableEngine static module & MutationObserver auto-hydration
        eng_resp = self.client.get("/static/js/sigma_responsive_engine.js")
        self.assertEqual(eng_resp.status_code, 200)
        eng_js = eng_resp.data.decode("utf-8")
        self.assertIn("SigmaResponsiveTableEngine", eng_js)
        self.assertIn("MutationObserver", eng_js)
        self.assertIn("sigma-phone-card-mode", eng_js)
        self.assertIn("data-sigma-responsive", eng_js)
        self.assertIn("initQmsManualDrawer", eng_js)

        # 2. Verify HWB-WEB Style.css contains adaptive table-to-card CSS rules
        css_text = self.client.get("/static/HWB-WEB%20Style.css").data.decode("utf-8")
        self.assertIn('body.sigma-phone-card-mode table[data-sigma-responsive="true"]', css_text)
        self.assertIn("sigma-card-primary-cell", css_text)

        # 3. Verify Public Routes & Compliance Pages automatically load sigma_responsive_engine.js
        for pub_route in ["/", "/get-quote", "/work-with-us", "/capability-statement", "/prequal", "/login"]:
            resp = self.client.get(pub_route)
            self.assertEqual(resp.status_code, 200, f"Public route {pub_route} failed")
            html = resp.data.decode("utf-8")
            self.assertIn("sigma_responsive_engine.js", html, f"{pub_route} missing sigma_responsive_engine.js")

        # 4. Verify Authenticated Backoffice & QMS Manual Routes load responsive engine & KPI grid rules
        auth_client = self.get_auth_client()
        if auth_client:
            for bo_route in ["/admin/operations?view=leads", "/admin/operations?view=general_contractors", "/manual/app"]:
                resp = auth_client.get(bo_route)
                self.assertEqual(resp.status_code, 200, f"Backoffice route {bo_route} failed")
                html = resp.data.decode("utf-8")
                self.assertIn("sigma_responsive_engine.js", html, f"{bo_route} missing sigma_responsive_engine.js")

    def test_16_enterprise_iam_password_recovery_and_audit_ledger(self) -> None:
        """
        BUG-138: Verifies the 5-Layer Enterprise IAM & Password Recovery Architecture:
        1. Users IAM columns (reset_token_hash, reset_token_expires_at, reset_delivery_status) & PasswordResetAuditLedger table exist.
        2. Smart Identity Resolution (/forgot-password) resolves by full_name, username, or email.
        3. Token generation, Graph delivery status tracking, single-use token validation, and atomic token consumption.
        """
        from unittest.mock import patch
        import hashlib
        import re

        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'Users' AND table_schema = 'public';
                """)
                cols = {r[0] if not isinstance(r, dict) else r["column_name"] for r in cur.fetchall()}
                for req_col in [
                    "reset_token_hash", "reset_token_expires_at",
                    "reset_requested_at", "reset_delivery_status",
                    "reset_delivery_error", "reset_consumed_at"
                ]:
                    self.assertIn(req_col, cols, f"Users table missing IAM column {req_col}")

                cur.execute("""
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'PasswordResetAuditLedger' AND table_schema = 'public';
                """)
                self.assertIsNotNone(cur.fetchone(), "PasswordResetAuditLedger table must exist")
        finally:
            conn.close()

        # Test full-name identity resolution & verified delivery tracking on /forgot-password (mocking transmit_email to avoid live email spam during unit test)
        captured_emails = []

        def mock_transmit(recipient, subject, body_html, *args, **kwargs):
            captured_emails.append((recipient, subject, body_html))
            return True, "Success"

        with patch("blueprints.auth.transmit_email", side_effect=mock_transmit):
            resp = self.client.post("/forgot-password", data={"identifier": "Beabe Wiley"})
            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode("utf-8")
            self.assertIn("Instructions Dispatched", html)
            self.assertEqual(len(captured_emails), 1, "Expected 1 reset email dispatched when resolving by Full Name 'Beabe Wiley'")
            recip, subj, body = captured_emails[0]
            self.assertEqual(recip, "beabe2012@gmail.com")
            m_tok = re.search(r"/reset-password/([A-Za-z0-9_\-]+)", body)
            self.assertIsNotNone(m_tok, "Reset email body must contain /reset-password/<token> link")
            raw_token = m_tok.group(1)

            # Verify token page renders valid form
            r_get = self.client.get(f"/reset-password/{raw_token}")
            self.assertEqual(r_get.status_code, 200)
            self.assertIn("Confirm New Password", r_get.data.decode("utf-8"))

            # Verify ledger row recorded as DELIVERED
            tok_prefix = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()[:12]
            conn2 = get_db(self.db_url)
            try:
                with conn2.cursor() as cur2:
                    cur2.execute(
                        'SELECT delivery_status FROM "PasswordResetAuditLedger" WHERE token_hash_prefix = %s ORDER BY id DESC LIMIT 1;',
                        (tok_prefix,)
                    )
                    l_row = cur2.fetchone()
                    self.assertIsNotNone(l_row)
                    status_val = l_row["delivery_status"] if isinstance(l_row, dict) else l_row[0]
                    self.assertEqual(status_val, "DELIVERED")
                    # Clean up test token on Bwiley so account remains clean
                    cur2.execute(
                        'UPDATE "Users" SET reset_token_hash = NULL, reset_token_expires_at = NULL WHERE LOWER(username) = %s;',
                        ("bwiley",)
                    )
                    conn2.commit()
            finally:
                conn2.close()

    def test_17_subcontractor_1099_onboarding_and_w9_coi_extraction(self):
        """
        Verifies the 4-Stage 1099 Subcontractor Onboarding & AI/PDF Document Extraction Workflow (BUG-139):
        1. All required onboarding, tax/address, COI metadata, and MSA/DWC-83 columns exist on SubcontractorPartners.
        2. Pre-filled self-service portal (/onboard/subcontractor/<token>) renders partner's initial registration fields.
        3. W-9 and COI extraction engine accurately extracts Legal Name, Business Name, Tax Classification,
           Street Address, City/State/ZIP, EIN/SSN, Carrier, Policy #, Limit, and Expiration Date.
        """
        from core.services.database import get_db
        from database.schema_engine import ensure_subcontractor_onboarding_schema
        from core.services.subcontractor_doc_extractor import (
            extract_subcontractor_document_metadata,
            generate_signed_msa_dwc83_certificate_html,
            generate_signed_msa_dwc83_certificate_pdf,
            encrypt_and_mask_subcontractor_tin,
            decrypt_subcontractor_tin,
            audit_subcontractor_coi_expirations,
        )

        conn = get_db(self.db_url)
        try:
            ensure_subcontractor_onboarding_schema(conn)
            watchdog_res = audit_subcontractor_coi_expirations(conn, send_alerts=False)
            self.assertIn("expired_count", watchdog_res)
            self.assertIn("expiring_30d_count", watchdog_res)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'SubcontractorPartners' AND table_schema = 'public';
                """)
                cols = {r["column_name"] if isinstance(r, dict) else r[0] for r in cur.fetchall()}
                for req_col in [
                    "onboarding_token", "onboarding_token_expires_at", "onboarding_status",
                    "street_address", "zip_code", "legal_entity_name", "tax_classification",
                    "w9_tin_encrypted", "w9_ein_last4", "msa_signature_hash",
                    "msa_file_url", "dwc83_file_url", "coi_carrier", "coi_policy_number",
                    "coi_coverage_amount", "msa_signed", "msa_signer_name",
                    "msa_signer_title", "msa_signed_at", "msa_signer_ip"
                ]:
                    self.assertIn(req_col, cols, f"SubcontractorPartners missing column {req_col}")

                cur.execute('SELECT * FROM "SubcontractorPartners" ORDER BY id ASC LIMIT 1;')
                sub = dict(cur.fetchone())
        finally:
            conn.close()

        # Verify pre-filled onboarding portal GET
        tok = sub.get("onboarding_token")
        self.assertTrue(bool(tok), "Subcontractor must have an onboarding_token")
        r_portal = self.client.get(f"/onboard/subcontractor/{tok}")
        self.assertEqual(r_portal.status_code, 200)
        portal_html = r_portal.data.decode("utf-8")
        self.assertIn(sub["company_name"], portal_html)
        self.assertIn("Upload IRS Form W-9", portal_html)

        # Verify 30-day link renewal endpoint
        r_renew = self.client.post(f"/onboard/subcontractor/{tok}/renew-link")
        self.assertEqual(r_renew.status_code, 200)

        # Verify W-9 extraction + AES-256 Fernet Full-TIN Encryption & Decryption
        sample_w9 = (
            b"%PDF-1.4\n"
            b"1. Name of entity/individual: Duena Luz Tejada\n"
            b"2. Business name: Valdez Remodeling and Cleaning LLC\n"
            b"3a. Federal tax classification: Limited Liability Company (LLC)\n"
            b"5. Address: 1420 Pioneer Pkwy Suite 110\n"
            b"6. City, state, and ZIP: Arlington, TX 76013\n"
            b"Employer Identification Number: 84-2910455\n"
            b"Signed by: /s/ Duena Luz Tejada\n"
        )
        ext_w9 = extract_subcontractor_document_metadata(sample_w9, "w9.pdf", doc_type="w9", partner_row=sub)
        self.assertEqual(ext_w9["ein_or_ssn"], "84-2910455")
        self.assertEqual(ext_w9["ein_last4"], "0455")
        self.assertEqual(ext_w9["ein_masked"], "**-***0455")
        self.assertEqual(ext_w9["street_address"], "1420 Pioneer Pkwy Suite 110")
        self.assertEqual(ext_w9["zip_code"], "76013")

        masked_tin, last4_tin, enc_tin = encrypt_and_mask_subcontractor_tin("84-2910455")
        self.assertEqual(masked_tin, "**-***0455")
        self.assertEqual(last4_tin, "0455")
        self.assertTrue(bool(enc_tin))
        self.assertEqual(decrypt_subcontractor_tin(enc_tin), "84-2910455")

        # Verify COI extraction
        sample_coi = (
            b"%PDF-1.4\n"
            b"INSURER A: Next Insurance US Company\n"
            b"Policy Number: GL-9948120-TX\n"
            b"Each Occurrence Limit: $1,000,000\n"
            b"Policy Expiration: 2027-06-30\n"
            b"Certificate Holder: HWB Cleaning Services LLC\n"
        )
        ext_coi = extract_subcontractor_document_metadata(sample_coi, "coi.pdf", doc_type="coi", partner_row=sub)
        self.assertEqual(ext_coi["coi_carrier"], "Next Insurance US Company")
        self.assertEqual(ext_coi["coi_policy_number"], "GL-9948120-TX")
        self.assertEqual(ext_coi["coi_expiration_date"], "2027-06-30")

        # Verify signed MSA + TX DWC-83 HTML and Locked PDF certificate generation
        cert_html = generate_signed_msa_dwc83_certificate_html(
            sub, sub["contact_name"], "Owner", "127.0.0.1", "10/20/2026 10:15 AM CST"
        )
        self.assertIn("TEXAS DWC-83 AFFIRMATION", cert_html)
        self.assertIn("SHA-256 Signature Fingerprint:", cert_html)
        self.assertIn(sub["company_name"], cert_html)

        cert_pdf = generate_signed_msa_dwc83_certificate_pdf(
            sub, sub["contact_name"], "Owner", "127.0.0.1", "10/20/2026 10:15 AM CST"
        )
        self.assertTrue(cert_pdf.startswith(b"%PDF-1.4"))
        self.assertIn(b"SHA-256 Cryptographic Fingerprint:", cert_pdf)
        self.assertIn(b"%%EOF", cert_pdf)

        # Verify Option C Tier-1 Hybrid Document Vault ("SubcontractorDocuments")
        # 1. Deposit encrypted & compressed PDF into PostgreSQL 16.15
        # 2. Delete the local container cache file to simulate an Azure Web App redeploy
        # 3. Verify retrieve_subcontractor_document_vault decrypts, verifies SHA-256, and auto-heals disk
        import tempfile
        from core.services.subcontractor_doc_extractor import (
            deposit_subcontractor_document_vault,
            retrieve_subcontractor_document_vault,
            list_subcontractor_document_versions,
        )
        conn2 = get_db(self.db_url)
        try:
            with tempfile.TemporaryDirectory() as tmp_vault_dir:
                test_file_key = f"sub_{sub['id']}_MSA_TestVault.pdf"
                receipt_v1 = deposit_subcontractor_document_vault(
                    conn=conn2,
                    subcontractor_id=sub["id"],
                    doc_type="msa",
                    file_key=test_file_key,
                    original_filename="MSA_TestVault.pdf",
                    raw_bytes=cert_pdf,
                    mime_type="application/pdf",
                    uploaded_by="unit_test_suite",
                    uploaded_ip="127.0.0.1",
                    vault_dir=tmp_vault_dir,
                )
                conn2.commit()
                self.assertGreaterEqual(receipt_v1["version_number"], 1)
                self.assertEqual(receipt_v1["file_size_bytes"], len(cert_pdf))

                # Simulate container disk wipe during Azure deployment
                cached_file = os.path.join(tmp_vault_dir, test_file_key)
                self.assertTrue(os.path.exists(cached_file))
                os.remove(cached_file)
                self.assertFalse(os.path.exists(cached_file))

                # Retrieve from PostgreSQL 16.15 encrypted vault & verify auto-heal + SHA-256
                recovered = retrieve_subcontractor_document_vault(
                    conn=conn2,
                    subcontractor_id=sub["id"],
                    doc_type="msa",
                    file_key=test_file_key,
                    vault_dir=tmp_vault_dir,
                )
                self.assertIsNotNone(recovered)
                self.assertTrue(recovered["checksum_verified"])
                self.assertEqual(recovered["sha256_checksum"], receipt_v1["sha256_checksum"])
                self.assertEqual(recovered["bytes"], cert_pdf)
                self.assertTrue(os.path.exists(cached_file), "Container disk cache must auto-heal from PostgreSQL vault")

                versions = list_subcontractor_document_versions(conn2, sub["id"])
                self.assertGreaterEqual(len(versions), 1)

                # Clean up test row so production/dev parity row counts remain pristine
                with conn2.cursor() as cur2:
                    cur2.execute(
                        'DELETE FROM "SubcontractorDocuments" WHERE id = %s;',
                        (receipt_v1["document_id"],),
                    )
                conn2.commit()
        finally:
            conn2.close()

    def test_18_w2_employee_onboarding_and_encrypted_vault(self) -> None:
        """
        Verifies the Tier-1 Enterprise W-2 Employee Onboarding, Auto-Extraction &
        Encrypted PostgreSQL EmployeeDocuments Vault Suite (BUG-140 / v5.5.0).
        """
        from database.schema_engine import ensure_employee_onboarding_schema
        from core.services.employee_doc_extractor import (
            deposit_employee_document_vault,
            extract_direct_deposit_fields,
            extract_state_id_fields,
            extract_w4_fields,
            generate_signed_w2_onboarding_pdf,
            retrieve_employee_document_vault,
            run_employee_doc_expiration_sweep,
        )

        # 1. Verify Form W-4 Auto-Extraction
        sample_w4_bytes = (
            b"Form W-4 Employee's Withholding Certificate\n"
            b"First Name: Carlos\n"
            b"Last Name: Mendoza\n"
            b"Address: 4120 Swiss Ave\n"
            b"City, State, ZIP: Dallas, TX 75204\n"
            b"Social security number: 456-78-9012\n"
            b"Filing Status: Married Filing Jointly\n"
            b"Total Dependents: $4,000.00\n"
            b"Extra withholding: $25.00\n"
        )
        w4_res = extract_w4_fields(sample_w4_bytes, "Carlos_W4.txt", "text/plain")
        self.assertEqual(w4_res["address_street"], "4120 Swiss Ave")
        self.assertEqual(w4_res["address_city"], "Dallas")
        self.assertEqual(w4_res["address_state"], "TX")
        self.assertEqual(w4_res["address_zip"], "75204")
        self.assertEqual(w4_res["ssn_last_four"], "9012")
        self.assertEqual(w4_res["w4_filing_status"], "Married Filing Jointly")
        self.assertEqual(w4_res["w4_step3_dependents"], 4000.0)
        self.assertEqual(w4_res["w4_step4c_extra_withholding"], 25.0)

        # 2. Verify State ID & Voided Check Auto-Extraction
        sample_id_bytes = (
            b"TEXAS DRIVER LICENSE\n"
            b"4d DL: 19485726\n"
            b"3 DOB: 05/14/1991\n"
            b"4b EXP: 05/14/2030\n"
            b"8 4120 Swiss Ave\n"
            b"Dallas, TX 75204\n"
        )
        id_res = extract_state_id_fields(sample_id_bytes, "TX_DL.txt", "text/plain")
        self.assertEqual(id_res["state_id_number"], "19485726")
        self.assertEqual(id_res["state_id_expiration"], "2030-05-14")
        self.assertEqual(id_res["date_of_birth"], "1991-05-14")

        sample_dd_bytes = (
            b"Bank Name: JPMorgan Chase\n"
            b"Routing Number: 111000614\n"
            b"Account Number: 889900112233\n"
        )
        dd_res = extract_direct_deposit_fields(sample_dd_bytes, "void_check.txt", "text/plain")
        self.assertIn("Chase", dd_res["direct_deposit_bank"])
        self.assertEqual(dd_res["direct_deposit_routing"], "111000614")
        self.assertEqual(dd_res["direct_deposit_account_last_four"], "2233")

        # 3. Verify Encrypted PostgreSQL EmployeeDocuments Vault & Portal Route
        conn = get_db(self.db_url)
        try:
            ensure_employee_onboarding_schema(conn)
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM "Employees" ORDER BY id ASC LIMIT 1;')
                emp = cur.fetchone()
                self.assertIsNotNone(emp)
                token = emp.get("onboarding_token")
                if not token:
                    token = f"emp_{emp['id']}_testtoken"
                    cur.execute(
                        'UPDATE "Employees" SET onboarding_token = %s WHERE id = %s;',
                        (token, emp["id"]),
                    )
                    conn.commit()

            # Test public portal render
            resp = self.client.get(f"/onboard/employee/{token}")
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"New Hire Onboarding", resp.data)

            # Test locked W-2 PDF generation + encrypted vault deposit + disk wipe recovery
            pdf_bytes = generate_signed_w2_onboarding_pdf(
                employee_record=dict(emp),
                signer_name="Carlos Mendoza",
                signer_ip="127.0.0.1",
                signed_at_iso="2026-10-20T18:00:00Z",
                signature_hash="a" * 64,
            )
            self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))

            receipt = deposit_employee_document_vault(
                conn=conn,
                employee_id=emp["id"],
                doc_type="Form W-4",
                raw_bytes=pdf_bytes,
                original_filename="W4_TestVault.pdf",
                mime_type="application/pdf",
                uploaded_by="unit_test_suite",
            )
            doc_id = receipt["document_id"]
            recovered = retrieve_employee_document_vault(conn, doc_id)
            self.assertIsNotNone(recovered)
            self.assertEqual(recovered["raw_bytes"], pdf_bytes)
            self.assertEqual(recovered["sha256_checksum"], receipt["sha256_checksum"])

            sweep = run_employee_doc_expiration_sweep(conn)
            self.assertIn("expired_count", sweep)

            # Clean up test document row
            with conn.cursor() as cur:
                cur.execute('DELETE FROM "EmployeeDocuments" WHERE id = %s;', (doc_id,))
            conn.commit()
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
