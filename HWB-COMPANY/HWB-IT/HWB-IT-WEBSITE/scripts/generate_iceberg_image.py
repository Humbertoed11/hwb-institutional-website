import os
import requests
import base64
from dotenv import load_dotenv
from datetime import datetime

# Load Institutional Secrets (HWB-QMS-9.5)
dotenv_path = os.path.join(os.getcwd(), '.env')
load_dotenv(dotenv_path)

api_key = os.getenv('GEMINI_API_KEY')
STAGING_ZONE = "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/gen_ai_staging/"

if not api_key:
    print("CRITICAL: No API key found in .env")
    exit(1)

if not os.path.exists(STAGING_ZONE):
    os.makedirs(STAGING_ZONE)

# Prompt for the LinkedIn Series
prompt = (
    "A high-fidelity, cinematic split-view iceberg in dark, professional ocean water. "
    "Above the waterline: a small, visible peak labeled 'Visible Cost Control'. "
    "Below the waterline: a massive, glowing blue underwater mountain labeled 'Systemic Waste' in bold, clean typography. "
    "Photorealistic, 8k, professional branding aesthetic, 16:9 aspect ratio."
)

# Endpoint for image generation (adjusting to the likely v1beta endpoint)
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateImages?key={api_key}"

headers = {
    "Content-Type": "application/json"
}

payload = {
    "prompts": [{"text": prompt}],
    "image_generation_config": {
        "number_of_images": 1,
        "aspect_ratio": "16:9"
    }
}

print(f"--- SigmaFidelity: Generating Strategic Asset [LinkedIn Series] ---")
try:
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        if 'images' in data and len(data['images']) > 0:
            image_data = data['images'][0]['image_binary']
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_iceberg_{timestamp}.png"
            filepath = os.path.join(STAGING_ZONE, filename)
            
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(image_data))
            
            print(f"SUCCESS: Image saved to {filepath}")
            print(f"RELATIVE_PATH: /static/gen_ai_staging/{filename}")
        else:
            print("FAILURE: No images returned in response.")
            print(f"DEBUG: {data}")
    else:
        print(f"FAILURE: Status {response.status_code}")
        print(f"DEBUG: {response.text}")
except Exception as e:
    print(f"CRITICAL ERROR: {str(e)}")
