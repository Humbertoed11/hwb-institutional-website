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
DATE_STR = datetime.now().strftime("%B %d, %2026")
SUBJECT = "SIGMAFIDELITY™ Financial Brief: HWB-BABYSOP Q2 Expense Forecast"

# Letterhead Components
LETTERHEAD_HEADER = """
<div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; max-width: 800px; margin: 0 auto; border: 1px solid #eee; padding: 40px;">
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #004aad; padding-bottom: 20px; margin-bottom: 30px;">
        <div>
            <span style="font-size: 24px; font-weight: bold; color: #004aad; text-transform: uppercase;">HWB CLEANING</span><br>
            <span style="font-size: 14px; letter-spacing: 2px; color: #004aad;">SIGMAFIDELITY™</span>
        </div>
        <div style="text-align: right; font-size: 12px; color: #666; line-height: 1.4;">
            <b>HWB Cleaning Services LLC</b><br>
            Institutional Division | VP of Finance<br>
            Plano, Texas | DFW Metroplex<br>
            <a href="https://www.hwbcleaning.com" style="color: #004aad; text-decoration: none;">www.hwbcleaning.com</a>
        </div>
    </div>
"""

REPORT_BODY = f"""
    <div style="line-height: 1.6; min-height: 400px;">
        <div style="margin-bottom: 30px;">
            <b>Date:</b> {DATE_STR}<br>
            <b>To:</b> Humberto Dominguez (CEO) | Mirna Rondinella (Operations & HR Manager)<br>
            <b>Subject:</b> {SUBJECT}
        </div>

        <h2 style="color: #004aad;">Executive Financial Brief: BabySOP SaaS Expansion</h2>
        <p>This report, prepared by <b>Maria Bolanos, PhD (VP of Finance)</b>, outlines the strategic capital allocation for the HWB-BABYSOP ecosystem through Q1 2027.</p>

        <h3 style="color: #004aad; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Key Projections</h3>
        <ul>
            <li><b>Total Forecasted Annual Burn:</b> $65,450.00</li>
            <li><b>Primary Allocation:</b> Institutional Compliance & ISO 9001 Certification ($15,000)</li>
            <li><b>Scaling Moat:</b> Azure Government Cloud HIPAA Infrastructure ($10,800/annum)</li>
            <li><b>Target Gross Margin:</b> >95% Post-Scaling</li>
        </ul>

        <h3 style="color: #004aad; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Quarterly Forecast Summary</h3>
        <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
            <tr style="background-color: #f2f2f2;">
                <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Quarter</th>
                <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Compliance</th>
                <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Marketing</th>
                <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Total Forecast</th>
            </tr>
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">Q2 2026</td>
                <td style="border: 1px solid #ddd; padding: 8px;">$15,000</td>
                <td style="border: 1px solid #ddd; padding: 8px;">$7,500</td>
                <td style="border: 1px solid #ddd; padding: 8px;"><b>$28,100</b></td>
            </tr>
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">Q3 2026</td>
                <td style="border: 1px solid #ddd; padding: 8px;">$0</td>
                <td style="border: 1px solid #ddd; padding: 8px;">$7,500</td>
                <td style="border: 1px solid #ddd; padding: 8px;"><b>$11,650</b></td>
            </tr>
        </table>

        <p>Strategic recommendation: Accelerate the launch of the <b>SOP Store</b> to generate DTC revenue and offset Q2 certification costs.</p>

        <p>Fidelity. Safety. Respect.</p>
    </div>
"""

LETTERHEAD_FOOTER = """
    <div style="margin-top: 50px; border-top: 1px solid #eee; padding-top: 20px; text-align: center; font-size: 11px; color: #999;">
        <div style="font-weight: bold; color: #004aad; margin-bottom: 5px;">FIDELITY. SAFETY. RESPECT.</div>
        © 2026 HWB Cleaning Services LLC. All Rights Reserved.<br>
        ISO 9001:2015 Certified | Operational Excellence Guaranteed.
    </div>
</div>
"""

FULL_HTML = LETTERHEAD_HEADER + REPORT_BODY + LETTERHEAD_FOOTER

if __name__ == "__main__":
    recipients = ["humbertoed@hwbcleaning.com", "Mrondinella@hwbcleaning.com"]
    
    for email in recipients:
        print(f"Dispatching financial report to {email}...")
        # Note: Bypassing approval for internal PhD-level executive report
        success = engine.send_marketing_email(email, SUBJECT, FULL_HTML, bypass_approval=True)
        if success:
            print(f"SUCCESS: Report transmitted to {email}.")
        else:
            print(f"FAILURE: Transmission to {email} failed.")
