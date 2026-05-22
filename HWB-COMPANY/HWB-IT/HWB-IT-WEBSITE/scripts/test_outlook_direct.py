import os
import requests
import msal
from dotenv import load_dotenv

load_dotenv()

def test_outlook_connectivity():
    print("--- SigmaFidelity: Outlook Email Connectivity Test ---")
    
    cid = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
    secret = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
    tid = os.getenv("GRAPH_API_PROD_TENANT_ID")
    
    authority = f"https://login.microsoftonline.com/{tid}"
    app = msal.ConfidentialClientApplication(cid, authority=authority, client_credential=secret)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" not in result:
        print(f"FAILURE: Could not acquire token. {result.get('error_description')}")
        return

    token = result["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test reading mail for a specific user
    user_email = "humbertoed@hwbcleaning.com"
    print(f"Testing mail access for {user_email}...")
    res = requests.get(f"https://graph.microsoft.com/v1.0/users/{user_email}/messages?$top=1", headers=headers)
    
    if res.status_code == 200:
        messages = res.json().get('value', [])
        if messages:
            print(f"SUCCESS: Connected to Outlook. Latest Subject: {messages[0]['subject']}")
        else:
            print("SUCCESS: Connected to Outlook, but no messages found.")
    else:
        print(f"FAILURE: {res.status_code} - {res.text}")

if __name__ == "__main__":
    test_outlook_connectivity()
