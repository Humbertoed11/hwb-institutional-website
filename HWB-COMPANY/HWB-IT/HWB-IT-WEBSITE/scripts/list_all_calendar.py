import os
import requests
import msal
from dotenv import load_dotenv

load_dotenv()

def list_all_upcoming():
    print("--- SigmaFidelity: Comprehensive Calendar Audit ---")
    
    cid = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
    secret = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
    tid = os.getenv("GRAPH_API_PROD_TENANT_ID")
    sender = "humbertoed@hwbcleaning.com"
    
    authority = f"https://login.microsoftonline.com/{tid}"
    app = msal.ConfidentialClientApplication(cid, authority=authority, client_credential=secret)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" not in result:
        print(f"FAILED to acquire token: {result.get('error_description')}")
        return

    token = result["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Fetch all events from now forward
    url = f"https://graph.microsoft.com/v1.0/users/{sender}/calendar/events"
    params = {
        "$select": "subject,start,end,location",
        "$orderby": "start/dateTime asc"
    }
    
    res = requests.get(url, headers=headers, params=params)
    
    if res.status_code == 200:
        events = res.json().get('value', [])
        if not events:
            print("Status: No events found in the institutional calendar.")
        else:
            print(f"Total Events Found: {len(events)}")
            for event in events:
                start = event['start']['dateTime']
                subject = event['subject']
                print(f"   - [{start}] {subject}")
    else:
        print(f"FAILURE: Status {res.status_code} - {res.text}")

if __name__ == "__main__":
    list_all_upcoming()
