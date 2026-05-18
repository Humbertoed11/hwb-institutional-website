import os
import requests
import msal
import time
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

def verify_scm_link():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    RG = "HWB-Production-RG"
    
    print(f"--- SigmaFidelity: Final Link Integrity Audit ---")
    
    # 1. Fetch site config to verify scmType
    url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/config/web?api-version=2022-03-01"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        config = res.json()['properties']
        print(f"SCM Handshake Status: {config.get('scmType')}")
        print(f"Active Startup Command: {config.get('appCommandLine')}")
    
    # 2. Fetch recent site state
    url_site = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}?api-version=2022-03-01"
    res_site = requests.get(url_site, headers=headers)
    if res_site.status_code == 200:
        site = res_site.json()['properties']
        print(f"Site Operational State: {site['state']}")
        print(f"Last Handshake Update: {site['lastModifiedTimeUtc']}")

if __name__ == "__main__":
    verify_scm_link()
