import os
import requests
import msal
from dotenv import load_dotenv

load_dotenv()

def check_permissions():
    cid = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
    secret = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
    tid = os.getenv("GRAPH_API_PROD_TENANT_ID")
    
    authority = f"https://login.microsoftonline.com/{tid}"
    app = msal.ConfidentialClientApplication(cid, authority=authority, client_credential=secret)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        token = result["access_token"]
        print("SUCCESS: Token acquired!")
        
        # Try a simple GET /users
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("https://graph.microsoft.com/v1.0/users?$top=1", headers=headers)
        if response.status_code == 200:
            print("SUCCESS: Can read users.")
            print(f"Sample User: {response.json()['value'][0]['userPrincipalName']}")
        else:
            print(f"FAILURE on /users: {response.status_code} - {response.text}")

        # Try /me (usually fails for client_credentials but worth checking)
        response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
        print(f"Result for /me: {response.status_code} - {response.text}")
        
    else:
        print(f"FAILED to acquire token: {result.get('error_description')}")

check_permissions()
