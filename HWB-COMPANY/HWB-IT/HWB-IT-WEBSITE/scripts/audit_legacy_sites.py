import os
import requests
import msal
import json
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def audit_sites():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    sites = {
        "HWBDASH": "netorgft3163094.sharepoint.com,1bc2c68e-96a4-4861-b4a1-92f645b6e729,f9d1ba88-588c-4219-93f1-50b0654f5ee3",
        "HWB_Intranet": "netorgft3163094.sharepoint.com,209d0f3a-000f-4540-9463-0c08f8cb7ae2,f111966f-99de-4ac3-9d86-03440c83af54"
    }
    
    for name, site_id in sites.items():
        print(f"\n--- AUDITING SITE: {name} ---")
        
        # 1. List Drives (Document Libraries)
        res_drives = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives", headers=headers)
        if res_drives.status_code == 200:
            drives = res_drives.json().get("value", [])
            print(f"Found {len(drives)} Document Libraries:")
            for d in drives:
                print(f"  - Library: {d['name']} | ID: {d['id']} | URL: {d['webUrl']}")
        
        # 2. List Lists
        res_lists = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists", headers=headers)
        if res_lists.status_code == 200:
            lists = res_lists.json().get("value", [])
            print(f"Found {len(lists)} Lists:")
            for l in lists:
                if l['displayName'] not in ['Documents', 'Site Assets', 'Style Library', 'Site Pages']:
                    print(f"  - List: {l['displayName']} | ID: {l['id']}")

if __name__ == "__main__":
    audit_sites()
