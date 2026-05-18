import os
import requests
import msal
from dotenv import load_dotenv

load_dotenv()

def try_send(cid, secret, tid, label):
    print(f"--- Attempting with {label} ---")
    authority = f"https://login.microsoftonline.com/{tid}"
    app = msal.ConfidentialClientApplication(cid, authority=authority, client_credential=secret)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        print(f"SUCCESS: Token acquired for {label}!")
        token = result["access_token"]
        endpoint = "https://graph.microsoft.com/v1.0/users/humbertoed@hwbcleaning.com/sendMail"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        email_body = {
            "message": {
                "subject": "test",
                "body": {
                    "contentType": "Text",
                    "content": "this is a tes of the system"
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": "hdominguez@hwbcleaning.com"
                        }
                    }
                ]
            }
        }
        response = requests.post(endpoint, headers=headers, json=email_body)
        if response.status_code == 202:
            print(f"SUCCESS: Email sent via {label}!")
            return True
        else:
            print(f"FAILURE: Status {response.status_code} - {response.text}")
            return False
    else:
        print(f"FAILED to acquire token for {label}: {result.get('error_description')}")
        return False

# Attempt 1: GRAPH_API_PROD
try_send(
    os.getenv("GRAPH_API_PROD_APPLICATION_ID"),
    os.getenv("GRAPH_API_PROD_SECRET_VALUE"),
    os.getenv("GRAPH_API_PROD_TENANT_ID"),
    "GRAPH_API_PROD"
)

# Attempt 2: AZURE_ (if attempt 1 failed)
try_send(
    os.getenv("AZURE_CLIENT_ID"),
    os.getenv("AZURE_CLIENT_SECRET"),
    os.getenv("AZURE_TENANT_ID"),
    "AZURE_APP_REG"
)
