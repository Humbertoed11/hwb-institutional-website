import os
import requests
import msal
import time
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

# IDs from previous audits
ROOT_SITE_ID = "netorgft3163094.sharepoint.com,ba333e69-0b50-4a68-a226-6733cbcb7fdd,819b0286-8cdb-44a1-b1a7-8644604fc29d"
HWB_INTRANET_DRIVE_ID = "b!Og-dIA8AQEWUYwwI-Mt64m-WEfHemcNKnYYDRAyDr1RfLdOkTe3FTZfBPNMmApdB"
HWBDASH_DRIVE_ID = "b!jsbCG6SWYUi0oZL2RbbnKYi60fmMWBlCk_FQsGVPXuPkvAB57B3RQbKw45fBTZCj"

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def migrate_via_copy(source_drive_id, target_folder_name):
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Get Root Drive
    res_root_drive = requests.get(f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/drive", headers=headers)
    target_drive_id = res_root_drive.json().get("id")
    
    # 2. Create Target Folder
    print(f"Ensuring target folder '{target_folder_name}' exists...")
    folder_data = {"name": target_folder_name, "folder": {}}
    res_folder = requests.post(f"https://graph.microsoft.com/v1.0/drives/{target_drive_id}/root/children", headers=headers, json=folder_data)
    
    if res_folder.status_code == 201:
        target_folder_id = res_folder.json().get("id")
    else:
        # Fetch ID if exists
        res_existing = requests.get(f"https://graph.microsoft.com/v1.0/drives/{target_drive_id}/root/children/{target_folder_name}", headers=headers)
        target_folder_id = res_existing.json().get("id")

    # 3. List Source Items
    res_items = requests.get(f"https://graph.microsoft.com/v1.0/drives/{source_drive_id}/root/children", headers=headers)
    items = res_items.json().get("value", [])
    
    print(f"Initiating copy for {len(items)} items...")
    
    for item in items:
        # Copy Item
        copy_data = {
            "parentReference": {
                "driveId": target_drive_id,
                "id": target_folder_id
            }
        }
        
        print(f"Copying: {item['name']}...")
        # Note: Copy is an async operation in Graph, returns 202 Accepted
        res_copy = requests.post(f"https://graph.microsoft.com/v1.0/drives/{source_drive_id}/items/{item['id']}/copy", headers=headers, json=copy_data)
        
        if res_copy.status_code == 202:
            print(f"SUCCESS: Copy started for {item['name']}")
        else:
            print(f"WARNING: Copy failed for {item['name']}. Status {res_copy.status_code} - {res_copy.text}")

if __name__ == "__main__":
    print("MIGRATION PHASE II: Copy Protocol (HWB_Intranet)")
    migrate_via_copy(HWB_INTRANET_DRIVE_ID, "LEGACY_INTRANET_MIGRATION")
    
    print("\nMIGRATION PHASE II: Copy Protocol (HWBDASH)")
    migrate_via_copy(HWBDASH_DRIVE_ID, "LEGACY_HWBDASH_MIGRATION")
