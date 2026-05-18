import os
import requests
import msal
import time
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")
CEO_EMAIL = "humbertoed@hwbcleaning.com"
GROUP_ID = "b1ab9c1b-7ccc-4236-a52b-343267b4214b"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def fix_ownership():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Get CEO User ID
    print(f"Searching for user ID for {CEO_EMAIL}...")
    user_res = requests.get(f"https://graph.microsoft.com/v1.0/users/{CEO_EMAIL}", headers=headers)
    if user_res.status_code != 200:
        print(f"FAILURE: Could not find user {CEO_EMAIL}. Status {user_res.status_code}")
        return
    ceo_id = user_res.json().get("id")
    print(f"SUCCESS: User ID is {ceo_id}")

    # 2. Add CEO as Owner
    owner_url = f"https://graph.microsoft.com/v1.0/groups/{GROUP_ID}/owners/$ref"
    owner_body = {"@odata.id": f"https://graph.microsoft.com/v1.0/users/{ceo_id}"}
    
    print(f"Adding {CEO_EMAIL} as Owner of Group {GROUP_ID}...")
    res = requests.post(owner_url, headers=headers, json=owner_body)
    if res.status_code in [204, 201, 200]:
        print("SUCCESS: Owner added.")
    elif res.status_code == 400 and "already exists" in res.text:
        print("INFO: User is already an owner.")
    else:
        print(f"FAILURE: Could not add owner. Status {res.status_code} - {res.text}")

    # 3. Add CEO as Member (Redundant but safe)
    member_url = f"https://graph.microsoft.com/v1.0/groups/{GROUP_ID}/members/$ref"
    print(f"Adding {CEO_EMAIL} as Member of Group {GROUP_ID}...")
    res = requests.post(member_url, headers=headers, json=owner_body)
    if res.status_code in [204, 201, 200]:
        print("SUCCESS: Member added.")
    
    # 4. Final attempt to Provision Team
    print("Waiting 10 seconds for permission propagation...")
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
        print("SUCCESS: Team Provisioned!")
    else:
        print(f"FAILURE: Final Team provisioning failed. Status {res.status_code} - {res.text}")

if __name__ == "__main__":
    fix_ownership()
