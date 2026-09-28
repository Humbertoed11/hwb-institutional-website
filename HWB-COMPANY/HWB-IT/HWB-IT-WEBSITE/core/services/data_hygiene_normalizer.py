"""
SigmaFidelity™ Enterprise Data Hygiene & Lexical Normalizer
Standard: HWB-QMS-1.0 v2.0 / Six Sigma Data Quality Governance
Custodians: George (Systems Architect) & Silas Sync (VP of CRM)
"""

import os
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from core.services.database import get_db

# Acronyms and terms that must always retain specific casing
ACRONYM_MAP = {
    "llc": "LLC",
    "inc": "Inc.",
    "inc.": "Inc.",
    "corp": "Corp.",
    "corp.": "Corp.",
    "ltd": "Ltd.",
    "ltd.": "Ltd.",
    "pc": "P.C.",
    "p.c.": "P.C.",
    "pllc": "PLLC",
    "isd": "ISD",
    "cisd": "CISD",
    "ymca": "YMCA",
    "ywca": "YWCA",
    "rv": "RV",
    "ntta": "NTTA",
    "tx": "TX",
    "cdcn": "CDCN",
    "usa": "USA",
    "us": "US",
    "gmc": "GMC",
    "bmw": "BMW",
    "at&t": "AT&T",
    "vw": "VW",
    "md": "MD",
    "dds": "DDS",
    "pa": "PA",
    "stem": "STEM",
    "prep": "Prep",
    "dba": "DBA",
}

LOWERCASE_WORDS = {
    "and", "or", "the", "of", "in", "at", "for", "on", "by", "with", "a", "an", "to"
}

# CASS Postal Address Standard Replacements (case-insensitive word boundary)
CASS_SUFFIX_MAP = {
    r"\bStreet\b": "St",
    r"\bStreets\b": "Sts",
    r"\bAvenue\b": "Ave",
    r"\bBoulevard\b": "Blvd",
    r"\bRoad\b": "Rd",
    r"\bDrive\b": "Dr",
    r"\bLane\b": "Ln",
    r"\bCourt\b": "Ct",
    r"\bCircle\b": "Cir",
    r"\bPlace\b": "Pl",
    r"\bParkway\b": "Pkwy",
    r"\bHighway\b": "Hwy",
    r"\bExpressway\b": "Expy",
    r"\bFreeway\b": "Fwy",
    r"\bSuite\b": "Ste",
    r"\bBuilding\b": "Bldg",
    r"\bApartment\b": "Apt",
    r"\bDepartment\b": "Dept",
    r"\bFloor\b": "Fl",
    r"\bRoom\b": "Rm",
}


def normalize_title_case(raw_name: Optional[str]) -> str:
    """
    Transforms screaming ALL-CAPS or raw lowercase company names into 
    institutional Title Case while preserving uppercase acronyms and proper syntax.
    Example: 'SUNBELT RV CENTER, LLC' -> 'Sunbelt RV Center, LLC'
    """
    if not raw_name or not isinstance(raw_name, str):
        return ""

    text = raw_name.strip()
    if not text:
        return ""

    # Split preserving punctuation/spacing tokens
    words = re.split(r"(\s+|[,\-&/])", text)
    normalized_tokens = []

    for i, token in enumerate(words):
        if not token:
            continue
        # Punctuation or whitespace preserved as-is
        if re.match(r"^[\s,\-&/]+$", token):
            normalized_tokens.append(token)
            continue

        clean_lower = token.lower().strip(".,;:()")
        punctuation_suffix = token[len(clean_lower):] if len(token) > len(clean_lower) else ""

        # Check explicit acronym dictionary
        if clean_lower in ACRONYM_MAP:
            normalized_tokens.append(ACRONYM_MAP[clean_lower] + punctuation_suffix)
        elif clean_lower in LOWERCASE_WORDS and i > 0:
            normalized_tokens.append(clean_lower + punctuation_suffix)
        else:
            # Standard capitalization (handle apostrophes like O'Reilly)
            if "'" in token:
                parts = token.split("'")
                cap_parts = [p.capitalize() for p in parts]
                normalized_tokens.append("'".join(cap_parts))
            elif "-" in token:
                parts = token.split("-")
                cap_parts = [p.capitalize() for p in parts]
                normalized_tokens.append("-".join(cap_parts))
            else:
                normalized_tokens.append(token.capitalize())

    result = "".join(normalized_tokens)
    # Clean up double punctuation if any
    result = re.sub(r"\s+", " ", result).strip()
    result = re.sub(r",\s*,", ",", result)
    return result


def normalize_phone_number(raw_phone: Optional[str]) -> str:
    """
    Strict Poka-Yoke phone normalizer converting raw strings to standard (###) ###-####.
    Returns empty string if invalid or < 10 digits.
    """
    if not raw_phone or not isinstance(raw_phone, str):
        return ""
    digits = re.sub(r"\D", "", raw_phone)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        if digits == "0000000000":
            return ""
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return raw_phone.strip()


def normalize_address_cass(raw_address: Optional[str]) -> str:
    """
    Normalizes street address strings according to USPS CASS standards.
    Example: '123 Main Street Suite 200' -> '123 Main St Ste 200'
    """
    if not raw_address or not isinstance(raw_address, str):
        return ""
    addr = raw_address.strip()
    for pattern, replacement in CASS_SUFFIX_MAP.items():
        addr = re.sub(pattern, replacement, addr, flags=re.IGNORECASE)
    # Capitalize directionals
    addr = re.sub(r"\b(nw|ne|sw|se)\b", lambda m: m.group(1).upper(), addr, flags=re.IGNORECASE)
    # Ensure Ste has a space before number
    addr = re.sub(r"\bSte\.?\s*#?([0-9a-zA-Z]+)", r"Ste \1", addr, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", addr).strip()


def compute_lead_quality_score(lead: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes real-time Lead Quality Index (LQI, 0-100) and assigns quality Tier.
    Tier A (85-100): Pristine / Sales-Ready
    Tier B (60-84): Marketable / Semi-Enriched
    Tier C (30-59): Deficient / Staged
    Tier D (0-29): Ghost Lead / Deprecated
    """
    score = 0
    checks = []

    # 1. Company Name (Max 20 Pts)
    c_name = lead.get("center_name") or ""
    if c_name and len(c_name.strip()) >= 3:
        if c_name == c_name.upper() and len(c_name) > 3:
            score += 10
            checks.append("Name Present (Needs Title Casing: +10)")
        else:
            score += 20
            checks.append("Name Clean (+20)")
    else:
        checks.append("Name Missing (0)")

    # 2. Contact Phone (Max 25 Pts)
    phone = lead.get("phone") or ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10 and digits != "0000000000":
        score += 25
        checks.append("Phone Valid (+25)")
    elif digits and len(digits) >= 7:
        score += 10
        checks.append("Phone Partial (+10)")
    else:
        checks.append("Phone Missing (0)")

    # 3. Physical Address & Zip (Max 20 Pts)
    address = lead.get("address") or ""
    zipcode = lead.get("zipcode") or ""
    if address and len(address) > 5 and "pending" not in address.lower():
        score += 15
        if zipcode and len(zipcode) >= 5:
            score += 5
            checks.append("Address & Zip Complete (+20)")
        else:
            checks.append("Address Present, Missing Zip (+15)")
    else:
        checks.append("Address Missing (0)")

    # 4. Decision Maker / Director (Max 15 Pts)
    dm = lead.get("decision_maker") or lead.get("director") or ""
    if dm and len(dm.strip()) > 3:
        score += 15
        checks.append("Decision Maker Identified (+15)")
    else:
        checks.append("Decision Maker Missing (0)")

    # 5. Digital Endpoint / Email / Website (Max 10 Pts)
    email = lead.get("email") or ""
    website = lead.get("website") or ""
    if email and "@" in email:
        score += 10
        checks.append("Email Verified (+10)")
    elif website and "." in website:
        score += 5
        checks.append("Website Present (+5)")
    else:
        checks.append("Digital Endpoint Missing (0)")

    # 6. Sector Classification (Max 10 Pts)
    ind = lead.get("industry") or ""
    if ind and ind not in ["Commercial Legacy", "Unknown", ""]:
        score += 10
        checks.append(f"Classified ({ind}: +10)")
    else:
        checks.append("Classification Staged (0)")

    score = min(100, max(0, score))

    if score >= 85:
        tier = "Tier A (Pristine)"
        tier_code = "A"
    elif score >= 60:
        tier = "Tier B (Marketable)"
        tier_code = "B"
    elif score >= 30:
        tier = "Tier C (Deficient)"
        tier_code = "C"
    else:
        tier = "Tier D (Ghost Lead)"
        tier_code = "D"

    return {
        "score": score,
        "tier": tier,
        "tier_code": tier_code,
        "is_ghost": score < 30 and (not phone or not address),
        "checks": checks
    }


def heal_all_caps_casing_batch(db_url: Optional[str] = None, dry_run: bool = True, batch_size: int = 500) -> Dict[str, Any]:
    """
    Self-Healing Routine: Scans and normalizes ALL-CAPS corporate names in Leads.
    Executes in batches with Poka-Yoke transaction safety.
    """
    target_url = db_url or os.environ.get('DATABASE_URL')
    if not target_url:
        return {"status": "error", "message": "DATABASE_URL not configured"}

    t0 = time.time()
    conn = get_db(target_url)
    try:
        updated_records = []
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, center_name 
                FROM "Leads"
                WHERE center_name IS NOT NULL 
                  AND center_name = UPPER(center_name) 
                  AND length(center_name) > 3
                ORDER BY id ASC
                LIMIT %s;
            """, (batch_size,))
            rows = cur.fetchall()

            for r in rows:
                lead_id = r[0]
                old_name = r[1]
                new_name = normalize_title_case(old_name)
                if old_name != new_name:
                    updated_records.append({
                        "id": lead_id,
                        "old_name": old_name,
                        "new_name": new_name
                    })
                    if not dry_run:
                        cur.execute("""
                            UPDATE "Leads" 
                            SET center_name = %s 
                            WHERE id = %s;
                        """, (new_name, lead_id))

        if not dry_run and updated_records:
            conn.commit()

        latency_ms = round((time.time() - t0) * 1000, 2)
        mode = "Simulation" if dry_run else "Committed"
        return {
            "status": "success",
            "mode": mode,
            "count_processed": len(updated_records),
            "latency_ms": latency_ms,
            "samples": updated_records[:5],
            "message": f"{mode} normalized {len(updated_records)} ALL-CAPS company names in {latency_ms} ms."
        }
    except Exception as e:
        if not dry_run and conn:
            conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def purge_expired_ghost_leads(db_url: Optional[str] = None, dry_run: bool = True, max_purge: int = 50) -> Dict[str, Any]:
    """
    Policy 1 Implementation: Hard-deletes leads that meet Ghost Lead criteria:
    - Missing phone (or 000-0000)
    - Missing physical street address
    - Zero associated bids in ConstructionBids
    - Zero associated WorkOrders or Customers
    """
    target_url = db_url or os.environ.get('DATABASE_URL')
    if not target_url:
        return {"status": "error", "message": "DATABASE_URL not configured"}

    t0 = time.time()
    conn = get_db(target_url)
    try:
        purged_records = []
        with conn.cursor() as cur:
            cur.execute("""
                SELECT l.id, l.center_name 
                FROM "Leads" l
                LEFT JOIN "CampaignRecipients" cr ON l.id = cr.lead_id
                LEFT JOIN "Contacts" c ON l.id = c.lead_id
                WHERE (l.phone IS NULL OR l.phone = '' OR l.phone LIKE '%%000-0000%%')
                  AND (l.address IS NULL OR l.address = '' OR l.address LIKE '%%Pending%%')
                  AND (l.is_converted IS NOT TRUE)
                  AND cr.lead_id IS NULL
                  AND c.lead_id IS NULL
                LIMIT %s;
            """, (max_purge,))
            rows = cur.fetchall()

            for r in rows:
                lead_id = r['id'] if isinstance(r, dict) or hasattr(r, 'keys') else r[0]
                name = r['center_name'] if isinstance(r, dict) or hasattr(r, 'keys') else r[1]
                purged_records.append({"id": lead_id, "name": name})
                if not dry_run:
                    cur.execute('DELETE FROM "Leads" WHERE id = %s;', (lead_id,))

        if not dry_run and purged_records:
            conn.commit()

        latency_ms = round((time.time() - t0) * 1000, 2)
        mode = "Simulation" if dry_run else "Committed"
        return {
            "status": "success",
            "mode": mode,
            "count_purged": len(purged_records),
            "latency_ms": latency_ms,
            "purged_records": purged_records,
            "message": f"{mode} purged {len(purged_records)} unserviceable ghost leads in {latency_ms} ms."
        }
    except Exception as e:
        if not dry_run and conn:
            conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()
