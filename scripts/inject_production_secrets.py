import os
import requests
import msal
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")
SUBSCRIPTION_ID = "d778faac-02a4-4d74-9881-199994f2bd98"
APP_NAME = "hwb-institutional-website"
RG = "HWB-Production-RG"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://management.azure.com/.default"]

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def inject_secrets():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print(f"--- SigmaFidelity: Production Secret Synchronization ---")
    
    # Define keys to migrate from .env to Azure
    keys_to_migrate = [
        "LINKEDIN_CLIENT_ID",
        "LINKEDIN_CLIENT_SECRET",
        "LINKEDIN_REDIRECT_URI",
        "GRAPH_API_PROD_APPLICATION_ID",
        "GRAPH_API_PROD_SECRET_VALUE",
        "GRAPH_API_PROD_TENANT_ID"
    ]
    
    # 1. Fetch current settings first to avoid overwriting existing ones
    url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/config/appsettings/list?api-version=2022-03-01"
    res_current = requests.post(url, headers=headers)
    settings = res_current.json().get('properties', {})
    
    # 2. Add new secrets from local environment
    for key in keys_to_migrate:
        val = os.getenv(key)
        if val:
            settings[key] = val
            print(f"Staging Secret: {key}")
    
    # 3. Push updated settings back to Azure
    update_url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/config/appsettings?api-version=2022-03-01"
    payload = {"properties": settings}
    res_update = requests.put(update_url, headers=headers, json=payload)
    
    if res_update.status_code == 200:
        print("SUCCESS: Institutional secrets synchronized to Azure production.")
    else:
        print(f"FAILURE: Secret injection failed ({res_update.status_code})")

if __name__ == "__main__":
    inject_secrets()
