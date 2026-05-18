import os
import sys
from dotenv import load_dotenv
import importlib.util

# Load Institutional Secrets (HWB-QMS-9.5)
load_dotenv()

# Institutional path for the marketing engine
engine_path = os.path.join("scripts", "HWB-WEB Microsoft Marketing Engine.py")

# Standard import logic
spec = importlib.util.spec_from_file_location("MarketingEngine", engine_path)
marketing_module = importlib.util.module_from_spec(spec)
sys.modules["MarketingEngine"] = marketing_module
spec.loader.exec_module(marketing_module)

# Initialize the engine
engine = marketing_module.MicrosoftMarketingEngine()

# Event Details
subject = "WOMEN-OWNED BUSINESS EXPO | EXPO MUJER 2026"
start_time = "2026-03-28T11:00:00"
end_time = "2026-03-28T16:00:00"
location = "The Epic Rec, 2960 Epic Place, Grand Prairie, TX 75052"
body = """
<p><b>Event:</b> WOMEN-OWNED BUSINESS EXPO | EXPO MUJER 2026</p>
<p><b>Location:</b> The Epic Rec, 2960 Epic Place, Grand Prairie, TX 75052</p>
<p>An empowering community event celebrating women-owned businesses. The expo showcases local talent, creativity, and innovation, offering attendees the opportunity to shop local, discover new businesses, and network with entrepreneurs.</p>
<p><b>Fidelity. Community. Support.</b></p>
"""

if __name__ == "__main__":
    print(f"Creating calendar event: {subject}...")
    # subject, start_time, end_time, attendees=None, body=""
    success = engine.create_calendar_event(subject, start_time, end_time, body=body)
    if success:
        print("SUCCESS: Event has been added to the institutional Outlook calendar.")
    else:
        print("FAILURE: Calendar event creation failed.")
