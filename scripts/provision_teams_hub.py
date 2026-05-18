import os
import requests
import msal
import time
from dotenv import load_dotenv

# Load Institutional Secrets (HWB-QMS-9.5)
load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")
SENDER_EMAIL = "humbertoed@hwbcleaning.com"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def provision_teams():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Create the Group (Teams are backed by Microsoft 365 Groups)
    group_data = {
        "displayName": "HWB SigmaFidelity™ Executive Hub",
        "description": "Institutional command center for CEO and AI Vice Presidents.",
        "groupTypes": ["Unified"],
        "mailEnabled": True,
        "mailNickname": "sigmaexecutivehub",
        "securityEnabled": False,
        "visibility": "Private"
    }
    
    print("Step 1: Creating Microsoft 365 Group...")
    res = requests.post("https://graph.microsoft.com/v1.0/groups", headers=headers, json=group_data)
    
    if res.status_code not in [201, 200]:
        print(f"FAILURE: Group creation failed. Status {res.status_code} - {res.text}")
        return
    
    group_id = res.json().get("id")
    print(f"SUCCESS: Group created with ID: {group_id}")
    
    # Wait for propagation
    print("Waiting 15 seconds for directory propagation...")
    time.sleep(15)
    
    # 2. Add CEO as Owner (Humberto Dominguez)
    # Finding CEO user ID first
    user_res = requests.get(f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}", headers=headers)
    ceo_id = user_res.json().get("id")
    
    if ceo_id:
        owner_data = {"@odata.id": f"https://graph.microsoft.com/v1.0/users/{ceo_id}"}
        requests.post(f"https://graph.microsoft.com/v1.0/groups/{group_id}/owners/$ref", headers=headers, json=owner_data)
        requests.post(f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/$ref", headers=headers, json=owner_data)
        print(f"SUCCESS: CEO {SENDER_EMAIL} added as owner.")

    # 3. Create the Team from the Group
    team_data = {
        "memberSettings": {
            "allowCreateUpdateChannels": True
        },
        "messagingSettings": {
            "allowUserEditMessages": True,
            "allowUserDeleteMessages": True
        },
        "funSettings": {
            "allowGiphy": True,
            "giphyContentRating": "moderate"
        }
    }
    
    print("Step 2: Provisioning Team...")
    # Use POST to the team endpoint for an existing group
    res = requests.put(f"https://graph.microsoft.com/v1.0/groups/{group_id}/team", headers=headers, json=team_data)
    
    if res.status_code not in [201, 202, 200]:
        # Handle cases where the group is still propagating or other errors
        print(f"FAILURE: Team provisioning failed. Status {res.status_code} - {res.text}")
        return
    print("SUCCESS: Team provisioned.")

    # 4. Create Strategic Channels
    channels = [
        {"displayName": "strategy-sync", "description": "CEO & VP Alignment Hub."},
        {"displayName": "finance-warchest", "description": "Real-time burn alerts and reports from Maria Bolanos."},
        {"displayName": "marketing-leads", "description": "High-intent lead dispatch from Lauri Tells."}
    ]
    
    print("Step 3: Creating Strategic Channels...")
    for channel in channels:
        res = requests.post(f"https://graph.microsoft.com/v1.0/teams/{group_id}/channels", headers=headers, json=channel)
        if res.status_code == 201:
            print(f"SUCCESS: Channel '{channel['displayName']}' created.")
        else:
            print(f"WARNING: Could not create channel '{channel['displayName']}'. Status {res.status_code}")

if __name__ == "__main__":
    provision_teams()
