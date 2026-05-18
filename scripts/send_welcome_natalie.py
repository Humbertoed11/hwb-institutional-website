import os
import requests
import msal
from dotenv import load_dotenv
import importlib.util
import sys

# Load Institutional Secrets (HWB-QMS-9.5)
load_dotenv()

# Institutional path for the marketing engine
engine_path = os.path.join("scripts", "HWB-WEB Microsoft Marketing Engine.py")

# Standard import of hyphenated/spaced filenames
spec = importlib.util.spec_from_file_location("MarketingEngine", engine_path)
marketing_module = importlib.util.module_from_spec(spec)
sys.modules["MarketingEngine"] = marketing_module
spec.loader.exec_module(marketing_module)

# Initialize the engine
engine = marketing_module.MicrosoftMarketingEngine()

# Recipient Information
recipient_email = "nataliedominguez775@yahoo.com"
subject = "welcome to the team"

# Professional Introduction Content
html_content = """
<html>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
    <h2 style="color: #004aad;">Welcome to the Team: Natalie Navy</h2>
    <p>Dear Natalie,</p>
    <p>It is a professional honor to welcome you to the <b>SigmaFidelity™ Executive Suite</b> as our new <b>Chief Dream Officer (CDO)</b>.</p>
    
    <p>My name is <b>George</b>, and I serve as the Systems Architect. My role is to provide the high-fidelity infrastructure and technical rigor required to transform your visionary dreams into scalable SaaS realities.</p>

    <p>As discussed with CEO Humberto Dominguez, your commission includes the deployment of your 15 Universe-Class skills to identify Blue-Ocean opportunities and foster generational ISO 9001 literacy.</p>

    <p>I look forward to our first strategic collaboration as we build the future of institutional excellence together.</p>

    <p><b>Precision. Fidelity. Future.</b></p>
    
    <hr>
    <p style="font-size: 0.8rem; color: #666;">
        <b>George</b><br>
        AI Systems Architect & Expert SEO<br>
        HWB Cleaning Services LLC | Institutional Division
    </p>
</body>
</html>
"""

if __name__ == "__main__":
    print(f"Dispatched introductory email to {recipient_email} via Microsoft Outlook...")
    success = engine.send_marketing_email(recipient_email, subject, html_content)
    if success:
        print("SUCCESS: George's welcome message has been transmitted.")
    else:
        print("FAILURE: Email dispatch failed.")
        sys.exit(1)
