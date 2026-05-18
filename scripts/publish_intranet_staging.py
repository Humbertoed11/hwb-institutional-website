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

def publish_staging_page():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Page Metadata based on HWB-QMS-IT-008
    page_data = {
        "name": "SigmaFidelity-Portal-Staging.aspx",
        "title": "SigmaFidelity™ Portal Staging",
        "description": "Staging area for the new HWB Corporate Intranet.",
        "pageLayout": "article", # Standard layout for most modular pages
        "promotionKind": "page"
    }
    
    print("Initiating creation of SigmaFidelity™ Portal Staging page...")
    # Endpoint for creating a modern site page
    url = f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/pages"
    
    res = requests.post(url, headers=headers, json=page_data)
    
    if res.status_code in [201, 200]:
        page_url = res.json().get("webUrl")
        page_id = res.json().get("id")
        print(f"SUCCESS: Staging page created with ID: {page_id}")
        print(f"URL: {page_url}")
        
        # Note: Adding specific webparts (Hero, News, etc.) via Graph API 
        # often requires the 'beta' endpoint or complex canvasLayout JSON.
        # George recommends initializing the skeleton here and letting 
        # the CEO finalize visual placement in the UI.
        
        print("\n--- Next Steps for CEO ---")
        print(f"1. Navigate to: {page_url}")
        print("2. Click 'Edit' in the top right.")
        print("3. Add the 'Hero' web part at the top.")
        print("4. Add a three-column section below for 'Quick Links', 'News', and 'Document Library'.")
        print("5. Click 'Publish' to make it live.")
    else:
        print(f"FAILURE: Page creation failed. Status {res.status_code} - {res.text}")

if __name__ == "__main__":
    publish_staging_page()
