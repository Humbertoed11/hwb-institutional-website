import os
import requests
import msal
import sqlite3
from datetime import datetime
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

# Execute the send
engine = marketing_module.MicrosoftMarketingEngine()
success = engine.send_marketing_email("hdominguez@hwbcleaning.com", "test", "this is a tes of the system")

if success:
    print("SUCCESS: Test email dispatched via Microsoft Graph.")
else:
    print("FAILURE: Email dispatch failed.")
    sys.exit(1)
