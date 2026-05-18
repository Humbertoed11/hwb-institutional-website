import os
import requests
import msal

# Credentials from .gemini/settings.json
TID = "7c80802d-13b2-41d0-bbb0-b1ee54cea5f1"
CID = "5971f0e3-7c06-466c-9254-85096200328f"
SECRET = "kIo8Q~gy7aDjpTEizxy5GjpuBMOBPXcr-GNabaVH"

def try_send_v3():
    print("--- Attempting with settings.json Credentials ---")
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
            print("SUCCESS: Email sent via settings.json credentials!")
            return True
        else:
            print(f"FAILURE: Status {response.status_code} - {response.text}")
            return False
    else:
        print(f"FAILED to acquire token: {result.get('error_description')}")
        return False

try_send_v3()
