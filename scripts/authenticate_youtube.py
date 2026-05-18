import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

# Institutional Path for the Client Secret
CLIENT_SECRET_FILE = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/client_secret_711349909963-q8n4726cpjmn7mfodjd7v66hpst3v1ae.apps.googleusercontent.com.json"
TOKEN_PICKLE_FILE = "scripts/youtube_token.pickle"

# Mandatory Scopes for full metadata management
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

def authenticate_youtube():
    creds = None
    # Check for existing institutional token
    if os.path.exists(TOKEN_PICKLE_FILE):
        with open(TOKEN_PICKLE_FILE, 'rb') as token:
            creds = pickle.load(token)
            
    # If no valid credentials, initiate handshake
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing institutional YouTube token...")
            creds.refresh(Request())
        else:
            print("Initiating new YouTube OAuth2 handshake...")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            # Using a fixed port for consistency
            creds = flow.run_local_server(port=8080, prompt='consent')
            
        # Securely store the token for automated reuse
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)
            print(f"SUCCESS: Institutional YouTube token archived at {TOKEN_PICKLE_FILE}")

    return creds

if __name__ == "__main__":
    authenticate_youtube()
