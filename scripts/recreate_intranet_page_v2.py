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

# Root Site ID
ROOT_SITE_ID = "netorgft3163094.sharepoint.com,ba333e69-0b50-4a68-a226-6733cbcb7fdd,819b0286-8cdb-44a1-b1a7-8644604fc29d"

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def recreate_page():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Use the beta endpoint for site pages
    page_data = {
        "title": "HWB SigmaFidelity™ Portal",
        "name": "SigmaFidelity-Portal.aspx",
        "description": "The Official Corporate Intranet. Single Source of Truth.",
        "pageLayout": "article"
    }
    
    print("Creating the Portal page via Beta endpoint...")
    # Creating a new page on the beta endpoint
    res = requests.post(f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}/pages", headers=headers, json=page_data)
    
    if res.status_code in [201, 200]:
        new_page = res.json()
        print(f"SUCCESS: Portal page created.")
        print(f"URL: {new_page['webUrl']}")
        
        # Immediate attempt to discard checkout/publish to make it visible
        page_id = new_page['id']
        print(f"Publishing page {page_id}...")
        requests.post(f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}/pages/{page_id}/publish", headers=headers)
        
    else:
        print(f"FAILURE: Status {res.status_code} - {res.text}")

if __name__ == "__main__":
    recreate_page()
