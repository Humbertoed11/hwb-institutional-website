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

# Email Content for CEO Personal Template
RECIPIENT_EMAIL = "humbertoed@hwbcleaning.com"
SUBJECT = "SIGMAFIDELITY™ Official Letterhead Template"

BODY_CONTENT = """
<p>This is the official institutional template. To set this as your default Outlook signature:</p>
<ol>
    <li>Copy this entire email content.</li>
    <li>Open Outlook Settings -> Email -> Signatures.</li>
    <li>Create a new signature and paste this content.</li>
    <li>Set it as the default for New Messages and Replies/Forwards.</li>
</ol>
"""

# Wrap with letterhead
FULL_HTML = engine.wrap_with_letterhead("CEO Humberto Dominguez", SUBJECT, BODY_CONTENT)

if __name__ == "__main__":
    print(f"Staging personal letterhead template for {RECIPIENT_EMAIL}...")
    # NOTE: Bypassing approval for personal user-requested template
    success = engine.send_marketing_email(RECIPIENT_EMAIL, SUBJECT, FULL_HTML, bypass_approval=False)
    if success:
        print("SUCCESS: Personal template has been STAGED in the PendingOutbox.")
    else:
        print("FAILURE: Template staging failed.")
        sys.exit(1)
