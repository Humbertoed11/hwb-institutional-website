import os
import requests
import msal
from dotenv import load_dotenv

load_dotenv()

def verify_full_suite():
    print("--- SigmaFidelity: Full Microsoft 365 Functional Audit ---")
    
    cid = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
    secret = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
    tid = os.getenv("GRAPH_API_PROD_TENANT_ID")
    
    authority = f"https://login.microsoftonline.com/{tid}"
    app = msal.ConfidentialClientApplication(cid, authority=authority, client_credential=secret)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" not in result:
        print(f"FAILED to acquire token: {result.get('error_description')}")
        return

    token = result["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Verify Directory / Users
    print("\n1. Directory Access (Users):")
    res = requests.get("https://graph.microsoft.com/v1.0/users?$top=1", headers=headers)
    if res.status_code == 200:
        print(f"   SUCCESS: Can read directory. Sample: {res.json()['value'][0]['userPrincipalName']}")
    else:
        print(f"   FAILURE: {res.status_code} - {res.text}")

    # 2. Verify SharePoint / Sites
    print("\n2. SharePoint Access (Sites):")
    res = requests.get("https://graph.microsoft.com/v1.0/sites/root", headers=headers)
    if res.status_code == 200:
        print(f"   SUCCESS: Root Site Access Verified ({res.json().get('displayName')})")
    else:
        print(f"   FAILURE: {res.status_code} - {res.text}")

    # 3. Verify OneDrive / Files
    print("\n3. OneDrive Access (Files):")
    # Attempt to list files for the primary user
    res = requests.get("https://graph.microsoft.com/v1.0/users/hdominguez@hwbcleaning.com/drive/root/children?$top=1", headers=headers)
    if res.status_code == 200:
        print("   SUCCESS: Can access user OneDrive files.")
    else:
        print(f"   FAILURE: {res.status_code} - {res.text}")

    # 4. Verify Tasks / Planner
    print("\n4. Tasks Access (Planner):")
    res = requests.get("https://graph.microsoft.com/v1.0/planner/plans?$top=1", headers=headers)
    # Note: Application access to /planner/plans is restricted; usually need to go via groups.
    # We will check if we can list groups as a proxy for planner access capability.
    res_group = requests.get("https://graph.microsoft.com/v1.0/groups?$top=1", headers=headers)
    if res_group.status_code == 200:
        print("   SUCCESS: Can access Groups (Prerequisite for Planner/Teams management).")
    else:
        print(f"   FAILURE: {res_group.status_code} - {res_group.text}")

if __name__ == "__main__":
    verify_full_suite()
