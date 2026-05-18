import os
import requests
import msal
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def list_users():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Listing all users in directory to find exact UPN...")
    res = requests.get("https://graph.microsoft.com/v1.0/users?$select=displayName,userPrincipalName,id", headers=headers)
    
    if res.status_code == 200:
        users = res.json().get("value", [])
        for u in users:
            print(f"- {u['displayName']} | UPN: {u['userPrincipalName']} | ID: {u['id']}")
    else:
        print(f"FAILURE: Could not list users. Status {res.status_code} - {res.text}")

if __name__ == "__main__":
    list_users()
