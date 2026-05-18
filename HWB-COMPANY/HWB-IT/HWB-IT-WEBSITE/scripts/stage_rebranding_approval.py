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

# Email Content for CEO Approval
RECIPIENT_EMAIL = "humbertoed@hwbcleaning.com"
SUBJECT = "APPROVAL REQUIRED: Official Rebranding & SEO Logo Update (HWB-COM-002)"

HTML_CONTENT = """
<html>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
    <h2 style="color: #004aad;">Institutional Action: Rebranding Approval</h2>
    <p>Dear CEO Humberto Dominguez,</p>
    
    <p>George (Expert SEO & Systems Architect) has completed the technical audit and rebranding documentation for the company logo. Per the mandatory approval protocol, this documentation is now staged for your review and final authorization.</p>

    <h3 style="color: #004aad; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Key Updates</h3>
    <ul>
        <li><b>New SEO-Optimized Filename:</b> <code>hwb-cleaning-services-llc-logo-plano-tx.png</code></li>
        <li><b>Institutional Impact:</b> Boosts local search authority for "Cleaning Services" and "Plano TX."</li>
        <li><b>Documentation:</b> HWB-COM-002 (Official Logo Rebranding & SEO Audit).</li>
        <li><b>Letterhead Update:</b> HWB-COM-001 has been updated with the new asset path.</li>
    </ul>

    <p>Please review the staged documentation in the <code>HWB-COMMUNICATION</code> directory. Upon your approval, the changes will be propagated across the institutional web infrastructure.</p>

    <p><b>Fidelity. Safety. Respect.</b></p>
    
    <hr>
    <p style="font-size: 0.8rem; color: #666;">
        <b>George</b><br>
        AI Marketing Assistant & Expert SEO<br>
        HWB Cleaning Services LLC | Institutional Division
    </p>
</body>
</html>
"""

if __name__ == "__main__":
    print(f"Staging rebranding approval email for {RECIPIENT_EMAIL}...")
    # NOTE: Mandatory use of 'send_marketing_email' WITHOUT bypass_approval to ensure staging.
    success = engine.send_marketing_email(RECIPIENT_EMAIL, SUBJECT, HTML_CONTENT, bypass_approval=False)
    if success:
        print("SUCCESS: Approval email has been STAGED in the PendingOutbox.")
        print("To send, the CEO must run the approval command: engine.approve_and_send(ID)")
    else:
        print("FAILURE: Email staging failed.")
        sys.exit(1)
