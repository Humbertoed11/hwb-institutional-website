import os
import requests
import msal
from dotenv import load_dotenv

load_dotenv()

def check_sharepoint_access():
    cid = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
    secret = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
    tid = os.getenv("GRAPH_API_PROD_TENANT_ID")
    
    authority = f"https://login.microsoftonline.com/{tid}"
    app = msal.ConfidentialClientApplication(cid, authority=authority, client_credential=secret)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        token = result["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to list root site
        endpoint = "https://graph.microsoft.com/v1.0/sites/root"
        response = requests.get(endpoint, headers=headers)
        
        if response.status_code == 200:
            print("SUCCESS: SharePoint Root Site accessed!")
            site = response.json()
            print(f"- Site Name: {site.get('displayName')}")
            print(f"- Site URL: {site.get('webUrl')}")
        else:
            print(f"FAILURE on SharePoint: {response.status_code} - {response.text}")
            
    else:
        print(f"FAILED to acquire token: {result.get('error_description')}")

if __name__ == "__main__":
    check_sharepoint_access()
