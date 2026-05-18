import os
import pickle
import google_auth_oauthlib.flow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

# Fresh Institutional Path
CLIENT_SECRET_FILE = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/client_secret_1012258935790-58ds1o5q6t0pn72pu09fvu584jqs4nuh.apps.googleusercontent.com.json"
TOKEN_PICKLE_FILE = "scripts/youtube_token.pickle"

# Mandatory Scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

def run_fresh_handshake():
    print("--- SigmaFidelity: YouTube Handshake Restoration ---")
    
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE, SCOPES)
    
    # Generate the Authorization URL
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    
    print("\n1. ACTION REQUIRED: Copy and paste this URL into your browser:")
    print(f"\n{auth_url}\n")
    
    print("2. Log in as hwbclean@gmail.com and grant permissions.")
    print("3. Your browser will redirect to a 'localhost' URL. COPY THAT FULL URL.")
    
    redirected_url = input("\n4. PASTE THE FULL REDIRECTED URL HERE: ")
    
    # Extract the code and finalize
    try:
        flow.fetch_token(authorization_response=redirected_url)
        creds = flow.credentials
        
        # Archive the token
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)
            print(f"\nSUCCESS: Institutional YouTube token archived at {TOKEN_PICKLE_FILE}")
    except Exception as e:
        print(f"\nFAILURE: Handshake failed. {str(e)}")

if __name__ == "__main__":
    run_fresh_handshake()
