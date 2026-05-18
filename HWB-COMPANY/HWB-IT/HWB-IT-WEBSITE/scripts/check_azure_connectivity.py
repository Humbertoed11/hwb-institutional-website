import os
import requests
import msal
from dotenv import load_dotenv

# Load institutional secrets
load_dotenv()

# Institutional Credentials (HWB-QMS-9.5 Mandate)
CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")
SUBSCRIPTION_ID = "d778faac-02a4-4d74-9881-199994f2bd98"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://management.azure.com/.default"]

def check_connectivity():
    print("--- SigmaFidelity™: Initiating Azure Connectivity Audit ---")
    
    if not all([CLIENT_ID, CLIENT_SECRET, TENANT_ID]):
        print("CRITICAL: Missing Azure Credentials in .env")
        return

    # 1. Acquire Bearer Token
    try:
        app = msal.ConfidentialClientApplication(
            CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
        )
        result = app.acquire_token_for_client(scopes=SCOPE)
        
        if "access_token" in result:
            print("SUCCESS: Azure Management Token Acquired.")
            token = result["access_token"]
        else:
            print(f"FAILED: Token acquisition failed. Error: {result.get('error_description')}")
            return

        # 2. Test Resource Group Access
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resources?api-version=2021-04-01"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            count = len(response.json().get("value", []))
            print("SUCCESS: Azure Management API Connectivity Verified.")
            print(f"Audit Result: {count} resources identified in subscription.")
        else:
            print(f"FAILED: Azure Management API returned status {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"EXCEPTION: Connectivity check failed. {str(e)}")

if __name__ == "__main__":
    check_connectivity()
