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

def run_v3_handshake():
    print("--- SigmaFidelity: YouTube Handshake v3 (Local Server) ---")
    
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE, SCOPES)
    
    # run_local_server handles the code_verifier and code_challenge automatically
    # It will print the URL since it cannot open the browser
    creds = flow.run_local_server(port=8080, prompt='consent', access_type='offline', open_browser=False)
    
    # Archive the persistent token
    with open(TOKEN_PICKLE_FILE, 'wb') as token:
        pickle.dump(creds, token)
        print(f"\nSUCCESS: Institutional YouTube token archived at {TOKEN_PICKLE_FILE}")

if __name__ == "__main__":
    run_v3_handshake()
