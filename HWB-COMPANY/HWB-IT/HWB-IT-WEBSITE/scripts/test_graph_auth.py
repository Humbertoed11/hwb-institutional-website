import msal
import os
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("MS_CLIENT_ID")
client_secret = os.getenv("MS_CLIENT_SECRET")

def test_auth(tid, cid, secret):
    print(f"Testing Auth: Tenant={tid}, Client={cid}")
    authority = f"https://login.microsoftonline.com/{tid}"
    try:
        app = msal.ConfidentialClientApplication(cid, authority=authority, client_credential=secret)
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" in result:
            print("SUCCESS: Token acquired!")
            return True
        else:
            print(f"FAILED: {result.get('error')}")
            print(f"Description: {result.get('error_description')}")
            return False
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        return False

# Test 1: Common (Multi-tenant)
print("--- Test 1: 'common' Tenant ---")
if not test_auth("common", client_id, client_secret):
    # Test 2: Alternative Tenant ID
    alt_tenant = "f4e215a9-e3b4-4c0f-8ce8-9413a96d3646"
    print("\n--- Test 2: Alternative Tenant ID ---")
    test_auth(alt_tenant, client_id, client_secret)
