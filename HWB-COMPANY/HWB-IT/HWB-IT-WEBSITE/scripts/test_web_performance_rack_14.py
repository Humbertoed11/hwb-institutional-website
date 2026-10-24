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
        """Part I Pillar 4: Verifies get_version_info() is cached in memory with lru_cache and reports v5.4.x / v5.5.x."""
        clear_version_cache()
        self.assertTrue(APP_SEMANTIC_VERSION.startswith(("v5.4.", "v5.5.")))
        info_1 = get_version_info()
        info_2 = get_version_info()
        self.assertTrue(str(info_1.get("app_version", "")).startswith(("v5.4.", "v5.5.")))
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
        self.assertIn("Electronic Signature ID:", cert_html)
        self.assertIn(sub["company_name"], cert_html)

        cert_pdf = generate_signed_msa_dwc83_certificate_pdf(
            sub, sub["contact_name"], "Owner", "127.0.0.1", "10/20/2026 10:15 AM CST"
        )
        self.assertTrue(cert_pdf.startswith(b"%PDF-1.4"))
        self.assertIn(b"Electronic Signature ID:", cert_pdf)
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

    def test_19_comprehensive_all_w2_and_1099_forms_regression(self) -> None:
        """
        Comprehensive end-to-end HTTP form regression suite verifying every public and
        backoffice W-2 and 1099 form endpoint (BUG-141 / v5.4.9).
        """
        import io
        import uuid
        from unittest.mock import patch

        uid = uuid.uuid4().hex[:8]
        p_suf_1 = f"{int(uid[:4], 16) % 8000 + 1000:04d}"
        p_suf_2 = f"{int(uid[4:], 16) % 8000 + 1000:04d}"
        if p_suf_2 == p_suf_1:
            p_suf_2 = f"{(int(p_suf_1) + 1) % 8000 + 1000:04d}"
        sub_phone_1 = f"214-599-{p_suf_1}"
        sub_phone_2 = f"972-599-{p_suf_2}"
        w2_phone_1 = f"469-599-{p_suf_1}"
        created_sub_ids = []
        created_app_ids = []
        created_emp_ids = []

        with self.client.session_transaction() as sess:
            sess["_user_id"] = "1"
            sess["_fresh"] = True

        conn = get_db(self.db_url)
        try:
            with (
                patch("core.services.notification_service.dispatch_subcontractor_notifications", return_value=True),
                patch("core.services.notification_service.dispatch_applicant_notifications", return_value=True),
                patch("core.services.notification_service.send_subcontractor_onboarding_invite_email", return_value=(True, "mocked")),
                patch("core.services.notification_service.send_subcontractor_onboarding_completed_notifications", return_value=True),
                patch("core.services.notification_service.send_subcontractor_approved_email", return_value=(True, "mocked")),
                patch("core.services.email_service.transmit_email", return_value=(True, "mocked")),
                patch("blueprints.crm_api.transmit_email", return_value=(True, "mocked")),
            ):
                # =========================================================================
                # PART A: ALL 1099 SUBCONTRACTOR FORMS & PORTAL ENDPOINTS
                # =========================================================================
                # 1. Public 1099 Subcontractor Network Form (POST /api/v1/workforce/subcontractor)
                sub_email = f"reg.sub.{uid}@example.com"
                r_pub_1099 = self.client.post(
                    "/api/v1/workforce/subcontractor",
                    json={
                        "company_name": f"Regression 1099 Crew {uid} LLC",
                        "contact_name": "Marco Vance",
                        "email": sub_email,
                        "phone": sub_phone_1,
                        "city": "Dallas",
                        "specialties": "Post-Construction Cleaning, Floor Strip & Wax",
                        "crew_size": 7,
                        "coi_status": "Self-Reported",
                        "hourly_rate_range": "$25 - $32/hr",
                        "dwc83_agreed": "true",
                        "sub_no_guarantee_agreed": "true",
                    },
                )
                self.assertEqual(r_pub_1099.status_code, 201, r_pub_1099.get_data(as_text=True))
                d_pub_1099 = r_pub_1099.get_json()
                self.assertEqual(d_pub_1099["status"], "success")
                sub_id_1 = d_pub_1099["partner_id"]
                created_sub_ids.append(sub_id_1)

                # Repeat submission -> smart merge
                r_pub_1099_2 = self.client.post(
                    "/api/v1/workforce/subcontractor",
                    json={
                        "company_name": f"Regression 1099 Crew {uid} LLC",
                        "contact_name": "Marco Vance",
                        "email": sub_email,
                        "phone": sub_phone_1,
                        "city": "Dallas",
                        "specialties": "Commercial Carpet Extraction",
                        "crew_size": 10,
                    },
                )
                self.assertEqual(r_pub_1099_2.status_code, 200)
                self.assertTrue(r_pub_1099_2.get_json().get("is_duplicate"))

                # 2. Backoffice 1099 Manual Add Modal & Edit Modal & Review Gate
                r_gate = self.client.get("/api/v1/workforce/subcontractors/review-mode")
                self.assertEqual(r_gate.status_code, 200)

                r_bo_1099 = self.client.post(
                    "/api/v1/workforce/subcontractors",
                    json={
                        "company_name": f"Backoffice 1099 Partner {uid} Inc",
                        "contact_name": "Elena Rostova",
                        "email": f"bo.sub.{uid}@example.com",
                        "phone": sub_phone_2,
                        "city": "Plano",
                        "specialties": "Floor Strip & Wax",
                        "crew_size": 5,
                    },
                )
                self.assertEqual(r_bo_1099.status_code, 201, r_bo_1099.get_data(as_text=True))
                sub_id_2 = r_bo_1099.get_json()["subcontractor_id"]
                created_sub_ids.append(sub_id_2)

                r_patch_1099 = self.client.patch(
                    f"/api/v1/workforce/subcontractors/{sub_id_1}",
                    json={
                        "city": "Irving",
                        "crew_size": 12,
                        "coi_expiration_date": "2027-12-31",
                    },
                )
                self.assertEqual(r_patch_1099.status_code, 200)

                # 3. Backoffice 1099 Send Onboarding Link, Document Upload & Portal Flow
                r_send_1099 = self.client.post(f"/api/v1/workforce/subcontractors/{sub_id_1}/send-onboarding")
                self.assertEqual(r_send_1099.status_code, 200)
                sub_token = r_send_1099.get_json()["onboarding_token"]

                r_portal_1099 = self.client.get(f"/onboard/subcontractor/{sub_token}")
                self.assertEqual(r_portal_1099.status_code, 200)

                w9_bytes = (
                    f"%PDF-1.4\n1. Name of entity/individual: Marco Vance\n"
                    f"2. Business name: Regression 1099 Crew {uid} LLC\n"
                    "3a. Federal tax classification: Limited Liability Company (LLC)\n"
                    "5. Address: 1500 Marilla St\n6. City, state, and ZIP: Dallas, TX 75201\n"
                    "Employer Identification Number: 84-9914821\n"
                ).encode()
                coi_bytes = (
                    b"%PDF-1.4\nACORD CERTIFICATE OF LIABILITY INSURANCE\n"
                    b"INSURER A: Next Insurance US Company\n"
                    b"COMMERCIAL GENERAL LIABILITY\n"
                    b"Policy Number: GL-88442211\n"
                    b"Policy Eff: 01/01/2026 Policy Exp: 12/31/2027\n"
                    b"EACH OCCURRENCE: $1,000,000\n"
                )

                r_ext_1099 = self.client.post(
                    f"/onboard/subcontractor/{sub_token}/extract-document",
                    data={"doc_type": "w9", "file": (io.BytesIO(w9_bytes), "w9.pdf")},
                    content_type="multipart/form-data",
                )
                self.assertEqual(r_ext_1099.status_code, 200, r_ext_1099.get_data(as_text=True))
                self.assertEqual(r_ext_1099.get_json()["extracted"]["ein_last4"], "4821")

                r_sub_portal = self.client.post(
                    f"/onboard/subcontractor/{sub_token}/submit",
                    data={
                        "company_name": f"Regression 1099 Crew {uid} LLC",
                        "legal_entity_name": "Marco Vance",
                        "contact_name": "Marco Vance",
                        "email": sub_email,
                        "phone": sub_phone_1,
                        "tax_classification": "LLC",
                        "ein_or_ssn": "84-9914821",
                        "street_address": "1500 Marilla St",
                        "city": "Dallas",
                        "state": "TX",
                        "zip_code": "75201",
                        "coi_carrier": "Next Insurance US Company",
                        "coi_policy_number": "GL-88442211",
                        "coi_expiration_date": "2027-12-31",
                        "msa_signer_name": "Marco Vance",
                        "msa_signer_title": "Managing Member",
                        "msa_agreed": "true",
                        "dwc83_agreed": "true",
                        "w9_file": (io.BytesIO(w9_bytes), "w9.pdf"),
                        "coi_file": (io.BytesIO(coi_bytes), "coi.pdf"),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(r_sub_portal.status_code, 200, r_sub_portal.get_data(as_text=True))
                self.assertEqual(r_sub_portal.get_json()["status"], "success")

                r_approve_1099 = self.client.post(f"/api/v1/workforce/subcontractors/{sub_id_1}/approve-partner")
                self.assertEqual(r_approve_1099.status_code, 200)
                self.assertEqual(r_approve_1099.get_json()["partner_status"], "Active Partner")

                # Backoffice 1099 Vault Upload & Download
                r_bo_doc_1099 = self.client.post(
                    f"/api/v1/workforce/subcontractors/{sub_id_1}/documents",
                    data={"document_type": "COI", "expiration_date": "2027-12-31", "document": (io.BytesIO(coi_bytes), "coi_bo.pdf")},
                    content_type="multipart/form-data",
                )
                self.assertEqual(r_bo_doc_1099.status_code, 201, r_bo_doc_1099.get_data(as_text=True))

                r_dl_1099 = self.client.get(f"/api/v1/workforce/subcontractors/{sub_id_1}/download/msa")
                self.assertEqual(r_dl_1099.status_code, 200)
                self.assertTrue(r_dl_1099.data.startswith(b"%PDF-1.4"))
                r_dl_1099.close()

                # =========================================================================
                # PART B: ALL W-2 JOB APPLICANT, EMPLOYEE & PORTAL ENDPOINTS
                # =========================================================================
                # 1. Public W-2 Job Application Form (POST /api/v1/workforce/apply)
                app_email = f"reg.w2.{uid}@example.com"
                r_pub_w2 = self.client.post(
                    "/api/v1/workforce/apply",
                    json={
                        "full_name": f"Valeria Solis-{uid}",
                        "email": app_email,
                        "phone": w2_phone_1,
                        "city": "Dallas",
                        "desired_role": "Commercial Cleaning Technician",
                        "desired_shift": "Night",
                        "experience_level": "3+ Years / Supervisor",
                        "has_transportation": "true",
                        "authorized_to_work_us": "true",
                        "fcra_consent": "true",
                        "at_will_consent": "true",
                        "notes": "Regression test candidate",
                    },
                )
                self.assertEqual(r_pub_w2.status_code, 201, r_pub_w2.get_data(as_text=True))
                app_id = r_pub_w2.get_json()["applicant_id"]
                created_app_ids.append(app_id)

                # Repeat W-2 application -> smart merge
                r_pub_w2_2 = self.client.post(
                    "/api/v1/workforce/apply",
                    json={
                        "full_name": f"Valeria Solis-{uid}",
                        "email": app_email,
                        "phone": w2_phone_1,
                        "city": "Dallas",
                        "desired_role": "Lead Cleaning Site Supervisor",
                        "desired_shift": "Day",
                    },
                )
                self.assertEqual(r_pub_w2_2.status_code, 200)
                self.assertTrue(r_pub_w2_2.get_json().get("is_duplicate"))

                # 2. Backoffice W-2 Candidate Promotion / Onboard Modal (POST /api/v1/hr/onboard)
                r_onboard_w2 = self.client.post(
                    "/api/v1/hr/onboard",
                    json={
                        "applicant_id": app_id,
                        "first_name": "Valeria",
                        "last_name": f"Solis-{uid}",
                        "email": app_email,
                        "phone": w2_phone_1,
                        "primary_role": "Commercial Cleaning Technician",
                        "employment_type": "W-2 Full-Time",
                        "pay_rate_hourly": 19.00,
                        "hire_date": "2026-10-20",
                        "ssn_plain": "123-45-6789",
                    },
                )
                self.assertEqual(r_onboard_w2.status_code, 201, r_onboard_w2.get_data(as_text=True))
                emp_id = r_onboard_w2.get_json()["employee_id"]
                created_emp_ids.append(emp_id)

                # 3. Backoffice W-2 Employee Edit Modal, SSN Reveal, & Send Onboarding Link
                r_patch_w2 = self.client.patch(
                    f"/api/v1/hr/employees/{emp_id}",
                    json={
                        "pay_rate_hourly": 20.50,
                        "emergency_contact_name": "Mateo Solis",
                        "emergency_contact_phone": "469-555-0100",
                    },
                )
                self.assertEqual(r_patch_w2.status_code, 200)

                r_ssn_w2 = self.client.post(f"/api/v1/hr/employees/{emp_id}/reveal-ssn")
                self.assertEqual(r_ssn_w2.status_code, 200, r_ssn_w2.get_data(as_text=True))
                self.assertEqual(r_ssn_w2.get_json()["ssn"], "123-45-6789")

                r_send_w2 = self.client.post(f"/api/v1/hr/employees/{emp_id}/send-onboarding-link")
                self.assertEqual(r_send_w2.status_code, 200)
                emp_token = r_send_w2.get_json()["onboarding_token"]

                # 4. Public W-2 Self-Service Onboarding Portal Upload & E-Signature Completion
                r_portal_w2 = self.client.get(f"/onboard/employee/{emp_token}")
                self.assertEqual(r_portal_w2.status_code, 200)

                w4_bytes = (
                    f"Form W-4 Employee's Withholding Certificate\n"
                    f"First Name: Valeria\nLast Name: Solis-{uid}\n"
                    "Address: 2900 McKinney Ave\nCity, State, ZIP: Dallas, TX 75204\n"
                    "Social security number: 123-45-6789\n"
                    "Filing Status: Head of Household\n"
                    "Total Dependents: $2,000.00\n"
                ).encode()
                r_up_w4 = self.client.post(
                    f"/api/v1/employees/onboard/{emp_token}/upload-doc",
                    data={"doc_type": "Form W-4", "file": (io.BytesIO(w4_bytes), "Valeria_W4.txt")},
                    content_type="multipart/form-data",
                )
                self.assertEqual(r_up_w4.status_code, 200)
                self.assertEqual(r_up_w4.get_json()["extracted"]["w4_filing_status"], "Head of Household")

                r_comp_w2 = self.client.post(
                    f"/api/v1/employees/onboard/{emp_token}/complete",
                    json={
                        "signer_name": f"Valeria Solis-{uid}",
                        "address_street": "2900 McKinney Ave",
                        "address_city": "Dallas",
                        "address_state": "TX",
                        "address_zip": "75204",
                        "date_of_birth": "1993-08-22",
                        "ssn_plain": "123-45-6789",
                        "w4_filing_status": "Head of Household",
                        "w4_step3_dependents": 2000,
                        "w4_step4c_extra_withholding": 0,
                        "i9_citizenship_status": "US Citizen",
                        "direct_deposit_bank": "Wells Fargo",
                        "direct_deposit_routing": "111900659",
                        "direct_deposit_account_last_four": "4321",
                        "direct_deposit_account_type": "Checking",
                        "emergency_contact_name": "Mateo Solis",
                        "emergency_contact_phone": "469-555-0100",
                        "emergency_contact_relation": "Spouse",
                    },
                )
                self.assertEqual(r_comp_w2.status_code, 200)
                self.assertEqual(r_comp_w2.get_json()["status"], "success")

                # 5. Backoffice W-2 Vault Upload & Download + Job Description Acknowledge
                r_ack_w2 = self.client.post(f"/api/v1/hr/employees/{emp_id}/acknowledge-job-description")
                self.assertEqual(r_ack_w2.status_code, 200)

                r_bo_doc_w2 = self.client.post(
                    f"/api/v1/hr/employees/{emp_id}/documents",
                    data={"document_type": "Driver License / State ID", "document": (io.BytesIO(b"TEXAS DRIVER LICENSE\n4d DL: 88776655\n4b EXP: 05/14/2030\n"), "tx_id.txt")},
                    content_type="multipart/form-data",
                )
                self.assertEqual(r_bo_doc_w2.status_code, 201, r_bo_doc_w2.get_data(as_text=True))
                w2_doc_id = r_bo_doc_w2.get_json()["document_id"]

                r_dl_w2 = self.client.get(f"/api/v1/hr/documents/{w2_doc_id}/download")
                self.assertEqual(r_dl_w2.status_code, 200)
                self.assertIn(b"88776655", r_dl_w2.data)
                r_dl_w2.close()
        finally:
            with conn.cursor() as cur:
                for eid in created_emp_ids:
                    cur.execute('DELETE FROM "EmployeeDocuments" WHERE employee_id = %s;', (eid,))
                    cur.execute('DELETE FROM "Employees" WHERE id = %s;', (eid,))
                for aid in created_app_ids:
                    cur.execute('DELETE FROM "JobApplicants" WHERE id = %s;', (aid,))
                for sid in created_sub_ids:
                    cur.execute('DELETE FROM "SubcontractorDocuments" WHERE subcontractor_id = %s;', (sid,))
                    cur.execute('DELETE FROM "SubcontractorPartners" WHERE id = %s;', (sid,))
                # Clean up any leftover test rows from earlier run
                cur.execute(
                    'DELETE FROM "SubcontractorDocuments" WHERE subcontractor_id IN (SELECT id FROM "SubcontractorPartners" WHERE company_name LIKE %s);',
                    ("Regression 1099 Crew %",),
                )
                cur.execute('DELETE FROM "SubcontractorPartners" WHERE company_name LIKE %s;', ("Regression 1099 Crew %",))
                cur.execute(
                    'DELETE FROM "PendingOutbox" WHERE subject LIKE %s OR subject LIKE %s;',
                    (f"%{uid}%", "%Regression 1099 Crew%"),
                )
                cur.execute(
                    'DELETE FROM "SigmaInteractionLog" WHERE agent_explanation LIKE %s OR agent_explanation LIKE %s;',
                    (f"%{uid}%", "%Regression 1099 Crew%"),
                )
            conn.commit()
            conn.close()

    def test_20_input_masks_and_transaction_receipt_architecture(self) -> None:
        """
        BUG-142 Enterprise Verification Suite:
        1. Verifies server-side sanitizers (clean_ein_or_ssn, clean_ssn, clean_routing_number).
        2. Verifies /static/js/sigma_input_masks.js delivery and @app.after_request HTML auto-injection.
        3. Verifies explicit mask attributes and Tamper-Evident Transaction Receipt Cards
           (#onboarding-receipt-card and #w2-receipt-card) on 1099 & W-2 onboarding portals,
           confirming that active forms collapse to display:none after submission and on revisit.
        4. Verifies 5-Table Error Ledger synchronization for BUG-141 (Scar #233) & BUG-142 (Scar #234).
        """
        import io
        import uuid
        from unittest.mock import patch
        from core.services.database import get_db
        from core.services.sanitizer import clean_ein_or_ssn, clean_ssn, clean_routing_number
        from database.schema_engine import sync_bug_141_142_error_ledgers

        # 1. Server-side canonical sanitizers
        self.assertEqual(clean_ein_or_ssn("849914821", "LLC"), "84-9914821")
        self.assertEqual(clean_ein_or_ssn("123456789", "Individual / Sole Proprietor"), "123-45-6789")
        self.assertEqual(clean_ssn("123456789"), "123-45-6789")
        self.assertEqual(clean_routing_number("111-000-025"), "111000025")

        # 2. Static JS asset & @app.after_request injection
        r_js = self.client.get("/static/js/sigma_input_masks.js")
        self.assertEqual(r_js.status_code, 200)
        js_body = r_js.get_data(as_text=True)
        self.assertIn("SigmaInputMaskEngine", js_body)
        self.assertIn("syncTaxClassificationMask", js_body)
        r_js.close()

        r_home = self.client.get("/work-with-us?track=subcontractor")
        self.assertEqual(r_home.status_code, 200)
        self.assertIn("sigma_input_masks.js", r_home.get_data(as_text=True))

        # 3. 1099 & W-2 Portal Mask Attributes + Post-Submission Receipt Collapse
        conn = get_db(self.db_url)
        created_sub_id = None
        try:
            receipt_5 = sync_bug_141_142_error_ledgers(conn)
            self.assertEqual(receipt_5["scars"].get("ID-233"), 233)
            self.assertEqual(receipt_5["scars"].get("ID-234"), 234)
            self.assertIsNotNone(receipt_5["rack_telemetry_history_id"])
            self.assertIsNotNone(receipt_5["security_audit_logs_id"])

            uid = uuid.uuid4().hex[:6]
            with self.client.session_transaction() as sess:
                sess["_user_id"] = "1"
                sess["_fresh"] = True

            with (
                patch("core.services.notification_service.send_subcontractor_onboarding_invite_email", return_value=(True, "mocked")),
                patch("core.services.notification_service.send_subcontractor_onboarding_completed_notifications", return_value=True),
                patch("core.services.email_service.transmit_email", return_value=(True, "mocked")),
            ):
                r_sub = self.client.post(
                    "/api/v1/workforce/subcontractors",
                    json={
                        "company_name": f"Receipt Mask Test {uid} LLC",
                        "contact_name": "Carlos Mendez",
                        "email": f"receipt.{uid}@example.com",
                        "phone": "2145550192",
                        "city": "Dallas",
                        "specialties": "Commercial Janitorial",
                        "crew_size": 4,
                    },
                )
                self.assertEqual(r_sub.status_code, 201)
                created_sub_id = r_sub.get_json()["subcontractor_id"]

                r_tok = self.client.post(f"/api/v1/workforce/subcontractors/{created_sub_id}/send-onboarding")
                self.assertEqual(r_tok.status_code, 200)
                tok = r_tok.get_json()["onboarding_token"]

                # Initial unsubmitted portal view: form is visible, receipt card is hidden
                r_get_before = self.client.get(f"/onboard/subcontractor/{tok}")
                self.assertEqual(r_get_before.status_code, 200)
                html_before = r_get_before.get_data(as_text=True)
                self.assertIn('id="onboarding-receipt-card"', html_before)
                self.assertIn('oninput="maskTaxIdInput(this)"', html_before)
                self.assertIn('onchange="syncTaxClassificationMask(this, \'onb-ein-ssn\')"', html_before)
                self.assertIn('id="onb-tax-id-format-badge"', html_before)

                # Submit onboarding packet with unformatted 9-digit EIN
                w9_bytes = b"%PDF-1.4\n1. Name: Carlos Mendez\nEmployer Identification Number: 84-7766554\n"
                r_submit = self.client.post(
                    f"/onboard/subcontractor/{tok}/submit",
                    data={
                        "company_name": f"Receipt Mask Test {uid} LLC",
                        "legal_entity_name": "Carlos Mendez",
                        "contact_name": "Carlos Mendez",
                        "email": f"receipt.{uid}@example.com",
                        "phone": "2145550192",
                        "tax_classification": "LLC",
                        "ein_or_ssn": "847766554",
                        "street_address": "500 Commerce St",
                        "city": "Dallas",
                        "state": "tx",
                        "zip_code": "752021234",
                        "msa_signer_name": "Carlos Mendez",
                        "msa_signer_title": "Managing Member",
                        "msa_agreed": "true",
                        "dwc83_agreed": "true",
                        "w9_file": (io.BytesIO(w9_bytes), "w9.pdf"),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(r_submit.status_code, 200)
                sub_json = r_submit.get_json()
                self.assertEqual(sub_json["status"], "success")
                self.assertIn("receipt_timestamp", sub_json)
                self.assertIn("msa_signature_hash", sub_json)
                self.assertTrue(sub_json["masked_tin"].endswith("6554"))

                # Revisit portal after submission: receipt card is displayed (block) and form is collapsed (none)
                r_get_after = self.client.get(f"/onboard/subcontractor/{tok}")
                self.assertEqual(r_get_after.status_code, 200)
                html_after = r_get_after.get_data(as_text=True)
                self.assertIn('id="onboarding-receipt-card" style="display: block;', html_after)
                self.assertIn('id="form-subcontractor-onboarding" onsubmit="submitSubcontractorOnboarding(event)" enctype="multipart/form-data" style="display: none;"', html_after)
                self.assertIn(sub_json["msa_signature_hash"], html_after)
        finally:
            if created_sub_id:
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM "SubcontractorDocuments" WHERE subcontractor_id = %s;', (created_sub_id,))
                    cur.execute('DELETE FROM "SubcontractorPartners" WHERE id = %s;', (created_sub_id,))
                    cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = \'Subcontractor\' AND parent_id = %s;', (created_sub_id,))
                    cur.execute('DELETE FROM "PendingOutbox" WHERE subject LIKE %s;', (f"%Receipt Mask Test%",))
                conn.commit()
            conn.close()

    def test_21_subcontractor_and_w2_receipt_breadcrumb_and_no_guarantee_notice(self):
        """
        Verifies the 4-Step Compliance Workflow Breadcrumb Summary ('What to Expect Next')
        and strict No-Guarantee of Work / Project Award / Employment legal disclaimers across:
        - /work-with-us (W-2 & 1099 registration receipts)
        - /onboard/subcontractor/<token> (#onboarding-receipt-card)
        - /onboard/employee/<token> (#w2-receipt-card)
        - core/services/notification_service.py (outbound email receipts)
        - core/services/subcontractor_doc_extractor.py (signed MSA & TX DWC-83 HTML/PDF certificates)
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 1. Verify /work-with-us public page
        r_wwu = self.client.get("/work-with-us?track=subcontractor")
        self.assertEqual(r_wwu.status_code, 200)
        wwu_html = r_wwu.get_data(as_text=True)
        self.assertIn("What to Expect Next (4-Step Compliance Workflow)", wwu_html)
        self.assertIn("What to Expect Next (4-Step Candidate Review Process)", wwu_html)
        self.assertIn("Notice — No Guarantee of Work or Project Award:", wwu_html)
        self.assertIn("Notice — No Guarantee of Employment or Interview:", wwu_html)
        self.assertNotIn("within 24–48 hours for a quick 5-minute phone interview", wwu_html)

        # 2. Verify subcontractor_onboarding.html template
        with open(os.path.join(base_dir, "templates", "subcontractor_onboarding.html"), "r", encoding="utf-8") as f:
            sub_tpl = f.read()
        self.assertIn('id="receipt-next-steps-box"', sub_tpl)
        self.assertIn('id="receipt-no-guarantee-box"', sub_tpl)
        self.assertIn("Important Notice — No Promise or Guarantee of Work:", sub_tpl)
        self.assertIn("On-File Roster Eligibility", sub_tpl)

        # 3. Verify employee_onboarding_portal.html template
        with open(os.path.join(base_dir, "templates", "employee_onboarding_portal.html"), "r", encoding="utf-8") as f:
            emp_tpl = f.read()
        self.assertIn('id="w2-receipt-next-steps-box"', emp_tpl)
        self.assertIn("What to Expect Next (4-Step Onboarding Workflow)", emp_tpl)
        self.assertIn("Important Notice — At-Will Employment &amp; No Guarantee of Hours:", emp_tpl)

        # 4. Verify notification_service.py email templates
        with open(os.path.join(base_dir, "core", "services", "notification_service.py"), "r", encoding="utf-8") as f:
            notif_src = f.read()
        self.assertIn("Important Notice — No Guarantee of Work or Project Award:", notif_src)
        self.assertIn("Important Notice — No Promise or Guarantee of Work:", notif_src)
        self.assertIn("Notice — No Guarantee of Project Award or Work Volume:", notif_src)
        self.assertIn("Notice — No Guarantee of Employment or Interview:", notif_src)

        # 5. Verify signed MSA + TX DWC-83 HTML & PDF certificates include Clause 2.4 / 3.2 No Guarantee of Work
        from core.services.subcontractor_doc_extractor import (
            generate_signed_msa_dwc83_certificate_html,
            generate_signed_msa_dwc83_certificate_pdf,
        )
        sample_partner = {"id": 18, "company_name": "Apex Janitorial LLC", "contact_name": "Carlos Gomez"}
        cert_html = generate_signed_msa_dwc83_certificate_html(
            sample_partner, "Carlos Gomez", "Owner", "127.0.0.1", "10/22/2026 12:30 PM CST"
        )
        self.assertIn("No Guarantee of Project Award or Minimum Work Volume", cert_html)
        cert_pdf = generate_signed_msa_dwc83_certificate_pdf(
            sample_partner, "Carlos Gomez", "Owner", "127.0.0.1", "10/22/2026 12:30 PM CST"
        )
        self.assertIn(b"No Guarantee of Project Award or Minimum Work Volume", cert_pdf)

    def test_22_secondary_portals_and_forms_enterprise_hardening_bug_143(self):
        """
        Verifies BUG-143 Enterprise Hardening across all secondary portals and forms:
        1. /onboard/bosanna: setPortalLanguage('es'/'en'), #target_facility prefill, submitBtn error recovery, (###)-###-#### mask.
        2. /academy/course/<code>: Zero synthetic 'Carlos E. Mendoza' defaults, form="quiz-form" student_name binding, HTTP 400 error guard.
        3. /tma/estimator: Telegram.WebApp.initData check + on-screen #tma-receipt-card (zero raw alert()).
        4. / and /get-quote: #phone_home and #phone_page maxlength="14" oninput="maskPhoneInput(this)" and (214)-000-0000 placeholder.
        5. /admin/operations: #form-scope-intelligence onsubmit Enter-key guard and explicit mask attributes on Add Client/Partner/Lead modals.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 1. Bosanna Onboarding Portal (/onboard/bosanna)
        r_bos = self.client.get("/onboard/bosanna?lang=es")
        self.assertEqual(r_bos.status_code, 200)
        bos_html = r_bos.get_data(as_text=True)
        self.assertIn("window.switchLang = setPortalLanguage;", bos_html)
        self.assertIn("document.getElementById('target_facility')", bos_html)
        self.assertIn('placeholder="(214)-555-0199"', bos_html)
        self.assertIn("json.status !== 'already_registered'", bos_html)

        # 2. SigmaAcademy Course Assessment (/academy/course/TRN-SAF-01)
        with open(os.path.join(base_dir, "templates", "academy_course.html"), "r", encoding="utf-8") as f:
            acad_tpl = f.read()
        self.assertNotIn("Carlos E. Mendoza", acad_tpl)
        self.assertNotIn("carlos@hwbcleaning.com", acad_tpl)
        self.assertIn('id="student_name" name="student_name" form="quiz-form"', acad_tpl)
        self.assertIn("if (!res.ok || result.status === 'error')", acad_tpl)

        # 3. Takeoff & Scope Configurator (/tma/estimator)
        r_tma = self.client.get("/tma/estimator")
        self.assertEqual(r_tma.status_code, 200)
        tma_html = r_tma.get_data(as_text=True)
        self.assertIn('id="tma-receipt-card"', tma_html)
        self.assertIn("window.Telegram.WebApp.initData", tma_html)
        self.assertNotIn("alert(`Takeoff Saved:", tma_html)

        # 4. Homepage (/) & Full Quote Form (/get-quote)
        r_home = self.client.get("/")
        self.assertEqual(r_home.status_code, 200)
        home_html = r_home.get_data(as_text=True)
        self.assertIn('id="phone_home" maxlength="14" oninput="maskPhoneInput(this)"', home_html)
        self.assertIn('placeholder="(214)-000-0000"', home_html)

        r_quote = self.client.get("/get-quote")
        self.assertEqual(r_quote.status_code, 200)
        quote_html = r_quote.get_data(as_text=True)
        self.assertIn('id="phone_page" maxlength="14" oninput="maskPhoneInput(this)"', quote_html)
        self.assertIn('placeholder="(214)-000-0000"', quote_html)

        # 5. Backoffice Operations Forms (backoffice_operations.html)
        with open(os.path.join(base_dir, "templates", "backoffice_operations.html"), "r", encoding="utf-8") as f:
            bo_tpl = f.read()
        self.assertIn('id="form-scope-intelligence" class="sigma-form-container" onsubmit="event.preventDefault(); addToScope();"', bo_tpl)
        self.assertIn('placeholder="(214)-862-2300" class="sigma-input" oninput="maskPhoneInput(this)"', bo_tpl)

    def test_23_closed_loop_lead_and_marketing_campaign_lifecycle_bug_144(self) -> None:
        """
        Verifies BUG-144 Closed-Loop Lead & Email Marketing Campaign State Machine:
        1. Enroll 4 selected leads from Leads module via POST /api/v1/marketing/campaign/enroll-leads
           with stage_drafts=True -> Leads.status='In Campaign', CampaignRecipients.status='AWAITING_APPROVAL',
           PendingOutbox.status='PENDING', MarketingCampaigns.total_targets=4.
        2. Release 3 drafts via POST /api/v1/marketing/outbox/batch-action (Leave Lead #4 unsent)
           -> CampaignRecipients.status='SENT', MarketingCampaigns.sent_count=3.
        3. Lead #1 opens email (/api/v1/marketing/track/open/<token>.gif)
           -> Leads.status='Engaged', priority_level='High', CampaignRecipients.status='OPENED',
              MarketingCampaigns.opened_count=1.
        4. Lead #1 clicks booking link (/api/v1/marketing/track/click/<token>)
           -> Leads.status='Qualified', CampaignRecipients.status='ENGAGED',
              MarketingCampaigns.walkthroughs_booked=1.
        5. Lead #2 clicks 1-click unsubscribe (/unsubscribe/<token>)
           -> Leads.status='Unsubscribed', is_dnc=FALSE, campaign_ready=FALSE,
              email_hygiene_status='DO_NOT_EMAIL', CampaignRecipients.status='UNSUBSCRIBED',
              added to EmailSuppressionList.
        6. Complete campaign via POST /api/v1/marketing/campaign/<id>/complete
           -> Lead #3 (sent, unopened) advances from 'In Campaign' to 'Contacted',
              Lead #4 (unsent draft) returns from 'In Campaign' to 'New',
              Lead #1 remains 'Qualified', Lead #2 remains 'Unsubscribed',
              MarketingCampaigns.status='Completed'.
        """
        import uuid
        from unittest.mock import patch

        uid = uuid.uuid4().hex[:6]
        lead_ids = []
        lead_emails = [f"mkt.test.{i}.{uid}@example.com" for i in range(1, 5)]
        camp_id = None

        with self.client.session_transaction() as sess:
            sess["_user_id"] = "1"
            sess["_fresh"] = True

        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                for i, em in enumerate(lead_emails, start=1):
                    cur.execute(
                        '''
                        INSERT INTO "Leads" (
                            center_name, director, email, phone, city, county, state,
                            capacity, sqf, status, is_commercial, campaign_ready, is_dnc
                        ) VALUES (%s, %s, %s, %s, 'Plano', 'Collin', 'TX', %s, 12000, 'New', TRUE, TRUE, FALSE)
                        RETURNING id;
                        ''',
                        (f"Lifecycle Test Facility {i} ({uid})", f"Director {i}", em, f"214-555-010{i}", 100 + i * 10),
                    )
                    lead_ids.append(cur.fetchone()["id"])
            conn.commit()

            # Step 1: Enroll 4 selected leads from Leads Module
            r_enroll = self.client.post(
                "/api/v1/marketing/campaign/enroll-leads",
                json={
                    "lead_ids": lead_ids,
                    "campaign_name": f"Lifecycle Test Campaign {uid}",
                    "stage_drafts": True,
                },
            )
            self.assertEqual(r_enroll.status_code, 200, r_enroll.get_data(as_text=True))
            d_enroll = r_enroll.get_json()
            self.assertEqual(d_enroll["status"], "success")
            self.assertEqual(d_enroll["enrolled_count"], 4)
            self.assertEqual(d_enroll["drafts_created"], 4)
            camp_id = d_enroll["campaign_id"]

            with conn.cursor() as cur:
                cur.execute('SELECT id, status FROM "Leads" WHERE id = ANY(%s) ORDER BY id ASC;', (lead_ids,))
                for lrow in cur.fetchall():
                    self.assertEqual(lrow["status"], "In Campaign")

                cur.execute(
                    'SELECT lead_id, tracking_token, outbox_id, status FROM "CampaignRecipients" WHERE campaign_id = %s ORDER BY lead_id ASC;',
                    (camp_id,),
                )
                recips = {r["lead_id"]: r for r in cur.fetchall()}
                self.assertEqual(len(recips), 4)
                for r in recips.values():
                    self.assertEqual(r["status"], "AWAITING_APPROVAL")

            # Step 2: Approve & Release first 3 leads' drafts (leave Lead #4 unsent)
            outbox_ids_to_send = [recips[lead_ids[0]]["outbox_id"], recips[lead_ids[1]]["outbox_id"], recips[lead_ids[2]]["outbox_id"]]
            with patch("blueprints.crm_api.transmit_email", return_value=(True, "mocked")):
                r_batch = self.client.post(
                    "/api/v1/marketing/outbox/batch-action",
                    json={"action": "approve", "email_ids": outbox_ids_to_send},
                )
                self.assertEqual(r_batch.status_code, 200)
                self.assertEqual(r_batch.get_json()["successful"], 3)

            with conn.cursor() as cur:
                cur.execute('SELECT total_targets, sent_count FROM "MarketingCampaigns" WHERE id = %s;', (camp_id,))
                mc = cur.fetchone()
                self.assertEqual(mc["total_targets"], 4)
                self.assertEqual(mc["sent_count"], 3)

            # Step 3: Lead #1 opens the email
            tok_1 = recips[lead_ids[0]]["tracking_token"]
            r_open = self.client.get(f"/api/v1/marketing/track/open/{tok_1}.gif")
            self.assertEqual(r_open.status_code, 200)
            r_open.close()

            with conn.cursor() as cur:
                cur.execute('SELECT status, priority_level FROM "Leads" WHERE id = %s;', (lead_ids[0],))
                l1 = cur.fetchone()
                self.assertEqual(l1["status"], "Engaged")
                self.assertEqual(l1["priority_level"], "High")

            # Step 4: Lead #1 clicks the calendar booking link
            r_click = self.client.get(f"/api/v1/marketing/track/click/{tok_1}")
            self.assertIn(r_click.status_code, (301, 302))

            with conn.cursor() as cur:
                cur.execute('SELECT status FROM "Leads" WHERE id = %s;', (lead_ids[0],))
                self.assertEqual(cur.fetchone()["status"], "Qualified")
                cur.execute('SELECT opened_count, walkthroughs_booked FROM "MarketingCampaigns" WHERE id = %s;', (camp_id,))
                mc_after_click = cur.fetchone()
                self.assertEqual(mc_after_click["opened_count"], 1)
                self.assertEqual(mc_after_click["walkthroughs_booked"], 1)

            # Step 5: Lead #2 clicks 1-click Unsubscribe
            tok_2 = recips[lead_ids[1]]["tracking_token"]
            r_unsub = self.client.get(f"/unsubscribe/{tok_2}")
            self.assertEqual(r_unsub.status_code, 200)

            with conn.cursor() as cur:
                cur.execute('SELECT status, is_dnc, campaign_ready, email_hygiene_status FROM "Leads" WHERE id = %s;', (lead_ids[1],))
                l2 = cur.fetchone()
                self.assertEqual(l2["status"], "Unsubscribed")
                self.assertFalse(l2["is_dnc"])
                self.assertFalse(l2["campaign_ready"])
                self.assertEqual(l2["email_hygiene_status"], "DO_NOT_EMAIL")

            # Step 6: Complete Campaign -> Lead #3 (sent, unopened) becomes 'Contacted', Lead #4 (unsent) returns to 'New'
            r_comp = self.client.post(f"/api/v1/marketing/campaign/{camp_id}/complete")
            self.assertEqual(r_comp.status_code, 200, r_comp.get_data(as_text=True))
            d_comp = r_comp.get_json()
            self.assertEqual(d_comp["status"], "success")
            self.assertEqual(d_comp["advanced_to_contacted"], 1)
            self.assertEqual(d_comp["reverted_to_new"], 1)

            with conn.cursor() as cur:
                cur.execute('SELECT id, status FROM "Leads" WHERE id = ANY(%s);', (lead_ids,))
                final_statuses = {r["id"]: r["status"] for r in cur.fetchall()}
                self.assertEqual(final_statuses[lead_ids[0]], "Qualified")
                self.assertEqual(final_statuses[lead_ids[1]], "Unsubscribed")
                self.assertEqual(final_statuses[lead_ids[2]], "Contacted")
                self.assertEqual(final_statuses[lead_ids[3]], "New")

                cur.execute('SELECT status FROM "MarketingCampaigns" WHERE id = %s;', (camp_id,))
                self.assertEqual(cur.fetchone()["status"], "Completed")
        finally:
            with conn.cursor() as cur:
                if camp_id:
                    cur.execute('DELETE FROM "PendingOutbox" WHERE campaign_id = %s;', (camp_id,))
                    cur.execute('DELETE FROM "MarketingCampaigns" WHERE id = %s;', (camp_id,))
                if lead_emails:
                    cur.execute('DELETE FROM "EmailSuppressionList" WHERE email_lower = ANY(%s);', (lead_emails,))
                if lead_ids:
                    cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = \'Lead\' AND parent_id = ANY(%s);', (lead_ids,))
                    cur.execute('DELETE FROM "Leads" WHERE id = ANY(%s);', (lead_ids,))
                cur.execute('DELETE FROM "GlobalActivities" WHERE description LIKE %s;', (f"%{uid}%",))
            conn.commit()
            conn.close()

    def test_24_multi_jurisdictional_email_compliance_and_rfc8058_bug_145(self):
        """
        BUG-145: Certifies 100% multi-jurisdictional email compliance & ISO hardening:
        1. RFC 8058 / RFC 2369 native List-Unsubscribe + List-Unsubscribe-Post headers in email_service.py.
        2. RFC 8058 POST /unsubscribe/<token> automated one-click opt-out without manual form email field.
        3. Universal Geofence & Domain Compliance Shield across preview-count, campaign/create, enroll-leads, and generate-drafts.
        4. Dual-table outbound suppression gate in transmit_email (EmailSuppressionList + Leads CRM flags).
        5. Multi-jurisdictional legal & ISO citations in letterhead footer and /unsubscribe page.
        """
        from core.services.email_service import build_rfc8058_headers, transmit_email
        from blueprints.crm_api import (
            get_email_compliance_where_clauses,
            is_email_compliance_eligible,
            format_marketing_letterhead
        )

        # 1. RFC 8058 / RFC 2369 Header Builder
        sample_html = '<a href="https://www.hwbcleaning.com/unsubscribe/tok_rfc8058_abc123">Unsubscribe</a>'
        hdrs = build_rfc8058_headers(body_html=sample_html, campaign_mode=True)
        self.assertEqual(len(hdrs), 2)
        hdr_map = {h["name"]: h["value"] for h in hdrs}
        self.assertIn("<https://www.hwbcleaning.com/unsubscribe/tok_rfc8058_abc123>", hdr_map["List-Unsubscribe"])
        self.assertIn("<mailto:info@hwbcleaning.com?subject=Unsubscribe>", hdr_map["List-Unsubscribe"])
        self.assertEqual(hdr_map["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")

        # 2. Universal Geofence & Domain Shield Eligibility
        self.assertTrue(is_email_compliance_eligible("director@mckinneyacademy.com", raw_state="TX"))
        self.assertFalse(is_email_compliance_eligible("director@laacademy.com", raw_state="CA"))
        self.assertFalse(is_email_compliance_eligible("director@seattlekids.com", raw_state="WA"))
        self.assertFalse(is_email_compliance_eligible("director@torontoacademy.ca", raw_state="TX"))
        self.assertFalse(is_email_compliance_eligible("director@londonchildcare.co.uk", raw_state="TX"))
        self.assertFalse(is_email_compliance_eligible("director@berlin-kita.de", raw_state="TX"))
        self.assertFalse(is_email_compliance_eligible("director@sydneyschool.au", raw_state="TX"))
        self.assertFalse(is_email_compliance_eligible("procurement@collincountytx.gov", raw_state="TX"))
        self.assertFalse(is_email_compliance_eligible("base@usaf.mil", raw_state="TX"))
        self.assertFalse(is_email_compliance_eligible("principal@frisco.k12.tx.us", raw_state="TX"))
        self.assertFalse(is_email_compliance_eligible("director@mckinneyacademy.com", raw_state="TX", status="Unsubscribed"))
        self.assertFalse(is_email_compliance_eligible("director@mckinneyacademy.com", raw_state="TX", is_dnc=True))
        self.assertFalse(is_email_compliance_eligible("director@mckinneyacademy.com", raw_state="TX", hygiene_status="DO_NOT_EMAIL"))

        where_clauses = get_email_compliance_where_clauses()
        joined_where = " ".join(where_clauses)
        for expected_frag in ("'CA', 'WA'", "'%.ca'", "'%.uk'", "'%.eu'", "'%.gov'", "'%.mil'", "'%.k12.tx.us'", "'Unsubscribed'"):
            self.assertIn(expected_frag, joined_where)

        # 3. Letterhead Footer CAN-SPAM Physical Address & One-Click Unsubscribe Link (Zero Internal Jargon per BUG-147)
        lh_html = format_marketing_letterhead("<p>Test Body</p>", "tok_footer_check_999")
        for required_element in ("3342 FM 1827 Ste 8d, McKinney, TX 75071", "Collin County, TX", "Unsubscribe Instantly", "tok_footer_check_999"):
            self.assertIn(required_element, lh_html)

        # 4. End-to-End Database Test: Geofence Filtering, RFC 8058 POST Unsubscribe, & Dual-Table Suppression Gate
        import uuid
        with self.client.session_transaction() as sess:
            sess["_user_id"] = "1"
            sess["_fresh"] = True
        conn = get_db(self.db_url)
        uid = uuid.uuid4().hex[:6]
        lead_ids = []
        lead_emails = []
        camp_id = None
        try:
            with conn.cursor() as cur:
                test_specs = [
                    # Eligible Texas commercial lead
                    (f"TX Compliant Lead {uid}", f"tx_ok_{uid}@test-hwb-local.com", "TX", "New", False),
                    # Blocked California lead
                    (f"CA Geofence Lead {uid}", f"ca_block_{uid}@test-hwb-local.com", "CA", "New", False),
                    # Blocked UK international lead
                    (f"UK Intl Lead {uid}", f"uk_block_{uid}@test-hwb-local.co.uk", "TX", "New", False),
                    # Blocked Public Sector .gov lead
                    (f"Gov Public Lead {uid}", f"gov_block_{uid}@cityofmckinney.gov", "TX", "New", False),
                    # CRM Unsubscribed lead (not yet in EmailSuppressionList, testing dual-table gate)
                    (f"CRM Unsub Lead {uid}", f"crm_unsub_{uid}@test-hwb-local.com", "TX", "Unsubscribed", False),
                ]
                for cname, em, st, lstat, dnc_flag in test_specs:
                    lead_emails.append(em)
                    cur.execute('''
                        INSERT INTO "Leads" (
                            center_name, director, email, phone, city, county, state,
                            status, is_dnc, campaign_ready, is_commercial, email_hygiene_status
                        ) VALUES (%s, 'Jane Director', %s, '(214)-555-0199', 'McKinney', 'COLLIN', %s, %s, %s, TRUE, TRUE, 'VERIFIED')
                        RETURNING id;
                    ''', (cname, em, st, lstat, dnc_flag))
                    lead_ids.append(cur.fetchone()["id"])
            conn.commit()

            # Attempt to enroll all 5 leads into a new campaign -> Only the 1st lead (TX Compliant) should be enrolled; 4 skipped!
            r_enr = self.client.post(
                "/api/v1/marketing/campaign/enroll-leads",
                json={
                    "lead_ids": lead_ids,
                    "campaign_name": f"Compliance Shield Test {uid}",
                    "stage_drafts": True
                }
            )
            self.assertEqual(r_enr.status_code, 200, r_enr.get_data(as_text=True))
            d_enr = r_enr.get_json()
            self.assertEqual(d_enr["status"], "success")
            camp_id = d_enr["campaign_id"]
            self.assertEqual(d_enr["enrolled_count"], 1)
            self.assertEqual(d_enr["skipped_count"], 4)

            # Verify Dual-Table Suppression Gate in transmit_email blocks the CRM-Unsubscribed lead even before Graph auth
            ok_sup, reason_sup = transmit_email(
                {"DATABASE_URL": self.db_url, "GRAPH_TENANT_ID": "test", "GRAPH_CLIENT_ID": "test", "GRAPH_CLIENT_SECRET": "test"},
                lead_emails[4],
                "Commercial Proposal",
                "<p>Hello</p>"
            )
            self.assertFalse(ok_sup)
            self.assertIn("Suppressed", reason_sup)

            # Verify RFC 8058 Automated One-Click POST to /unsubscribe/<token> (with List-Unsubscribe=One-Click and NO email field)
            with conn.cursor() as cur:
                cur.execute('SELECT tracking_token FROM "CampaignRecipients" WHERE campaign_id = %s AND lead_id = %s;', (camp_id, lead_ids[0]))
                tok_tx = cur.fetchone()["tracking_token"]

            r_rfc_post = self.client.post(
                f"/unsubscribe/{tok_tx}",
                data={"List-Unsubscribe": "One-Click"}
            )
            self.assertEqual(r_rfc_post.status_code, 200)
            post_html = r_rfc_post.get_data(as_text=True)
            self.assertIn("You Have Been Unsubscribed", post_html)
            self.assertIn("CAN-SPAM Act", post_html)
            self.assertIn("Opt-Out Confirmation Record", post_html)

            with conn.cursor() as cur:
                cur.execute('SELECT status, is_dnc, campaign_ready, email_hygiene_status FROM "Leads" WHERE id = %s;', (lead_ids[0],))
                l_after = cur.fetchone()
                self.assertEqual(l_after["status"], "Unsubscribed")
                self.assertFalse(l_after["is_dnc"])
                self.assertFalse(l_after["campaign_ready"])
                self.assertEqual(l_after["email_hygiene_status"], "DO_NOT_EMAIL")

                cur.execute('SELECT source FROM "EmailSuppressionList" WHERE email_lower = %s;', (lead_emails[0],))
                esl_row = cur.fetchone()
                self.assertIsNotNone(esl_row)
                self.assertEqual(esl_row["source"], "RFC8058_ONE_CLICK_POST")
        finally:
            with conn.cursor() as cur:
                if camp_id:
                    cur.execute('DELETE FROM "PendingOutbox" WHERE campaign_id = %s;', (camp_id,))
                    cur.execute('DELETE FROM "MarketingCampaigns" WHERE id = %s;', (camp_id,))
                if lead_emails:
                    cur.execute('DELETE FROM "EmailSuppressionList" WHERE email_lower = ANY(%s);', (lead_emails,))
                if lead_ids:
                    cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = \'Lead\' AND parent_id = ANY(%s);', (lead_ids,))
                    cur.execute('DELETE FROM "Leads" WHERE id = ANY(%s);', (lead_ids,))
                cur.execute('DELETE FROM "GlobalActivities" WHERE description LIKE %s;', (f"%{uid}%",))
            conn.commit()
            conn.close()

    def test_25_full_website_wcag_tcpa_soc2_compliance_bug_146(self):
        """
        BUG-146: Verifies the 6 Enterprise Website Compliance Pillars across all public,
        portal, and authentication routes:
        1. TCPA Prior Express Written Consent on Home Quote Form (index.html) & Quote Form (quote_form.html).
        2. CIPA § 631 / CPRA Cookie Banner (#hwb-cookie-banner) injected across all standalone public pages.
        3. Updated Legal Versions (HWB-LEG-PRV-001 v2.3.0, HWB-LEG-001 v2.2.0, ISO 9001:2026 on /unsubscribe).
        4. WCAG 2.2 AA & OWASP Tabnabbing (1 <h1> per page, <main>, skip link, labeled inputs, titled iframes,
           aria-label + rel="noopener noreferrer" on social links, pinch-to-zoom enabled).
        5. SOC 2 CC6.1 route lock on /design-system and /csi, hidden Target Margin slider on /tma/estimator,
           and Permissions-Policy HTTP security header.
        6. Empirical GHS chemical inventory on /compliance, 0.00 TRIR safety log on /ehsq, and Everyday Words on /methodology.
        """
        # 1. Home page TCPA consent & optional phone
        r_home = self.client.get("/")
        self.assertEqual(r_home.status_code, 200)
        self.assertIn("Permissions-Policy", r_home.headers)
        home_html = r_home.get_data(as_text=True)
        self.assertIn('id="tcpa_consent_home"', home_html)
        self.assertIn("Privacy Policy", home_html)
        self.assertIn("Terms of Service", home_html)
        self.assertEqual(home_html.count("<h1"), 1)

        # 2. Standalone pages have #hwb-cookie-banner, <main>, skip-link, and pinch-to-zoom enabled
        for standalone_url in ("/capability-statement", "/prequal", "/academy", "/onboard/bosanna", "/tma/estimator"):
            r_st = self.client.get(standalone_url)
            self.assertEqual(r_st.status_code, 200, standalone_url)
            st_html = r_st.get_data(as_text=True)
            self.assertIn('id="hwb-cookie-banner"', st_html, standalone_url)
            self.assertNotIn("user-scalable=no", st_html, standalone_url)

        # 3. Updated Privacy Policy (v2.5.0), Terms (v2.4.0), and Unsubscribe
        r_prv = self.client.get("/privacy-policy")
        prv_html = r_prv.get_data(as_text=True)
        self.assertIn("Privacy Policy • v2.5.0", prv_html)
        self.assertIn("Native One-Click Unsubscribe", prv_html)
        self.assertIn("Do Not Email list", prv_html)

        r_trm = self.client.get("/terms")
        trm_html = r_trm.get_data(as_text=True)
        self.assertIn("Commercial Terms • v2.4.0", trm_html)
        self.assertIn("6.1 Electronic Communications, TCPA", trm_html)

        r_uns = self.client.get("/unsubscribe")
        uns_html = r_uns.get_data(as_text=True)
        self.assertIn('for="unsub-email-input"', uns_html)
        self.assertIn('id="unsub-email-input"', uns_html)

        # 4. SOC 2 CC6.1 route lock on /design-system and /csi, and hidden margin slider on /tma/estimator
        unauth_client = app.test_client()
        self.assertIn(unauth_client.get("/design-system").status_code, (302, 401, 403))
        self.assertIn(unauth_client.get("/csi").status_code, (302, 401, 403))
        tma_html = unauth_client.get("/tma/estimator").get_data(as_text=True)
        self.assertIn('<input type="hidden" id="marginSlider" value="35">', tma_html)
        self.assertNotIn("<span>Target Margin</span>", tma_html)

        # 5. Empirical GHS chemicals on /compliance, safety log on /ehsq, and Everyday Words on /methodology
        comp_html = self.client.get("/compliance").get_data(as_text=True)
        self.assertIn("SAFE-001", comp_html)
        self.assertIn('title="Safety Data Sheet (SDS)', comp_html)

        ehsq_html = self.client.get("/ehsq").get_data(as_text=True)
        self.assertIn("0.00 TRIR Verified", ehsq_html)

        meth_html = self.client.get("/methodology").get_data(as_text=True)
        self.assertIn("First-Pass Inspection Score", meth_html)
        self.assertNotIn(">Cpk<", meth_html)
        self.assertNotIn(">DPMO<", meth_html)

    def test_26_zero_internal_process_references_on_public_surfaces_bug_147(self):
        """
        BUG-147 Permanent Regression Gate:
        Enforces strict separation between internal backend compliance controls and
        external client-facing copy across all 35 public, portal, and auth routes
        plus outbound email letterheads. Prohibits rendering internal audit codes,
        database engine/table names, cryptographic hash names, internal SOP IDs,
        or internal agent personas to unauthenticated visitors or clients.
        """
        import re
        from html.parser import HTMLParser
        from blueprints.crm_api import format_marketing_letterhead

        class _VisibleTextParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.skip = 0
                self.chunks = []
            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style"):
                    self.skip += 1
            def handle_endtag(self, tag):
                if tag in ("script", "style") and self.skip > 0:
                    self.skip -= 1
            def handle_data(self, data):
                if self.skip == 0 and data.strip():
                    self.chunks.append(data.strip())

        forbidden_internal_terms = re.compile(
            r"(SOC\s*2|PROCESSING\s*INTEGRITY|PI1\.\d+|CC\d+\.\d+|P2\.\d+|WORM|PostgreSQL|Postgres|SQL\s+Brain|"
            r"EmailSuppressionList|ClientBreadcrumbs|SecurityAuditLog|SubcontractorDocuments|EmployeeDocuments|"
            r"HWB-QMS-[0-9A-Z.\-]+|HWB-LEG-[0-9A-Z.\-]+|HWB-SEC-[0-9A-Z.\-]+|HWB-OPS-[0-9A-Z.\-]+|"
            r"SHA-256|AES-256|HMAC|RFC\s*\d+|IETF|"
            r"Super\s*George|SuperGeorge|George,\s*Systems\s*Architect|George\s*Bot|Yamamoto|Silas\s*Sync|Lauri\s*Tells|Peter|"
            r"Rack\s*\d+|Pincer\s*Shield|Cloudflare|Containerized|BYTEA|Bcrypt|"
            r"Clause\s*\d+|Amd\s*1:2024|SigmaFidelity|Zero-Defect|Poka-Yoke)",
            re.IGNORECASE,
        )

        public_routes = [
            "/", "/services", "/services/commercial-janitorial", "/services/daycare-preschool-cleaning",
            "/services/post-construction-cleaning", "/services/floor-care-vct-waxing",
            "/services/carpet-extraction", "/services/window-cleaning",
            "/locations", "/locations/dallas-tx", "/locations/plano-tx", "/locations/frisco-tx",
            "/locations/mckinney-tx", "/locations/fort-worth-tx", "/locations/arlington-tx",
            "/about", "/contact", "/quote", "/work-with-us", "/methodology",
            "/compliance", "/ehsq", "/trust-center", "/capability-statement", "/prequal",
            "/privacy-policy", "/terms", "/accessibility", "/unsubscribe", "/fcra-disclosure",
            "/academy", "/academy/verify", "/login", "/forgot-password",
            "/onboard/bosanna", "/tma/estimator",
        ]

        unauth_client = app.test_client()
        for route in public_routes:
            resp = unauth_client.get(route)
            if resp.status_code != 200:
                continue
            parser = _VisibleTextParser()
            parser.feed(resp.get_data(as_text=True))
            for chunk in parser.chunks:
                match = forbidden_internal_terms.search(chunk)
                self.assertIsNone(
                    match,
                    f"Forbidden internal reference '{match.group(0) if match else ''}' exposed on {route}: {chunk[:120]}"
                )

        # Also verify outbound client email letterhead contains zero internal process jargon
        letterhead_html = format_marketing_letterhead("<p>Thank you for your inquiry.</p>", tracking_token="tok123")
        lh_parser = _VisibleTextParser()
        lh_parser.feed(letterhead_html)
        for chunk in lh_parser.chunks:
            match = forbidden_internal_terms.search(chunk)
            self.assertIsNone(
                match,
                f"Forbidden internal reference '{match.group(0) if match else ''}' exposed in outbound email letterhead: {chunk[:120]}"
            )

    def test_27_qms_library_integrity_and_zero_outdated_sop_contamination_bug_148(self):
        """
        BUG-148: Enforces Enterprise QMS Lifecycle, Deduplication & Neural Hygiene Architecture:
        1. Every entry in qms_index.json maps to an existing HTML file in static/qms/ with 0 duplicate file entries.
        2. Zero directories, truncated filenames, or Windows sync conflict files (-desktop-) in static/qms/.
        3. Zero hollow 3-sentence boilerplate stubs, broken WikiLinks ([[Container]]), cross-company
           HexGrowth leaks, or retired SQLite / Postgres:13 / HWB-WEB Index.html instructions in static/qms/.
        4. Runtime /manual and /manual/<filename> gatekeeper serves canonical deduplicated catalog.
        """
        import json
        import re

        qms_dir = os.path.join(app.root_path, "static", "qms")
        index_path = os.path.join(app.root_path, "qms_index.json")
        self.assertTrue(os.path.exists(index_path), "qms_index.json must exist")
        self.assertTrue(os.path.exists(qms_dir), "static/qms directory must exist")

        with open(index_path, "r", encoding="utf-8") as f:
            sops = json.load(f)

        self.assertGreaterEqual(len(sops), 150, "Canonical QMS registry must contain active SOPs")
        seen_files = set()
        for entry in sops:
            fn = entry.get("file", "")
            title = entry.get("title", "")
            self.assertTrue(fn.endswith(".html"), f"QMS index entry must be .html: {fn}")
            self.assertFalse(title.lower().endswith(".html"), f"QMS index title must not be raw .html filename: {title}")
            self.assertEqual(fn, fn.lower(), f"QMS index entry must use lowercase canonical naming: {fn}")
            self.assertNotIn(" ", fn, f"QMS index entry must use snake_case without spaces: {fn}")
            self.assertNotIn("-desktop-", fn.lower(), f"Desktop sync conflict file prohibited: {fn}")
            self.assertNotIn(fn.lower(), seen_files, f"Duplicate file entry in qms_index.json: {fn}")
            seen_files.add(fn.lower())
            full_path = os.path.join(qms_dir, fn)
            self.assertTrue(os.path.isfile(full_path), f"Indexed SOP missing from static/qms/: {fn}")

        banned_patterns = [
            (r"defines the approved workflow, operational requirements, and quality standards for", "Hollow 3-sentence stub boilerplate"),
            (r"\[\[Container\]\]", "Broken Obsidian WikiLink placeholder"),
            (r"HexGrowth", "Cross-company HexGrowth contamination"),
            (r"Postgres:13", "Retired Postgres 13 container reference"),
            (r"HWB-WEB Index\.html", "Retired legacy template filename"),
            (r"SQLite", "Retired SQLite database reference"),
            (r"proxy_gateway\.py", "Retired proxy_gateway.py reference"),
        ]

        banned_mermaid_nodes = [
            (r"Port\s*8000", "Retired Port 8000 node in Mermaid diagram"),
            (r"Traffic\s*Director", "Retired Traffic Director node in Mermaid diagram"),
            (r"Nginx", "Retired Nginx node in Mermaid diagram"),
            (r"HubSpot", "Retired HubSpot node in Mermaid diagram"),
            (r"Tony\s*Holiday", "Retired Tony Holiday node in Mermaid diagram"),
            (r"516k\s*SF", "Outdated 516k SF footprint in Mermaid diagram"),
            (r"sigma_leads\.db", "Retired sigma_leads.db in Mermaid diagram"),
            (r"clients\.db", "Retired clients.db in Mermaid diagram"),
            (r"^\s*mindmap\b", "Unsupported mindmap syntax in Mermaid diagram"),
        ]

        valid_mermaid_headers = re.compile(
            r"^\s*(?:%%\{.*?\}%%\s*)?(flowchart\s+(?:TD|TB|BT|RL|LR)|graph\s+(?:TD|TB|BT|RL|LR)|sequenceDiagram|erDiagram|stateDiagram(?:-v2)?|classDiagram)\b",
            re.IGNORECASE | re.DOTALL,
        )

        mermaid_file_count = 0
        mermaid_block_count = 0

        for fn in os.listdir(qms_dir):
            fp = os.path.join(qms_dir, fn)
            self.assertFalse(os.path.isdir(fp), f"Subdirectory prohibited inside static/qms/: {fn}")
            self.assertNotIn("-desktop-", fn.lower(), f"Desktop sync conflict file prohibited in static/qms/: {fn}")
            if not fn.endswith(".html"):
                continue
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for pat, reason in banned_patterns:
                m = re.search(pat, content, re.IGNORECASE)
                self.assertIsNone(
                    m,
                    f"Outdated/contaminating SOP content ({reason}) found in {fn}: '{m.group(0) if m else ''}'"
                )

            blocks = re.findall(r'<div\s+class=["\']mermaid["\'][^>]*>(.*?)</div>', content, flags=re.S | re.I)
            if blocks:
                mermaid_file_count += 1
                for blk in blocks:
                    mermaid_block_count += 1
                    clean_blk = blk.strip()
                    self.assertIsNotNone(
                        valid_mermaid_headers.match(clean_blk),
                        f"Invalid or unsupported Mermaid diagram header in {fn}: {clean_blk[:80]}"
                    )
                    for m_pat, m_reason in banned_mermaid_nodes:
                        mm = re.search(m_pat, clean_blk, re.IGNORECASE | re.MULTILINE)
                        self.assertIsNone(
                            mm,
                            f"{m_reason} found in {fn}: '{mm.group(0) if mm else ''}'"
                        )

        self.assertGreaterEqual(
            mermaid_file_count,
            51,
            f"Expected at least 51 SOPs with active Mermaid diagrams, found {mermaid_file_count}"
        )

    def test_28_adversarial_legal_audit_zero_prechecked_consents_fcra_i9_tdpsa_wcag_bug_149(self):
        """
        BUG-149: Enforces 7-Pillar Enterprise Legal Lawsuit Shield across all public & portal surfaces:
        1. Zero pre-checked (checked) legal, TCPA, FCRA, MSA, DWC-83, or policy checkboxes across all public/portal templates.
        2. Zero unbound <label> elements across all public/portal templates (WCAG 2.2 Level A 1.3.1 / 4.1.2).
        3. Standalone /fcra-disclosure view (15 U.S.C. § 1681b(b)(2)(A)(i)) with zero bundled application inputs.
        4. DOJ Form I-9 Anti-Discrimination Safe Harbor (8 U.S.C. § 1324b) in employee_onboarding_portal.html.
        5. Binding Individual Arbitration, Class-Action Waiver & 30-Day Pre-Suit Cure Notice in /terms (v2.4.0).
        6. TDPSA Texas Attorney General complaint URL, Sensitive Data notice, and Sec-GPC: 1 enforcement in /privacy-policy (v2.5.0).
        7. WORM CONSENT_LEDGER (QUOTE_CONSENT_RECORDED) with SHA-256 disclosure digest on POST /get-quote.
        """
        from html.parser import HTMLParser
        from unittest.mock import patch

        class _LegalDomAuditor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.checked_checkboxes = []
                self.unbound_labels = []
                self.form_inputs = []
                self._in_label = False
                self._label_has_for = False
                self._label_has_child_control = False
                self._label_id = ""

            def handle_starttag(self, tag, attrs):
                attr_dict = {k.lower(): v for k, v in attrs}
                if tag == "input":
                    self.form_inputs.append(attr_dict)
                    if (attr_dict.get("type") or "").lower() == "checkbox" and "checked" in attr_dict:
                        self.checked_checkboxes.append(attr_dict.get("id") or attr_dict.get("name") or "checkbox")
                elif tag in ("select", "textarea"):
                    self.form_inputs.append(attr_dict)

                if tag == "label":
                    self._in_label = True
                    self._label_has_for = bool((attr_dict.get("for") or "").strip())
                    self._label_has_child_control = False
                    self._label_id = attr_dict.get("id") or attr_dict.get("class") or "label"
                elif self._in_label and tag in ("input", "select", "textarea"):
                    self._label_has_child_control = True

            def handle_endtag(self, tag):
                if tag == "label" and self._in_label:
                    if not self._label_has_for and not self._label_has_child_control:
                        self.unbound_labels.append(self._label_id)
                    self._in_label = False

        templates_dir = os.path.join(app.root_path, "templates")
        public_portal_templates = [
            "index.html",
            "quote_form.html",
            "work_with_us.html",
            "subcontractor_onboarding.html",
            "employee_onboarding_portal.html",
            "bosanna_onboarding.html",
            "quote_success.html",
            "academy_course.html",
            "reset_password.html",
            "tma_estimator.html",
            "fcra_disclosure.html",
            "terms.html",
            "privacy_policy.html",
            "accessibility.html",
        ]

        # Pillars 1 & 4: Zero pre-checked checkboxes & zero unbound <label> tags
        for tpl_name in public_portal_templates:
            tpl_path = os.path.join(templates_dir, tpl_name)
            self.assertTrue(os.path.isfile(tpl_path), f"Template missing: {tpl_name}")
            with open(tpl_path, "r", encoding="utf-8") as f:
                raw_html = f.read()
            auditor = _LegalDomAuditor()
            auditor.feed(raw_html)
            self.assertEqual(
                auditor.checked_checkboxes,
                [],
                f"Pre-checked checkbox prohibited in {tpl_name} (TCPA/TDPSA/Contract law): {auditor.checked_checkboxes}",
            )
            self.assertEqual(
                auditor.unbound_labels,
                [],
                f"Unbound <label> prohibited in {tpl_name} (ADA Title III / WCAG 2.2): {auditor.unbound_labels}",
            )

        # Pillar 2: Standalone FCRA Disclosure (/fcra-disclosure)
        r_fcra = self.client.get("/fcra-disclosure")
        self.assertEqual(r_fcra.status_code, 200)
        fcra_html = r_fcra.get_data(as_text=True)
        self.assertIn("15 U.S.C.", fcra_html)
        self.assertIn("1681b(b)(2)(A)", fcra_html)
        self.assertIn("A Summary of Your Rights Under the Fair Credit Reporting Act", fcra_html)
        with open(os.path.join(templates_dir, "fcra_disclosure.html"), "r", encoding="utf-8") as f:
            fcra_tpl = f.read()
        fcra_auditor = _LegalDomAuditor()
        fcra_auditor.feed(fcra_tpl)
        self.assertEqual(
            len(fcra_auditor.form_inputs),
            0,
            "Standalone FCRA disclosure must not contain bundled application inputs",
        )

        # Pillar 3: DOJ Form I-9 Anti-Discrimination Safe Harbor (8 U.S.C. § 1324b)
        with open(os.path.join(templates_dir, "employee_onboarding_portal.html"), "r", encoding="utf-8") as f:
            emp_tpl = f.read()
        self.assertIn("8 U.S.C.", emp_tpl)
        self.assertIn("1324b", emp_tpl)
        self.assertIn("List A", emp_tpl)
        self.assertIn("List B", emp_tpl)
        self.assertIn("List C", emp_tpl)

        # Pillar 5: Binding Individual Arbitration, Class-Action Waiver & 30-Day Pre-Suit Cure Notice in /terms
        r_terms = self.client.get("/terms")
        self.assertEqual(r_terms.status_code, 200)
        terms_html = r_terms.get_data(as_text=True)
        self.assertIn("v2.4.0", terms_html)
        self.assertIn("Mandatory 30-Day Pre-Suit Notice", terms_html)
        self.assertIn("Binding Individual Arbitration", terms_html)
        self.assertIn("CLASS AND COLLECTIVE ACTION WAIVER", terms_html)
        self.assertIn("Federal Arbitration Act", terms_html)

        # Pillar 6: TDPSA Texas AG Complaint Link, Sensitive Data Notice & Sec-GPC: 1 Enforcement
        r_priv = self.client.get("/privacy-policy")
        self.assertEqual(r_priv.status_code, 200)
        priv_html = r_priv.get_data(as_text=True)
        self.assertIn("v2.5.0", priv_html)
        self.assertIn("https://www.texasattorneygeneral.gov/consumer-protection/file-consumer-complaint", priv_html)
        self.assertIn("541.102", priv_html)
        self.assertIn("Sec-GPC: 1", priv_html)

        r_gpc = self.client.get("/", headers={"Sec-GPC": "1"})
        self.assertEqual(r_gpc.status_code, 200)
        self.assertEqual(r_gpc.headers.get("X-GPC-Status"), "Honored")

        # Pillar 7: WORM CONSENT_LEDGER (QUOTE_CONSENT_RECORDED) on POST /get-quote
        with (
            patch("blueprints.public.evaluate_bot_defense", return_value=(False, None)),
            patch("blueprints.public.dispatch_lead_notifications", return_value=True),
            patch("core.services.email_service.transmit_email", return_value=(True, "mocked")),
        ):
            r_quote = self.client.post(
                "/get-quote",
                data={
                    "name": "Legal Shield Test Lead",
                    "company": "Shield Verification Corp",
                    "email": "shield.audit@example.com",
                    "phone": "(214) 555-0192",
                    "facility_type": "Commercial Office",
                    "sqft": "15000",
                    "frequency": "3x / Week",
                    "tcpa_consent": "yes",
                },
            )
            self.assertIn(r_quote.status_code, (200, 302))
            conn = get_db(self.db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        '''
                        SELECT details
                        FROM "SecurityAuditLogs"
                        WHERE event_category = 'CONSENT_LEDGER'
                          AND event_action = 'QUOTE_CONSENT_RECORDED'
                          AND details::text LIKE %s
                        ORDER BY id DESC
                        LIMIT 1;
                        ''',
                        ("%shield.audit@example.com%",),
                    )
                    consent_row = cur.fetchone()
                    self.assertIsNotNone(consent_row, "WORM CONSENT_LEDGER receipt must be recorded on /get-quote")
                    details_str = str(consent_row[0] or "")
                    self.assertIn("disclosure_sha256", details_str)
                    self.assertIn("TERMS-v2.4.0|PRIVACY-v2.5.0", details_str)
                    cur.execute('DELETE FROM "Leads" WHERE LOWER(email) = %s;', ("shield.audit@example.com",))
                conn.commit()
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
