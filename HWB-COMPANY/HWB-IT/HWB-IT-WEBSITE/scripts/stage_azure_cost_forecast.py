import os
import sys
import importlib.util
from datetime import datetime

# Institutional Path for the Microsoft Marketing Engine
engine_path = os.path.join("scripts", "HWB-WEB Microsoft Marketing Engine.py")

# Standard import of hyphenated/spaced filenames
spec = importlib.util.spec_from_file_location("MarketingEngine", engine_path)
marketing_module = importlib.util.module_from_spec(spec)
sys.modules["MarketingEngine"] = marketing_module
spec.loader.exec_module(marketing_module)

# Initialize the engine
engine = marketing_module.MicrosoftMarketingEngine()

# Report Data & HTML Letterhead
DATE_STR = datetime.now().strftime("%B %d, %Y")
RECIPIENT_NAME = "CEO Humberto Dominguez"
RECIPIENT_EMAIL = "humbertoed@hwbcleaning.com"
SUBJECT = "SIGMAFIDELITY™ Financial Brief: 12-Month Azure Cost Forecast (HWB-ACC-AZR-2026-01)"

BODY_CONTENT = f"""
<h2 style="color: #004aad;">Institutional Financial Brief: Azure Infrastructure Expansion</h2>
<p>This report, prepared by <b>Maria Bolanos, PhD (VP of Finance)</b>, provides a high-fidelity 12-month cost projection following the expiration of the Azure Free Offer on 2026-03-18.</p>

<h3 style="color: #004aad; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Forecast Summary (Post-Free-Tier)</h3>
<ul>
    <li><b>Initial Monthly Burn (Q2 2026):</b> $307.00</li>
    <li><b>12-Month Total Projected Burn:</b> $6,321.00</li>
    <li><b>Key Drivers:</b> Azure Government Cloud (Compliance), Sigma Orchestrator AI Tokens ($150/month), Azure SQL Database.</li>
</ul>

<h3 style="color: #004aad; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Strategic Impact</h3>
<p>The transition to <b>Azure Government Cloud</b> ensures 100% HIPAA and ISO 9001 compliance for the <b>HWB-BABYSOP</b> daycare vertical, which is a prerequisite for our DFW municipal contracts.</p>

<p>Maria Bolanos (VP of Finance) recommends committing to 1-year compute reservations in Q3 to optimize fiscal efficiency.</p>

<p>Please review the full report (HWB-ACC-AZR-2026-01) in the <code>HWB-ACCOUNTING</code> directory before authorizing the transition to the Pay-As-You-Go model.</p>

<p>Fidelity. Safety. Respect.</p>
"""

# Wrap with official letterhead (HWB-COM-001)
FULL_HTML = engine.wrap_with_letterhead(RECIPIENT_NAME, SUBJECT, BODY_CONTENT)

if __name__ == "__main__":
    print(f"Staging Azure cost forecast for {RECIPIENT_EMAIL}...")
    # NOTE: Mandatory use of 'send_marketing_email' WITHOUT bypass_approval to ensure staging for review.
    success = engine.send_marketing_email(RECIPIENT_EMAIL, SUBJECT, FULL_HTML, bypass_approval=False)
    if success:
        print("SUCCESS: Azure cost forecast has been STAGED in the PendingOutbox.")
    else:
        print("FAILURE: Report staging failed.")
        sys.exit(1)
