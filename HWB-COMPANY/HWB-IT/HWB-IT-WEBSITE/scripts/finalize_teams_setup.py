import os
import requests
import msal
import time
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")
SENDER_EMAIL = "humbertoed@hwbcleaning.com"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

# Group ID from previous successful step
GROUP_ID = "b1ab9c1b-7ccc-4236-a52b-343267b4214b"

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def finalize_teams():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Provision Team for existing Group
    team_data = {
        "memberSettings": {"allowCreateUpdateChannels": True},
        "messagingSettings": {"allowUserEditMessages": True, "allowUserDeleteMessages": True},
        "funSettings": {"allowGiphy": True, "giphyContentRating": "moderate"}
    }
    
    print(f"Step 1: Provisioning Team for Group {GROUP_ID}...")
    res = requests.put(f"https://graph.microsoft.com/v1.0/groups/{GROUP_ID}/team", headers=headers, json=team_data)
    
    if res.status_code not in [201, 202, 200]:
        print(f"FAILURE: Team provisioning failed. Status {res.status_code} - {res.text}")
        if res.status_code == 404:
            print("Note: The group might still be propagating. Waiting 30 seconds...")
            time.sleep(30)
            res = requests.put(f"https://graph.microsoft.com/v1.0/groups/{GROUP_ID}/team", headers=headers, json=team_data)
    
    if res.status_code in [201, 202, 200]:
        print("SUCCESS: Team provisioned or already exists.")
    else:
        return

    # 2. Create Strategic Channels
    channels = [
        {"displayName": "strategy-sync", "description": "CEO & VP Alignment Hub."},
        {"displayName": "finance-warchest", "description": "Real-time burn alerts and reports from Maria Bolanos."},
        {"displayName": "marketing-leads", "description": "High-intent lead dispatch from Lauri Tells."}
    ]
    
    print("Step 2: Creating Strategic Channels...")
    for channel in channels:
        # Check if channel exists first
        list_res = requests.get(f"https://graph.microsoft.com/v1.0/teams/{GROUP_ID}/channels", headers=headers)
        existing_channels = [c['displayName'] for c in list_res.json().get('value', [])]
        
        if channel['displayName'] in existing_channels:
            print(f"INFO: Channel '{channel['displayName']}' already exists.")
            continue

        res = requests.post(f"https://graph.microsoft.com/v1.0/teams/{GROUP_ID}/channels", headers=headers, json=channel)
        if res.status_code == 201:
            print(f"SUCCESS: Channel '{channel['displayName']}' created.")
        else:
            print(f"WARNING: Could not create channel '{channel['displayName']}'. Status {res.status_code} - {res.text}")

if __name__ == "__main__":
    finalize_teams()
