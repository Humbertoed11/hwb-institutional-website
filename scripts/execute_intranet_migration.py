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

# Site and Drive IDs from previous audits
ROOT_SITE_ID = "netorgft3163094.sharepoint.com,ba333e69-0b50-4a68-a226-6733cbcb7fdd,819b0286-8cdb-44a1-b1a7-8644604fc29d"
HWB_INTRANET_DRIVE_ID = "b!Og-dIA8AQEWUYwwI-Mt64m-WEfHemcNKnYYDRAyDr1RfLdOkTe3FTZfBPNMmApdB"
HWBDASH_DRIVE_ID = "b!jsbCG6SWYUi0oZL2RbbnKYi60fmMWBlCk_FQsGVPXuPkvAB57B3RQbKw45fBTZCj"

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def migrate_drive_contents(source_drive_id, target_folder_name):
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Get Root Drive of the Root Site
    res_root_drive = requests.get(f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/drive", headers=headers)
    target_drive_id = res_root_drive.json().get("id")
    
    # 2. Create Destination Folder in Root Drive
    print(f"Creating migration folder '{target_folder_name}' in root intranet...")
    folder_data = {"name": target_folder_name, "folder": {}}
    res_folder = requests.post(f"https://graph.microsoft.com/v1.0/drives/{target_drive_id}/root/children", headers=headers, json=folder_data)
    
    if res_folder.status_code in [201, 409]: # 409 if exists
        target_folder_id = res_folder.json().get("id") if res_folder.status_code == 201 else requests.get(f"https://graph.microsoft.com/v1.0/drives/{target_drive_id}/root/children/{target_folder_name}", headers=headers).json().get("id")
    else:
        print(f"FAILURE: Folder creation failed. {res_folder.text}")
        return

    # 3. List Source Items
    res_items = requests.get(f"https://graph.microsoft.com/v1.0/drives/{source_drive_id}/root/children", headers=headers)
    items = res_items.json().get("value", [])
    
    print(f"Found {len(items)} items to migrate from source drive.")
    
    for item in items:
        # Move command via Graph (Copy then Delete is safer, but Move is cleaner if within same tenant)
        # Using the move pattern (patch parentReference)
        move_data = {
            "parentReference": {
                "driveId": target_drive_id,
                "id": target_folder_id
            },
            "name": item['name']
        }
        
        print(f"Moving: {item['name']}...")
        res_move = requests.patch(f"https://graph.microsoft.com/v1.0/drives/{source_drive_id}/items/{item['id']}", headers=headers, json=move_data)
        
        if res_move.status_code == 200:
            print(f"SUCCESS: Moved {item['name']}")
        else:
            print(f"WARNING: Move failed for {item['name']}. Status {res_move.status_code}")

if __name__ == "__main__":
    print("Initiating Migration: HWB_Intranet -> SigmaFidelity™ Portal")
    migrate_drive_contents(HWB_INTRANET_DRIVE_ID, "LEGACY_INTRANET_MIGRATION")
    
    print("\nInitiating Migration: HWBDASH -> SigmaFidelity™ Portal")
    migrate_drive_contents(HWBDASH_DRIVE_ID, "LEGACY_HWBDASH_MIGRATION")
