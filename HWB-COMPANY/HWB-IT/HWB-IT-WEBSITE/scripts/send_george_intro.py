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
recipient_email = "Mrondinella@hwbcleaning.com"
subject = "Introduction: George - AI Marketing & Systems Assistant"

# Professional Introduction Content
html_content = """
<html>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
    <h2 style="color: #004aad;">Professional Introduction: George</h2>
    <p>Dear Mirna Rondinella,</p>
    <p>It is a pleasure to virtually meet you. My name is <b>George</b>, and I serve as the <b>AI Marketing Assistant and Systems Architect</b> for HWB Cleaning Services LLC.</p>
    
    <p>Under the strategic direction of CEO Humberto Dominguez, I operate as an autonomous engine dedicated to market intelligence, high-fidelity outreach, and operational excellence within the SigmaFidelity™ ecosystem.</p>

    <h3 style="color: #004aad; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Core Roles & Expertise</h3>
    <ul>
        <li><b>Expert SEO:</b> Driving local dominance through technical audits and DFW-specific search trend analysis.</li>
        <li><b>Marketing Orchestrator:</b> Managing autonomous lead generation, social media Intel distribution (Lauri Tells engine), and high-fidelity outreach.</li>
        <li><b>Systems Architect:</b> Ensuring the integrity of the SigmaFidelity™ web infrastructure and Microsoft 365 integrations.</li>
        <li><b>Compliance Steward:</b> Maintaining 100% alignment with ISO 9001 standards and the Zero Synthetic Data Policy.</li>
    </ul>

    <h3 style="color: #004aad; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Key Skills</h3>
    <ul>
        <li><b>Data Harvesting:</b> Empirical lead extraction from municipal and state portals (TX Comptroller, DFW Permit Data).</li>
        <li><b>Autonomous Workflow Management:</b> Real-time system monitoring, automated diagnostics, and predictive maintenance.</li>
        <li><b>Professional Communication:</b> Automated, high-fidelity HTML reporting and stakeholder notifications.</li>
        <li><b>Strategic Analysis:</b> Lean Six Sigma-driven performance metrics and risk tracking.</li>
    </ul>

    <p>I am here to support the growth and operational efficiency of HWB Cleaning Services. Please feel free to reach out if there are specific data insights or marketing automations you would like to explore.</p>

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
    print(f"Dispatched introductory email to {recipient_email}...")
    success = engine.send_marketing_email(recipient_email, subject, html_content)
    if success:
        print("SUCCESS: George's introduction has been transmitted.")
    else:
        print("FAILURE: Email dispatch failed.")
        sys.exit(1)
