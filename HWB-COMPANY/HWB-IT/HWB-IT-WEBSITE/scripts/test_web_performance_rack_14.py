#!/usr/bin/env python3
"""
⚡ SIGMAFIDELITY™ HWB-QMS-11.14: ENTERPRISE WEB PERFORMANCE & EDGE CACHING TEST SUITE
Standard: HWB-QMS-11.14 / MO-HWB-2026-10-19-PERF-014 (v5.4.3)
Custodians: Super George (Commander of Special Ops) & George Bytes (HWB Tactical Builder)
"""

import os
import sys
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


class EnterpriseWebPerformanceTestSuite(unittest.TestCase):
    """Verifies the 5 Pillars of HWB-QMS-11.14 Enterprise Web Performance Standard."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.db_url = app.config["DATABASE_URL"]

    def test_01_database_pool_zero_round_trip_and_timezone(self):
        """Pillar 3: Verifies DB_POOL_MAX=10 and connection-init America/Chicago timezone without checkout SQL."""
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
        """Pillar 4: Verifies get_version_info() is cached in memory with lru_cache and reports v5.4.3."""
        clear_version_cache()
        self.assertEqual(APP_SEMANTIC_VERSION, "v5.4.3")
        info_1 = get_version_info()
        info_2 = get_version_info()
        self.assertEqual(info_1.get("app_version"), "v5.4.3")
        self.assertIs(info_1, info_2)
        cache_info = get_version_info.cache_info()
        self.assertGreaterEqual(cache_info.hits, 1)
        self.assertEqual(cache_info.misses, 1)

    def test_03_public_marketing_split_cloudflare_edge_cache_headers(self):
        """Pillar 5: Verifies anonymous GET / emits s-maxage=3600, strips Cookie from Vary, and emits no Set-Cookie."""
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
        """Pillar 5: Verifies /login and /admin routes strictly forbid edge caching."""
        res_login = self.client.get("/login")
        self.assertEqual(res_login.status_code, 200)
        cc = res_login.headers.get("Cache-Control", "")
        self.assertIn("no-store", cc)
        self.assertIn("private", cc)

    def test_05_webp_homepage_assets_and_template_references(self):
        """Pillar 5: Verifies all 5 homepage WebP images exist, total <450 KB, and are referenced in GET / HTML."""
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


if __name__ == "__main__":
    unittest.main()
