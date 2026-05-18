import os
import msal
import json
import base64
from dotenv import load_dotenv

load_dotenv()

def decode_token():
    cid = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
    secret = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
    tid = os.getenv("GRAPH_API_PROD_TENANT_ID")
    
    authority = f"https://login.microsoftonline.com/{tid}"
    app = msal.ConfidentialClientApplication(cid, authority=authority, client_credential=secret)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        token = result["access_token"]
        # Split and decode
        _, payload_b64, _ = token.split('.')
        # Fix padding
        payload_b64 += '=' * (-len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        print(f"Roles: {payload.get('roles', 'No Roles Found')}")
        print(f"Scp: {payload.get('scp', 'No Scopes Found')}")
    else:
        print(f"FAILED to acquire token: {result.get('error_description')}")

decode_token()
