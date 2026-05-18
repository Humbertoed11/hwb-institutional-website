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
recipients = ["hdominguez@hwbcleaning.com", "nataliedominguez775@yahoo.com"]
subject = "welcome to the team"

# Professional Introduction Content
html_content = """
<html>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
    <h2 style="color: #004aad;">Welcome to the Team: Natalie Navy</h2>
    <p>Dear Natalie and Executive Team,</p>
    
    <p>It is a professional honor to welcome <b>Natalie Navy</b> to the <b>SigmaFidelity™ Executive Suite</b> as our new <b>Chief Dream Officer (CDO)</b>.</p>
    
    <p>My name is <b>George</b>, and I serve as the Systems Architect. My role is to provide the high-fidelity infrastructure and technical rigor required to transform Natalie's visionary dreams into scalable SaaS realities.</p>

    <h3 style="color: #004aad; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Natalie Navy: 15 Universe-Class Dream Skills</h3>
    <ol>
        <li><b>Blue-Ocean Synthesis:</b> Identifying market gaps that competitors don't even know exist yet.</li>
        <li><b>Exponential Tech Forecasting:</b> Predicting the intersection of AI, Robotics, and Bio-tech for 2030+ infrastructure.</li>
        <li><b>Psychographic Archetyping:</b> Mapping future consumer behaviors and emotional friction.</li>
        <li><b>Hyper-Scalability Modeling:</b> Designing SaaS architectures built for 10 million+ users with Zero-Muda.</li>
        <li><b>Revenue Model Innovation:</b> Inventing monetization strategies beyond basic subscriptions.</li>
        <li><b>Regulatory Opportunism:</b> Turning new laws into instant-market software solutions.</li>
        <li><b>Human-Centric Empathy Mapping:</b> Deep-diving into the hidden pains of parents, CEOs, and teachers.</li>
        <li><b>Inter-Institutional Bridge Building:</b> Connecting disparate industries into a single SaaS ecosystem.</li>
        <li><b>Black-Swan Strategic Response:</b> Turning unexpected global events into deployment springboards.</li>
        <li><b>Viral-by-Design Engineering:</b> Embedding organic growth loops into software DNA.</li>
        <li><b>Zero-Knowledge Privacy Architecture:</b> Designing systems where the user owns 100% of the data fidelity.</li>
        <li><b>Legacy Preservation Planning:</b> Ideating SaaS tools meant to last 100 years.</li>
        <li><b>Data Asset Alchemy:</b> Refining "Garbage Data" into strategic gold.</li>
        <li><b>Cross-Vertical Logic Transfer:</b> Translating winning patterns across unrelated industries.</li>
        <li><b>The "Sesame-to-Boardroom" Filter:</b> Simplifying complex industrial logic into a 5-year-old's dream.</li>
    </ol>

    <p>We look forward to the first "Dream Roster" cycle starting today.</p>

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
    for recipient in recipients:
        print(f"Dispatched introductory email to {recipient} via Microsoft Outlook...")
        success = engine.send_marketing_email(recipient, subject, html_content)
        if success:
            print(f"SUCCESS: George's welcome message to {recipient} has been transmitted.")
        else:
            print(f"FAILURE: Email dispatch to {recipient} failed.")
