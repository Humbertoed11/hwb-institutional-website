import os
import requests
import json
import base64
from dotenv import load_dotenv

# SigmaFidelity™ Institutional Image Generator
# Version 1.0.0 (George / VP Systems Architecture)

# 1. Load Environment
load_dotenv('.env')
API_KEY = os.getenv('GEMINI_API_KEY')
STAGING_DIR = 'HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/gen_ai_staging'

if not API_KEY:
    print("CRITICAL ERROR: GEMINI_API_KEY not found in root .env file.")
    exit(1)

if not os.path.exists(STAGING_DIR):
    os.makedirs(STAGING_DIR)

# 2. Master Prompt (from HWB-LEG-002 Registry)
MASTER_PROMPT = """A professional, high-resolution website hero illustration of a warm and welcoming daycare lobby. 
In the center, an office director—dressed in a crisp, business-casual suit—stands calmly and with a humbling presence, 
holding a mop as if ready for a natural part of their evening routine. On the wall, a clock clearly points to 5:00 PM. 
In the soft-focus background, parents are seen checking out their children, creating a scene of daily transition. 
The lighting is golden and soft, reflecting a spirit of servant leadership rather than one of burden. 
Minimalist 5S organizational outlines are subtly visible on a nearby shelf, hinting at the modified job culture in a quiet, 
non-accusatory way. Wide 16:9 cinematic composition."""

# 3. API Execution
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={API_KEY}"

payload = {
    "contents": [
        {
            "parts": [
                {"text": MASTER_PROMPT}
            ]
        }
    ]
}

print("--- Initiating SigmaFidelity™ Image Generation Cycle ---")
print(f"Target: {STAGING_DIR}/HWB-WEB-Daycare-Hero.png")

try:
    response = requests.post(URL, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        # The response for generateContent with image output is usually in data['candidates'][0]['content']['parts'][0]['inlineData']
        # However, for specialized image generation models, it might differ.
        print("✅ SUCCESS: API responded. Analyzing image data...")
        print(json.dumps(data, indent=2)[:500] + "...") # Preview structure
    else:
        print(f"❌ API FAILURE (Status {response.status_code}):")
        print(response.text)

except Exception as e:
    print(f"❌ SYSTEM EXCEPTION: {str(e)}")
