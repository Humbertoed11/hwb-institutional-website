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

def fetch_live_logs():
    token = get_token()
    if not token:
        print("CRITICAL: Failed to acquire Azure token.")
        return
        
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print("--- SigmaFidelity: Fetching Live Azure Web App Logs ---")
    
    # 1. Fetch Publishing Credentials
    url_pub = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/listpublishingcredentials?api-version=2022-03-01"
    res_pub = requests.post(url_pub, headers=headers)
    if res_pub.status_code != 200:
        print(f"FAILED to fetch publishing credentials: {res_pub.status_code}")
        print(res_pub.text)
        return
        
    creds = res_pub.json().get("properties", {})
    username = creds.get("publishingUserName")
    password = creds.get("publishingPassword")
    
    # 2. Fetch recent docker logs from Kudu SCM API
    print("Connecting to SCM Log Stream API...")
    scm_url = f"https://{APP_NAME}.scm.azurewebsites.net/api/vfs/LogFiles/docker/"
    
    try:
        # Fetch file list in LogFiles/docker
        res_files = requests.get(scm_url, auth=(username, password), timeout=10)
        if res_files.status_code == 200:
            files_list = res_files.json()
            # Sort files by last modified time to find the newest log
            files_list.sort(key=lambda x: x.get("mtime", ""), reverse=True)
            if files_list:
                latest_log = files_list[0]
                log_name = latest_log.get("name")
                print(f"Latest log file found: {log_name} ({latest_log.get('size')} bytes)")
                
                # Download and print the last 200 lines of the latest log file
                res_content = requests.get(scm_url + log_name, auth=(username, password), timeout=15)
                if res_content.status_code == 200:
                    lines = res_content.text.split("\n")
                    print("\n--- BEGIN LIVE CONTAINER LOG (LAST 50 LINES) ---")
                    for line in lines[-50:]:
                        print(line)
                    print("--- END LIVE CONTAINER LOG ---")
                else:
                    print(f"Failed to fetch content of log: {res_content.status_code}")
            else:
                print("No log files found in /api/vfs/LogFiles/docker/")
        else:
            print(f"SCM API call returned status {res_files.status_code}")
            print(res_files.text)
    except Exception as e:
        print(f"EXCEPTION during logs fetch: {e}")

if __name__ == "__main__":
    fetch_live_logs()
