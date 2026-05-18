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

def populate_page():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Check out the page first to allow editing
    print("Checking out page for content injection...")
    requests.post(f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}/checkout", headers=headers)

    # 1. Define the High-Fidelity Canvas Layout
    # Adding a Text Webpart with the Mission Statement
    # WebPart ID for Text is standard
    canvas_data = {
        "canvasLayout": {
            "horizontalSections": [
                {
                    "layout": "oneColumn",
                    "columns": [
                        {
                            "webparts": [
                                {
                                    "@odata.type": "#microsoft.graph.textWebPart",
                                    "innerHtml": "<h1>Fidelity. Safety. Respect.</h1><p>Welcome to the <b>SigmaFidelity™ Portal</b>, the official intranet for HWB Cleaning Services LLC. This platform serves as our central command center for operational excellence, ISO 9001 compliance, and PhD-level SaaS financial oversight.</p>"
                                }
                            ]
                        }
                    ]
                },
                {
                    "layout": "threeColumns",
                    "columns": [
                        {
                            "webparts": [
                                {
                                    "@odata.type": "#microsoft.graph.textWebPart",
                                    "innerHtml": "<h3>Strategic Hubs</h3><ul><li><a href='https://netorgft3163094.sharepoint.com/sites/sigmaexecutivehub'>Executive Hub</a></li><li><a href='https://www.hwbcleaning.com'>Corporate Site</a></li></ul>"
                                }
                            ]
                        },
                        {
                            "webparts": [
                                {
                                    "@odata.type": "#microsoft.graph.textWebPart",
                                    "innerHtml": "<h3>Operational Data</h3><p>Consolidated legacy libraries are now available in the <b>Documents</b> section of this portal.</p>"
                                }
                            ]
                        },
                        {
                            "webparts": [
                                {
                                    "@odata.type": "#microsoft.graph.textWebPart",
                                    "innerHtml": "<h3>Institutional News</h3><p>Real-time industry updates and company milestones will be posted here weekly.</p>"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    print("Injecting content into canvas...")
    url = f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}"
    res = requests.patch(url, headers=headers, json=canvas_data)
    
    if res.status_code == 200:
        print("SUCCESS: Canvas populated.")
        # Publish the changes
        print("Publishing updated page...")
        requests.post(f"https://graph.microsoft.com/beta/sites/{ROOT_SITE_ID}/pages/{PAGE_ID}/publish", headers=headers)
    else:
        print(f"FAILURE: Status {res.status_code} - {res.text}")

if __name__ == "__main__":
    populate_page()
