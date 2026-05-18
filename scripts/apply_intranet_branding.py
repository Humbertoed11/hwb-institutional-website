import os
import requests
import msal
import base64
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

# Root Site ID
ROOT_SITE_ID = "netorgft3163094.sharepoint.com,ba333e69-0b50-4a68-a226-6733cbcb7fdd,819b0286-8cdb-44a1-b1a7-8644604fc29d"
LOGO_PATH = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/hwb-cleaning-services-llc-logo-plano-tx.png"

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def apply_branding():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Upload Logo to Site Assets
    print("Step 1: Uploading logo to Root Site Assets...")
    # First find the 'Site Assets' drive
    res_drives = requests.get(f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/drives", headers=headers)
    drives = res_drives.json().get("value", [])
    asset_drive_id = next((d['id'] for d in drives if d['name'] == 'Site Assets'), None)
    
    if not asset_drive_id:
        # Fallback to 'Documents' if Site Assets isn't explicitly found
        asset_drive_id = next((d['id'] for d in drives if d['name'] == 'Documents'), None)

    if asset_drive_id:
        with open(LOGO_PATH, "rb") as f:
            content = f.read()
        
        filename = os.path.basename(LOGO_PATH)
        upload_url = f"https://graph.microsoft.com/v1.0/drives/{asset_drive_id}/root:/{filename}:/content"
        res_upload = requests.put(upload_url, headers={"Authorization": f"Bearer {token}", "Content-Type": "image/png"}, data=content)
        
        if res_upload.status_code in [200, 201]:
            logo_web_url = res_upload.json().get("webUrl")
            print(f"SUCCESS: Logo uploaded to {logo_web_url}")
        else:
            print(f"WARNING: Logo upload failed. {res_upload.text}")
    
    # 2. Update Site Description/Display Name to match Intranet SOP
    print("Step 2: Updating Site Identity...")
    site_data = {
        "displayName": "HWB SigmaFidelity™ Portal",
        "description": "Official Corporate Intranet for HWB Cleaning Services LLC. The Single Source of Truth."
    }
    res_patch = requests.patch(f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=site_data)
    
    if res_patch.status_code == 200:
        print("SUCCESS: Site identity updated to 'HWB SigmaFidelity™ Portal'.")
    else:
        print(f"WARNING: Site identity update failed. Status {res_patch.status_code}")

    print("\n--- Branding Cycle Complete ---")
    print("Manual Note: To apply the Navy Blue theme (#004aad), the CEO should navigate to 'Change the look' -> 'Theme' in the SharePoint UI, as theme application via Graph API is restricted to Global Admins via PowerShell.")

if __name__ == "__main__":
    apply_branding()
