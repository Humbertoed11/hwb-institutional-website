import os
import requests
import msal
import zipfile
import io
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

def download_logs():
    token = get_token()
    if not token:
        print("CRITICAL: Failed to acquire Azure token.")
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    
    print("--- SigmaFidelity: Downloading Live Container Logs via ARM API ---")
    url_logs = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/containerlogs/zip?api-version=2022-03-01"
    
    res = requests.post(url_logs, headers=headers)
    if res.status_code == 200:
        print("SUCCESS: Logs zip downloaded.")
        try:
            z = zipfile.ZipFile(io.BytesIO(res.content))
            print("Zip Files list:", z.namelist())
            for name in z.namelist():
                if "docker" in name.lower() or "gunicorn" in name.lower():
                    print(f"\n=== LOG FILE: {name} ===")
                    content = z.read(name).decode("utf-8", errors="ignore")
                    lines = content.split("\n")
                    # Print the last 60 lines of the log file
                    for line in lines[-60:]:
                        print(line)
        except Exception as e:
            print(f"Failed to parse zip content: {e}")
    else:
        print(f"ARM API returned status {res.status_code}")
        print(res.text)

if __name__ == "__main__":
    download_logs()
