import os
import requests
import msal
import time
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")

# VERIFIED CEO ID from list_org_users.py
CEO_USER_ID = "47df85a1-cc91-46b2-bd1c-9fdecdc801ab"
GROUP_ID = "b1ab9c1b-7ccc-4236-a52b-343267b4214b"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def deploy_teams():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Add CEO as Owner
    owner_url = f"https://graph.microsoft.com/v1.0/groups/{GROUP_ID}/owners/$ref"
    owner_body = {"@odata.id": f"https://graph.microsoft.com/v1.0/users/{CEO_USER_ID}"}
    
    print(f"Assigning verified owner {CEO_USER_ID} to Group {GROUP_ID}...")
    res = requests.post(owner_url, headers=headers, json=owner_body)
    if res.status_code in [204, 201, 200]:
        print("SUCCESS: Owner assigned.")
    
    # 2. Add CEO as Member
    member_url = f"https://graph.microsoft.com/v1.0/groups/{GROUP_ID}/members/$ref"
    requests.post(member_url, headers=headers, json=owner_body)
    print("SUCCESS: Member assigned.")

    # 3. Provision Team
    print("Waiting 10 seconds for directory sync...")
    time.sleep(10)
    
    team_url = f"https://graph.microsoft.com/v1.0/groups/{GROUP_ID}/team"
    team_body = {
        "memberSettings": {"allowCreateUpdateChannels": True},
        "messagingSettings": {"allowUserEditMessages": True, "allowUserDeleteMessages": True},
        "funSettings": {"allowGiphy": True, "giphyContentRating": "moderate"}
    }
    
    print("Provisioning Team...")
    res = requests.put(team_url, headers=headers, json=team_body)
    
    if res.status_code in [201, 202, 200]:
        print("SUCCESS: SIGMAFIDELITY™ EXECUTIVE HUB PROVISIONED!")
        
        # 4. Create Strategic Channels
        channels = ["strategy-sync", "finance-warchest", "marketing-leads"]
        for c in channels:
            print(f"Creating channel: {c}...")
            c_data = {"displayName": c, "description": f"SigmaFidelity™ {c} channel."}
            requests.post(f"https://graph.microsoft.com/v1.0/teams/{GROUP_ID}/channels", headers=headers, json=c_data)
    else:
        print(f"FAILURE: Team provisioning failed. Status {res.status_code} - {res.text}")

if __name__ == "__main__":
    deploy_teams()
