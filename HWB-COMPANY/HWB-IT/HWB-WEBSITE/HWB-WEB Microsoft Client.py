import os
import requests
import msal
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
# TENANT_ID = os.getenv("MS_TENANT_ID")
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_access_token():
    """Retrieves an OAuth2 access token via client credentials flow."""
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )
    result = app.acquire_token_silent(SCOPE, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=SCOPE)
    
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Failed to obtain access token: {result.get('error_description')}")

def send_test_email(recipient):
    """Sends a test email via Microsoft Graph API to verify connectivity."""
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    email_data = {
        "message": {
            "subject": "SigmaFidelity™ Integration Test",
            "body": {
                "contentType": "Text",
                "content": "George has successfully connected to Microsoft 365. Veritas Fidelity."
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": recipient
                    }
                }
            ]
        },
        "saveToSentItems": "true"
    }
    
    # Note: Requires a specific user ID or UPN to send 'from'. 
    # For app-only, we usually specify the user's ID.
    endpoint = f"https://graph.microsoft.com/v1.0/users/humbertoed@hwbcleaning.com/sendMail"
    
    response = requests.post(endpoint, headers=headers, json=email_data)
    if response.status_code == 202:
        print("Test email sent successfully.")
    else:
        print(f"Failed to send email: {response.status_code} - {response.text}")

if __name__ == "__main__":
    try:
        token = get_access_token()
        print("SUCCESS: George is connected to Microsoft 365. Access Token retrieved.")
        # send_test_email("humbertoed@hwbcleaning.com")
    except Exception as e:
        print(f"ERROR: {e}")
