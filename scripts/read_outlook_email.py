import os
import requests
import msal
import json
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
TENANT_ID = "f4e215a9-e3b4-4c0f-8ce8-9413a96d3646"  # Using provided Tenant ID
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_access_token():
    """Retrieves an OAuth2 access token via client credentials flow."""
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )
    # Using client credentials flow (App permissions)
    result = app.acquire_token_for_client(scopes=SCOPE)
    
    if "access_token" in result:
        return result["access_token"]
    else:
        # Check for specific error details
        error_msg = result.get('error_description', result.get('error', 'Unknown Error'))
        raise Exception(f"Failed to obtain access token: {error_msg}")

def get_latest_email(user_email):
    """Fetches the latest email and outputs it as JSON."""
    try:
        token = get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Pull latest message
        endpoint = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages?$top=1&$select=id,subject,from,receivedDateTime,bodyPreview"
        
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            messages = response.json().get('value', [])
            if messages:
                # Output as clean JSON for piping
                print(json.dumps(messages[0], indent=2))
            else:
                print(json.dumps({"error": "No messages found"}))
        else:
            print(json.dumps({"error": f"API Error {response.status_code}", "details": response.text}))
            
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    # Target the primary user for hwbcleaning.com
    get_latest_email("humbertoed@hwbcleaning.com")
