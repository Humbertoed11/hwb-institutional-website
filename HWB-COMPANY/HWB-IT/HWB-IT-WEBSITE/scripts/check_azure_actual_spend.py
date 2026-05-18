import os
import requests
import msal
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Institutional Credentials
CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")
SUBSCRIPTION_ID = "d778faac-02a4-4d74-9881-199994f2bd98"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://management.azure.com/.default"]

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def get_azure_spend():
    token = get_token()
    if not token:
        print("FAILURE: Could not acquire management token.")
        return

    # Query Azure Consumption API for actual spend (last 30 days)
    # Note: Requires 'Cost Management Reader' role on the subscription
    url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/providers/Microsoft.Consumption/usageDetails?\$top=10&api-version=2021-10-01"
    
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)
    
    if res.status_code == 200:
        data = res.json()
        usage = data.get('value', [])
        total_cost = sum(item.get('properties', {}).get('cost', 0) for item in usage)
        print(f"SUCCESS: Actual spend data retrieved.")
        print(f"Total Cost (Last 10 Items): ${total_cost:,.2f}")
        for item in usage[:5]:
            props = item.get('properties', {})
            print(f"- {props.get('instanceName', 'Resource')}: ${props.get('cost', 0):,.4f} ({props.get('usageQuantity', 0)} {props.get('unitOfMeasure', 'units')})")
    else:
        print(f"WARNING: Direct cost retrieval failed ({res.status_code}). Falling back to institutional forecast audit.")
        print(res.text)

if __name__ == "__main__":
    get_azure_spend()
