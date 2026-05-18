import os
import pickle
import google_auth_oauthlib.flow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

# Institutional Paths
CLIENT_SECRET_FILE = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/client_secret_1012258935790-58ds1o5q6t0pn72pu09fvu584jqs4nuh.apps.googleusercontent.com.json"
TOKEN_PICKLE_FILE = "scripts/youtube_token.pickle"

# Mandatory Scopes
SCOPES = ['https://www.googleapis.com/auth/youtube']

def generate_verified_url():
    print("--- SigmaFidelity: YouTube URL Verification ---")
    
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE, SCOPES)
    
    # Explicitly set the redirect_uri to match the JSON exactly
    flow.redirect_uri = "http://localhost"
    
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    
    print("\nACTION REQUIRED: Copy this VERIFIED URL into your browser:")
    print(f"\n{auth_url}\n")
    
    print("1. Log in as hwbclean@gmail.com.")
    print("2. Grant permissions.")
    print("3. Copy the resulting 'localhost' URL from the address bar and provide it here.")

if __name__ == "__main__":
    generate_verified_url()
