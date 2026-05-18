import os
import pickle
import google_auth_oauthlib.flow
from dotenv import load_dotenv

load_dotenv()

CLIENT_SECRET_FILE = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/client_secret_1012258935790-58ds1o5q6t0pn72pu09fvu584jqs4nuh.apps.googleusercontent.com.json"
VERIFIER_FILE = "scripts/youtube_verifier.txt"
TOKEN_PICKLE_FILE = "scripts/youtube_token.pickle"
SCOPES = ['https://www.googleapis.com/auth/youtube']

# URL provided by the CEO
REDIRECT_URL = "http://localhost/?state=UtQJRExDKSU5UNggZcMVKx2xkORivb&iss=https://accounts.google.com&code=4/0AfrIepC6m4kYV3mHxbEbIQr78M0QuZFCnQaujYV-bkZh4Vuo4vfi0orelJNBQef5Qf-dVg&scope=https://www.googleapis.com/auth/youtube"

def finalize_phase_2():
    print("--- SigmaFidelity: YouTube Headless Handshake (Phase II) ---")
    
    # 1. Load the verifier
    if not os.path.exists(VERIFIER_FILE):
        print("FAILURE: Verifier file missing. Run Phase I again.")
        return
    with open(VERIFIER_FILE, 'r') as f:
        code_verifier = f.read().strip()

    # 2. Re-initialize flow
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE, SCOPES, code_verifier=code_verifier)
    flow.redirect_uri = "http://localhost"
    
    # 3. Fetch Token
    try:
        # Enable insecure transport for localhost
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        flow.fetch_token(authorization_response=REDIRECT_URL)
        creds = flow.credentials
        
        # 4. Archive the persistent token
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)
            print(f"SUCCESS: Institutional YouTube token archived at {TOKEN_PICKLE_FILE}")
            
        # Cleanup verifier
        os.remove(VERIFIER_FILE)
            
    except Exception as e:
        print(f"FAILURE: Handshake failed. {str(e)}")

if __name__ == "__main__":
    finalize_phase_2()
