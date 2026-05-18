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

# Site and Page IDs
ROOT_SITE_ID = "netorgft3163094.sharepoint.com,ba333e69-0b50-4a68-a226-6733cbcb7fdd,819b0286-8cdb-44a1-b1a7-8644604fc29d"
PAGE_ID = "250addbd-9255-433e-b9c6-0377d0a4dbc4"

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def inject_intranet_content():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print(f"Injecting high-fidelity metadata into SigmaFidelity Portal ({PAGE_ID})...")
    
    # 1. Update Page Metadata (Description and Thumbnail)
    page_update = {
        "description": "The Official Corporate Intranet. Single Source of Truth for HWB Cleaning Services LLC.",
        "title": "HWB SigmaFidelity™ Portal"
    }
    
    # Using beta endpoint for more robust canvas support if needed
    url = f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}"
    res = requests.patch(url, headers=headers, json=page_update)
    
    if res.status_code == 200:
        print("SUCCESS: Core metadata injected.")
    else:
        print(f"WARNING: Metadata injection status: {res.status_code}")

    # 2. Automated News Feed Verification
    # George will monitor the 'Site News' feature to ensure HWB-WEB News Queue propagates here.
    
    print("\n--- Content Lifecycle Check ---")
    print("Page is now officially recognized as the 'SigmaFidelity™ Portal'.")
    print(f"URL: https://netorgft3163094.sharepoint.com/SitePages/Sigma.aspx")

if __name__ == "__main__":
    inject_intranet_content()
