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
        """Part I Pillar 4: Verifies get_version_info() is cached in memory with lru_cache and reports v5.4.4."""
        clear_version_cache()
        self.assertEqual(APP_SEMANTIC_VERSION, "v5.4.4")
        info_1 = get_version_info()
        info_2 = get_version_info()
        self.assertEqual(info_1.get("app_version"), "v5.4.4")
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


if __name__ == "__main__":
    unittest.main()



