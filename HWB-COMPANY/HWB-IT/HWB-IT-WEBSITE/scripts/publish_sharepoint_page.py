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
PAGE_ID = "fd86d2fb-dad3-44a1-b1a7-8644604fc29d"

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def publish_page():
    token = get_token()
    # The 'publish' action for site pages is typically on the beta endpoint
    url = f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}/publish"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Publishing page {PAGE_ID} via Beta endpoint...")
    res = requests.post(url, headers=headers)
    
    if res.status_code in [204, 200, 201]:
        print("SUCCESS: Page has been published.")
    else:
        print(f"FAILURE: Status {res.status_code} - {res.text}")
        
        # Fallback: Attempt to 'Save' if not published
        print("Attempting to check-in/save first...")
        checkin_url = f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}/microsoft.graph.sitePage/publish"
        res_fallback = requests.post(checkin_url, headers=headers)
        print(f"Fallback Publish Status: {res_fallback.status_code}")

if __name__ == "__main__":
    publish_page()
