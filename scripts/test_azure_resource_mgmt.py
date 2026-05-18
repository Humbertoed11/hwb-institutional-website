import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_azure_mgmt():
    print("--- SigmaFidelity: Azure Resource Management Connectivity Check ---")
    
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant_id = os.getenv("AZURE_TENANT_ID")
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    
    # 1. Get Access Token for Azure Management
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://management.azure.com/.default"
    }
    
    try:
        token_res = requests.post(token_url, data=token_data)
        if token_res.status_code != 200:
            print(f"FAILURE: Could not acquire management token. Status {token_res.status_code}")
            print(token_res.text)
            return
        
        token = token_res.json().get("access_token")
        print("SUCCESS: Azure Management Token Acquired.")
        
        # 2. List Resource Groups to verify Subscription access
        mgmt_url = f"https://management.azure.com/subscriptions/{subscription_id}/resourcegroups?api-version=2021-04-01"
        headers = {"Authorization": f"Bearer {token}"}
        
        rg_res = requests.get(mgmt_url, headers=headers)
        if rg_res.status_code == 200:
            groups = rg_res.json().get("value", [])
            print(f"SUCCESS: Connected to Subscription. Found {len(groups)} Resource Groups.")
            for rg in groups:
                print(f"   - {rg['name']} ({rg['location']})")
        else:
            print(f"FAILURE: Could not list Resource Groups. Status {rg_res.status_code}")
            print(rg_res.text)
            
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")

if __name__ == "__main__":
    test_azure_mgmt()
