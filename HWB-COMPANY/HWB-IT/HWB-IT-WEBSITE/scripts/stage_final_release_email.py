import os
import sys
import importlib.util
from datetime import datetime

# Institutional Path for the Microsoft Marketing Engine
engine_path = os.path.join("scripts", "HWB-WEB Microsoft Marketing Engine.py")

# Standard import
spec = importlib.util.spec_from_file_location("MarketingEngine", engine_path)
marketing_module = importlib.util.module_from_spec(spec)
sys.modules["MarketingEngine"] = marketing_module
spec.loader.exec_module(marketing_module)

# Initialize
engine = marketing_module.MicrosoftMarketingEngine()

# Final Release Content
SUBJECT = "SIGMAFIDELITY™ INSTITUTIONAL LAUNCH: Corporate Intranet & Executive Hub"
RELEASE_DATE = "March 20, 2026"

BODY_CONTENT = f"""
<h2 style="color: #004aad;">Institutional Milestone: Full System Synchronization</h2>
<p>Dear HWB Cleaning Services Team,</p>

<p>We are proud to announce the full activation of the <b>SigmaFidelity™ Institutional Ecosystem</b>. Effective today, {RELEASE_DATE}, all corporate operations, documentation, and communications are synchronized under our new high-fidelity standards.</p>

<h3 style="color: #004aad; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Operational Command Centers</h3>
<ol>
    <li><b>The SigmaFidelity™ Portal (Intranet):</b> Our single source of truth for ISO 9001 SOPs, chemical safety data, and corporate reports.<br>
    <a href="https://netorgft3163094.sharepoint.com/SitePages/Sigma.aspx">Access Portal</a></li>
    
    <li><b>The Executive Hub (Microsoft Teams):</b> Our primary internal communication channel. All department-level synchronization now occurs here (Goodbye WhatsApp/Messenger).</li>
</ol>

<h3 style="color: #004aad; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Institutional Mandates</h3>
<ul>
    <li><b>Zero Process Fog:</b> All project-related data must be stored in the consolidated SharePoint libraries.</li>
    <li><b>High-Fidelity Branding:</b> All external correspondence must utilize the official <b>HWB-COM-001</b> letterhead.</li>
</ul>

<p>This expansion represents a significant leap in our technical authority and operational capacity as we scale the <b>BabySOP.com</b> vertical.</p>

<p><b>Fidelity. Safety. Respect.</b></p>

<hr>
<p style="font-size: 0.8rem; color: #666;">
    <b>Humberto Dominguez, PhD</b><br>
    CEO | HWB Cleaning Services LLC<br>
    Certified Lean Six Sigma Master Black Belt
</p>
"""

RECIPIENTS = [
    {"name": "Humberto Dominguez", "email": "hdominguez@hwbcleaning.com"},
    {"name": "Mirna Rondinella", "email": "mrondinella@hwbcleaning.com"},
    {"name": "Kevin Bailey", "email": "kbailey@hwbcleaning.com"}
]

if __name__ == "__main__":
    print(f"Staging FINAL RELEASE email for {RELEASE_DATE}...")
    
    for user in RECIPIENTS:
        # Wrap with letterhead (CID PNG logo)
        full_html = engine.wrap_with_letterhead(user['name'], SUBJECT, BODY_CONTENT)
        
        # Stage for CEO approval
        success = engine.send_marketing_email(user['email'], SUBJECT, full_html, bypass_approval=False)
        if success:
            print(f"STAGED: Final Release for {user['name']}")

    print("\n--- Staging Complete ---")
    print("This release is now held in the PendingOutbox for your final authorization on Friday, March 20.")
