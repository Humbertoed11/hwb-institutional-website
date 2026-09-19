import os
import requests
import msal
import json
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")
SUBSCRIPTION_ID = "d778faac-02a4-4d74-9881-199994f2bd98"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://management.azure.com/.default"]

app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
res = app.acquire_token_for_client(scopes=SCOPE)
token = res.get("access_token")
if not token:
    print("No token acquired:", res)
    exit(1)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 1. Query all web apps
r = requests.get(f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/providers/Microsoft.Web/sites?api-version=2022-03-01", headers=headers)
if r.status_code == 200:
    sites = r.json().get("value", [])
    print(f"Found {len(sites)} sites in Azure:")
    for s in sites:
        name = s.get("name")
        rg = s.get("id").split("/")[4]
        state = s.get("properties", {}).get("state")
        last_mod = s.get("properties", {}).get("lastModifiedTimeUtc")
        hostnames = s.get("properties", {}).get("enabledHostNames", [])
        print(f"\nSite: {name} (RG: {rg})")
        print(f"  State: {state}")
        print(f"  Last Modified (UTC): {last_mod}")
        print(f"  Hostnames: {hostnames}")
        
        # Check deployments for this site
        dep_url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{rg}/providers/Microsoft.Web/sites/{name}/deployments?api-version=2022-03-01"
        dep_res = requests.get(dep_url, headers=headers)
        if dep_res.status_code == 200:
            deps = dep_res.json().get("value", [])
            print(f"  Total Deployments recorded: {len(deps)}")
            for d in deps[:5]:
                d_props = d.get("properties", {})
                print(f"    - ID: {d.get('name')}")
                print(f"      Status: {d_props.get('status')}")
                print(f"      Deployer: {d_props.get('deployer')}")
                print(f"      Start Time: {d_props.get('start_time')}")
                print(f"      End Time: {d_props.get('end_time')}")
                print(f"      Message: {d_props.get('message')}")
        else:
            print(f"  Deployments query returned: {dep_res.status_code}")
else:
    print("Sites query failed:", r.status_code, r.text)

# 2. Check Container Registries (ACR)
acr_url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/providers/Microsoft.ContainerRegistry/registries?api-version=2023-01-01-preview"
r_acr = requests.get(acr_url, headers=headers)
if r_acr.status_code == 200:
    registries = r_acr.json().get("value", [])
    print(f"\nFound {len(registries)} Container Registries:")
    for reg in registries:
        reg_name = reg.get("name")
        login_server = reg.get("properties", {}).get("loginServer")
        creation_date = reg.get("properties", {}).get("creationDate")
        print(f"  Registry: {reg_name} | LoginServer: {login_server} | Created: {creation_date}")
