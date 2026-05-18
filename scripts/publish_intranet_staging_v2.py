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
    
    # Use the beta endpoint for better modern page support if v1.0 fails
    page_data = {
        "@odata.type": "#microsoft.graph.sitePage",
        "name": "SigmaFidelity-Portal-Staging.aspx",
        "title": "SigmaFidelity™ Portal Staging",
        "description": "Staging area for the new HWB Corporate Intranet.",
        "pageLayout": "article"
    }
    
    print("Initiating creation of SigmaFidelity™ Portal Staging page (v2)...")
    url = f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/pages"
    
    res = requests.post(url, headers=headers, json=page_data)
    
    if res.status_code in [201, 200]:
        page_url = res.json().get("webUrl")
        print(f"SUCCESS: Staging page created.")
        print(f"URL: {page_url}")
    else:
        # Try Beta endpoint as fallback
        print(f"v1.0 failed ({res.status_code}). Attempting Beta endpoint...")
        beta_url = f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}/pages"
        res_beta = requests.post(beta_url, headers=headers, json=page_data)
        if res_beta.status_code in [201, 200]:
            print(f"SUCCESS (Beta): Staging page created.")
            print(f"URL: {res_beta.json().get('webUrl')}")
        else:
            print(f"FAILURE: Page creation failed. Status {res_beta.status_code} - {res_beta.text}")

if __name__ == "__main__":
    publish_staging_page()
