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

def fetch_config():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print(f"--- SigmaFidelity: Auditing High-Fidelity Configuration ---")
    
    # 1. Fetch ALL App Settings
    url_settings = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/config/appsettings/list?api-version=2022-03-01"
    res_settings = requests.post(url_settings, headers=headers)
    if res_settings.status_code == 200:
        settings = res_settings.json().get('properties', {})
        for key in settings:
            if 'SECRET' in key or 'TOKEN' in key or 'VALUE' in key:
                print(f"- {key}: [MASKED]")
            else:
                print(f"- {key}: {settings[key]}")
    
    # 2. Fetch the Web Config (Startup Command)
    url_web = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/config/web?api-version=2022-03-01"
    res_web = requests.get(url_web, headers=headers)
    if res_web.status_code == 200:
        config = res_web.json().get('properties', {})
        print(f"\nStartup Command: {config.get('appCommandLine')}")
        print(f"Python Version: {config.get('linuxFxVersion')}")

if __name__ == "__main__":
    fetch_config()
