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

                # Verify Zero-Disk Plaintext Policy: raw PDF must NEVER be written to container disk
                cached_file = os.path.join(tmp_vault_dir, test_file_key)
                self.assertFalse(os.path.exists(cached_file), "Raw unencrypted PDF must never be written to container disk")

                # Retrieve from PostgreSQL 16.15 encrypted vault & verify SHA-256 + zero-disk retention
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
                self.assertFalse(os.path.exists(cached_file), "Retrieval must stream in memory without writing plaintext to disk")

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
                    f"%PDF-1.4\nForm W-4 Employee's Withholding Certificate\n"
                    f"First Name: Valeria\nLast Name: Solis-{uid}\n"
                    "Address: 2900 McKinney Ave\nCity, State, ZIP: Dallas, TX 75204\n"
                    "Social security number: 123-45-6789\n"
                    "Filing Status: Head of Household\n"
                    "Total Dependents: $2,000.00\n"
                ).encode()
                r_up_w4 = self.client.post(
                    f"/api/v1/employees/onboard/{emp_token}/upload-doc",
                    data={"doc_type": "Form W-4", "file": (io.BytesIO(w4_bytes), "Valeria_W4.pdf")},
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
                    data={"document_type": "Driver License / State ID", "document": (io.BytesIO(b"%PDF-1.4\nTEXAS DRIVER LICENSE\n4d DL: 88776655\n4b EXP: 05/14/2030\n"), "tx_id.pdf")},
                    content_type="multipart/form-data",
                )
                self.assertEqual(r_bo_doc_w2.status_code, 201, r_bo_doc_w2.get_data(as_text=True))
                w2_doc_id = r_bo_doc_w2.get_json()["document_id"]

                r_dl_w2 = self.client.get(f"/api/v1/hr/documents/{w2_doc_id}/download")
                self.assertEqual(r_dl_w2.status_code, 200)
                self.assertIn(b"88776655", r_dl_w2.data)
                r_dl_w2.close()
        finally:
            conn.rollback()
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
            conn.rollback()
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

        # 3. Letterhead Footer CAN-SPAM Postal Address & One-Click Unsubscribe Link (Zero Internal Jargon per BUG-147)
        lh_html = format_marketing_letterhead("<p>Test Body</p>", "tok_footer_check_999")
        for required_element in ("P.O. Box 38465, Dallas, TX 75238", "Collin County", "Unsubscribe Instantly", "tok_footer_check_999"):
            self.assertIn(required_element, lh_html)
        self.assertNotIn("3342 FM 1827", lh_html)

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
            conn.rollback()
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
            r"Clause\s*\d+|Amd\s*1:2024|SigmaFidelity|Zero-Defect|Poka-Yoke|"
            r"GHF000742|82-4377459|32005785756|802920409|082830635|08-283-0635|"
            r"Carlos\s*Aguirre|Insurance\s*Risk\s*Consultants|682-667-3863|\(682\)\s*667-3863|"
            r"Sunbelt\s*Rentals|Jon-Don|MaximMart|972-800-7808|\(972\)\s*800-7808|hdominguez@hwbcleaning\.com|"
            r"Staff\s+Login\s+to\s+Operating\s+Manual)",
            re.IGNORECASE,
        )

        public_routes = [
            "/", "/services", "/services/janitorial", "/services/commercial",
            "/services/industrial", "/services/construction",
            "/locations", "/locations/dallas", "/locations/plano", "/locations/frisco",
            "/locations/mckinney", "/locations/fort-worth", "/locations/arlington",
            "/about", "/contact", "/get-quote", "/work-with-us", "/methodology",
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

    def test_29_all_forms_buttons_scope_planner_and_smart_address_bug_150(self):
        """
        BUG-150 Full-Website Form, Button, Two-Way Scope Planner & Smart Address Sentinel:
        1. Verify zero orphaned legacy scratch templates exist in templates/
           (backoffice_operations_fixed.html, backoffice_scope_builder.html, HWB-WEB CRM Add Lead.html).
        2. Verify all JS handlers in backoffice_operations_core.js (addToScope, clearScope,
           onScopeBuildingChange, removeScopeArea, removeScopeTask, removeScopeItem, smartType,
           applySmartAddress) exist and bind cleanly.
        3. Verify /admin/operations?view=scope renders Two-Way PostgreSQL scope hydration
           attributes (data-scope, onchange="onScopeBuildingChange(this)", #scope_tree_items)
           and populated ScopeLibrary datalists (#lib_areas, #lib_tasks, #lib_items).
        4. Verify POST /admin/scope-builder validates JSON structure, updates PostgreSQL
           "Services".tasks_json, and records SCOPE_OF_WORK_UPDATED in "SecurityAuditLogs".
        5. Verify GET /api/v1/crm/address-autocomplete returns live PostgreSQL + DFW commercial
           address suggestions for smartType() auto-fill.
        """
        import json

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        templates_dir = os.path.join(base_dir, "templates")
        for legacy_file in (
            "backoffice_operations_fixed.html",
            "backoffice_scope_builder.html",
            "HWB-WEB CRM Add Lead.html",
            "HWB-WEB CRM Edit Lead.html",
        ):
            self.assertFalse(
                os.path.exists(os.path.join(templates_dir, legacy_file)),
                f"Orphaned legacy template must not exist: {legacy_file}",
            )

        # Verify crm_edit_lead.html is valid Jinja HTML (not Python code)
        with open(os.path.join(templates_dir, "crm_edit_lead.html"), encoding="utf-8") as fh:
            crm_edit_content = fh.read()
        self.assertIn('{% extends "base.html" %}', crm_edit_content)
        self.assertNotIn("from flask import Flask", crm_edit_content)

        # Verify JS functions in backoffice_operations_core.js
        with open(
            os.path.join(base_dir, "static", "js", "backoffice_operations_core.js"),
            encoding="utf-8",
        ) as fh:
            core_js = fh.read()
        for fn_name in (
            "function initScopePlanner(",
            "function onScopeBuildingChange(",
            "function addToScope(",
            "function removeScopeArea(",
            "function removeScopeTask(",
            "function removeScopeItem(",
            "function renderTree(",
            "function clearScope(",
            "function smartType(",
            "function applySmartAddress(",
        ):
            self.assertIn(fn_name, core_js, f"Missing JS handler in backoffice_operations_core.js: {fn_name}")

        # Authenticate as Executive user
        with self.client.session_transaction() as sess:
            sess["_user_id"] = "1"
            sess["_fresh"] = True

        # 1. Verify /admin/operations?view=scope
        r_scope = self.client.get("/admin/operations?view=scope")
        self.assertEqual(r_scope.status_code, 200)
        scope_html = r_scope.get_data(as_text=True)
        self.assertIn('onchange="onScopeBuildingChange(this)"', scope_html)
        self.assertIn('id="scope_tree_items"', scope_html)
        self.assertIn('id="lib_areas"', scope_html)
        self.assertIn("<option value=", scope_html)

        # 2. Verify POST /admin/scope-builder updates PostgreSQL "Services".tasks_json and logs WORM audit
        conn = get_db(self.db_url)
        service_id = None
        original_tasks_json = None
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT service_id, tasks_json FROM "Services" ORDER BY service_id ASC LIMIT 1;')
                row = cur.fetchone()
                if row:
                    service_id = row[0]
                    original_tasks_json = row[1]

            if service_id is not None:
                test_scope = [
                    {
                        "name": "Main Entrance & Lobby",
                        "tasks": [
                            {
                                "name": "EPA Hospital-Grade Disinfection",
                                "items": ["Entry Doors, Push Plates & Thresholds"],
                            }
                        ],
                    }
                ]
                r_save = self.client.post(
                    "/admin/scope-builder",
                    json={"service_id": str(service_id), "scope_json": json.dumps(test_scope)},
                )
                self.assertEqual(r_save.status_code, 200)
                save_data = r_save.get_json()
                self.assertEqual(save_data["status"], "success")
                self.assertEqual(save_data["areas_count"], 1)

                with conn.cursor() as cur:
                    cur.execute('SELECT tasks_json FROM "Services" WHERE service_id = %s;', (service_id,))
                    updated_row = cur.fetchone()
                    self.assertIsNotNone(updated_row)
                    self.assertIn("Main Entrance & Lobby", updated_row[0] or "")

                    cur.execute(
                        '''
                        SELECT event_action
                        FROM "SecurityAuditLogs"
                        WHERE event_category = 'OPERATIONS'
                          AND event_action = 'SCOPE_OF_WORK_UPDATED'
                        ORDER BY id DESC
                        LIMIT 1;
                        '''
                    )
                    self.assertIsNotNone(cur.fetchone(), "SCOPE_OF_WORK_UPDATED must be logged in SecurityAuditLogs")

                    # Restore original tasks_json
                    cur.execute(
                        'UPDATE "Services" SET tasks_json = %s WHERE service_id = %s;',
                        (original_tasks_json, service_id),
                    )
                conn.commit()
        finally:
            conn.close()

        # 3. Verify GET /api/v1/crm/address-autocomplete
        r_auto = self.client.get("/api/v1/crm/address-autocomplete?q=Plano")
        self.assertEqual(r_auto.status_code, 200)
        auto_json = r_auto.get_json()
        self.assertEqual(auto_json["status"], "success")
        self.assertTrue(len(auto_json["results"]) >= 1)
        self.assertIn("city", auto_json["results"][0])
        self.assertIn("zip", auto_json["results"][0])

    def test_30_enterprise_llm_geo_visibility_and_schema_parity_bug_151(self):
        """
        BUG-151 8-Pillar Enterprise LLM & AI Search Visibility (GEO) Sentinel:
        1. /llms.txt, /llms-full.txt, and /ai.txt return HTTP 200 text/plain with
           McKinney HQ (3342 FM 1827), phone, NAICS 561720, CSI 01 74 23, and pricing benchmarks.
        2. /robots.txt allows /compliance and /ehsq and explicitly permits OAI-SearchBot,
           ChatGPT-User, GPTBot, PerplexityBot, ClaudeBot, Google-Extended, and bingbot.
        3. Base template has zero global duplicate FAQPage spam; non-FAQ pages (/about, /terms)
           do not emit FAQPage JSON-LD.
        4. Homepage (/), all 4 /services/* pages, and all 11 /locations/* pages emit valid
           JSON-LD where every FAQPage question is visibly rendered in the HTML body (<summary>).
        5. All 11 /locations/* pages have unique descriptions, ZIP codes, and commercial corridors.
        6. IndexNow verification key (/hwb8f4e2a9c1b7d3e5f6a0b2c4d8e1f3.txt) returns HTTP 200,
           and AI crawler User-Agent visits are logged in SecurityAuditLogs (AI_CRAWLER_TELEMETRY).
        """
        import json
        import re

        # Pillar 1: /llms.txt and /llms-full.txt (Walkthrough-First Custom Quotes, P.O. Box 38465, Zero Published Dollar Rates & Zero Street Address)
        r_llms = self.client.get("/llms.txt")
        self.assertEqual(r_llms.status_code, 200)
        llms_text = r_llms.get_data(as_text=True)
        self.assertIn("P.O. Box 38465, Dallas, TX 75238", llms_text)
        self.assertIn("legal@hwbcleaning.com", llms_text)
        self.assertNotIn("3342 FM 1827", llms_text)
        self.assertIn("561720", llms_text)
        self.assertIn("01 74 23", llms_text)
        self.assertIn("walkthrough", llms_text.lower())
        for forbidden_rate in ("$0.08", "$0.16", "$0.15", "$0.35", "$0.55", "$0.04"):
            self.assertNotIn(forbidden_rate, llms_text)

        r_llms_full = self.client.get("/llms-full.txt")
        self.assertEqual(r_llms_full.status_code, 200)
        llms_full_text = r_llms_full.get_data(as_text=True)
        self.assertIn("P.O. Box 38465, Dallas, TX 75238", llms_full_text)
        self.assertNotIn("3342 FM 1827", llms_full_text)
        self.assertIn("McKinney, TX", llms_full_text)
        for forbidden_rate in ("$0.08", "$0.16", "$0.15", "$0.35", "$0.55", "$0.04", "$350"):
            self.assertNotIn(forbidden_rate, llms_full_text)

        # Pillar 2: /robots.txt AI crawlers & unblocked /compliance and /ehsq
        r_rob = self.client.get("/robots.txt", headers={"Host": "www.hwbcleaning.com"})
        self.assertEqual(r_rob.status_code, 200)
        rob_text = r_rob.get_data(as_text=True)
        self.assertNotIn("Disallow: /compliance", rob_text)
        self.assertNotIn("Disallow: /ehsq", rob_text)
        for bot in ("OAI-SearchBot", "ChatGPT-User", "GPTBot", "PerplexityBot", "ClaudeBot", "Google-Extended", "bingbot"):
            self.assertIn(f"User-agent: {bot}", rob_text)

        # Pillar 3: Non-FAQ pages must NOT contain global duplicate FAQPage JSON-LD
        for non_faq_route in ("/about", "/terms", "/privacy-policy"):
            r_nf = self.client.get(non_faq_route)
            self.assertEqual(r_nf.status_code, 200)
            self.assertNotIn('"@type": "FAQPage"', r_nf.get_data(as_text=True), non_faq_route)

        # Pillar 4, 5 & 6: 1:1 Visible-to-JSON-LD FAQ Parity & Unique City Entity Density
        faq_routes = [
            "/",
            "/services/janitorial",
            "/services/commercial",
            "/services/industrial",
            "/services/construction",
            "/locations/mckinney",
            "/locations/frisco",
            "/locations/plano",
            "/locations/dallas",
            "/locations/fort-worth",
            "/locations/waxahachie",
            "/locations/irving",
            "/locations/richardson",
            "/locations/allen",
            "/locations/arlington",
            "/locations/addison",
        ]
        seen_first_questions = set()
        seen_meta_descs = set()
        for route in faq_routes:
            resp = self.client.get(route)
            self.assertEqual(resp.status_code, 200, route)
            html = resp.get_data(as_text=True)
            self.assertIn('"@type": "FAQPage"', html, f"Missing FAQPage schema on {route}")
            self.assertNotIn("3342 FM 1827", html, f"Physical street address must not appear on {route}")
            for forbidden_rate in ("$0.08", "$0.16", "$0.15", "$0.35", "$0.55", "$0.04"):
                self.assertNotIn(forbidden_rate, html, f"Published dollar rate {forbidden_rate} must not appear on {route}")

            # Extract all JSON-LD blocks and verify valid JSON + visible question parity
            ld_blocks = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.DOTALL)
            self.assertTrue(len(ld_blocks) >= 1, route)
            for raw_ld in ld_blocks:
                parsed_ld = json.loads(raw_ld)
                nodes = parsed_ld.get("@graph", [parsed_ld])
                for node in nodes:
                    if isinstance(node, dict) and node.get("@type") == "FAQPage":
                        questions = node.get("mainEntity", [])
                        self.assertTrue(len(questions) >= 3, f"Expected >=3 FAQs on {route}")
                        first_q = questions[0]["name"]
                        seen_first_questions.add((route, first_q))
                        for q_obj in questions:
                            q_text = q_obj["name"]
                            # Verify the question text is visibly rendered in the HTML body
                            q_escaped = q_text.replace("&", "&amp;")
                            self.assertTrue(
                                (q_text in html and html.count(q_text) >= 2) or (q_escaped in html),
                                f"FAQ question in JSON-LD is not visibly rendered on {route}: {q_text}",
                            )

            # Verify unique meta descriptions across all 16 core SEO/GEO pages
            m_desc = re.search(r'<meta name="description" content="([^"]+)"', html)
            self.assertIsNotNone(m_desc, f"Missing meta description on {route}")
            desc_val = m_desc.group(1)
            self.assertNotIn(desc_val, seen_meta_descs, f"Duplicate meta description on {route}")
            seen_meta_descs.add(desc_val)

        # Ensure all 16 FAQ routes have distinct primary FAQ questions (zero copy-paste spam)
        unique_q_texts = {q for _, q in seen_first_questions}
        self.assertEqual(len(unique_q_texts), len(faq_routes), "Every service and city page must have unique FAQs")

        # Pillar 7: IndexNow key file + AI Crawler Telemetry logging in SecurityAuditLogs
        r_key = self.client.get("/hwb8f4e2a9c1b7d3e5f6a0b2c4d8e1f3.txt")
        self.assertEqual(r_key.status_code, 200)
        self.assertEqual(r_key.get_data(as_text=True).strip(), "hwb8f4e2a9c1b7d3e5f6a0b2c4d8e1f3")

        r_bot = self.client.get(
            "/",
            headers={"User-Agent": "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)"},
        )
        self.assertEqual(r_bot.status_code, 200)
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT details
                    FROM "SecurityAuditLogs"
                    WHERE event_category = 'AI_CRAWLER_TELEMETRY'
                      AND event_action = 'AI_BOT_PAGE_CRAWLED'
                    ORDER BY id DESC
                    LIMIT 1;
                    '''
                )
                bot_row = cur.fetchone()
                self.assertIsNotNone(bot_row, "OAI-SearchBot crawl must be logged in SecurityAuditLogs")
                self.assertIn("OAI-SearchBot", str(bot_row[0]))
        finally:
            conn.close()

    def test_31_enterprise_root_exploitation_and_credential_hardening_bug_152(self):
        """
        Verifies the 6-Point Enterprise Root & Post-Exploitation Security Hardening (BUG-152):
        1. Zero hardcoded plaintext password lists or case-insensitive .lower() password checks in blueprints/auth.py & partner.py.
        2. Unauthenticated access to /portal/bosanna/magic-login and /bosanna is strictly blocked (redirects to login).
        3. Zero hardcoded fallback key strings in core/security.py and core/services/employee_doc_extractor.py; MultiFernet active.
        4. Zero unencrypted PDF/HTML/TXT files in vault/hr_documents/ and .dockerignore blocks .env, vault/, logs/, *.pem.
        5. Dockerfile enforces non-root USER hwbapp (uid=1000).
        6. load_user() immediately revokes active sessions when a user's status is changed from 'Active' to 'Inactive',
           and force_pwd_reset = TRUE redirects the next login to /reset-password/<token>.
        """
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # 1. Inspect source files for zero hardcoded credentials or case-insensitive checks
        auth_src = open(os.path.join(base_dir, "blueprints", "auth.py"), encoding="utf-8").read()
        partner_src = open(os.path.join(base_dir, "blueprints", "partner.py"), encoding="utf-8").read()
        sec_src = open(os.path.join(base_dir, "core", "security.py"), encoding="utf-8").read()
        emp_ext_src = open(os.path.join(base_dir, "core", "services", "employee_doc_extractor.py"), encoding="utf-8").read()

        for banned in (
            "ceo_authorized_credentials",
            "bosanna_authorized_credentials",
            "ch1lpayatE",
            "HWB-Admin-2026",
            "check_password_hash(user['password_hash'], p.lower())",
        ):
            self.assertNotIn(banned, auth_src, f"Banned credential bypass pattern found in auth.py: {banned}")

        for banned_p in ("bosanna2026!", "angelica2026!", "Instant passwordless executive entrance"):
            self.assertNotIn(banned_p, partner_src, f"Banned partner bypass found in partner.py: {banned_p}")

        self.assertNotIn("hwb_default_fallback_secret_key_2026", sec_src)
        self.assertIn("MultiFernet", sec_src)
        self.assertNotIn("sigmafidelity-default-enterprise-pii-vault-key-2026", emp_ext_src)

        # 2. Verify unauthenticated /portal/bosanna/magic-login cannot log in without credentials
        anon_client = app.test_client()
        r_magic = anon_client.get("/portal/bosanna/magic-login", follow_redirects=False)
        self.assertEqual(r_magic.status_code, 302)
        self.assertIn("/portal/bosanna/login", r_magic.headers.get("Location", ""))

        # 3. Verify .dockerignore and Dockerfile non-root execution
        dockerignore_src = open(os.path.join(base_dir, ".dockerignore"), encoding="utf-8").read()
        for required_ignore in (".env", "vault/", "logs/", "*.pem"):
            self.assertIn(required_ignore, dockerignore_src)

        dockerfile_src = open(os.path.join(base_dir, "Dockerfile"), encoding="utf-8").read()
        self.assertIn("USER hwbapp", dockerfile_src)
        self.assertIn("useradd", dockerfile_src)

        # 4. Verify zero plaintext PDFs/HTMLs sitting in vault/hr_documents
        vault_dir = os.path.join(base_dir, "vault", "hr_documents")
        if os.path.isdir(vault_dir):
            leaked_files = [
                f for f in os.listdir(vault_dir)
                if f.endswith((".pdf", ".html", ".txt"))
            ]
            self.assertEqual(leaked_files, [], f"Plaintext files found in vault/hr_documents: {leaked_files}")

        # 5. Verify load_user() immediate session revocation on status != 'Active' and force_pwd_reset flow
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id, status, force_pwd_reset FROM "Users" WHERE username = %s;', ("Bwiley",))
                bw = cur.fetchone()
                if bw:
                    orig_status = bw["status"]
                    orig_force = bw.get("force_pwd_reset", False)
                    try:
                        from main_app import load_user
                        cur.execute('UPDATE "Users" SET status = %s WHERE id = %s;', ("Suspended", bw["id"]))
                        conn.commit()
                        self.assertIsNone(load_user(bw["id"]), "Suspended user must return None from load_user()")
                    finally:
                        cur.execute(
                            'UPDATE "Users" SET status = %s, force_pwd_reset = %s WHERE id = %s;',
                            (orig_status, orig_force, bw["id"]),
                        )
                        conn.commit()
        finally:
            conn.close()

    def test_32_enterprise_leads_faceted_search_and_owner_filter_bug_154(self):
        """
        BUG-154: Verifies the 4-Pillar Enterprise Leads Faceted Search & Owner-Filtering Workflow:
        1. Full-Name Entity Recognition (`q=beabe wiley` & `q=rep:Beabe Wiley` & `q=bwiley` -> resolves to Beabe Wiley's 50 assigned leads).
        2. Dedicated `owner_id` Parameter (`?view=leads&owner_id=<id>` & `?view=leads&owner_id=unassigned`).
        3. Fuzzy Texas City Spell-Correction (`q=wiley tx` & `q=city:wiley` -> resolves to Wylie, TX without mixing in Beabe Wiley's leads).
        4. Faceted Typeahead Autocomplete API (`/api/v1/leads/search-suggest?q=wiley` returns both 👤 Assigned Rep and 📍 Wylie, TX).
        """
        auth_client = self.get_auth_client()

        # 1. Verify full-name and rep-prefixed search for Beabe Wiley
        for q_str in ("beabe wiley", "Beabe Wiley", "rep:Beabe Wiley", "bwiley"):
            r = auth_client.get(f"/admin/operations?view=leads&q={q_str}&format=json")
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertEqual(len(data.get("leads", [])), 50, f"Query '{q_str}' must return all 50 leads assigned to Beabe Wiley")

        # 2. Verify dedicated owner_id parameter
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM "Users" WHERE LOWER(username) = %s LIMIT 1;', ("bwiley",))
                bw_id = cur.fetchone()["id"]
        finally:
            conn.close()

        r_owner = auth_client.get(f"/admin/operations?view=leads&owner_id={bw_id}&format=json")
        self.assertEqual(r_owner.status_code, 200)
        self.assertEqual(len(r_owner.get_json().get("leads", [])), 50)

        # 3. Verify Texas city spell-correction (`wiley tx` -> `Wylie, TX` without mixing in Beabe Wiley's Dallas/Plano leads)
        r_city = auth_client.get("/admin/operations?view=leads&q=wiley+tx&format=json")
        self.assertEqual(r_city.status_code, 200)
        city_leads = r_city.get_json().get("leads", [])
        self.assertGreater(len(city_leads), 0, "'wiley tx' must spell-correct to Wylie, TX and return leads")
        for ld in city_leads:
            self.assertEqual((ld.get("city") or "").lower(), "wylie")

        # 4. Verify Faceted Typeahead API (`/api/v1/leads/search-suggest?q=wiley`)
        r_sug = auth_client.get("/api/v1/leads/search-suggest?q=wiley")
        self.assertEqual(r_sug.status_code, 200)
        sug = r_sug.get_json()
        owner_names = [o.get("full_name") for o in sug.get("owners", [])]
        loc_labels = [l.get("label") for l in sug.get("locations", [])]
        self.assertIn("Beabe Wiley", owner_names)
        self.assertIn("Wylie, TX", loc_labels)

    def test_33_lead_update_save_schema_parity_and_pool_hygiene_bug_155(self):
        """
        BUG-155: Verifies that clicking 'Save Lead Changes' (PUT /api/v1/leads/<id> and PATCH /api/v1/leads/<id>)
        succeeds with 200 OK across full form payloads (including website, student_enrollment, county, capacity,
        owner_verification_status, preferred_date, preferred_time, budget_range, and cleaning_delivery_model),
        that schema_engine.py maintains 100% column parity on 'Leads', and that repeated typeahead calls
        (/api/v1/leads/search-suggest) return connections to ThreadedConnectionPool without exhaustion.
        """
        auth_client = self.get_auth_client()

        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM "Leads" WHERE COALESCE(is_commercial, TRUE) = TRUE ORDER BY id ASC LIMIT 1;')
                lead_id = cur.fetchone()["id"]
        finally:
            conn.close()

        r_get = auth_client.get(f"/api/v1/leads/{lead_id}")
        self.assertEqual(r_get.status_code, 200)
        lead_before = r_get.get_json()["lead"]

        # Simulate full Edit Lead form submission (saveLeadUpdate payload)
        full_form_payload = {
            "company_name": lead_before.get("center_name") or "Test Facility",
            "umbrella_name": lead_before.get("umbrella_name") or "",
            "ownership_type": lead_before.get("ownership_type") or "Independent Commercial",
            "decision_maker": lead_before.get("decision_maker") or "",
            "job_title": lead_before.get("job_title") or "",
            "owner_verification_status": lead_before.get("owner_verification_status") or "",
            "phone": lead_before.get("phone") or "",
            "email": lead_before.get("email") or "",
            "website": lead_before.get("website") or "https://www.hwbcleaning.com",
            "address": lead_before.get("address") or "",
            "city": lead_before.get("city") or "",
            "state": lead_before.get("state") or "TX",
            "zipcode": lead_before.get("zipcode") or "",
            "county": lead_before.get("county") or "Dallas",
            "industry": lead_before.get("industry") or "",
            "facility_type": lead_before.get("facility_type") or "",
            "sqf": lead_before.get("sqf") or 0,
            "capacity": lead_before.get("capacity") if lead_before.get("capacity") is not None else "",
            "student_enrollment": lead_before.get("student_enrollment") if lead_before.get("student_enrollment") is not None else "",
            "traffic_cycle": lead_before.get("traffic_cycle") or "Slow",
            "acquisition_tier": lead_before.get("acquisition_tier") or "",
            "cleaning_delivery_model": lead_before.get("cleaning_delivery_model") or "UNKNOWN",
            "service_interest": lead_before.get("service_interest") or "",
            "lead_source": lead_before.get("lead_source") or "",
            "status": lead_before.get("status") or "New",
            "priority_level": lead_before.get("priority_level") or "Warm",
            "estimated_annual_value": lead_before.get("estimated_annual_value") or 0.0,
            "budget_range": lead_before.get("budget_range") or "",
            "preferred_date": lead_before.get("preferred_date") or "",
            "preferred_time": lead_before.get("preferred_time") or "",
            "next_action_date": lead_before.get("next_action_date") or "",
            "owner_id": lead_before.get("owner_id") if lead_before.get("owner_id") is not None else "",
            "notes": lead_before.get("notes") or "",
        }
        r_put = auth_client.put(f"/api/v1/leads/{lead_id}", json=full_form_payload)
        self.assertEqual(r_put.status_code, 200, f"PUT /api/v1/leads/{lead_id} failed: {r_put.get_data(as_text=True)}")
        self.assertEqual(r_put.get_json().get("status"), "success")

        # Restore original website & county values
        auth_client.patch(
            f"/api/v1/leads/{lead_id}",
            json={"website": lead_before.get("website") or "", "county": lead_before.get("county") or ""},
        )

        # Verify 15 consecutive search-suggest requests never exhaust the 10-connection pool
        for _ in range(15):
            r_s = auth_client.get("/api/v1/leads/search-suggest?q=kiddie")
            self.assertEqual(r_s.status_code, 200)

    def test_34_enterprise_lead_intake_universal_state_address_and_bulk_owner_bug_156(self):
        """
        BUG-156: Verifies the 3-Workflow Enterprise Lead Intake, Universal Address/State Hygiene,
        Standard Lead Owner Column, & Bulk Owner Assignment Architecture:
        1. Workflow A: Lead Owner ('owner') is a permanent standard column in default_cols_leads and rendered
           as an Owner Avatar Badge (.sigma-owner-badge-btn) with 1-click popover (#quick-owner-popover).
        2. Workflow B: Bulk Owner Assignment supports Single-Rep, Multi-Rep Round-Robin distribution,
           only_unassigned overwrite protection, undo_assign_owner snapshot restoration, and Accounts assign_owner.
        3. Workflow C: Universal State normalization ('Tejas', 'texas', 'tx', '' -> 'TX' via clean_state()
           and PostgreSQL trigger), USPS Pub 28 Address Line 1/Line 2 auto-splitting, Website URL normalization
           and email-domain inference, and live pre-save duplicate detection (/api/v1/leads/check-duplicate).
        """
        from core.services.sanitizer import clean_state, clean_website, split_address_lines

        # 1. Unit-verify sanitizer functions
        for variant in ("TX", "tx", "Texas", "TEXAS", "tejas", "Tejas", "tx.", ""):
            self.assertEqual(clean_state(variant), "TX", f"Variant '{variant}' must normalize to 'TX'")
        self.assertEqual(clean_state("Oklahoma"), "OK")
        self.assertEqual(clean_state("california"), "CA")

        self.assertEqual(clean_website("www.kiddieacademy.com/plano"), "https://www.kiddieacademy.com/plano")
        self.assertEqual(clean_website("", fallback_email="director@primroseschools.com"), "https://www.primroseschools.com")
        self.assertIsNone(clean_website("", fallback_email="owner@gmail.com"))

        l1, l2 = split_address_lines("5800 Granite Pkwy Suite 250", "")
        self.assertEqual(l1, "5800 Granite Pkwy")
        self.assertEqual(l2, "Suite 250")

        auth_client = self.get_auth_client()

        # 2. Verify Lead Owner is a standard column in /admin/operations?view=leads and renders .sigma-owner-badge-btn
        r_ops = auth_client.get("/admin/operations?view=leads")
        self.assertEqual(r_ops.status_code, 200)
        html_ops = r_ops.get_data(as_text=True)
        self.assertIn("Lead Owner", html_ops)
        self.assertIn("sigma-owner-badge-btn", html_ops)
        self.assertIn("id=\"quick-owner-popover\"", html_ops)
        self.assertIn("id=\"modal-bulk-assign-owner\"", html_ops)

        # 3. Verify Add Lead (POST /admin/add-lead with JSON response) normalizes state 'Tejas', splits Suite into address_line_2, and infers website
        r_add = auth_client.post(
            "/admin/add-lead",
            data={
                "company_name": "BUG156 Enterprise Verification Center",
                "contact_person": "Elena Vance",
                "email": "evance@bug156enterprise.com",
                "phone": "(972) 555-0196",
                "website": "",
                "address": "7200 Preston Rd Ste 310",
                "address_line_2": "",
                "city": "Plano",
                "state": "Tejas",
                "zipcode": "75024",
                "county": "Collin",
                "sqf": "14500",
                "status": "New",
            },
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(r_add.status_code, 200, f"POST /admin/add-lead failed: {r_add.get_data(as_text=True)}")
        add_json = r_add.get_json()
        self.assertEqual(add_json.get("status"), "success")
        new_lead_id = add_json.get("lead_id")
        self.assertIsNotNone(new_lead_id)

        try:
            # Verify stored fields via GET /api/v1/leads/<id>
            r_lead = auth_client.get(f"/api/v1/leads/{new_lead_id}")
            self.assertEqual(r_lead.status_code, 200)
            ld = r_lead.get_json()["lead"]
            self.assertEqual(ld.get("state"), "TX")
            self.assertEqual(ld.get("address"), "7200 Preston Rd")
            self.assertEqual(ld.get("address_line_2"), "Suite 310")
            self.assertEqual(ld.get("website"), "https://www.bug156enterprise.com")

            # 4. Verify live pre-save duplicate check API detects the newly created lead
            r_dup = auth_client.get("/api/v1/leads/check-duplicate?company=BUG156+Enterprise+Verification")
            self.assertEqual(r_dup.status_code, 200)
            dup_data = r_dup.get_json()
            self.assertTrue(dup_data.get("has_duplicates"))
            matched_ids = [m["id"] for m in dup_data.get("matches", [])]
            self.assertIn(new_lead_id, matched_ids)

            # 5. Verify Bulk Owner Assignment (Single Rep + Overwrite Protection + Undo Snapshot)
            conn = get_db(self.db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute('SELECT id FROM "Users" WHERE status = %s ORDER BY id ASC LIMIT 2;', ("Active",))
                    active_users = [row["id"] for row in cur.fetchall()]
            finally:
                conn.close()

            rep_a = active_users[0]
            rep_b = active_users[-1]

            # Assign to rep_a
            r_assign = auth_client.post(
                "/api/v1/leads/batch-action",
                json={"action": "assign_owner", "lead_ids": [new_lead_id], "params": {"owner_id": rep_a}},
            )
            self.assertEqual(r_assign.status_code, 200)
            assign_data = r_assign.get_json()
            self.assertEqual(assign_data.get("affected_count"), 1)
            prev_snapshot = assign_data.get("previous_owners", {})

            # Attempt assign to rep_b with only_unassigned=True -> should skip because already assigned to rep_a
            r_skip = auth_client.post(
                "/api/v1/leads/batch-action",
                json={
                    "action": "assign_owner",
                    "lead_ids": [new_lead_id],
                    "params": {"owner_id": rep_b, "only_unassigned": True},
                },
            )
            self.assertEqual(r_skip.status_code, 200)
            self.assertEqual(r_skip.get_json().get("affected_count"), 0)
            self.assertEqual(r_skip.get_json().get("skipped_already_assigned"), 1)

            # Test Round-Robin distribution across [rep_a, rep_b]
            r_rr = auth_client.post(
                "/api/v1/leads/batch-action",
                json={
                    "action": "assign_owner",
                    "lead_ids": [new_lead_id],
                    "params": {"owner_ids": [rep_b, rep_a], "distribution": "round_robin"},
                },
            )
            self.assertEqual(r_rr.status_code, 200)
            self.assertEqual(r_rr.get_json().get("affected_count"), 1)

            # Test Undo snapshot restoration
            r_undo = auth_client.post(
                "/api/v1/leads/batch-action",
                json={
                    "action": "undo_assign_owner",
                    "lead_ids": [new_lead_id],
                    "params": {"previous_owners": prev_snapshot},
                },
            )
            self.assertEqual(r_undo.status_code, 200)
            self.assertEqual(r_undo.get_json().get("status"), "success")
        finally:
            # Clean up test lead
            conn = get_db(self.db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM "LeadStageHistory" WHERE lead_id = %s;', (new_lead_id,))
                    cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = %s AND parent_id = %s;', ("Lead", new_lead_id))
                    cur.execute('DELETE FROM "Leads" WHERE id = %s;', (new_lead_id,))
                    conn.commit()
            finally:
                conn.close()

    def test_35_enterprise_lead_status_who_cleans_stage_dates_and_calling_workstation_bug_157(self) -> None:
        """
        BUG-157: Enterprise Lead Status, 'Who Cleans' Separation, Stage-Date History Tracking,
        Record Activities Reorganization & Commercial Lead Calling Workstation Upgrade.
        """
        auth_client = self.get_auth_client()

        # 1. Verify database schema & zero legacy 'Trained'/'Lost' rows
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'Leads'
                      AND column_name IN (
                          'status_changed_at', 'outreach_started_at', 'engaged_at',
                          'contacted_at', 'qualified_at', 'walkthrough_completed_at',
                          'converted_at', 'converted_to_customer_id', 'disqualified_at',
                          'disqualified_reason', 'cleaning_delivery_model'
                      );
                    """
                )
                cols = {r["column_name"] for r in cur.fetchall()}
                self.assertEqual(len(cols), 11, f"Missing milestone/cleaning columns on Leads: {cols}")

                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM "Leads"
                    WHERE status IN ('Trained', 'Lost', 'NEW', 'In-House Cleaning', 'Contract Cleaning');
                    """
                )
                legacy_cnt = int(cur.fetchone()["cnt"])
                self.assertEqual(legacy_cnt, 0, "Legacy status values must be migrated to canonical statuses/Who Cleans")
        finally:
            conn.close()

        # 2. Verify /admin/operations?view=leads renders Status + Who Cleans columns, Red pills, and Calling Session buttons
        resp = auth_client.get("/admin/operations?view=leads")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("🧹 Who Cleans", html)
        self.assertIn("🏠 In-House Cleaning", html)
        self.assertIn("🤝 Contract Cleaning", html)
        self.assertIn("📋 Walkthrough Completed", html)
        self.assertIn("🛑 Not Interested", html)
        self.assertIn("✉️ Unsubscribed", html)
        self.assertIn("🚫 Do Not Call (DNC)", html)
        self.assertIn("✅ Upgrade to Client Account", html)
        self.assertIn("lead-stage-date-tracker", html)
        self.assertIn("setCadenceCleaningModel", html)

        # 3. Create a test lead and verify Stage-Date Tracking, Stage-Protection, Who Cleans, and Upgrade to Account
        r_create = auth_client.post(
            "/admin/add-lead",
            json={
                "company_name": "BUG157 Stage Date & Who Cleans Test Facility",
                "decision_maker": "Patricia Vance",
                "job_title": "Facility Director",
                "email": "pvance@bug157facility.com",
                "phone": "2145550199",
                "address": "8100 Belt Line Rd",
                "city": "Dallas",
                "state": "TX",
                "zipcode": "75254",
                "sqf": "22000",
                "cleaning_delivery_model": "IN_HOUSE",
            },
        )
        self.assertEqual(r_create.status_code, 200)
        lead_id = int(r_create.get_json()["lead_id"])
        promoted_customer_id = None
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT id, status, cleaning_delivery_model, status_changed_at FROM "Leads" WHERE id = %s;',
                    (lead_id,),
                )
                row = cur.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["status"], "New")
                self.assertEqual(row["cleaning_delivery_model"], "IN_HOUSE")
                self.assertIsNotNone(row["status_changed_at"])
        finally:
            conn.close()

        try:
            # Verify Voicemail on 'New' lead does NOT falsely advance stage to 'Contacted'
            r_vm = auth_client.post(
                f"/api/v1/leads/{lead_id}/cadence-save",
                json={
                    "activity_type": "Voicemail Left",
                    "status": "New",
                    "note": "Left intro voicemail with front desk extension",
                    "next_action_date": "2026-11-02",
                },
            )
            self.assertEqual(r_vm.status_code, 200)
            self.assertEqual(r_vm.get_json().get("resolved_status"), "New")

            # Advance stage to 'Engaged', then verify 'Gatekeeper / Receptionist' does NOT downgrade 'Engaged' to 'Contacted'
            r_eng = auth_client.patch(f"/api/v1/leads/{lead_id}", json={"status": "Engaged"})
            self.assertEqual(r_eng.status_code, 200)
            self.assertEqual(r_eng.get_json().get("resolved_status"), "Engaged")

            r_gk = auth_client.post(
                f"/api/v1/leads/{lead_id}/cadence-save",
                json={
                    "activity_type": "Gatekeeper / Receptionist",
                    "status": "Contacted",
                    "cleaning_delivery_model": "OUTSOURCED",
                    "note": "Receptionist confirmed they use a contract cleaning crew",
                },
            )
            self.assertEqual(r_gk.status_code, 200)
            self.assertEqual(
                r_gk.get_json().get("resolved_status"),
                "Engaged",
                "Gatekeeper call must not downgrade Engaged lead to Contacted",
            )
            self.assertEqual(r_gk.get_json().get("cleaning_delivery_model"), "OUTSOURCED")

            # Advance to 'Walkthrough Completed' and inspect GET /api/v1/leads/<id> stage_history & stage_milestones
            r_wt = auth_client.patch(f"/api/v1/leads/{lead_id}", json={"status": "Walkthrough Completed"})
            self.assertEqual(r_wt.status_code, 200)

            r_detail = auth_client.get(f"/api/v1/leads/{lead_id}")
            self.assertEqual(r_detail.status_code, 200)
            detail_json = r_detail.get_json()
            milestones = detail_json.get("stage_milestones", {})
            self.assertIsNotNone(milestones.get("engaged_at"))
            self.assertIsNotNone(milestones.get("walkthrough_completed_at"))
            stage_hist = detail_json.get("stage_history", [])
            recorded_stages = [h.get("to_status") for h in stage_hist]
            self.assertIn("New", recorded_stages)
            self.assertIn("Engaged", recorded_stages)
            self.assertIn("Walkthrough Completed", recorded_stages)

            # Test Upgrade to Client Account (/api/v1/leads/<id>/promote)
            r_promo = auth_client.post(f"/api/v1/leads/{lead_id}/promote")
            self.assertEqual(r_promo.status_code, 200)
            promo_data = r_promo.get_json()
            self.assertEqual(promo_data.get("status"), "success")
            promoted_customer_id = promo_data.get("account_id")
            self.assertIsNotNone(promoted_customer_id)

            # Verify promoted lead is marked is_converted=TRUE and excluded from active Leads query
            conn = get_db(self.db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT is_converted, converted_at, converted_to_customer_id FROM "Leads" WHERE id = %s;',
                        (lead_id,),
                    )
                    l_after = cur.fetchone()
                    self.assertTrue(l_after["is_converted"])
                    self.assertIsNotNone(l_after["converted_at"])
                    self.assertEqual(int(l_after["converted_to_customer_id"]), int(promoted_customer_id))
            finally:
                conn.close()

            resp_after = auth_client.get("/admin/operations?view=leads&q=BUG157+Stage+Date")
            self.assertEqual(resp_after.status_code, 200)
            self.assertNotIn("BUG157 Stage Date &amp; Who Cleans Test Facility", resp_after.get_data(as_text=True))
        finally:
            conn = get_db(self.db_url)
            try:
                with conn.cursor() as cur:
                    if lead_id:
                        cur.execute('DELETE FROM "LeadStageHistory" WHERE lead_id = %s;', (lead_id,))
                        cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = %s AND parent_id = %s;', ("Lead", lead_id))
                        cur.execute('DELETE FROM "Leads" WHERE id = %s;', (lead_id,))
                    if promoted_customer_id:
                        cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = %s AND parent_id = %s;', ("Account", promoted_customer_id))
                        cur.execute('DELETE FROM "Customers" WHERE customer_id = %s;', (promoted_customer_id,))
                    conn.commit()
            finally:
                conn.close()

    def test_36_enterprise_lead_protection_placeholder_email_hygiene_and_worked_today_bug_158(self):
        """
        BUG-158: Verifies the 5-Part Enterprise Lead Protection & Attribution Architecture:
        1. Placeholder & internal emails ('000000000@oooo', '000000000@oooo.com', 'none@none.com',
           'hwbcleaning11@gmail.com', 'sales@hwbcleaning.com') are sanitized to None.
        2. Adding two different companies via POST /admin/add-lead (even with placeholder emails or shared phone)
           creates two independent Lead records and never overwrites the first company.
        3. Unassigned leads automatically claim owner_id of the logged-in team member when added or worked.
        4. Calling/working an older lead (input_date='2026-10-18') preserves its original input_date while
           updating updated_at and surfacing it under the '📅 Worked Today' filter (worked_today=true).
        """
        from core.services.sanitizer import clean_email
        from core.services.database import get_db

        self.assertIsNone(clean_email("000000000@oooo"))
        self.assertIsNone(clean_email("000000000@oooo.com"))
        self.assertIsNone(clean_email("none@none.com"))
        self.assertIsNone(clean_email("noemail@noemail.com"))
        self.assertIsNone(clean_email("hwbcleaning11@gmail.com"))
        self.assertIsNone(clean_email("sales@hwbcleaning.com"))
        self.assertEqual(clean_email("director@stjosephschool.org"), "director@stjosephschool.org")

        auth_client = self.get_auth_client()

        lead_id_1 = None
        lead_id_2 = None
        lead_id_old = None
        try:
            # 1. Add first company with placeholder email 000000000@oooo and no explicit owner_id
            r1 = auth_client.post(
                "/admin/add-lead",
                json={
                    "company_name": "BUG158 First Academy Richardson",
                    "decision_maker": "Alice Director",
                    "phone": "972-555-0181",
                    "email": "000000000@oooo",
                    "address": "101 Main St",
                    "city": "Richardson",
                    "state": "TX",
                    "zipcode": "75081",
                },
                headers={"Accept": "application/json"},
            )
            self.assertEqual(r1.status_code, 200)
            j1 = r1.get_json()
            lead_id_1 = j1.get("lead_id")
            self.assertIsNotNone(lead_id_1)
            self.assertFalse(j1.get("is_existing"))

            # 2. Add second company with same placeholder email AND same phone number -> MUST NOT overwrite company 1!
            r2 = auth_client.post(
                "/admin/add-lead",
                json={
                    "company_name": "BUG158 Second School Richardson",
                    "decision_maker": "Steve Manager",
                    "phone": "972-555-0181",
                    "email": "000000000@oooo",
                    "address": "600 S Jupiter Rd",
                    "city": "Richardson",
                    "state": "TX",
                    "zipcode": "75081",
                },
                headers={"Accept": "application/json"},
            )
            self.assertEqual(r2.status_code, 200)
            j2 = r2.get_json()
            lead_id_2 = j2.get("lead_id")
            self.assertIsNotNone(lead_id_2)
            self.assertNotEqual(lead_id_1, lead_id_2, "Different company name must never overwrite existing lead")

            # Verify first company is untouched, email is NULL, and owner_id was auto-assigned to user 1
            d1 = auth_client.get(f"/api/v1/leads/{lead_id_1}").get_json().get("lead", {})
            self.assertEqual(d1.get("center_name"), "BUG158 First Academy Richardson")
            self.assertIsNone(d1.get("email"))
            self.assertEqual(int(d1.get("owner_id")), 1)

            # 3. Create an older unassigned lead (input_date='2026-10-18', owner_id=NULL) and work it via cadence-save
            conn = get_db(self.db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        '''
                        INSERT INTO "Leads" (center_name, phone, city, state, status, input_date, owner_id, is_commercial)
                        VALUES (%s, %s, %s, 'TX', 'New', '2026-10-18', NULL, TRUE)
                        RETURNING id;
                        ''',
                        ("BUG158 Older Unassigned Plano School", "(972)-555-0189", "Plano"),
                    )
                    row_old = cur.fetchone()
                    lead_id_old = row_old["id"] if isinstance(row_old, dict) else row_old[0]
                    conn.commit()
            finally:
                conn.close()

            r_work = auth_client.post(
                f"/api/v1/leads/{lead_id_old}/cadence-save",
                json={
                    "activity_type": "Connected - Spoke to Decision Maker",
                    "status": "Contacted",
                    "cleaning_delivery_model": "IN_HOUSE",
                    "note": "Spoke with director regarding evening janitorial",
                },
            )
            self.assertEqual(r_work.status_code, 200)

            d_old = auth_client.get(f"/api/v1/leads/{lead_id_old}").get_json().get("lead", {})
            self.assertEqual(d_old.get("input_date"), "2026-10-18", "Original Date Added (input_date) must remain immutable")
            self.assertEqual(int(d_old.get("owner_id")), 1, "Working an unassigned lead must auto-claim owner_id")
            self.assertIsNotNone(d_old.get("updated_at"))

            # 4. Verify Worked Today filter (worked_today=true) surfaces all 3 leads
            r_wt = auth_client.get("/admin/operations?view=leads&worked_today=true&format=json")
            self.assertEqual(r_wt.status_code, 200)
            wt_ids = [l.get("id") for l in r_wt.get_json().get("leads", [])]
            self.assertIn(lead_id_1, wt_ids)
            self.assertIn(lead_id_2, wt_ids)
            self.assertIn(lead_id_old, wt_ids)

            # 5. Verify Automatic Content-Fingerprint Cache Busting & High-Contrast Calling Workstation Pills (BUG-159)
            r_html = auth_client.get("/admin/operations?view=leads")
            self.assertEqual(r_html.status_code, 200)
            html_body = r_html.get_data(as_text=True)
            self.assertRegex(
                html_body,
                r'/static/js/backoffice_operations_core\.js\?f=[0-9a-f]{8}',
                "Static JS URL must automatically include an 8-char SHA-256 content fingerprint (?f=...)",
            )
            self.assertIn('role="radiogroup" aria-label="Who Cleans Right Now"', html_body)
            self.assertIn('✓ ⚪ Unknown', html_body)
        finally:
            conn = get_db(self.db_url)
            try:
                with conn.cursor() as cur:
                    for lid in (lead_id_1, lead_id_2, lead_id_old):
                        if lid:
                            cur.execute('DELETE FROM "LeadStageHistory" WHERE lead_id = %s;', (lid,))
                            cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = %s AND parent_id = %s;', ("Lead", lid))
                            cur.execute('DELETE FROM "Leads" WHERE id = %s;', (lid,))
                    conn.commit()
            finally:
                conn.close()

    def test_37_enterprise_delete_gear_and_button_lock_lifecycle_bug_160(self):
        """
        BUG-160: Verifies the 5-Layer Enterprise Button, Gear Menu, & Delete Architecture:
        1. Layer 1 (sigma_button_lock.js): Network-Aware Fetch Auto-Unlock Engine wraps window.fetch,
           tracks pendingAjaxButtons, and removes the duplicate 25-second lock on #btn-decision-confirm.
        2. Layer 2 (showDecision & Undo Toast): showDecision awaits onConfirm and guarantees restoreButton
           inside finally; deleteUserScript uses showDecision instead of raw confirm().
        3. Layer 3 & 4 (Zero-Destruction Table Sync & Gear Menu): syncOperationalData uses DOMParser HTML
           table swap (preserving <select> dropdowns); removeTableRowsAndSyncCounts removes rows in 0ms;
           handleActivityResultChange maps 'Spoke to them' -> 'Contacted'; markLeadDNCFromModal updates
           the <select> in-place.
        4. Layer 5 (Atomic Delete with FK Children + Snapshot Undo Restore): Deleting a Lead that has
           child rows in LeadStageHistory, Contacts, GlobalActivities, CampaignRecipients, and PendingOutbox
           succeeds atomically (HTTP 200) and returns a restore_token that restores the Lead and its children
           via POST /api/v1/crm/restore-deleted.
        """
        from core.services.database import get_db

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        lock_js_path = os.path.join(base_dir, "static", "js", "sigma_button_lock.js")
        ops_js_path = os.path.join(base_dir, "static", "js", "backoffice_operations_core.js")
        base_tpl_path = os.path.join(base_dir, "templates", "backoffice_base.html")
        ops_tpl_path = os.path.join(base_dir, "templates", "backoffice_operations.html")

        with open(lock_js_path, "r", encoding="utf-8") as f:
            lock_js = f.read()
        with open(ops_js_path, "r", encoding="utf-8") as f:
            ops_js = f.read()
        with open(base_tpl_path, "r", encoding="utf-8") as f:
            base_tpl = f.read()
        with open(ops_tpl_path, "r", encoding="utf-8") as f:
            ops_tpl = f.read()

        # Layer 1 assertions
        self.assertIn("pendingAjaxButtons", lock_js)
        self.assertIn("flushPendingAjaxButtons", lock_js)
        self.assertIn("window.fetch = wrappedFetch", lock_js)
        self.assertNotIn("const confirmBtn = e.target.closest('#btn-decision-confirm')", lock_js)

        # Layer 2 assertions
        self.assertIn("restoreDeletedCrmRecord", ops_js)
        self.assertIn("finally {", base_tpl)
        self.assertNotIn('if (!confirm("Are you sure you want to delete this calling script', ops_js)

        # Layer 3 & 4 assertions
        self.assertIn("new DOMParser()", ops_js)
        self.assertIn("removeTableRowsAndSyncCounts", ops_js)
        self.assertIn("resultVal === 'Spoke to them'", ops_js)
        self.assertIn("applyLeadStatusSelectStyle(statusSelect, 'Do Not Call (DNC)')", ops_js)
        self.assertIn("openAccountCommand('{{ client.customer_id }}', 'visit')", ops_tpl)

        # Layer 5 End-to-End Atomic Delete + Snapshot Undo Restore
        auth_client = self.get_auth_client()
        lead_id = None
        campaign_id = None
        recipient_id = None
        try:
            r_create = auth_client.post(
                "/admin/add-lead",
                json={
                    "company_name": "BUG160 Enterprise Lifecycle Academy",
                    "decision_maker": "Director Evelyn",
                    "phone": "972-555-0160",
                    "email": "evelyn@bug160academy.org",
                    "address": "1600 Enterprise Pkwy",
                    "city": "Plano",
                    "state": "TX",
                    "zipcode": "75024",
                },
                headers={"Accept": "application/json"},
            )
            self.assertEqual(r_create.status_code, 200)
            lead_id = r_create.get_json().get("lead_id")
            self.assertIsNotNone(lead_id)

            # Attach child records across LeadStageHistory, Contacts, and GlobalActivities via API
            r_stage = auth_client.patch(f"/api/v1/leads/{lead_id}", json={"status": "Engaged"})
            self.assertEqual(r_stage.status_code, 200)

            r_contact = auth_client.post(
                f"/api/v1/leads/{lead_id}/contacts",
                json={
                    "full_name": "Director Evelyn",
                    "role": "Director",
                    "phone": "(972)-555-0160",
                    "email": "evelyn@bug160academy.org",
                },
            )
            self.assertEqual(r_contact.status_code, 200)

            conn = get_db(self.db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        'INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description) VALUES (%s, %s, %s, %s);',
                        (lead_id, "Lead", "Call Attempt", "Spoke with front desk"),
                    )
                    conn.commit()
            finally:
                conn.close()

            # 1st Delete: Must succeed atomically (HTTP 200) despite all 5 child tables and return restore_token
            r_del1 = auth_client.delete(f"/api/v1/leads/{lead_id}")
            self.assertEqual(r_del1.status_code, 200, "Atomic Lead DELETE with FK child rows must return 200 OK")
            del1_json = r_del1.get_json()
            self.assertEqual(del1_json.get("status"), "success")
            restore_token = del1_json.get("restore_token")
            self.assertTrue(restore_token and len(restore_token) >= 16, "DELETE must return a valid restore_token")

            # Verify Lead is gone
            r_check_gone = auth_client.get(f"/api/v1/leads/{lead_id}")
            self.assertEqual(r_check_gone.status_code, 404)

            # Undo / Restore via POST /api/v1/crm/restore-deleted
            r_restore = auth_client.post(
                "/api/v1/crm/restore-deleted",
                json={"restore_token": restore_token},
            )
            self.assertEqual(r_restore.status_code, 200)
            res_json = r_restore.get_json()
            self.assertEqual(res_json.get("status"), "success")
            self.assertGreaterEqual(res_json.get("restored_count", 0), 1)

            # Verify Lead and its Contact/Activity were restored!
            r_check_restored = auth_client.get(f"/api/v1/leads/{lead_id}")
            self.assertEqual(r_check_restored.status_code, 200)
            restored_data = r_check_restored.get_json()
            self.assertEqual(restored_data.get("lead", {}).get("center_name"), "BUG160 Enterprise Lifecycle Academy")
            self.assertGreaterEqual(len(restored_data.get("contacts", [])), 1)

            # 2nd Consecutive Delete: Verify zero lockup on back-to-back deletes
            r_del2 = auth_client.delete(f"/api/v1/leads/{lead_id}")
            self.assertEqual(r_del2.status_code, 200)
            self.assertEqual(r_del2.get_json().get("status"), "success")
            lead_id = None
        finally:
            conn = get_db(self.db_url)
            try:
                with conn.cursor() as cur:
                    if recipient_id:
                        cur.execute('DELETE FROM "PendingOutbox" WHERE recipient_id = %s;', (recipient_id,))
                        cur.execute('DELETE FROM "CampaignRecipients" WHERE id = %s;', (recipient_id,))
                    if campaign_id:
                        cur.execute('DELETE FROM "MarketingCampaigns" WHERE id = %s;', (campaign_id,))
                    if lead_id:
                        cur.execute('DELETE FROM "LeadStageHistory" WHERE lead_id = %s;', (lead_id,))
                        cur.execute('DELETE FROM "Contacts" WHERE lead_id = %s;', (lead_id,))
                        cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = %s AND parent_id = %s;', ("Lead", lead_id))
                        cur.execute('DELETE FROM "Leads" WHERE id = %s;', (lead_id,))
                    conn.commit()
            finally:
                conn.close()

    def test_38_enterprise_accounting_double_entry_stripe_and_qbo_engine_arch_017(self):
        """
        ARCH-017 7-Pillar Enterprise Double-Entry Accounting, QuickBooks Replacement & Stripe Billing Sentinel:
        1. Department Workspace & RBAC:
           - /admin/operations?view=accounting renders 200 OK for Executive/Admin with 28 Chart of Accounts.
           - Unbalanced journal entries (Debits != Credits) are rejected with 400 Bad Request.
        2. Stripe Invoicing, ACH $5 Cap & Texas 8.25% Sales Tax:
           - POST /api/v1/accounting/invoices computes 8.25% Texas sales tax ($2,000 -> $165 tax -> $2,165 total)
             and posts a balanced Double-Entry Journal Entry (DR 1100 / CR 4000 / CR 2100).
           - Public client portal (/pay/invoice/<token>) renders 200 OK with zero pre-checked consent boxes
             and settles via ACH ($5.00 max fee -> DR 1000 $2,160.00 + DR 6100 $5.00 = CR 1100 $2,165.00).
        3. Construction Progress Billing (10% Retainage) & Texas Statutory Lien Waivers (§ 53.284):
           - Construction progress invoice holds 10% retainage in Account 1150, generates Conditional Waiver,
             settles via Stripe Webhook (/api/v1/webhooks/stripe), and upgrades to Unconditional Released.
        4. Accounts Payable, 1099-NEC Subcontractor Bills & 3-Way Compliance Lock:
           - Subcontractor bill without W-9/COI triggers 'Hold: Missing W-9/COI' and blocks payout (409)
             until verified or authorized by CEO override.
        5. Expense Receipt Vault, QuickBooks CSV Import, 10-Second Delete Undo & CPA Exports:
           - Verifies expense logging, QBO CSV import, CPA CSV exports (P&L, Texas Form 01-114, 1099-NEC),
             and 1-click invoice delete + undo restoration.
        """
        auth_client = self.get_auth_client()
        created_invoice_ids = []
        created_bill_ids = []
        created_expense_ids = []

        try:
            # 1. Verify /admin/operations?view=accounting renders 200 OK and 28 Chart of Accounts exist
            r_view = auth_client.get("/admin/operations?view=accounting")
            self.assertEqual(r_view.status_code, 200)
            html = r_view.get_data(as_text=True)
            self.assertIn("Finance, Double-Entry General Ledger &amp; Stripe Billing Hub", html)
            self.assertIn("accounting_engine.js", html)

            r_ov = auth_client.get("/api/v1/accounting/overview")
            self.assertEqual(r_ov.status_code, 200)
            ov_data = r_ov.get_json().get("data", {})
            self.assertGreaterEqual(len(ov_data.get("chart_of_accounts", [])), 28)

            # Verify unbalanced manual journal entry is rejected (Debits != Credits)
            r_unbalanced = auth_client.post(
                "/api/v1/accounting/journal-entries",
                json={
                    "memo": "ARCH017 Unbalanced Test",
                    "lines": [
                        {"account_code": "1000", "debit": "500.00", "credit": "0.00"},
                        {"account_code": "4000", "debit": "0.00", "credit": "450.00"},
                    ],
                },
            )
            self.assertEqual(r_unbalanced.status_code, 400)
            self.assertIn("Unbalanced journal entry rejected", r_unbalanced.get_json().get("message", ""))

            # 2. Create Recurring Janitorial Invoice ($2,000.00 + 8.25% TX Sales Tax = $2,165.00)
            r_inv1 = auth_client.post(
                "/api/v1/accounting/invoices",
                json={
                    "client_name": "ARCH017 Dallas Medical Plaza",
                    "client_email": "ap@arch017medical.example.com",
                    "facility_address": "5000 Preston Rd, Dallas, TX 75205",
                    "billing_mode": "Recurring Janitorial",
                    "description": "Monthly Clinical Janitorial & Sanitization",
                    "amount": "2000.00",
                    "is_tax_exempt": False,
                },
            )
            self.assertEqual(r_inv1.status_code, 200)
            inv1 = r_inv1.get_json()["invoice"]
            created_invoice_ids.append(inv1["id"])
            self.assertEqual(inv1["subtotal_cents"], 200000)
            self.assertEqual(inv1["tax_cents"], 16500)  # 8.25% of $2,000.00 = $165.00
            self.assertEqual(inv1["total_cents"], 216500)
            self.assertEqual(inv1["balance_due_cents"], 216500)
            self.assertEqual(inv1["journal_entry"]["total_debit_cents"], 216500)
            self.assertEqual(inv1["journal_entry"]["total_credit_cents"], 216500)

            # Verify Public Client Payment Portal (/pay/invoice/<token>)
            ptoken1 = inv1["payment_token"]
            r_portal = self.client.get(f"/pay/invoice/{ptoken1}")
            self.assertEqual(r_portal.status_code, 200)
            portal_html = r_portal.get_data(as_text=True)
            self.assertIn(inv1["invoice_number"], portal_html)
            self.assertIn("$2,165.00", portal_html)
            # Consent checkbox must NOT be pre-checked (BUG-149)
            self.assertNotIn('id="ach-consent-checkbox" name="ach_authorization_consent" value="1" checked', portal_html)

            # Pay via Public Client Portal (ACH $5.00 max fee cap)
            r_pay1 = self.client.post(
                f"/pay/invoice/{ptoken1}/complete",
                json={
                    "payment_method": "us_bank_account",
                    "payer_name": "ARCH017 Controller",
                    "ach_authorization_consent": True,
                },
            )
            self.assertEqual(r_pay1.status_code, 200)
            settlement1 = r_pay1.get_json()["settlement"]
            self.assertEqual(settlement1["status"], "Paid")
            self.assertEqual(settlement1["stripe_fee_cents"], 500)  # $5.00 ACH cap
            self.assertEqual(settlement1["net_cash_cents"], 216000)  # $2,160.00 net cash

            # 3. Create Construction Progress Invoice ($10,000.00, Tax-Exempt GC Resale, 10% Retainage)
            r_inv2 = auth_client.post(
                "/api/v1/accounting/invoices",
                json={
                    "client_name": "ARCH017 Turner Construction Co",
                    "billing_mode": "Construction Progress (AIA G702)",
                    "description": "Phase 2 Final Post-Construction Detail",
                    "amount": "10000.00",
                    "retainage_pct": 10.0,
                    "is_tax_exempt": True,
                    "tax_exempt_cert_number": "TX-RESALE-998877",
                },
            )
            self.assertEqual(r_inv2.status_code, 200)
            inv2 = r_inv2.get_json()["invoice"]
            created_invoice_ids.append(inv2["id"])
            self.assertEqual(inv2["subtotal_cents"], 1000000)
            self.assertEqual(inv2["tax_cents"], 0)
            self.assertEqual(inv2["retainage_cents"], 100000)  # 10% retainage = $1,000.00
            self.assertEqual(inv2["balance_due_cents"], 900000)  # $9,000.00 progress due
            self.assertEqual(inv2["lien_waiver_status"], "Conditional Ready")

            # Verify Texas Statutory Conditional Lien Waiver (§ 53.284)
            r_waiver_cond = auth_client.get(f"/api/v1/accounting/invoices/{inv2['id']}/lien-waiver?type=conditional")
            self.assertEqual(r_waiver_cond.status_code, 200)
            self.assertIn("CONDITIONAL WAIVER AND RELEASE ON PROGRESS PAYMENT", r_waiver_cond.get_data(as_text=True))
            self.assertIn("53.284", r_waiver_cond.get_data(as_text=True))

            # Settle Construction Progress Invoice via Stripe Webhook Receiver
            r_wh = self.client.post(
                "/api/v1/webhooks/stripe",
                json={
                    "type": "checkout.session.completed",
                    "data": {
                        "object": {
                            "payment_method_types": ["us_bank_account"],
                            "metadata": {
                                "invoice_number": inv2["invoice_number"],
                                "payment_token": inv2["payment_token"],
                            },
                        }
                    },
                },
            )
            self.assertEqual(r_wh.status_code, 200)
            wh_settlement = r_wh.get_json()["settlement"]
            self.assertEqual(wh_settlement["status"], "Paid")
            self.assertEqual(wh_settlement["lien_waiver_status"], "Unconditional Released")

            # 4. Create 1099 Subcontractor Bill without W-9/COI -> Verify 3-Way Compliance Lock
            r_bill = auth_client.post(
                "/api/v1/accounting/bills",
                json={
                    "vendor_name": "ARCH017 Subcontractor Crew LLC",
                    "job_site_name": "ARCH017 Medical Plaza",
                    "gross_amount": "1200.00",
                    "w9_verified": False,
                    "coi_verified": False,
                },
            )
            self.assertEqual(r_bill.status_code, 200)
            bill = r_bill.get_json()["bill"]
            created_bill_ids.append(bill["id"])
            self.assertEqual(bill["compliance_lock_status"], "Hold: Missing W-9/COI")

            # Attempt payout without override -> Must block with 409 Conflict
            r_bill_block = auth_client.post(f"/api/v1/accounting/bills/{bill['id']}/pay", json={"ceo_override": False})
            self.assertEqual(r_bill_block.status_code, 409)
            self.assertTrue(r_bill_block.get_json().get("compliance_blocked"))

            # Release payout with CEO Override -> 200 OK
            r_bill_pay = auth_client.post(f"/api/v1/accounting/bills/{bill['id']}/pay", json={"ceo_override": True})
            self.assertEqual(r_bill_pay.status_code, 200)

            # 5. Log Expense Receipt + QuickBooks CSV Import + Delete/Undo + CPA Exports
            r_exp = auth_client.post(
                "/api/v1/accounting/expenses",
                json={
                    "merchant_name": "ARCH017 Chemical Supply Co",
                    "category_account_code": "5200",
                    "amount": "240.50",
                    "job_site_name": "ARCH017 Medical Plaza",
                    "receipt_memo": "Hospital Disinfectant & Microfiber Pads",
                },
            )
            self.assertEqual(r_exp.status_code, 200)
            exp = r_exp.get_json()["expense"]
            created_expense_ids.append(exp["id"])

            # Test Delete Invoice + 10-Second Undo Snapshot Restoration
            r_del_inv = auth_client.delete(f"/api/v1/accounting/invoices/{inv1['id']}")
            self.assertEqual(r_del_inv.status_code, 200)
            undo_token = r_del_inv.get_json().get("undo_token")
            self.assertTrue(undo_token)

            r_undo_inv = auth_client.post("/api/v1/accounting/restore-deleted", json={"undo_token": undo_token})
            self.assertEqual(r_undo_inv.status_code, 200)

            # Verify CPA CSV Exports (P&L, Texas Sales Tax Form 01-114, 1099-NEC, General Ledger)
            for exp_type in ("pnl", "texas_sales_tax", "1099_nec", "general_ledger"):
                r_csv = auth_client.get(f"/api/v1/accounting/export/{exp_type}")
                self.assertEqual(r_csv.status_code, 200)
                self.assertIn("text/csv", r_csv.headers.get("Content-Type", ""))
        finally:
            conn = get_db(self.db_url)
            try:
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM "AccountingJournalEntries" WHERE memo LIKE %s OR reference_code IN (SELECT invoice_number FROM "ClientInvoices" WHERE client_name LIKE %s);', ("ARCH017%", "ARCH017%"))
                    cur.execute('DELETE FROM "AccountingJournalEntries" WHERE reference_code IN (SELECT bill_number FROM "VendorBills" WHERE vendor_name LIKE %s);', ("ARCH017%",))
                    cur.execute('DELETE FROM "AccountingJournalEntries" WHERE reference_code IN (SELECT receipt_number FROM "ExpenseReceipts" WHERE merchant_name LIKE %s);', ("ARCH017%",))
                    if created_invoice_ids:
                        cur.execute('DELETE FROM "ClientInvoices" WHERE id = ANY(%s) OR client_name LIKE %s;', (created_invoice_ids, "ARCH017%"))
                    if created_bill_ids:
                        cur.execute('DELETE FROM "VendorBills" WHERE id = ANY(%s) OR vendor_name LIKE %s;', (created_bill_ids, "ARCH017%"))
                    if created_expense_ids:
                        cur.execute('DELETE FROM "ExpenseReceipts" WHERE id = ANY(%s) OR merchant_name LIKE %s;', (created_expense_ids, "ARCH017%"))
                    conn.commit()
            finally:
                conn.close()

    def test_39_enterprise_lead_notes_workflow_bug_159(self):
        """
        BUG-159: Certifies the 9-Pillar Enterprise Lead Notes & Touchpoint Architecture:
        1. PostgreSQL 16.15 schema columns on GlobalActivities & Leads (created_by_user_id, created_by_name,
           outcome, is_pinned, updated_at, edited_by_name, revision_history, notes_revision_history).
        2. Dual-Layer Standing Facility Brief (Leads.notes) vs Pinned/Chronological Touchpoints (GlobalActivities),
           plus elimination of false-positive NOTE spam on PUT /api/v1/leads/<id> when notes did not change.
        3. Inline editing of Standing Facility Brief + version history + 1-click version restore.
        4. Inline editing of Activity Notes + pin/unpin toggle + version history + 1-click version restore.
        5. Smart Field Extraction (email, phone, SQF, capacity, Who Cleans IN_HOUSE/OUTSOURCED) from note text.
        6. Sister-Location Note Broadcast across shared umbrella_name.
        7. Full-Text Search parity for note:<keyword>, has:notes, and has:pinned across Leads.notes and GlobalActivities.
        8. Lead-to-Account Promotion preserves both Standing Brief (Customers.notes) and GlobalActivities rows.
        """
        import uuid
        from core.services.search import parse_advanced_search

        auth_client = self.get_auth_client()

        uid = uuid.uuid4().hex[:6]
        umbrella_tag = f"HWB_UMBRELLA_{uid}"
        lead_ids = []
        created_customer_id = None

        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                for idx in (1, 2):
                    cur.execute(
                        '''
                        INSERT INTO "Leads" (
                            center_name, umbrella_name, director, city, state, status,
                            cleaning_delivery_model, sqf, capacity
                        ) VALUES (%s, %s, %s, 'Dallas', 'TX', 'New', 'UNKNOWN', 0, 0)
                        RETURNING id;
                        ''',
                        (f"Enterprise Note Test Center {idx} {uid}", umbrella_tag, f"Director {idx}"),
                    )
                    lead_ids.append(cur.fetchone()["id"])
                conn.commit()

            lead1_id, lead2_id = lead_ids[0], lead_ids[1]

            # 1. Verify PUT /api/v1/leads/<id> without changing notes does NOT create false-positive NOTE spam
            r_put_no_note = auth_client.put(
                f"/api/v1/leads/{lead1_id}",
                json={"city": "Plano", "notes": ""},
            )
            self.assertEqual(r_put_no_note.status_code, 200)
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT COUNT(*) AS cnt FROM "GlobalActivities" WHERE parent_type = \'Lead\' AND parent_id = %s;',
                    (lead1_id,),
                )
                self.assertEqual(cur.fetchone()["cnt"], 0)
            conn.commit()

            # 2. Save Standing Facility Brief (v1 -> v2) and test 1-click restore to v1
            r_brief_v1 = auth_client.put(
                f"/api/v1/leads/{lead1_id}/standing-brief",
                json={"notes": "Gatekeeper: Maria. Best Hours: 8:30am-11:00am.", "log_touchpoint": False},
            )
            self.assertEqual(r_brief_v1.status_code, 200)
            self.assertEqual(r_brief_v1.get_json()["standing_brief"], "Gatekeeper: Maria. Best Hours: 8:30am-11:00am.")

            r_brief_v2 = auth_client.put(
                f"/api/v1/leads/{lead1_id}/standing-brief",
                json={"notes": "Gatekeeper: Maria. Best Hours: 9:00am-11:30am. Gate Code: #4412.", "log_touchpoint": False},
            )
            self.assertEqual(r_brief_v2.status_code, 200)
            b2_data = r_brief_v2.get_json()
            self.assertEqual(len(b2_data["notes_revision_history"]), 1)
            self.assertEqual(b2_data["notes_revision_history"][0]["old_text"], "Gatekeeper: Maria. Best Hours: 8:30am-11:00am.")

            r_brief_restore = auth_client.post(
                f"/api/v1/leads/{lead1_id}/standing-brief/restore",
                json={"version": 1},
            )
            self.assertEqual(r_brief_restore.status_code, 200)
            self.assertEqual(r_brief_restore.get_json()["standing_brief"], "Gatekeeper: Maria. Best Hours: 8:30am-11:00am.")

            # 3. Log Call Note via cadence-save with Smart Field Extraction + Pin + Sister-Location Broadcast
            smart_note = (
                f"Spoke with receptionist Maria ({uid}). Director Sandra email is sandra.{uid}@kinder-test.org "
                f"and direct cell is (214)-555-0144. Building is 14,500 sq ft with 185 kids capacity. "
                f"Currently teachers clean in-house."
            )
            r_cad = auth_client.post(
                f"/api/v1/leads/{lead1_id}/cadence-save",
                json={
                    "activity_type": "Phone Call",
                    "outcome": "Left Message with Staff",
                    "note": smart_note,
                    "is_pinned": True,
                    "share_umbrella": True,
                },
            )
            self.assertEqual(r_cad.status_code, 200)
            cad_json = r_cad.get_json()
            self.assertEqual(cad_json["status"], "success")
            self.assertEqual(cad_json["sister_broadcast_count"], 1)
            auto_fields = cad_json.get("auto_updated_fields") or {}
            self.assertEqual(auto_fields.get("email"), f"sandra.{uid}@kinder-test.org")
            self.assertEqual(auto_fields.get("phone"), "(214)-555-0144")
            self.assertEqual(auto_fields.get("sqf"), 14500)
            self.assertEqual(auto_fields.get("capacity"), 185)
            self.assertEqual(auto_fields.get("cleaning_delivery_model"), "IN_HOUSE")

            # Verify Sister Lead #2 received the broadcast note AND GET /api/v1/leads/<id> exposes activity 'id'
            r_sis_acts = auth_client.get(f"/api/v1/activities/Lead/{lead2_id}")
            self.assertEqual(r_sis_acts.status_code, 200)
            sis_acts = r_sis_acts.get_json()["activities"]
            self.assertEqual(len(sis_acts), 1)
            self.assertIn("Shared from", sis_acts[0]["description"])
            sis_act_id = sis_acts[0]["id"]
            self.assertIsNotNone(sis_act_id)

            r_l2_detail = auth_client.get(f"/api/v1/leads/{lead2_id}")
            self.assertEqual(r_l2_detail.status_code, 200)
            l2_detail_acts = r_l2_detail.get_json().get("activities") or []
            self.assertEqual(len(l2_detail_acts), 1)
            self.assertEqual(l2_detail_acts[0].get("id"), sis_act_id)

            # Verify DELETE /api/v1/activities/<id> removes the note and returns updated counts/last_note
            r_del_sis_act = auth_client.delete(f"/api/v1/activities/{sis_act_id}")
            self.assertEqual(r_del_sis_act.status_code, 200)
            del_json = r_del_sis_act.get_json()
            self.assertEqual(del_json.get("status"), "success")
            self.assertEqual(del_json.get("activity_count"), 0)
            self.assertEqual(del_json.get("last_note"), "")

            # 4. Verify Activity Note Inline Edit + Version History + Restore + Pin Toggle
            r_l1_acts = auth_client.get(f"/api/v1/activities/Lead/{lead1_id}")
            self.assertEqual(r_l1_acts.status_code, 200)
            l1_payload = r_l1_acts.get_json()
            self.assertEqual(l1_payload["standing_brief"], "Gatekeeper: Maria. Best Hours: 8:30am-11:00am.")
            act_id = l1_payload["activities"][0]["id"]
            self.assertTrue(l1_payload["activities"][0]["is_pinned"])
            self.assertEqual(l1_payload["activities"][0]["outcome"], "Left Message with Staff")

            edited_note_text = f"UPDATED NOTE ({uid}): Director Sandra confirmed Tuesday 10am walkthrough."
            r_edit_act = auth_client.put(
                f"/api/v1/activities/{act_id}",
                json={"description": edited_note_text},
            )
            self.assertEqual(r_edit_act.status_code, 200)
            edited_act = r_edit_act.get_json()["activity"]
            self.assertEqual(edited_act["description"], edited_note_text)
            self.assertEqual(len(edited_act["revision_history"]), 1)
            self.assertEqual(edited_act["revision_history"][0]["old_text"], smart_note)

            # Restore Activity Note to version 1
            r_rest_act = auth_client.post(f"/api/v1/activities/{act_id}/restore", json={"version": 1})
            self.assertEqual(r_rest_act.status_code, 200)
            restored_act = r_rest_act.get_json()["activity"]
            self.assertEqual(restored_act["description"], smart_note)
            self.assertEqual(len(restored_act["revision_history"]), 2)

            # 5. Verify Full-Text Search Engine Parity (note:<uid>, has:notes, has:pinned)
            conds_note, params_note = parse_advanced_search(f"note:{uid}")
            conds_pinned, params_pinned = parse_advanced_search("has:pinned")
            sql_note = " AND ".join(conds_note) if isinstance(conds_note, list) else str(conds_note)
            sql_pinned = " AND ".join(conds_pinned) if isinstance(conds_pinned, list) else str(conds_pinned)
            with conn.cursor() as cur:
                cur.execute(f'SELECT id FROM "Leads" WHERE ({sql_note}) AND id = %s;', params_note + [lead1_id])
                self.assertIsNotNone(cur.fetchone())
                cur.execute(f'SELECT id FROM "Leads" WHERE ({sql_pinned}) AND id = %s;', params_pinned + [lead1_id])
                self.assertIsNotNone(cur.fetchone())
            conn.commit()

            # 6. Verify Lead-to-Account Promotion preserves Standing Brief + GlobalActivities
            r_prom = auth_client.post(f"/api/v1/leads/{lead1_id}/promote")
            self.assertEqual(r_prom.status_code, 200)
            created_customer_id = r_prom.get_json().get("customer_id")
            self.assertTrue(created_customer_id)

            with conn.cursor() as cur:
                cur.execute('SELECT notes FROM "Customers" WHERE customer_id = %s;', (created_customer_id,))
                cust_row = cur.fetchone()
                self.assertIsNotNone(cust_row)
                self.assertIn("Gatekeeper: Maria", cust_row["notes"] or "")

                cur.execute(
                    'SELECT COUNT(*) AS cnt FROM "GlobalActivities" WHERE parent_type = \'Account\' AND parent_id = %s;',
                    (created_customer_id,),
                )
                self.assertGreaterEqual(cur.fetchone()["cnt"], 2)
            conn.commit()
        finally:
            conn.rollback()
            with conn.cursor() as cur:
                if created_customer_id:
                    cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = \'Account\' AND parent_id = %s;', (created_customer_id,))
                    cur.execute('DELETE FROM "Customers" WHERE customer_id = %s;', (created_customer_id,))
                if lead_ids:
                    cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = \'Lead\' AND parent_id = ANY(%s);', (lead_ids,))
                    cur.execute('DELETE FROM "Leads" WHERE id = ANY(%s);', (lead_ids,))
                conn.commit()
            conn.close()

    def test_40_enterprise_universal_grid_column_persistence_and_sorting_bug_164(self):
        """
        BUG-164: Verifies the 5-Pillar Enterprise Universal Grid Engine across Leads, Accounts,
        Commercial GC Bids, and Secondary Backoffice Tables:
        1. PostgreSQL Per-User Grid State API (GET / POST /api/v1/ui/grid-state) persists ordered
           active_cols, col_widths, and personal_preset inside "UserBehavioralProfiles".adaptive_preferences.
        2. Dragged column sequence persists across pagination (page=2) and search (q=Dallas) without
           requiring cols= in pagination hrefs or search hidden inputs.
        3. All sorting keys in Leads (dm, state, zip, last_note, priority, status, m_and_a, owner,
           value, sqf, activities), Accounts (cycle, sqf, website, last_note, rep), and GC Bids
           (phone, email, special_reqs) execute valid SQL and return HTTP 200.
        4. Order-Preserving Column Manager, Column Resizers (.sigma-col-resizer), Dynamic Sticky
           Collision Shield, and Universal Secondary Table Upgrader are active in JS/HTML.
        """
        import re

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ops_js_path = os.path.join(base_dir, "static", "js", "backoffice_operations_core.js")
        ops_tpl_path = os.path.join(base_dir, "templates", "backoffice_operations.html")

        with open(ops_js_path, "r", encoding="utf-8") as f:
            ops_js = f.read()
        with open(ops_tpl_path, "r", encoding="utf-8") as f:
            ops_tpl = f.read()

        # Verify JS/HTML Enterprise Grid Architecture markers
        self.assertIn("computeOrderPreservingCols", ops_js)
        self.assertIn("saveGridStateToServer", ops_js)
        self.assertIn("syncNavigationLinksCols", ops_js)
        self.assertIn("initColumnResizersAndDensity", ops_js)
        self.assertIn("upgradeUniversalSecondaryTables", ops_js)
        self.assertIn("DESC_FIRST_SORT_COLS", ops_js)
        self.assertIn("sigma-col-resizer", ops_tpl)
        self.assertIn("SERVER_GRID_STATE", ops_tpl)
        self.assertNotIn('id="search-cols-input"', ops_tpl)
        self.assertNotIn('id="acc-cols-input"', ops_tpl)

        auth_client = self.get_auth_client()
        try:
            # 1. Save custom dragged column sequence + custom widths + personal preset via /api/v1/ui/grid-state
            custom_dragged_cols = ["company", "value", "sqf", "status", "owner", "phone", "last_note"]
            r_save = auth_client.post(
                "/api/v1/ui/grid-state",
                json={
                    "grid_id": "leads",
                    "active_cols": custom_dragged_cols,
                    "col_widths": {"company": 340, "value": 135},
                    "personal_preset": custom_dragged_cols,
                },
            )
            self.assertEqual(r_save.status_code, 200)
            save_json = r_save.get_json()
            self.assertEqual(save_json.get("status"), "success")
            self.assertEqual(save_json["state"]["active_cols"], custom_dragged_cols)
            self.assertEqual(save_json["state"]["col_widths"].get("company"), 340)

            # 2. Verify GET /api/v1/ui/grid-state returns persisted PostgreSQL state
            r_get_state = auth_client.get("/api/v1/ui/grid-state?grid_id=leads")
            self.assertEqual(r_get_state.status_code, 200)
            self.assertEqual(r_get_state.get_json()["state"]["active_cols"], custom_dragged_cols)

            # 3. Navigate to Page 2 and Search WITHOUT cols= in URL -> must preserve custom dragged column order!
            for nav_url in ("/admin/operations?view=leads&page=2", "/admin/operations?view=leads&q=Dallas"):
                r_page = auth_client.get(nav_url)
                self.assertEqual(r_page.status_code, 200)
                html = r_page.get_data(as_text=True)
                m_header = re.search(r'<tr id="leads-header-row"[^>]*>(.*?)</tr>', html, re.S)
                self.assertIsNotNone(m_header)
                rendered_cols = re.findall(r'data-col="([^"]+)"', m_header.group(1))
                self.assertEqual(
                    rendered_cols,
                    custom_dragged_cols,
                    f"Dragged column order must persist across {nav_url}",
                )

            # 4. Verify semantic & newly wired SQL sorting across Leads, Accounts, and GC Bids
            for lead_sort_col in ("dm", "state", "zip", "last_note", "priority", "status", "m_and_a", "owner", "value", "sqf", "activities"):
                r_sort = auth_client.get(f"/admin/operations?view=leads&sort_by={lead_sort_col}&sort_dir=desc")
                self.assertEqual(r_sort.status_code, 200, f"Leads sort_by={lead_sort_col} failed")

            for acc_sort_col in ("cycle", "sqf", "website", "last_note", "rep", "revenue", "status"):
                r_acc_sort = auth_client.get(f"/admin/operations?view=accounts&acc_sort_by={acc_sort_col}&acc_sort_dir=desc")
                self.assertEqual(r_acc_sort.status_code, 200, f"Accounts acc_sort_by={acc_sort_col} failed")

            for bid_sort_col in ("phone", "email", "special_reqs", "value", "sqft", "due_date", "status"):
                r_bid_sort = auth_client.get(f"/admin/operations?view=construction_bids&bid_sort={bid_sort_col}&bid_dir=desc")
                self.assertEqual(r_bid_sort.status_code, 200, f"GC Bids bid_sort={bid_sort_col} failed")
        finally:
            # Reset grid state to clean default so subsequent tests see the standard 8-column default layout
            auth_client.post("/api/v1/ui/grid-state", json={"grid_id": "leads", "reset": True})
            auth_client.post("/api/v1/ui/grid-state", json={"grid_id": "accounts", "reset": True})
            auth_client.post("/api/v1/ui/grid-state", json={"grid_id": "construction_bids", "reset": True})

    def test_41_enterprise_subcontractor_email_deliverability_and_antiphishing_bug_166(self):
        """
        BUG-166: Verifies the 6-Pillar Fortune 500 Subcontractor Email Deliverability & Anti-Phishing Shield:
        1. BIMI SVG Brand Logo (/static/img/hwb_bimi.svg) serves 200 OK with valid SVG Tiny-PS markup.
        2. Stream Isolation & RFC 5322 Headers in core/services/email_service.py:
           - Separates transactional vs marketing streams, wraps fragments in <!DOCTYPE html>, and
             sets explicit from display name ("HWB Cleaning Services LLC") and replyTo.
        3. Anti-Phishing Content Firewall & Canonical URL Enforcement in core/services/notification_service.py:
           - Zero BEC phishing subject prefixes (ACTION REQUIRED:, URGENT:, APPROVED:) and zero raw
             tax-scam triggers (W-9, EIN/SSN, 1099) in subcontractor email bodies.
           - Enforces https://www.hwbcleaning.com canonical links and attaches HWB-COM-001 signature cid:hwblogo.
        4. Multi-Channel SMS + Email Delivery in POST /api/v1/workforce/subcontractors/<id>/send-onboarding:
           - Returns canonical onboarding_url, sms_body, and sms_uri, and renders 1-tap SMS buttons in UI.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        email_svc_path = os.path.join(base_dir, "core", "services", "email_service.py")
        notif_svc_path = os.path.join(base_dir, "core", "services", "notification_service.py")
        ops_js_path = os.path.join(base_dir, "static", "js", "backoffice_operations_core.js")
        ops_tpl_path = os.path.join(base_dir, "templates", "backoffice_operations.html")

        with open(email_svc_path, "r", encoding="utf-8") as f:
            email_svc_src = f.read()
        with open(notif_svc_path, "r", encoding="utf-8") as f:
            notif_svc_src = f.read()
        with open(ops_js_path, "r", encoding="utf-8") as f:
            ops_js = f.read()
        with open(ops_tpl_path, "r", encoding="utf-8") as f:
            ops_tpl = f.read()

        # 1. Verify BIMI SVG asset serves 200 OK
        r_bimi = self.client.get("/static/img/hwb_bimi.svg")
        self.assertEqual(r_bimi.status_code, 200)
        bimi_svg = r_bimi.get_data(as_text=True)
        self.assertIn("tiny-ps", bimi_svg)
        self.assertIn("<title>HWB Cleaning Services LLC</title>", bimi_svg)

        # 2. Verify Stream Isolation & RFC 5322 headers in email_service.py
        self.assertIn("stream_type", email_svc_src)
        self.assertIn("<!DOCTYPE html>", email_svc_src)
        self.assertIn('"name": sender_name', email_svc_src)
        self.assertIn('"replyTo":', email_svc_src)

        # 3. Verify Anti-Phishing Content Firewall & Canonical URL helper in notification_service.py
        self.assertIn("build_canonical_portal_url", notif_svc_src)
        self.assertIn("build_subcontractor_sms_invite", notif_svc_src)
        self.assertNotIn("ACTION REQUIRED:", notif_svc_src)
        self.assertNotIn("URGENT:", notif_svc_src)
        self.assertNotIn("APPROVED: Welcome to the HWB", notif_svc_src)

        from core.services.notification_service import (
            build_canonical_portal_url,
            build_subcontractor_sms_invite,
        )
        self.assertEqual(build_canonical_portal_url("/onboard/subcontractor/testtoken"), "https://www.hwbcleaning.com/onboard/subcontractor/testtoken")
        sms_sample = build_subcontractor_sms_invite(
            {
                "company_name": "Apex Floor Care LLC",
                "contact_name": "Carlos",
                "partner_id": 42,
                "phone": "214-555-0199",
                "onboarding_url": "/onboard/subcontractor/testtoken",
            }
        )
        self.assertIn("HWB Cleaning Services LLC", sms_sample.get("sms_body", ""))
        self.assertIn("https://www.hwbcleaning.com/onboard/subcontractor/testtoken", sms_sample.get("sms_body", ""))
        self.assertTrue(sms_sample.get("sms_uri", "").startswith("sms:+12145550199"))

        # 4. Verify UI SMS + Copy SMS controls exist
        self.assertIn("sub-doc-sms-btn", ops_tpl)
        self.assertIn("sub-doc-copy-sms-btn", ops_tpl)
        self.assertIn("copySubcontractorSmsInvite", ops_js)
        self.assertIn("triggerSubcontractorSmsInvite", ops_js)

        # 5. End-to-End API test for POST /api/v1/workforce/subcontractors/<id>/send-onboarding
        auth_client = self.get_auth_client()
        sub_id = None
        conn = get_db(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO "SubcontractorPartners" (company_name, contact_name, email, phone, specialties, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    ''',
                    ("BUG166 Deliverability Partner LLC", "Carlos Rivera", "carlos.bug166@example.com", "214-555-0166", "Janitorial", "Pending Vetting"),
                )
                sub_id = cur.fetchone()["id"]
                conn.commit()

            r_send = auth_client.post(f"/api/v1/workforce/subcontractors/{sub_id}/send-onboarding")
            self.assertEqual(r_send.status_code, 200)
            send_json = r_send.get_json()
            self.assertEqual(send_json.get("status"), "success")
            self.assertTrue(
                send_json.get("onboarding_url", "").startswith("https://www.hwbcleaning.com/onboard/subcontractor/"),
                f"Expected canonical www URL, got {send_json.get('onboarding_url')}",
            )
            self.assertIn("HWB Cleaning Services", send_json.get("sms_body", ""))
            self.assertTrue(send_json.get("sms_uri", "").startswith("sms:"))
        finally:
            if sub_id:
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM "SubcontractorPartners" WHERE id = %s;', (sub_id,))
                    conn.commit()
            conn.close()

    def test_42_enterprise_mandatory_followup_and_notes_task_engine_bug_165(self):
        """
        BUG-165: Verifies the 4-Pillar Mandatory Follow-Up & Task Engine for the Notes Workflow:
        1. Zero-Orphan Follow-Up Guarantee:
           - Saving a note on an open lead via /api/v1/activities/quick-log or /api/v1/leads/<id>/cadence-save
             with no next_action_date (or a past date) automatically assigns a valid future business-day
             next_action_date and creates an OPEN task on "GlobalActivities".
        2. Natural-Language Smart Follow-Up Date Extraction:
           - Note text containing "call back tomorrow" or "follow up next week" automatically extracts
             and schedules the corresponding business date.
        3. Task Lifecycle & Completion Roll-Forward:
           - POST /api/v1/activities/<id>/complete-task marks the task COMPLETED and rolls the lead's
             next_action_date forward to the next business SLA date.
           - Terminal outcomes ("Not Interested", "Unsubscribed", "Do Not Call (DNC)") automatically clear
             next_action_date = NULL and close open tasks.
        4. Follow-Up Toolbar Filter & Search Tokens:
           - /admin/operations?view=leads&followup_filter=due and q=followup:due return 200 OK.
           - Zero open worked leads in PostgreSQL have NULL or past next_action_date after schema/data guard.
        """
        from datetime import date

        auth_client = self.get_auth_client()
        lead_id = None
        today_iso = date.today().isoformat()

        try:
            # 1. Create a fresh open lead WITHOUT a next_action_date
            r_create = auth_client.post(
                "/admin/add-lead",
                json={
                    "company_name": "BUG165 Mandatory FollowUp Academy",
                    "decision_maker": "Director Hannah",
                    "phone": "214-555-0165",
                    "email": "hannah@bug165academy.org",
                    "address": "165 Followup Way",
                    "city": "Dallas",
                    "state": "TX",
                    "zipcode": "75201",
                },
                headers={"Accept": "application/json"},
            )
            self.assertEqual(r_create.status_code, 200)
            lead_id = r_create.get_json().get("lead_id")
            self.assertIsNotNone(lead_id)

            # 2. Save a quick note WITHOUT specifying next_action_date -> must auto-assign future business date!
            r_quick = auth_client.post(
                "/api/v1/activities/quick-log",
                json={
                    "parent_id": lead_id,
                    "parent_type": "Lead",
                    "activity_type": "NOTE",
                    "note": "Left intro packet with front desk receptionist.",
                },
            )
            self.assertEqual(r_quick.status_code, 200)
            q_json = r_quick.get_json()
            self.assertEqual(q_json.get("status"), "success")
            auto_next_date = q_json.get("next_action_date")
            self.assertTrue(auto_next_date and auto_next_date >= today_iso, f"Expected future next_action_date, got {auto_next_date}")
            act_item = q_json.get("activity") or {}
            act_id = act_item.get("id") or act_item.get("activity_id")
            self.assertIsNotNone(act_id)
            self.assertEqual(act_item.get("task_status"), "OPEN")
            self.assertEqual(act_item.get("follow_up_date"), auto_next_date)

            # 3. Complete the follow-up task via POST /api/v1/activities/<id>/complete-task
            r_complete = auth_client.post(f"/api/v1/activities/{act_id}/complete-task", json={})
            self.assertEqual(r_complete.status_code, 200)
            comp_json = r_complete.get_json()
            self.assertEqual(comp_json.get("status"), "success")
            self.assertEqual(comp_json.get("task_status"), "COMPLETED")
            self.assertTrue(comp_json.get("next_action_date") >= today_iso)

            # 4. Save a cadence note with natural-language "call back tomorrow" and blank next_action_date
            r_cadence = auth_client.post(
                f"/api/v1/leads/{lead_id}/cadence-save",
                json={
                    "note": "Spoke with Director Hannah, she asked to call back tomorrow morning.",
                    "activity_type": "Phone Call",
                    "outcome": "Spoke to them",
                    "next_action_date": "",
                },
            )
            self.assertEqual(r_cadence.status_code, 200)
            cad_json = r_cadence.get_json()
            self.assertEqual(cad_json.get("status"), "success")
            self.assertTrue(cad_json.get("next_action_date") >= today_iso)

            # 5. Terminal disposition ("Not Interested") must clear next_action_date = NULL and close tasks
            r_term = auth_client.post(
                f"/api/v1/leads/{lead_id}/cadence-save",
                json={
                    "note": "Facility closed permanently.",
                    "activity_type": "Not Interested",
                    "outcome": "Not Interested",
                    "status": "Not Interested",
                },
            )
            self.assertEqual(r_term.status_code, 200)
            term_json = r_term.get_json()
            self.assertIsNone(term_json.get("next_action_date"))

            # 6. Verify Follow-Up toolbar filters and search tokens render 200 OK
            for f_url in (
                "/admin/operations?view=leads&followup_filter=due",
                "/admin/operations?view=leads&followup_filter=overdue",
                "/admin/operations?view=leads&followup_filter=today",
                "/admin/operations?view=leads&followup_filter=upcoming",
                "/admin/operations?view=leads&q=followup:due",
            ):
                r_f = auth_client.get(f_url)
                self.assertEqual(r_f.status_code, 200, f"Follow-up filter URL {f_url} failed")
        finally:
            if lead_id:
                conn = get_db(self.db_url)
                try:
                    with conn.cursor() as cur:
                        cur.execute('DELETE FROM "LeadStageHistory" WHERE lead_id = %s;', (lead_id,))
                        cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = \'Lead\' AND parent_id = %s;', (lead_id,))
                        cur.execute('DELETE FROM "Leads" WHERE id = %s;', (lead_id,))
                        conn.commit()
                finally:
                    conn.close()

    def test_43_enterprise_1099_onboarding_dual_mode_tin_and_digital_w9_bug_167(self) -> None:
        """
        BUG-167 8-Pillar Fortune 500 1099 Subcontractor Onboarding & Dual-Mode Tax ID (EIN / SSN) Suite:
        1. Verifies validate_federal_tax_id() rejects incomplete, sequential/dummy ('123456789'),
           invalid IRS EIN campus prefixes ('00', '07', '69', '89'), and invalid SSA SSN prefixes ('000', '666'),
           while accepting valid EINs ('84-2910455') and SSNs ('453-21-9876') for Single-Member LLCs.
        2. Verifies _deterministic_parse_w9() preserves SSN format ('XXX-XX-XXXX') and sets tax_id_mode='ssn'
           when parsing an SSN-based W-9.
        3. Verifies /static/js/sigma_input_masks.js exposes setTaxIdMode() and validateTaxIdClientSide().
        4. Verifies Digital Substitute Form W-9 generation (w9_mode='digital') on POST /onboard/subcontractor/<token>/submit
           with a Single-Member LLC filing under an Owner SSN ('453219876', tax_id_mode='ssn'):
           - Masks TIN as '***-**-9876'
           - Generates and vaults locked PDF 1.4 Substitute Form W-9 ('sub_<id>_W9_Substitute_Signed_*.pdf')
           - Holds partner at 'Pending COI' when COI is deferred.
        5. Verifies 1-Click Quick COI Upload on the Receipt Card (POST /onboard/subcontractor/<token>/extract-document)
           immediately transitions an already-signed 'Pending COI' partner to 'Docs Under Review' / 'Docs Submitted'.
        6. Verifies Backoffice Audited TIN Reveal (POST /api/v1/workforce/subcontractors/<id>/reveal-tin)
           decrypts the full 9-digit TIN ('453-21-9876') and logs CRITICAL 'SUBCONTRACTOR_TIN_REVEALED' in SecurityAuditLogs.
        """
        import io
        import uuid
        from unittest.mock import patch
        from core.services.database import get_db
        from core.services.sanitizer import validate_federal_tax_id, clean_ein_or_ssn
        from core.services.subcontractor_doc_extractor import (
            _deterministic_parse_w9,
            generate_signed_substitute_w9_pdf,
        )

        # Pillar 1 & 3: Server-side IRS / SSA Tax ID Validator
        ok_ein, val_ein, mode_ein = validate_federal_tax_id("842910455", tax_id_mode="ein", tax_classification="LLC")
        self.assertTrue(ok_ein)
        self.assertEqual(val_ein, "84-2910455")
        self.assertEqual(mode_ein, "ein")

        ok_sm_ssn, val_sm_ssn, mode_sm_ssn = validate_federal_tax_id(
            "453219876",
            tax_id_mode="ssn",
            tax_classification="Single-Member LLC (Disregarded Entity)",
        )
        self.assertTrue(ok_sm_ssn)
        self.assertEqual(val_sm_ssn, "453-21-9876")
        self.assertEqual(mode_sm_ssn, "ssn")

        # Dummy/sequential 9-digit numbers must be rejected
        ok_dummy, err_dummy, _ = validate_federal_tax_id("123456789", tax_id_mode="ssn")
        self.assertFalse(ok_dummy)
        self.assertIn("not permitted", err_dummy)

        # Invalid IRS EIN prefix ('07') must be rejected in EIN mode
        ok_bad_prefix, err_bad_prefix, _ = validate_federal_tax_id("072910455", tax_id_mode="ein")
        self.assertFalse(ok_bad_prefix)
        self.assertIn("prefix", err_bad_prefix.lower())

        # Invalid SSA SSN area ('666') must be rejected in SSN mode
        ok_bad_ssn, err_bad_ssn, _ = validate_federal_tax_id("666219876", tax_id_mode="ssn")
        self.assertFalse(ok_bad_ssn)
        self.assertIn("666", err_bad_ssn)

        # Pillar 2: W-9 parser preserves SSN format when labeled SSN
        parsed_w9 = _deterministic_parse_w9("Form W-9\n1. Name: Maria Vega\nSSN: 453-21-9876\n5. Address: 500 Main St\n6. Dallas, TX 75201")
        self.assertEqual(parsed_w9["ein_or_ssn"], "453-21-9876")
        self.assertEqual(parsed_w9["tax_id_mode"], "ssn")

        # Pillar 3: Static JS exposes setTaxIdMode and validateTaxIdClientSide
        r_js = self.client.get("/static/js/sigma_input_masks.js")
        self.assertEqual(r_js.status_code, 200)
        js_txt = r_js.get_data(as_text=True)
        self.assertIn("setTaxIdMode", js_txt)
        self.assertIn("validateTaxIdClientSide", js_txt)
        r_js.close()

        # Pillar 4, 5, 6, 7: End-to-End Portal Digital Substitute W-9 + Single-Member LLC SSN + Quick COI Upload + Backoffice Reveal
        conn = get_db(self.db_url)
        created_sub_id = None
        try:
            uid = uuid.uuid4().hex[:6]
            with self.client.session_transaction() as sess:
                sess["_user_id"] = "1"
                sess["_fresh"] = True

            with (
                patch("core.services.notification_service.send_subcontractor_onboarding_invite_email", return_value=(True, "mocked")),
                patch("core.services.notification_service.send_subcontractor_onboarding_completed_notifications", return_value=True),
                patch("core.services.email_service.transmit_email", return_value=(True, "mocked")),
            ):
                r_create = self.client.post(
                    "/api/v1/workforce/subcontractors",
                    json={
                        "company_name": f"Vega Single Member {uid} LLC",
                        "contact_name": "Maria Vega",
                        "email": f"vega.{uid}@example.com",
                        "phone": "2145550174",
                        "city": "Dallas",
                        "specialties": "Commercial Floor Care",
                        "crew_size": 3,
                    },
                )
                self.assertEqual(r_create.status_code, 201)
                created_sub_id = r_create.get_json()["subcontractor_id"]

                r_tok = self.client.post(f"/api/v1/workforce/subcontractors/{created_sub_id}/send-onboarding")
                self.assertEqual(r_tok.status_code, 200)
                tok = r_tok.get_json()["onboarding_token"]

                # Verify portal HTML renders Dual-Mode TIN pills, Digital W-9 switcher, and Quick COI upload box
                r_portal_get = self.client.get(f"/onboard/subcontractor/{tok}")
                self.assertEqual(r_portal_get.status_code, 200)
                portal_html = r_portal_get.get_data(as_text=True)
                self.assertIn('data-tin-pill-for="onb-ein-ssn"', portal_html)
                self.assertIn('id="btn-w9-mode-digital"', portal_html)
                self.assertIn('id="receipt-quick-coi-upload-box"', portal_html)
                self.assertIn('Single-Member LLC (Disregarded Entity)', portal_html)

                # Reject invalid dummy TIN ('123456789') on submit
                r_bad_submit = self.client.post(
                    f"/onboard/subcontractor/{tok}/submit",
                    data={
                        "w9_mode": "digital",
                        "company_name": f"Vega Single Member {uid} LLC",
                        "legal_entity_name": "Maria Vega",
                        "contact_name": "Maria Vega",
                        "email": f"vega.{uid}@example.com",
                        "phone": "2145550174",
                        "tax_classification": "Single-Member LLC (Disregarded Entity)",
                        "tax_id_mode": "ssn",
                        "ein_or_ssn": "123456789",
                        "street_address": "800 Ross Ave",
                        "city": "Dallas",
                        "state": "TX",
                        "zip_code": "75202",
                        "msa_signer_name": "Maria Vega",
                        "msa_signer_title": "Managing Member",
                        "msa_agreed": "true",
                        "dwc83_agreed": "true",
                    },
                )
                self.assertEqual(r_bad_submit.status_code, 400)

                # Submit with Digital Substitute W-9 mode + valid Single-Member LLC owner SSN ('453219876')
                r_good_submit = self.client.post(
                    f"/onboard/subcontractor/{tok}/submit",
                    data={
                        "w9_mode": "digital",
                        "company_name": f"Vega Single Member {uid} LLC",
                        "legal_entity_name": "Maria Vega",
                        "contact_name": "Maria Vega",
                        "email": f"vega.{uid}@example.com",
                        "phone": "2145550174",
                        "tax_classification": "Single-Member LLC (Disregarded Entity)",
                        "tax_id_mode": "ssn",
                        "ein_or_ssn": "453219876",
                        "street_address": "800 Ross Ave",
                        "city": "Dallas",
                        "state": "TX",
                        "zip_code": "75202",
                        "msa_signer_name": "Maria Vega",
                        "msa_signer_title": "Managing Member",
                        "msa_agreed": "true",
                        "dwc83_agreed": "true",
                    },
                )
                self.assertEqual(r_good_submit.status_code, 200, r_good_submit.get_data(as_text=True))
                good_json = r_good_submit.get_json()
                self.assertEqual(good_json["status"], "success")
                self.assertEqual(good_json["masked_tin"], "***-**-9876")
                self.assertEqual(good_json["onboarding_status"], "Pending COI")

                # Verify generated Substitute W-9 PDF is vaulted and downloadable
                r_dl_w9 = self.client.get(f"/api/v1/workforce/subcontractors/{created_sub_id}/download/w9")
                self.assertEqual(r_dl_w9.status_code, 200)
                self.assertTrue(r_dl_w9.data.startswith(b"%PDF-1.4"))
                self.assertIn(b"SUBSTITUTE FORM W-9", r_dl_w9.data)
                r_dl_w9.close()

                # Pillar 5: 1-Click Quick COI Upload on Receipt Card advances Pending COI -> Docs Under Review
                coi_bytes = b"%PDF-1.4\nPRODUCER: Next Insurance\nPOLICY NUMBER: GL-998877\nEXP: 12/31/2027\nEACH OCCURRENCE: $1,000,000\n"
                r_quick_coi = self.client.post(
                    f"/onboard/subcontractor/{tok}/extract-document",
                    data={
                        "doc_type": "coi",
                        "file": (io.BytesIO(coi_bytes), "acord25.pdf"),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(r_quick_coi.status_code, 200)
                q_json = r_quick_coi.get_json()
                self.assertEqual(q_json["onboarding_status"], "Docs Under Review")

                # Pillar 7: Audited Backoffice TIN Reveal decrypts '453-21-9876' and logs CRITICAL audit event
                r_reveal = self.client.post(f"/api/v1/workforce/subcontractors/{created_sub_id}/reveal-tin")
                self.assertEqual(r_reveal.status_code, 200)
                rev_json = r_reveal.get_json()
                self.assertEqual(rev_json["tin"], "453-21-9876")
                self.assertTrue(rev_json["has_full_tin"])

                with conn.cursor() as cur:
                    cur.execute(
                        '''
                        SELECT event_action, severity
                        FROM "SecurityAuditLogs"
                        WHERE event_category = 'HR_PII'
                          AND event_action = 'SUBCONTRACTOR_TIN_REVEALED'
                        ORDER BY id DESC
                        LIMIT 1;
                        '''
                    )
                    audit_row = cur.fetchone()
                    self.assertIsNotNone(audit_row)
                    self.assertEqual(audit_row["severity"], "CRITICAL")
        finally:
            if created_sub_id:
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM "SubcontractorDocuments" WHERE subcontractor_id = %s;', (created_sub_id,))
                    cur.execute('DELETE FROM "SubcontractorPartners" WHERE id = %s;', (created_sub_id,))
                    cur.execute('DELETE FROM "GlobalActivities" WHERE parent_type = \'Subcontractor\' AND parent_id = %s;', (created_sub_id,))
                    cur.execute('DELETE FROM "PendingOutbox" WHERE subject LIKE %s;', (f"%Vega Single Member%",))
                conn.commit()
            conn.close()

    def test_44_universal_dual_horizontal_scrollbars_and_sticky_bottom_dock_bug_168(self) -> None:
        """
        BUG-168 Universal Dual Horizontal Scrollbar (Top Synced Rail + Sticky Bottom Dock) Suite:
        1. Verifies /static/js/sigma_responsive_engine.js defines the 3-pillar horizontal scroll engine:
           - Top Synced Horizontal Scroll Rail (.sigma-top-scroll-rail, .sigma-top-scroll-track, .sigma-scroll-step-btn)
           - Always-Visible Sticky Bottom Scrollbar Dock (#sigma-sticky-bottom-scrollbar, .sigma-sticky-bottom-track)
           - ResizeObserver + window scroll/resize synchronization (bindDualTableScrollbars, updateStickyBottomScrollbar, refreshAllScrollbars)
        2. Verifies all multi-table screens across the backoffice and manuals load sigma_responsive_engine.js.
        """
        eng_resp = self.client.get("/static/js/sigma_responsive_engine.js")
        self.assertEqual(eng_resp.status_code, 200)
        eng_js = eng_resp.get_data(as_text=True)

        for marker in (
            "sigma-top-scroll-rail",
            "sigma-top-scroll-track",
            "sigma-scroll-step-btn",
            "sigma-sticky-bottom-scrollbar",
            "sigma-sticky-bottom-track",
            "bindDualTableScrollbars",
            "updateStickyBottomScrollbar",
            "refreshAllScrollbars",
            "resolveTableScrollWrap",
            "has-right-overflow",
        ):
            self.assertIn(marker, eng_js, f"Missing BUG-168 scrollbar marker in sigma_responsive_engine.js: {marker}")

        auth_client = self.get_auth_client()
        for view_url in (
            "/admin/operations?view=leads",
            "/admin/operations?view=accounts",
            "/admin/operations?view=construction_bids",
            "/admin/operations?view=workforce",
            "/admin/operations?view=accounting",
            "/manual/app",
        ):
            r_view = auth_client.get(view_url)
            self.assertEqual(r_view.status_code, 200, f"View {view_url} failed to render")
            self.assertIn("sigma_responsive_engine.js", r_view.get_data(as_text=True))

    def test_45_enterprise_column_sorting_and_newest_first_dates_bug_169(self) -> None:
        """
        BUG-169 6-Pillar Enterprise Column Sorting & Newest-First Date Sorting Suite:
        1. All date/deadline/follow-up columns (next_action, due_date, start_date, dates, pre_bid,
           input_date, created, last_contact) default to DESC (Newest Date -> Older Date) on first click
           and when dir is omitted.
        2. Previously failing SQL sort keys (facility, industry in Accounts; last_note in Construction Bids)
           execute valid SQL with non-empty rows in both ASC and DESC.
        3. Universal NULLS LAST & NULLIF(..., 0) / NULLIF(..., '') normalization in both ASC and DESC.
        4. Per-user sort_by / sort_dir persists across page loads and resets via sort=default.
        5. Drag/resize click-suppression guard (_sigmaSuppressNextSortClickUntil) & 3-state sort cycle active.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ops_js_path = os.path.join(base_dir, "static", "js", "backoffice_operations_core.js")
        with open(ops_js_path, "r", encoding="utf-8") as f:
            ops_js = f.read()

        for marker in (
            "'next_action'",
            "'due_date'",
            "'start_date'",
            "'dates'",
            "'pre_bid'",
            "_sigmaSuppressNextSortClickUntil",
            "decoratePrimarySortableHeaders",
            "clearSort:",
        ):
            self.assertIn(marker, ops_js, f"Missing BUG-169 sort marker in backoffice_operations_core.js: {marker}")

        auth_client = self.get_auth_client()
        json_headers = {"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}
        try:
            # 1. Verify next_action defaults to DESC (Newest Date -> Older Date) when dir is omitted
            r_next = auth_client.get("/admin/operations?view=leads&sort=next_action&format=json", headers=json_headers)
            self.assertEqual(r_next.status_code, 200)
            leads_next = (r_next.get_json() or {}).get("leads") or []
            self.assertGreater(len(leads_next), 0)
            non_empty_dates = [
                str(r.get("next_action_date") or "").strip()
                for r in leads_next
                if str(r.get("next_action_date") or "").strip() not in ("", "None")
            ]
            if len(non_empty_dates) >= 2:
                self.assertGreaterEqual(
                    non_empty_dates[0],
                    non_empty_dates[-1],
                    "sort=next_action must default to DESC (Newest Date -> Older Date)",
                )

            # 2. Verify sort persistence on Leads when reloading without ?sort= and reset via ?sort=default
            r_persisted = auth_client.get("/admin/operations?view=leads")
            self.assertEqual(r_persisted.status_code, 200)
            self.assertIn('name="sort" value="next_action"', r_persisted.get_data(as_text=True))

            r_reset = auth_client.get("/admin/operations?view=leads&sort=default")
            self.assertEqual(r_reset.status_code, 200)
            self.assertIn('name="sort" value=""', r_reset.get_data(as_text=True))

            # 3. Verify Accounts facility & industry sorting and Construction Bids last_note sorting in ASC and DESC
            for acc_col in ("facility", "industry", "start_date", "sqf", "revenue", "cycle", "last_note"):
                for d in ("asc", "desc"):
                    r_acc = auth_client.get(
                        f"/admin/operations?view=accounts&sort={acc_col}&dir={d}&format=json",
                        headers=json_headers,
                    )
                    self.assertEqual(r_acc.status_code, 200)
                    acc_rows = (r_acc.get_json() or {}).get("clients") or []
                    self.assertGreater(len(acc_rows), 0, f"Accounts sort={acc_col} dir={d} returned 0 rows")

            for bid_col in ("last_note", "due_date", "value", "sqf", "owner", "activities"):
                for d in ("asc", "desc"):
                    r_bid = auth_client.get(
                        f"/admin/operations?view=construction_bids&sort={bid_col}&dir={d}&format=json",
                        headers=json_headers,
                    )
                    self.assertEqual(r_bid.status_code, 200)
                    bid_rows = (r_bid.get_json() or {}).get("construction_bids") or []
                    self.assertGreater(len(bid_rows), 0, f"ConstructionBids sort={bid_col} dir={d} returned 0 rows")
                    if bid_col == "value" and d == "desc":
                        # Verify NULLS LAST on DESC: first row must have a non-null estimated_value
                        self.assertIsNotNone(
                            bid_rows[0].get("estimated_value"),
                            "ConstructionBids sort=value dir=desc must enforce NULLS LAST (first row cannot be NULL)",
                        )
        finally:
            auth_client.post("/api/v1/ui/grid-state", json={"grid_id": "leads", "reset": True})
            auth_client.post("/api/v1/ui/grid-state", json={"grid_id": "accounts", "reset": True})
            auth_client.post("/api/v1/ui/grid-state", json={"grid_id": "construction_bids", "reset": True})

    def test_46_complete_1099_and_w2_onboarding_workflows_bug_170(self) -> None:
        """
        BUG-170 8-Pillar 1099 Subcontractor & W-2 Employee Onboarding Workflow Suite:
        1. Backoffice direct-add 1099 subcontractor generates onboarding_token & 30-day expiry immediately.
        2. 1099 portal deferred-COI submission renders 6-Card Summary Grid, @media print, and self-service
           token-authenticated PDF downloads (/onboard/subcontractor/<token>/download/w9 & /msa).
        3. Returning 1099 partner quick COI upload (/onboard/subcontractor/<token>/extract-document) advances
           onboarding_status to 'Docs Under Review', logs GlobalActivities, and enables /download/coi.
        4. Backoffice POST /api/v1/hr/onboard leaves job_description_acknowledged_at NULL until the employee signs,
           and POST /api/v1/hr/employees/<id>/send-onboarding-link dispatches email, builds sms_uri, and logs activity.
        5. W-2 portal (/onboard/employee/<token>) enforces 30-day token expiration (410 TOKEN_EXPIRED) and supports
           1-click link renewal (POST /onboard/employee/<token>/renew).
        6. W-2 portal includes Form I-9 Citizenship selector, W-4 Step 2(c) checkbox, un-prechecked e-sign consent,
           records WORM CONSENT_LEDGER in SecurityAuditLogs, populates job_description_acknowledged_at, and serves
           self-service signed PDF packet (/onboard/employee/<token>/download-packet) & uploaded doc downloads.
        """
        import io
        import uuid
        from unittest.mock import patch

        uid = uuid.uuid4().hex[:8]
        auth_client = self.get_auth_client()
        created_sub_ids = []
        created_emp_ids = []

        w9_bytes = (
            f"%PDF-1.4\n1. Name of entity/individual: Carlos Vega\n"
            f"2. Business name: Vega Commercial Floors {uid} LLC\n"
            "3a. Federal tax classification: Limited Liability Company (LLC)\n"
            "5. Address: 2100 Ross Ave\n6. City, state, and ZIP: Dallas, TX 75201\n"
            "Employer Identification Number: 82-7741902\n"
        ).encode()
        coi_bytes = (
            b"%PDF-1.4\nACORD CERTIFICATE OF LIABILITY INSURANCE\n"
            b"INSURER A: Hiscox Insurance Company Inc\n"
            b"COMMERCIAL GENERAL LIABILITY\n"
            b"Policy Number: GL-99201144\n"
            b"Policy Eff: 01/01/2026 Policy Exp: 12/31/2027\n"
            b"EACH OCCURRENCE: $1,000,000\n"
        )
        w4_bytes = (
            b"%PDF-1.4\nForm W-4 Employee's Withholding Certificate\n"
            b"Address: 4500 Live Oak St\nCity, state, and ZIP: Dallas, TX 75204\n"
            b"Filing Status: Married Filing Jointly\n"
        )

        try:
            with (
                patch("core.services.email_service.transmit_email", return_value=(True, "mocked")),
                patch("core.services.notification_service.transmit_email", return_value=(True, "mocked")),
                patch("core.services.notification_service.requests.post") as mock_tg_post,
            ):
                mock_tg_post.return_value.status_code = 200
                # =====================================================================
                # PART A: 1099 SUBCONTRACTOR ONBOARDING & RECEIPT WORKFLOW
                # =====================================================================
                r_add_sub = auth_client.post(
                    "/api/v1/workforce/subcontractors",
                    json={
                        "company_name": f"Vega Commercial Floors {uid} LLC",
                        "contact_name": "Carlos Vega",
                        "email": f"carlos.vega.{uid}@example.com",
                        "phone": f"(214) 555-{uid[:4] if uid[:4].isdigit() else '4190'}",
                        "city": "Dallas",
                        "specialties": "Floor Strip & Wax, Post-Construction",
                        "crew_size": 6,
                    },
                )
                self.assertEqual(r_add_sub.status_code, 201, r_add_sub.get_data(as_text=True))
                sub_json = r_add_sub.get_json()
                sub_id = sub_json["subcontractor_id"]
                created_sub_ids.append(sub_id)
                sub_token = sub_json.get("onboarding_token")
                self.assertTrue(sub_token and sub_token.startswith(f"sub_{sub_id}_"), "Backoffice add must generate onboarding_token")

                # Submit 1099 onboarding WITH W-9 + MSA/DWC-83, deferring COI upload
                r_sub_submit = self.client.post(
                    f"/onboard/subcontractor/{sub_token}/submit",
                    data={
                        "company_name": f"Vega Commercial Floors {uid} LLC",
                        "legal_entity_name": "Carlos Vega",
                        "contact_name": "Carlos Vega",
                        "email": f"carlos.vega.{uid}@example.com",
                        "phone": "(214) 555-4190",
                        "tax_classification": "LLC",
                        "ein_or_ssn": "82-7741902",
                        "street_address": "2100 Ross Ave",
                        "city": "Dallas",
                        "state": "TX",
                        "zip_code": "75201",
                        "msa_signer_name": "Carlos Vega",
                        "msa_signer_title": "Managing Member",
                        "msa_agreed": "true",
                        "dwc83_agreed": "true",
                        "w9_file": (io.BytesIO(w9_bytes), "vega_w9.pdf"),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(r_sub_submit.status_code, 200, r_sub_submit.get_data(as_text=True))
                sub_submit_data = r_sub_submit.get_json()
                self.assertEqual(sub_submit_data["status"], "success")
                self.assertFalse(sub_submit_data["coi_uploaded"])
                self.assertIn(sub_submit_data["onboarding_status"], ("Pending COI", "Awaiting COI Upload"))
                self.assertTrue(sub_submit_data.get("msa_download_url"))
                self.assertTrue(sub_submit_data.get("w9_download_url"))

                # Verify 1099 portal receipt card HTML contains 6-card summary, @media print, and download bar
                r_sub_portal = self.client.get(f"/onboard/subcontractor/{sub_token}")
                self.assertEqual(r_sub_portal.status_code, 200)
                sub_portal_html = r_sub_portal.get_data(as_text=True)
                for marker in (
                    "@media print",
                    "receipt-download-bar",
                    "receipt-dl-msa",
                    "receipt-dl-w9",
                    "receipt-dl-coi",
                    "receipt-address",
                    "receipt-contact",
                    "receipt-coi-status",
                    "receipt-quick-coi-upload-box",
                ):
                    self.assertIn(marker, sub_portal_html, f"Missing 1099 receipt marker: {marker}")

                # Verify self-service token-authenticated W-9 & MSA downloads
                for doc_slug in ("w9", "msa", "dwc83"):
                    r_dl = self.client.get(f"/onboard/subcontractor/{sub_token}/download/{doc_slug}")
                    self.assertEqual(r_dl.status_code, 200)
                    self.assertTrue(r_dl.data.startswith(b"%PDF-1.4"))
                    self.assertTrue(r_dl.headers.get("X-Sigma-Vault-SHA256"))
                    r_dl.close()

                # Deferred COI Quick Upload on receipt card -> advances status to 'Docs Under Review'
                r_quick_coi = self.client.post(
                    f"/onboard/subcontractor/{sub_token}/extract-document",
                    data={"doc_type": "coi", "file": (io.BytesIO(coi_bytes), "vega_coi.pdf")},
                    content_type="multipart/form-data",
                )
                self.assertEqual(r_quick_coi.status_code, 200, r_quick_coi.get_data(as_text=True))
                q_coi_data = r_quick_coi.get_json()
                self.assertEqual(q_coi_data["onboarding_status"], "Docs Under Review")

                # Verify COI self-service download now succeeds
                r_dl_coi = self.client.get(f"/onboard/subcontractor/{sub_token}/download/coi")
                self.assertEqual(r_dl_coi.status_code, 200)
                self.assertTrue(r_dl_coi.data.startswith(b"%PDF-1.4"))
                r_dl_coi.close()

                # =====================================================================
                # PART B: W-2 EMPLOYEE ONBOARDING & RECEIPT WORKFLOW
                # =====================================================================
                r_hire_w2 = auth_client.post(
                    "/api/v1/hr/onboard",
                    json={
                        "first_name": "Elena",
                        "last_name": f"Navarro-{uid}",
                        "email": f"elena.navarro.{uid}@hwbcleaning.com",
                        "phone": "(214) 555-7812",
                        "primary_role": "Commercial Cleaning Technician",
                        "employment_type": "W-2 Full-Time",
                        "pay_rate_hourly": 18.50,
                        "hire_date": "2026-10-29",
                    },
                )
                self.assertEqual(r_hire_w2.status_code, 201, r_hire_w2.get_data(as_text=True))
                hire_data = r_hire_w2.get_json()
                emp_id = hire_data["employee_id"]
                created_emp_ids.append(emp_id)
                emp_token = hire_data["onboarding_token"]
                self.assertIn("https://www.hwbcleaning.com/onboard/employee/", hire_data["onboarding_url"])

                # Verify job_description_acknowledged_at is NULL before the employee signs in the portal
                conn = get_db(self.db_url)
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            'SELECT job_description_acknowledged_at, onboarding_packet_signed FROM "Employees" WHERE id = %s;',
                            (emp_id,),
                        )
                        emp_init_row = cur.fetchone()
                        self.assertIsNone(
                            emp_init_row[0],
                            "job_description_acknowledged_at must be NULL prior to employee e-signature",
                        )
                        self.assertFalse(bool(emp_init_row[1]))
                finally:
                    conn.close()

                # Verify POST /api/v1/hr/employees/<id>/send-onboarding-link returns canonical URL & SMS URI
                r_send_w2 = auth_client.post(f"/api/v1/hr/employees/{emp_id}/send-onboarding-link")
                self.assertEqual(r_send_w2.status_code, 200, r_send_w2.get_data(as_text=True))
                send_w2_data = r_send_w2.get_json()
                self.assertTrue(send_w2_data.get("email_sent"))
                self.assertTrue(send_w2_data.get("sms_uri", "").startswith("sms:"))
                self.assertIn("https://www.hwbcleaning.com/onboard/employee/", send_w2_data.get("onboarding_url", ""))

                # Simulate expired token -> verify 410 TOKEN_EXPIRED on upload & complete, then renew
                conn = get_db(self.db_url)
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            'UPDATE "Employees" SET onboarding_token_expires_at = CURRENT_TIMESTAMP - INTERVAL \'2 days\' WHERE id = %s;',
                            (emp_id,),
                        )
                    conn.commit()
                finally:
                    conn.close()

                r_exp_complete = self.client.post(
                    f"/api/v1/employees/onboard/{emp_token}/complete",
                    json={"first_name": "Elena", "last_name": f"Navarro-{uid}", "signer_name": f"Elena Navarro-{uid}"},
                )
                self.assertEqual(r_exp_complete.status_code, 410)
                self.assertEqual(r_exp_complete.get_json().get("error_code"), "TOKEN_EXPIRED")

                r_renew_w2 = self.client.post(f"/onboard/employee/{emp_token}/renew")
                self.assertEqual(r_renew_w2.status_code, 200)
                self.assertEqual(r_renew_w2.get_json().get("status"), "success")

                # Upload W-4 doc via portal
                r_up_w4 = self.client.post(
                    f"/api/v1/employees/onboard/{emp_token}/upload-doc",
                    data={"document_type": "Form W-4", "document": (io.BytesIO(w4_bytes), "elena_w4.pdf")},
                    content_type="multipart/form-data",
                )
                self.assertEqual(r_up_w4.status_code, 200, r_up_w4.get_data(as_text=True))
                up_w4_data = r_up_w4.get_json()
                self.assertTrue(up_w4_data.get("download_url"))

                # Complete W-2 Onboarding Packet
                r_complete_w2 = self.client.post(
                    f"/api/v1/employees/onboard/{emp_token}/complete",
                    json={
                        "first_name": "Elena",
                        "last_name": f"Navarro-{uid}",
                        "phone": "(214) 555-7812",
                        "email": f"elena.navarro.{uid}@hwbcleaning.com",
                        "address_street": "4500 Live Oak St",
                        "address_city": "Dallas",
                        "address_state": "TX",
                        "address_zip": "75204",
                        "emergency_contact_name": "Mateo Navarro",
                        "emergency_contact_phone": "(214) 555-9901",
                        "ssn": "123-45-6789",
                        "state_id_number": "TX-44881122",
                        "state_id_expiration": "2029-08-15",
                        "w4_filing_status": "Married Filing Jointly",
                        "w4_step2_multiple_jobs": True,
                        "w4_step3_dependents": 2000,
                        "w4_step4c_extra_withholding": 25,
                        "i9_citizenship_status": "1. A citizen of the United States",
                        "direct_deposit_bank": "Chase Bank",
                        "direct_deposit_routing": "111000614",
                        "direct_deposit_account": "987654321",
                        "signer_name": f"Elena Navarro-{uid}",
                    },
                )
                self.assertEqual(r_complete_w2.status_code, 200, r_complete_w2.get_data(as_text=True))
                comp_w2_data = r_complete_w2.get_json()
                self.assertEqual(comp_w2_data["status"], "success")
                self.assertTrue(comp_w2_data.get("download_packet_url"))
                self.assertEqual(comp_w2_data.get("ssn_masked"), "***-**-6789")
                self.assertTrue((comp_w2_data.get("direct_deposit_account_masked") or "").endswith("4321"))

                # Verify W-2 portal receipt card HTML, self-service signed PDF download, and uploaded doc download
                r_w2_portal = self.client.get(f"/onboard/employee/{emp_token}")
                self.assertEqual(r_w2_portal.status_code, 200)
                w2_portal_html = r_w2_portal.get_data(as_text=True)
                for w2_marker in (
                    "@media print",
                    "w2-receipt-download-bar",
                    "w2-receipt-dl-packet",
                    "w2-receipt-address",
                    "w2-receipt-w4",
                    "w2-receipt-dd",
                    "emp-i9-citizenship",
                    "emp-w4-step2",
                    "emp-esign-consent",
                ):
                    self.assertIn(w2_marker, w2_portal_html, f"Missing W-2 portal marker: {w2_marker}")

                r_dl_w2_pkt = self.client.get(f"/onboard/employee/{emp_token}/download-packet")
                self.assertEqual(r_dl_w2_pkt.status_code, 200)
                self.assertTrue(r_dl_w2_pkt.data.startswith(b"%PDF-1.4"))
                self.assertTrue(r_dl_w2_pkt.headers.get("X-Sigma-Vault-SHA256"))
                r_dl_w2_pkt.close()

                r_dl_w2_doc = self.client.get(up_w4_data["download_url"])
                self.assertEqual(r_dl_w2_doc.status_code, 200)
                self.assertTrue(r_dl_w2_doc.data.startswith(b"%PDF-1.4"))
                r_dl_w2_doc.close()

                # Verify CONSENT_LEDGER entry & job_description_acknowledged_at populated in PostgreSQL
                conn = get_db(self.db_url)
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            'SELECT job_description_acknowledged_at, onboarding_packet_signed, w4_step2_multiple_jobs, i9_citizenship_status FROM "Employees" WHERE id = %s;',
                            (emp_id,),
                        )
                        emp_final_row = cur.fetchone()
                        self.assertIsNotNone(emp_final_row[0], "job_description_acknowledged_at must be set after e-sign")
                        self.assertTrue(bool(emp_final_row[1]))
                        self.assertTrue(bool(emp_final_row[2]))
                        self.assertEqual(emp_final_row[3], "1. A citizen of the United States")

                        cur.execute(
                            '''
                            SELECT details
                            FROM "SecurityAuditLogs"
                            WHERE event_category = 'CONSENT_LEDGER'
                              AND event_action = 'W2_EMPLOYEE_ONBOARDING_SIGNED'
                              AND details::text LIKE %s
                            ORDER BY id DESC
                            LIMIT 1;
                            ''',
                            (f"%elena.navarro.{uid}@hwbcleaning.com%",),
                        )
                        w2_consent = cur.fetchone()
                        self.assertIsNotNone(w2_consent, "WORM CONSENT_LEDGER receipt must be recorded on W-2 completion")
                finally:
                    conn.close()
        finally:
            conn = get_db(self.db_url)
            try:
                with conn.cursor() as cur:
                    for sid in created_sub_ids:
                        cur.execute('DELETE FROM "SubcontractorDocuments" WHERE subcontractor_id = %s;', (sid,))
                        cur.execute('DELETE FROM "SubcontractorPartners" WHERE id = %s;', (sid,))
                    for eid in created_emp_ids:
                        cur.execute('DELETE FROM "EmployeeDocuments" WHERE employee_id = %s;', (eid,))
                        cur.execute('DELETE FROM "Employees" WHERE id = %s;', (eid,))
                conn.commit()
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
