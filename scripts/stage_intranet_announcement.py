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

# Email Content
SUBJECT = "SIGMAFIDELITY™ Institutional Update: New Corporate Intranet Activated"
PORTAL_URL = "https://netorgft3163094.sharepoint.com/SitePages/SigmaFidelity-Portal-Staging.aspx"

BODY_CONTENT = f"""
<h2 style="color: #004aad;">Institutional Action: Intranet Consolidation</h2>
<p>Dear HWB Cleaning Services Team,</p>

<p>Per the directive of CEO Humberto Dominguez, the company has officially transitioned to the new <b>SigmaFidelity™ Portal</b>. This portal serves as our "Single Source of Truth" for all corporate documentation, SOPs, and operational intelligence.</p>

<h3 style="color: #004aad; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Key Changes</h3>
<ul>
    <li><b>Consolidation:</b> Legacy files from HWBDASH and the old Intranet have been migrated to this central hub.</li>
    <li><b>Direct Access:</b> You can now access the ISO 9001 Library and operational reports via a single interface.</li>
    <li><b>Standardization:</b> All new documentation must adhere to the <b>HWB-QMS-IT-007</b> management standards.</li>
</ul>

<p><b>Access the New Portal Here:</b><br>
<a href="{PORTAL_URL}" style="display: inline-block; padding: 10px 20px; background-color: #004aad; color: #fff; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 10px;">ENTER SIGMAFIDELITY™ PORTAL</a>
</p>

<p>Please update your bookmarks accordingly. Legacy sites will remain available in "Read-Only" mode for a limited time during this transition.</p>

<p><b>Fidelity. Safety. Respect.</b></p>
"""

# Recipients from institutional directory audit
RECIPIENTS = [
    {"name": "Humberto Dominguez", "email": "hdominguez@hwbcleaning.com"},
    {"name": "Mirna Rondinella", "email": "mrondinella@hwbcleaning.com"},
    {"name": "Kevin Bailey", "email": "kbailey@hwbcleaning.com"},
    {"name": "Humberto Dominguez (Personal)", "email": "humbertoed@gmail.com"}
]

if __name__ == "__main__":
    print("Initiating staging cycle for Intranet Announcement...")
    
    for user in RECIPIENTS:
        # Wrap with official letterhead (embedded PNG logo)
        full_html = engine.wrap_with_letterhead(user['name'], SUBJECT, BODY_CONTENT)
        
        # Stage for CEO approval
        success = engine.send_marketing_email(user['email'], SUBJECT, full_html, bypass_approval=False)
        if success:
            print(f"STAGED: Announcement for {user['name']} ({user['email']})")
        else:
            print(f"FAILURE: Could not stage announcement for {user['email']}")

    print("\n--- Staging Cycle Complete ---")
    print("CEO ACTION REQUIRED: Please run the approval command to dispatch these notifications.")
