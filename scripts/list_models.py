import os
import requests
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.getcwd(), '.env')
load_dotenv(dotenv_path)

api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    print("Error: No API key found in .env")
    exit(1)

# Endpoint for listing models
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        models = response.json()
        for model in models.get('models', []):
            print(f"{model['name']} - {model['description']}")
    else:
        print(f"Error Listing Models: {response.status_code}")
        print(f"DEBUG: {response.text}")
except Exception as e:
    print(f"Exception: {str(e)}")
