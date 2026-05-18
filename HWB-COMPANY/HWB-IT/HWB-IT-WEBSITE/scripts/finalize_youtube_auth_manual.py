import os
import pickle
import google_auth_oauthlib.flow
from dotenv import load_dotenv

load_dotenv()

# Institutional Paths
CLIENT_SECRET_FILE = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/client_secret_1012258935790-58ds1o5q6t0pn72pu09fvu584jqs4nuh.apps.googleusercontent.com.json"
TOKEN_PICKLE_FILE = "scripts/youtube_token.pickle"

# Mandatory Scopes
SCOPES = ['https://www.googleapis.com/auth/youtube']

# The manual code extracted from the URL
AUTH_CODE = "4/0AfrIepARgA6ylta1Vh-nfiLmb3tKvWze9huDoXZZLl_9kEAo7-2fWwydFoIkCg6kXeDMdA"

def finalize_manual():
    print("--- SigmaFidelity: YouTube Manual Code Finalization ---")
    
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE, SCOPES)
    flow.redirect_uri = "http://localhost"
    
    try:
        # Use fetch_token with the manual code
        flow.fetch_token(code=AUTH_CODE)
        creds = flow.credentials
        
        # Archive the token
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)
            print(f"SUCCESS: Institutional YouTube token archived at {TOKEN_PICKLE_FILE}")
            
    except Exception as e:
        print(f"FAILURE: Handshake failed. {str(e)}")

if __name__ == "__main__":
    finalize_manual()
