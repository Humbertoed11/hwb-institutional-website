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

# The redirected URL provided by the CEO
REDIRECTED_URL = "http://localhost/state=1RMWZ9g38DtgZcTI6NpFLEtBAisFFn&iss=https://accounts.google.com&code=4/0AfrIepARgA6ylta1Vh-nfiLmb3tKvWze9huDoXZZLl_9kEAo7-2fWwydFoIkCg6kXeDMdA&scope=https://www.googleapis.com/auth/youtube"

def finalize_auth():
    print("--- SigmaFidelity: YouTube Final Handshake ---")
    
    # Enable insecure transport for localhost finalization
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    # Re-initialize the flow with the exact same parameters
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE, SCOPES)
    flow.redirect_uri = "http://localhost"
    
    try:
        # Note: We manually perform the fetch_token using the code in the URL
        # We need to ensure the state matches the one used in the generation
        flow.fetch_token(authorization_response=REDIRECTED_URL)
        creds = flow.credentials
        
        # Archive the persistent token
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)
            print(f"SUCCESS: Institutional YouTube token archived at {TOKEN_PICKLE_FILE}")
            
    except Exception as e:
        print(f"FAILURE: Handshake finalization failed. {str(e)}")

if __name__ == "__main__":
    finalize_auth()
