import os
import requests
import msal

# Mix and match
TID = "f4e215a9-e3b4-4c0f-8ce8-9413a96d3646" # From .env
CID = "5971f0e3-7c06-466c-9254-85096200328f" # From settings.json
SECRET = "kIo8Q~gy7aDjpTEizxy5GjpuBMOBPXcr-GNabaVH" # From settings.json

def try_send_v4():
    print("--- Attempting with Mixed Credentials (Env Tenant + Settings Client) ---")
    authority = f"https://login.microsoftonline.com/{TID}"
    app = msal.ConfidentialClientApplication(CID, authority=authority, client_credential=SECRET)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        print("SUCCESS: Token acquired!")
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
            print("SUCCESS: Email sent via Mixed credentials!")
            return True
        else:
            print(f"FAILURE: Status {response.status_code} - {response.text}")
            return False
    else:
        print(f"FAILED to acquire token: {result.get('error_description')}")
        return False

try_send_v4()
