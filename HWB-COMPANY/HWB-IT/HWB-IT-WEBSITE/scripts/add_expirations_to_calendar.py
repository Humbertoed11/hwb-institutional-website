import os
from datetime import datetime, timedelta
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

# Expiration Dates to track
expirations = [
    {"date": "2026-04-08", "subject": "Azure Free Offer Expiration", "desc": "Verification of Azure free offer status and credit availability."},
    {"date": "2026-07-31", "subject": "FAA DroneZone Expiration (HWB-DRONE-001)", "desc": "Renewal requirement for drone registration/certification."},
    {"date": "2027-03-02", "subject": "SigmaFidelity™ (George) Secret Rotation", "desc": "Mandatory rotation of Microsoft Graph Client Secret per HWB-QMS-9.5."},
    {"date": "2027-09-30", "subject": "FAA DroneZone Expiration (HWB-DRONE-002)", "desc": "Renewal requirement for drone registration/certification."},
    {"date": "2027-10-31", "subject": "FAA DroneZone Expiration (HWB-DRONE-003)", "desc": "Renewal requirement for drone registration/certification."}
]

def create_events():
    for exp in expirations:
        exp_date = datetime.strptime(exp["date"], "%Y-%m-%d")
        
        # 1. Day of Expiration Event (9:00 AM - 10:00 AM)
        start_day = exp_date.replace(hour=9, minute=0).isoformat()
        end_day = exp_date.replace(hour=10, minute=0).isoformat()
        
        print(f"Scheduling Day-of event for: {exp['subject']}...")
        engine.create_calendar_event(
            subject=f"CRITICAL: {exp['subject']}",
            start_time=start_day,
            end_time=end_day,
            body=f"<p><b>System Alert:</b> {exp['desc']}</p><p>Fidelity. Safety. Respect.</p>"
        )

        # 2. One Week Warning (9:00 AM - 9:30 AM)
        warning_date = exp_date - timedelta(days=7)
        start_warn = warning_date.replace(hour=9, minute=0).isoformat()
        end_warn = warning_date.replace(hour=9, minute=30).isoformat()

        print(f"Scheduling Warning event for: {exp['subject']} (7-day lead time)...")
        engine.create_calendar_event(
            subject=f"WARNING: {exp['subject']} (7 Days Remaining)",
            start_time=start_warn,
            end_time=end_warn,
            body=f"<p><b>Lead Time Alert:</b> The {exp['subject']} is due in 7 days.</p><p>{exp['desc']}</p>"
        )

if __name__ == "__main__":
    create_events()
