#!/usr/bin/env python3
"""
SigmaFidelity™ QMS Catalog & Access Tier Governance Enforcer
Standard: HWB-QMS-1.0 v2.0 / SOC 2 Type II
Author: George (Systems Architect)
Approved: Humberto Dominguez (CEO)

1. Enforces 'access_tier' ('EXECUTIVE', 'AUDITOR', 'ESTIMATOR', 'STAFF', 'PUBLIC') across all catalog entries.
2. Corrects legacy filename mismatches (e.g. HWB-QMS-8.9).
3. Indexes active, unindexed operational and compliance HTML files.
4. Mirrors changes to both IT Website and BabySOP landing directories.
"""

import os
import sys
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.abspath(os.path.join(WEBSITE_DIR, "..", "..", ".."))
BABYSOP_DIR = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-IT", "HWB-BABYSOP-LANDING")

QMS_INDEX_WEBSITE = os.path.join(WEBSITE_DIR, "qms_index.json")
QMS_INDEX_BABYSOP = os.path.join(BABYSOP_DIR, "qms_index.json")
STATIC_QMS_DIR = os.path.join(WEBSITE_DIR, "static", "qms")

def classify_access_tier(dept: str, doc_id: str, filename: str, title: str) -> str:
    d = (dept or "").upper()
    fid = f"{doc_id} {filename} {title}".lower()
    
    # Executive tier: Financial forecasts, accounting, executive reviews, credentials, master prompts
    if d == "ACCOUNTING" or "acc-" in fid or "cost-forecast" in fid or "azure-account" in fid:
        return "EXECUTIVE"
    if "sec-" in fid or "security" in fid or "credential" in fid or "master_prompt" in fid or "big_brain" in fid:
        return "EXECUTIVE"
    if "comms-" in fid or "executive" in fid or "deal radar" in fid or "m&a" in fid:
        return "EXECUTIVE"
        
    # Auditor tier: ISO 9001 master manuals, external audits, management reviews, disaster recovery
    if "management_review" in fid or "form-006" in fid or "disaster_recovery" in fid or "panic_button" in fid or "emergency_database" in fid:
        return "AUDITOR"
    if any(fid.startswith(p) for p in ["hwb-qms-0.", "hwb-qms-4.", "hwb-qms-5.", "hwb-qms-9.3"]):
        return "AUDITOR"
    if "iso 9001" in fid or "quality-management-system-manual" in fid:
        return "AUDITOR"
        
    # Estimator tier: Bids, commercial quotes, estimating calculators, construction takeoffs
    if "bid-" in fid or "quote" in fid or "estimator" in fid or "calc-" in fid or "takeoff" in fid:
        return "ESTIMATOR"
    if "floor_finish_cost" in fid or "construction takeoff" in fid:
        return "ESTIMATOR"
        
    # Public tier: Capability statements, public compliance overviews
    if "public" in fid or "capability_statement" in fid or "trust_center" in fid:
        return "PUBLIC"
        
    # Default: Staff operational access
    return "STAFF"


def run_catalog_enrichment():
    print(f"[QMS-ENRICH] Reading {QMS_INDEX_WEBSITE}...")
    with open(QMS_INDEX_WEBSITE, "r", encoding="utf-8") as f:
        existing_items = json.load(f)

    # Track indexed filenames (case-insensitive)
    indexed_files = {}
    for item in existing_items:
        # Fix known mismatch for 8.9
        if item.get("id") == "HWB-QMS-8.9" and "hwb-qms-8.9" not in item.get("file", "").lower():
            item["file"] = "hwb-qms-8.9_municipal_procurement_and_certification_playbook.html"

        # Assign access tier
        item["access_tier"] = classify_access_tier(
            item.get("dept", ""),
            item.get("id", ""),
            item.get("file", ""),
            item.get("title", "")
        )
        indexed_files[item["file"].lower()] = item

    print(f"[QMS-ENRICH] Existing entries processed: {len(existing_items)}")

    # Unindexed documents mapping
    actual_files = sorted(os.listdir(STATIC_QMS_DIR))
    added_count = 0

    for fname in actual_files:
        if not fname.endswith(".html") or fname == "sop_template.html":
            continue
        if fname.lower() in indexed_files:
            continue

        file_path = os.path.join(STATIC_QMS_DIR, fname)
        if not os.path.isfile(file_path):
            continue

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                raw_html = fp.read()
        except Exception as e:
            print(f"[QMS-ENRICH] Could not read {fname}: {e}")
            continue

        soup = BeautifulSoup(raw_html, "html.parser")
        raw_title = soup.title.string.strip() if soup.title and soup.title.string else fname
        clean_title = raw_title.replace(" | HWB QMS", "").replace(" | HWB Services", "").strip()

        # Derive ID
        doc_id = "HWB-QMS"
        m = re.search(r"(HWB-[A-Z0-9.\-_]+)", fname, re.IGNORECASE)
        if m:
            doc_id = m.group(1).upper()
        else:
            # Check for header or h1
            h1 = soup.find("h1")
            if h1:
                m_h1 = re.search(r"(HWB-[A-Z0-9.\-_]+)", h1.text, re.IGNORECASE)
                if m_h1:
                    doc_id = m_h1.group(1).upper()

        # Derive Department
        fname_lower = fname.lower()
        dept = "QMS"
        if "acc-" in fname_lower:
            dept = "ACCOUNTING"
        elif "comms-" in fname_lower:
            dept = "EXECUTIVE"
        elif "ops-" in fname_lower or "calc-" in fname_lower:
            dept = "OPERATIONS"
        elif "sal-" in fname_lower:
            dept = "SALES-MARKETING"
        elif "ehs" in fname_lower:
            dept = "EHSQ"
        elif "hr" in fname_lower:
            dept = "HR"
        elif any(k in fname_lower for k in ["lexicon", "backend", "system", "terminal", "cognitive", "telegram", "antigravity", "memory"]):
            dept = "IT"

        tier = classify_access_tier(dept, doc_id, fname, clean_title)

        # Build clean title if needed
        if not clean_title.startswith("Standard Operating Procedure:") and not clean_title.startswith("Playbook:") and not clean_title.startswith("Manual:"):
            if "sop" in fname_lower:
                clean_title = f"Standard Operating Procedure: {clean_title}"
            elif "playbook" in fname_lower:
                clean_title = f"Playbook: {clean_title}"

        new_entry = {
            "title": clean_title,
            "id": doc_id,
            "dept": dept,
            "file": fname,
            "version": "1.0.0",
            "compliance": "UPDATED",
            "date": datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%m-%d-%Y"),
            "access_tier": tier
        }

        existing_items.append(new_entry)
        indexed_files[fname.lower()] = new_entry
        added_count += 1
        print(f"[QMS-ENRICH] + Indexed: [{tier:9}] {doc_id:25} | {fname}")

    print(f"[QMS-ENRICH] Added {added_count} newly indexed documents. Total items: {len(existing_items)}")

    # Sort items consistently: dept, then title
    existing_items.sort(key=lambda x: (x.get("dept", ""), x.get("title", "")))

    # Write to IT Website
    with open(QMS_INDEX_WEBSITE, "w", encoding="utf-8") as f:
        json.dump(existing_items, f, indent=2)
    print(f"[QMS-ENRICH] Successfully wrote {QMS_INDEX_WEBSITE}")

    # Write to BabySOP landing if it exists
    if os.path.exists(BABYSOP_DIR):
        with open(QMS_INDEX_BABYSOP, "w", encoding="utf-8") as f:
            json.dump(existing_items, f, indent=2)
        print(f"[QMS-ENRICH] Successfully mirrored {QMS_INDEX_BABYSOP}")

if __name__ == "__main__":
    run_catalog_enrichment()
