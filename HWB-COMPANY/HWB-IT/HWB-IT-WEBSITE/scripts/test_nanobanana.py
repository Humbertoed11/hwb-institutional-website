import os
import requests
import base64
from dotenv import load_dotenv

# Load environment variables from root .env
dotenv_path = os.path.join(os.getcwd(), '.env')
load_dotenv(dotenv_path)

api_key = os.getenv('GEMINI_API_KEY')
print(f"Testing with GEMINI_API_KEY (Length: {len(api_key) if api_key else 'N/A'})")

if not api_key:
    print("Error: No API key found in .env")
    exit(1)

# Simple test prompt
prompt = "A simple yellow banana on a blue background, minimalist style."

# Gemini Image Generation API URL (example)
# Note: Actual URL depends on the specific model and API version
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateImages?key={api_key}"

headers = {
    "Content-Type": "application/json"
}

payload = {
    "prompts": [
        {
            "text": prompt
        }
    ],
    "image_generation_config": {
        "number_of_images": 1
    }
}

try:
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Successfully generated image data!")
        # We don't need to save it for a connectivity test
    else:
        print(f"Error Response: {response.text}")
except Exception as e:
    print(f"Exception during request: {str(e)}")
