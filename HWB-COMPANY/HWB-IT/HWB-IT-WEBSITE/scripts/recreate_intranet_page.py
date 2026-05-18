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
OLD_PAGE_ID = "fd86d2fb-dad3-44a1-b1a7-8644604fc29d"
CEO_USER_ID = "47df85a1-cc91-46b2-bd1c-9fdecdc801ab"

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def recreate_page():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Delete the stuck page
    print(f"Deleting stuck page {OLD_PAGE_ID}...")
    requests.delete(f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/pages/{OLD_PAGE_ID}", headers=headers)
    
    # 2. Re-create the page using the standard endpoint
    page_data = {
        "name": "SigmaFidelity-Portal.aspx",
        "title": "HWB SigmaFidelity™ Portal",
        "description": "The Official Corporate Intranet. Single Source of Truth.",
        "pageLayout": "article"
    }
    
    print("Re-creating the Portal page...")
    res = requests.post(f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/pages", headers=headers, json=page_data)
    
    if res.status_code in [201, 200]:
        new_page = res.json()
        print(f"SUCCESS: Portal page re-created.")
        print(f"URL: {new_page['webUrl']}")
        print("\nACTION REQUIRED: Please refresh your 'Site Pages' library. The page should now be visible.")
    else:
        print(f"FAILURE: Status {res.status_code} - {res.text}")

if __name__ == "__main__":
    recreate_page()
