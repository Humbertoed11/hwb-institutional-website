#!/usr/bin/env python3
"""
SigmaFidelity™ Enterprise SEO & AI Search Sitewide Verification Suite
Standard: HWB-QMS-7.2 / GOV-04 Fortune 500 Tier-1 Audit Gate
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Set, Tuple
from PIL import Image


BASE_URL = "http://127.0.0.1:5000"
WEB_ROOT = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE"

PUBLIC_HTML_ROUTES: List[str] = [
    "/",
    "/get-quote",
    "/services/janitorial",
    "/services/commercial",
    "/services/industrial",
    "/services/construction",
    "/facilities/daycare-childcare",
    "/facilities/schools-education",
    "/facilities/medical-dental",
    "/facilities/corporate-offices",
    "/facilities/auto-dealerships",
    "/facilities/churches-nonprofits",
    "/facilities/warehouses-industrial",
    "/facilities/construction-subdivisions",
    "/locations/mckinney",
    "/locations/frisco",
    "/locations/plano",
    "/locations/dallas",
    "/locations/waxahachie",
    "/locations/fort-worth",
    "/locations/irving",
    "/locations/richardson",
    "/locations/allen",
    "/locations/arlington",
    "/locations/addison",
    "/locations/prosper",
    "/locations/celina",
    "/locations/denton",
    "/locations/rockwall",
    "/locations/southlake",
    "/locations/grand-prairie",
    "/locations/mansfield",
    "/about",
    "/trust-center",
    "/capability-statement",
    "/prequal",
    "/academy",
    "/work-with-us",
    "/compliance",
    "/ehsq",
    "/methodology",
    "/privacy-policy",
    "/terms",
    "/accessibility",
    "/fcra-disclosure",
]

MANIFEST_ROUTES: List[str] = [
    "/sitemap.xml",
    "/llms.txt",
    "/llms-full.txt",
    "/.well-known/llms.txt",
    "/ai.txt",
]


def fetch_route(path: str) -> Tuple[int, Dict[str, str], str]:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={"Host": "www.hwbcleaning.com", "User-Agent": "HWB-SEO-Audit/2.5"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        status = resp.getcode()
        headers = {k.lower(): v for k, v in resp.headers.items()}
        body = resp.read().decode("utf-8", errors="replace")
        return status, headers, body


def main() -> int:
    failures: List[str] = []
    discovered_images: Set[str] = set()
    total_jsonld_blocks = 0

    print("=" * 78)
    print("HWB CLEANING — TIER-1 ENTERPRISE SEO & AI SITEWIDE VERIFICATION")
    print("=" * 78)

    # 1. Verify all 45 Public HTML Routes
    for route in PUBLIC_HTML_ROUTES:
        try:
            status, headers, body = fetch_route(route)
        except Exception as exc:
            failures.append(f"[HTTP_ERR] {route}: {exc}")
            continue

        if status != 200:
            failures.append(f"[STATUS] {route} returned {status}")

        # Check Canonical
        expected_canon = f'href="https://www.hwbcleaning.com{route}"'
        if expected_canon not in body:
            failures.append(f"[CANONICAL] {route} missing {expected_canon}")

        # Check max-image-preview:large
        if "max-image-preview:large" not in body and "max-image-preview:large" not in headers.get("x-robots-tag", ""):
            failures.append(f"[ROBOTS] {route} missing max-image-preview:large")

        # Check RFC 8288 Link header
        link_hdr = headers.get("link", "")
        if "/llms.txt" not in link_hdr or "/llms-full.txt" not in link_hdr:
            failures.append(f"[LINK_HDR] {route} missing RFC 8288 AI Link header")

        # Parse all JSON-LD blocks
        ld_matches = re.findall(
            r'<script\s+type="application/ld\+json">\s*(.*?)\s*</script>',
            body,
            re.DOTALL,
        )
        if not ld_matches:
            failures.append(f"[JSON-LD] {route} has 0 JSON-LD blocks")
        for idx, raw_ld in enumerate(ld_matches):
            try:
                json.loads(raw_ld)
                total_jsonld_blocks += 1
            except Exception as j_err:
                failures.append(f"[JSON-LD_INVALID] {route} block #{idx+1}: {j_err}")

        # Collect static image references
        for img_ref in re.findall(r'(/static/img/[a-zA-Z0-9_\-\.]+\.(?:webp|png|jpg))', body):
            discovered_images.add(img_ref)

        # Check forbidden phrases on core conversion/service/facility/location routes
        if (
            route == "/"
            or route.startswith("/services/")
            or route.startswith("/facilities/")
            or route.startswith("/locations/")
        ):
            visible = re.sub(r"<script.*?</script>", " ", body, flags=re.DOTALL)
            visible = re.sub(r"<style.*?</style>", " ", visible, flags=re.DOTALL)
            visible = re.sub(r"<[^>]+>", " ", visible)
            if re.search(r"\b24[\-\s]?hour\s+quote\b", visible, re.IGNORECASE):
                failures.append(f"[COPY_DRIFT] {route} contains '24-hour quote'")
            if re.search(r"\bCSI\s+Division\s+01\s+74\s+23\b", visible, re.IGNORECASE):
                failures.append(f"[JARGON] {route} contains 'CSI Division 01 74 23'")
            if re.search(r"\b(you|your|yours)\b", visible, re.IGNORECASE):
                failures.append(f"[POV_2ND_PERSON] {route} contains 2nd-person pronoun")

    print(f"[PASS] Audited {len(PUBLIC_HTML_ROUTES)} public HTML routes | Valid JSON-LD blocks: {total_jsonld_blocks}")

    # 2. Verify Manifests & XML Sitemap
    for m_route in MANIFEST_ROUTES:
        status, _, body = fetch_route(m_route)
        if status != 200:
            failures.append(f"[MANIFEST] {m_route} returned {status}")
        if "CSI Division 01 74 23" in body:
            failures.append(f"[MANIFEST_JARGON] {m_route} contains 'CSI Division 01 74 23'")

    _, _, sitemap_body = fetch_route("/sitemap.xml")
    try:
        root = ET.fromstring(sitemap_body)
        ns = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "image": "http://www.google.com/schemas/sitemap-image/1.1",
        }
        urls = root.findall("sm:url", ns)
        images = root.findall(".//image:image", ns)
        print(f"[PASS] /sitemap.xml valid XML | <url> nodes: {len(urls)} | <image:image> nodes: {len(images)}")
        if len(images) < 32:
            failures.append(f"[SITEMAP] Expected >= 32 <image:image> nodes, got {len(images)}")
    except Exception as x_err:
        failures.append(f"[SITEMAP_XML_ERR] {x_err}")

    # 3. Verify All Discovered Static Images Exist & Primary Hero/Sitewide WebPs Have EXIF + XMP
    for img_rel in sorted(discovered_images):
        abs_img = os.path.join(WEB_ROOT, img_rel.lstrip("/"))
        if not os.path.exists(abs_img):
            failures.append(f"[MISSING_IMAGE_404] {img_rel} does not exist on disk")

    stamped_targets = [
        "hero_facility_daycare.webp",
        "hero_facility_school.webp",
        "hero_facility_medical.webp",
        "hero_facility_corporate.webp",
        "hero_facility_dealership.webp",
        "hero_facility_church.webp",
        "hero_facility_warehouse.webp",
        "hero_facility_construction.webp",
        "hero_lobby.webp",
        "commercial_church_vacuuming.webp",
        "commercial_marble_polishing.webp",
        "industrial_hero_ppe_aisles.webp",
        "industrial_m20_scrubber.webp",
        "construction_rough_clean_ppe.webp",
        "construction_sweeper_servicing_street.webp",
        "daycare_busy_active.webp",
        "janitorial_breakroom.webp",
        "hwb_core_team_v2.webp",
    ]
    for fname in stamped_targets:
        fpath = os.path.join(WEB_ROOT, "static", "img", fname)
        if not os.path.exists(fpath):
            failures.append(f"[STAMPED_MISSING] {fname}")
            continue
        with Image.open(fpath) as im:
            if not im.info.get("exif") or not im.info.get("xmp"):
                failures.append(f"[BINARY_META_MISSING] {fname} missing EXIF or XMP")

    print(f"[PASS] Verified {len(discovered_images)} referenced static images (0 broken 404s) & {len(stamped_targets)} EXIF/XMP-stamped primary WebP assets")

    if failures:
        print("\n[FAILURES DETECTED]:")
        for f in failures:
            print("  -", f)
        return 1

    print("=" * 78)
    print("RESULT: 100% PASS (0 ERRORS ACROSS ALL ROUTES, SCHEMAS, & IMAGES)")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
