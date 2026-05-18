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

# Assets
LOGO_PATH = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/hwb-cleaning-services-llc-logo-plano-tx.png"
BANNER_PATH = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/hwb-corporate-intranet-banner.png"

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def deploy_assets_to_all_sites():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Fetch all sites
    print("Fetching all institutional SharePoint sites...")
    res_sites = requests.get("https://graph.microsoft.com/v1.0/sites?search=*", headers=headers)
    sites = res_sites.json().get("value", [])
    
    # Files to upload
    assets = [
        {"path": LOGO_PATH, "name": "hwb-logo-official.png"},
        {"path": BANNER_PATH, "name": "hwb-corporate-banner.png"}
    ]

    for site in sites:
        site_id = site['id']
        site_name = site.get('displayName', 'Unnamed Site')
        print(f"\n--- DEPLOYING BRANDING TO: {site_name} ---")
        
        # 2. Find target drive (Documents or Site Assets)
        res_drives = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives", headers=headers)
        drives = res_drives.json().get("value", [])
        target_drive = next((d for d in drives if d['name'] == 'Documents'), None)
        if not target_drive and drives:
            target_drive = drives[0] # Use first available
            
        if target_drive:
            drive_id = target_drive['id']
            for asset in assets:
                print(f"Uploading {asset['name']}...")
                with open(asset['path'], "rb") as f:
                    content = f.read()
                
                upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{asset['name']}:/content"
                requests.put(upload_url, headers={"Authorization": f"Bearer {token}", "Content-Type": "image/png"}, data=content)
            
            print(f"SUCCESS: Branding assets staged in {site_name}.")
        else:
            print(f"WARNING: No document library found for {site_name}.")

if __name__ == "__main__":
    deploy_assets_to_all_sites()
