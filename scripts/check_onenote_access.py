import os
import requests
import msal
from dotenv import load_dotenv

load_dotenv()

def check_onenote_access():
    cid = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
    secret = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
    tid = os.getenv("GRAPH_API_PROD_TENANT_ID")
    
    authority = f"https://login.microsoftonline.com/{tid}"
    app = msal.ConfidentialClientApplication(cid, authority=authority, client_credential=secret)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        token = result["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to list notebooks
        endpoint = "https://graph.microsoft.com/v1.0/users/humbertoed@hwbcleaning.com/onenote/notebooks"
        response = requests.get(endpoint, headers=headers)
        
        if response.status_code == 200:
            print("SUCCESS: OneNote notebooks listed!")
            notebooks = response.json().get('value', [])
            for nb in notebooks:
                print(f"- {nb['displayName']} (ID: {nb['id']})")
        else:
            print(f"FAILURE on OneNote: {response.status_code} - {response.text}")
            
    else:
        print(f"FAILED to acquire token: {result.get('error_description')}")

if __name__ == "__main__":
    check_onenote_access()
