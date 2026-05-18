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

def fix_visibility():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Attempt 1: Explicitly PATCH the publishingState level to 'published'
    print("Attempting to PATCH publishingState to 'published'...")
    url = f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}"
    data = {
        "publishingState": {
            "level": "published"
        }
    }
    res = requests.patch(url, headers=headers, json=data)
    print(f"PATCH Status: {res.status_code}")
    
    # Attempt 2: Check for alternative URLs (sometimes name changes on first save)
    print("\nRe-listing all pages to verify exact URL...")
    list_url = f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/pages"
    res_list = requests.get(list_url, headers=headers)
    pages = res_list.json().get('value', [])
    for p in pages:
        print(f"- Title: {p['title']} | Name: {p['name']} | Status: {p['publishingState']['level']} | URL: {p['webUrl']}")

if __name__ == "__main__":
    fix_visibility()
