import os
import requests
import msal
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

# IDs
ROOT_SITE_ID = "netorgft3163094.sharepoint.com,ba333e69-0b50-4a68-a226-6733cbcb7fdd,819b0286-8cdb-44a1-b1a7-8644604fc29d"
PAGE_ID = "250addbd-9255-433e-b9c6-0377d0a4dbc4"

def get_token():
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

def inject_text_content():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print("Step 1: Checking out page...")
    requests.post(f"https://graph.microsoft.com/v1.0/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}/checkout", headers=headers)

    # Simplified Text Injection Protocol
    print("Step 2: Injecting Text Content...")
    # Modern Pages typically use 'textWebPart' in the canvas
    # We will try the Beta 'canvasLayout' property with just one section
    payload = {
        "canvasLayout": {
            "horizontalSections": [
                {
                    "layout": "oneColumn",
                    "columns": [
                        {
                            "webparts": [
                                {
                                    "@odata.type": "#microsoft.graph.textWebPart",
                                    "innerHtml": "<h1>Institutional Mission: SigmaFidelity™</h1><p>Welcome to the official <b>HWB Cleaning Services LLC</b> Intranet. This portal serves as the single source of truth for all corporate documentation and operational intelligence.</p>"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    # Try Beta endpoint for Canvas modifications
    url = f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}"
    res = requests.patch(url, headers=headers, json=payload)
    
    if res.status_code == 200:
        print("SUCCESS: Text content injected.")
        print("Step 3: Publishing changes...")
        requests.post(f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}/publish", headers=headers)
    else:
        print(f"FAILURE: Status {res.status_code} - {res.text}")

if __name__ == "__main__":
    inject_text_content()
