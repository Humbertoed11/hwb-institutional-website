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
APP_NAME = "hwb-institutional-website"
RG = "HWB-Production-RG"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
# The SCM API token scope is the App Service resource URI or management.azure.com
SCOPE = ["https://management.azure.com/.default"]

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def execute_live_command(cmd_str, target_dir=""):
    token = get_token()
    if not token:
        print("CRITICAL: Failed to acquire Azure token.")
        return
        
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Let's get the Kudu SCM publishing credentials first
    url_pub = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/config/publishingcredentials/list?api-version=2022-03-01"
    res_pub = requests.post(url_pub, headers=headers)
    if res_pub.status_code != 200:
        print(f"FAILED to fetch credentials: {res_pub.status_code}")
        print(res_pub.text)
        return
        
    creds = res_pub.json().get("properties", {})
    # Note: Kudu deployment credentials must be extracted correctly
    # Let's use the publishingUserName and publishingPassword
    username = creds.get("publishingUserName")
    password = creds.get("publishingPassword")
    
    # In Azure, Kudu basic auth requires the username to be prefixed with a dollar sign $
    # if it isn't already, e.g. '$hwb-institutional-website'
    # Let's check if the username has the site name in it
    print(f"Publishing Username: {username}")
    
    print(f"--- SigmaFidelity: Executing Live Command via SCM Basic Auth: '{cmd_str}' ---")
    scm_url = f"https://{APP_NAME}.scm.azurewebsites.net/api/command"
    payload = {
        "command": cmd_str,
        "dir": target_dir
    }
    
    try:
        # Kudu Basic Auth: auth=(username, password)
        res_cmd = requests.post(scm_url, auth=(username, password), json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        if res_cmd.status_code == 200:
            output = res_cmd.json()
            print("\nSTDOUT:")
            print(output.get("Output", ""))
            print("\nSTDERR:")
            print(output.get("Error", ""))
            print(f"Exit Code: {output.get('ExitCode')}")
        else:
            print(f"Command execution failed with status {res_cmd.status_code}")
            print(res_cmd.text)
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    # Let's list the root files and templates in the active container
    # Since it is a Dockerized Linux Web App, we run standard Linux commands
    execute_live_command("ls -la templates", "site/wwwroot")
