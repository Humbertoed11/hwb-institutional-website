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
LOGO_URL = "https://netorgft3163094.sharepoint.com/Shared%20Documents/hwb-cleaning-services-llc-logo-plano-tx.png"

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def perform_branding_and_audit():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print("--- Institutional Branding Phase ---")
    
    # 1. Attempt to set Site Identity via Beta (More flexible)
    site_update = {
        "displayName": "HWB SigmaFidelity™ Portal",
        "description": "Official Corporate Intranet. The Single Source of Truth."
    }
    res_site = requests.patch(f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}", headers=headers, json=site_update)
    print(f"Site Identity Update Status: {res_site.status_code}")

    # 2. Visual Audit: Inspecting Page Layout
    print("\n--- Visual Audit Phase (Logic Verification) ---")
    res_page = requests.get(f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}", headers=headers)
    
    if res_page.status_code == 200:
        page_data = res_page.json()
        print(f"Page Title: {page_data.get('title')}")
        print(f"Publishing Level: {page_data.get('publishingState', {}).get('level')}")
        
        # Checking for existing webparts via Beta (CanvasLayout)
        res_layout = requests.get(f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}/canvasLayout", headers=headers)
        if res_layout.status_code == 200:
            layout = res_layout.json()
            sections = layout.get('horizontalSections', [])
            print(f"Detected {len(sections)} page sections.")
            # Audit of specific webparts would go here
        else:
            print("INFO: Visual layout is currently in the default skeleton state.")
    else:
        print(f"FAILURE: Could not audit page. Status {res_page.status_code}")

if __name__ == "__main__":
    perform_branding_and_audit()
