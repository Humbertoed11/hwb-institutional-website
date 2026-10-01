"""
SigmaFidelity™ Institutional Lexicon Governance Engine
Standard: HWB-QMS-1.0 v2.0 (Everyday Words) & Executive Mandate [2026-09-30]
Authority: Humberto Dominguez (CEO)
Architect: George (Systems Architect & mbB)

Mission:
Enforce domain-driven, plain-English commercial cleaning vocabulary across all
public webpages, administrative interfaces, customer communications, and reports.
Prohibits aviation jargon (e.g., "cockpit"), esoteric developer slang (e.g.,
"handshake protocol", "poka-yoke" in customer-facing text), and replaces them
with authentic facilities management and commercial cleaning terminology.
"""

import os
import re
from typing import Dict, List, Tuple, Any, Optional

# Master Lexicon Dictionary: Prohibited Terms -> Approved Cleaning & Operations Terms
PROHIBITED_TERMS: Dict[str, Dict[str, Any]] = {
    "cockpit": {
        "domain": "aviation",
        "replacement": "Operations Hub",
        "context_replacements": {
            "security": "Site Security & Operations Hub",
            "parity": "Dev-to-Live Parity Center",
            "health": "Data Health & Maintenance Center",
            "partner": "Partner Portal",
            "executive": "Executive Portal",
            "default": "Operations Hub"
        },
        "rationale": "Aviation terminology is prohibited in commercial facilities and janitorial management."
    },
    "handshake protocol": {
        "domain": "software_engineering",
        "replacement": "Personal Scope Consultation",
        "context_replacements": {
            "default": "Scope Consultation"
        },
        "rationale": "Developer jargon creates confusion for facility directors and commercial clients."
    }
}

# Regex pattern for case-insensitive whole-word boundary matching
BANNED_WORDS_PATTERN = re.compile(
    r'\b(cockpit)\b',
    re.IGNORECASE
)


def inspect_text_for_jargon(text: str, context_label: str = "general") -> List[Dict[str, Any]]:
    """
    Audits a string of rendered HTML or text for prohibited jargon words.
    Returns a list of violations with location and recommended replacements.
    """
    violations = []
    lines = text.splitlines()
    for line_idx, line in enumerate(lines, 1):
        for match in BANNED_WORDS_PATTERN.finditer(line):
            matched_word = match.group(0)
            lowered = matched_word.lower()
            rule = PROHIBITED_TERMS.get(lowered, {})
            recommended = rule.get("replacement", "Operations Hub")
            violations.append({
                "line": line_idx,
                "term": matched_word,
                "domain": rule.get("domain", "unauthorized_jargon"),
                "recommended_replacement": recommended,
                "context": line.strip()[:120],
                "context_label": context_label
            })
    return violations


def sanitize_commercial_copy(text: str) -> str:
    """
    Replaces prohibited jargon in a string with approved commercial cleaning alternatives.
    Preserves case capitalization where feasible.
    """
    def _replace(match):
        word = match.group(0)
        lowered = word.lower()
        replacement = PROHIBITED_TERMS.get(lowered, {}).get("replacement", "Operations Hub")
        if word.isupper():
            return replacement.upper()
        if word.istitle():
            return replacement
        return replacement.lower()

    return BANNED_WORDS_PATTERN.sub(_replace, text)


def scan_templates_directory(templates_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Crawls active HTML templates and reports any prohibited terminology.
    Ignores retired, legacy, or snapshot directories per Active-Only Reference Mandate.
    """
    if not templates_dir:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        templates_dir = os.path.join(base_dir, "templates")

    ignored_dirs = {".snapshots_pre_salesforce_ui", "retired", "legacy", "backup"}
    results = {
        "scanned_files": 0,
        "violations_count": 0,
        "violations": []
    }

    if not os.path.exists(templates_dir):
        return results

    for root, dirs, files in os.walk(templates_dir):
        # Exclude ignored directories in-place
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]

        for file in files:
            if file.endswith(".html"):
                file_path = os.path.join(root, file)
                results["scanned_files"] += 1
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    file_violations = inspect_text_for_jargon(content, context_label=file)
                    if file_violations:
                        results["violations_count"] += len(file_violations)
                        results["violations"].extend([
                            {**v, "file": os.path.relpath(file_path, templates_dir)}
                            for v in file_violations
                        ])
                except Exception as e:
                    pass

    return results
