import os
import google_auth_oauthlib.flow
from dotenv import load_dotenv

load_dotenv()

CLIENT_SECRET_FILE = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/client_secret_1012258935790-58ds1o5q6t0pn72pu09fvu584jqs4nuh.apps.googleusercontent.com.json"
VERIFIER_FILE = "scripts/youtube_verifier.txt"
SCOPES = ['https://www.googleapis.com/auth/youtube']

def generate_url():
    print("--- SigmaFidelity: YouTube Headless Handshake (Phase I) ---")
    
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE, SCOPES)
    flow.redirect_uri = "http://localhost"
    
    # Generate URL and capture the code verifier
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    code_verifier = flow.code_verifier
    
    # Save only the verifier string
    with open(VERIFIER_FILE, 'w') as f:
        f.write(code_verifier)
    
    print("\n1. ACTION REQUIRED: Copy this URL into your browser:")
    print(f"\n{auth_url}\n")
    print("2. Log in as hwbclean@gmail.com and grant permissions.")
    print("3. After the 'Connection Refused' error, COPY the full URL from the address bar.")
    print("4. Provide that full URL to me.")

if __name__ == "__main__":
    generate_url()
