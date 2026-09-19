#!/usr/bin/env python3
"""
SigmaFidelity™ Autonomous Pre-Flight Risk Audit & Memory Gate
Standard: HWB-QMS-11.3 Cognitive Architecture & Neural Growth / HWB-QMS-11.5 Pre-Flight Risk Audit
Usage: python3 scripts/preflight_audit.py "<task directive or topic>"
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import sys
import os
import requests
import json

# Ensure project root is in sys.path
sys.path.insert(0, '/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE')

def run_preflight_audit(directive: str):
    print("================================================================================")
    print("  SigmaFidelity™ Pre-Flight Memory Gate & Risk Audit (ISO 9001 / SOC 2)")
    print(f"  Directive: \"{directive}\"")
    print("================================================================================\n")

    api_url = "http://localhost:5000/api/v1/kb/preflight"
    try:
        res = requests.get(api_url, params={"q": directive}, timeout=10)
        if res.status_code != 200:
            print(f"  [ERROR] Audit service responded with HTTP {res.status_code}: {res.text}")
            sys.exit(1)
        data = res.json()
    except Exception as e:
        print(f"  [ERROR] Could not connect to API preflight endpoint ({api_url}): {e}")
        sys.exit(1)

    risk_level = data.get("risk_level", "UNKNOWN")
    status = data.get("status", "UNKNOWN")
    relevant_scars = data.get("scars", [])
    guardrails = data.get("mandatory_guardrails", [])

    risk_symbol = {
        "LOW": "🟢 LOW RISK",
        "MEDIUM": "🟡 MEDIUM RISK",
        "HIGH": "🟠 HIGH RISK",
        "CRITICAL": "🔴 CRITICAL RISK"
    }.get(risk_level, risk_level)

    print(f"Audit Status : {status}")
    print(f"Risk Profile : {risk_symbol}")
    print(f"Scars Found  : {len(relevant_scars)} relevant historical failure modes\n")

    if guardrails:
        print("--------------------------------------------------------------------------------")
        print("  MANDATORY ARCHITECTURAL GUARDRAILS (MUST ADHERE BEFORE EDITING CODE):")
        print("--------------------------------------------------------------------------------")
        for idx, rule in enumerate(guardrails, 1):
            print(f"  [{idx}] {rule}\n")

    if relevant_scars:
        print("--------------------------------------------------------------------------------")
        print("  RELEVANT HISTORICAL KNOWLEDGE SCARS:")
        print("--------------------------------------------------------------------------------")
        for s in relevant_scars:
            print(f"  • Scar ID #{s['id']} [{s.get('status', 'N/A')}] (RRF: {s.get('rrf_score', 0):.4f})")
            print(f"    Description: {s.get('description', '')[:120]}...")
            if s.get('root_cause'):
                print(f"    Root Cause : {s['root_cause'][:120]}...")
            if s.get('implemented_fix'):
                print(f"    Fix Applied: {s['implemented_fix'][:120]}...")
            print()

    print("================================================================================")
    if status == "GUARDRAILS_MANDATED":
        print("  AUDIT VERDICT: PROCEED WITH CAUTION (Guardrails Enforced)")
    else:
        print("  AUDIT VERDICT: GREEN TO PROCEED")
    print("================================================================================\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/preflight_audit.py \"<directive or topic>\"")
        sys.exit(1)
    run_preflight_audit(" ".join(sys.argv[1:]))
