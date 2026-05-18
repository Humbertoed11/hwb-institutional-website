import os
import requests
import msal
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def list_today_events():
    print("--- SigmaFidelity: Daily Calendar Audit (March 12, 2026) ---")
    
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
    
    # Define time range for today
    start_of_day = "2026-03-12T00:00:00Z"
    end_of_day = "2026-03-12T23:59:59Z"
    
    url = f"https://graph.microsoft.com/v1.0/users/{sender}/calendar/events"
    params = {
        "$filter": f"start/dateTime ge '{start_of_day}' and start/dateTime le '{end_of_day}'",
        "$select": "subject,start,end,location"
    }
    
    res = requests.get(url, headers=headers, params=params)
    
    if res.status_code == 200:
        events = res.json().get('value', [])
        if not events:
            print("Status: No events scheduled for today.")
        else:
            print(f"Found {len(events)} events for today:")
            for event in events:
                start = event['start']['dateTime']
                subject = event['subject']
                print(f"   - [{start}] {subject}")
    else:
        print(f"FAILURE: Status {res.status_code} - {res.text}")

if __name__ == "__main__":
    list_today_events()
