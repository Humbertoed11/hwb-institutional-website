import msal
import requests
import datetime

def transmit_email(config, recipient, subject, body_html):
    """
    SigmaFidelity™ Microsoft Graph Email Service.
    Standard: HWB-COM-001 (Official Letterhead)
    """
    client_id = config.get("GRAPH_CLIENT_ID")
    client_secret = config.get("GRAPH_CLIENT_SECRET")
    tenant_id = config.get("GRAPH_TENANT_ID")
    user_id = config.get("GRAPH_USER_ID", "humbertoed@hwbcleaning.com")

    if not all([tenant_id, client_id, client_secret]):
        return False, "Missing Credentials"

    authority = f"https://login.microsoftonline.com/{tenant_id}" 
    app_msal = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    
    result = app_msal.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        headers = {
            "Authorization": f"Bearer {result['access_token']}",
            "Content-Type": "application/json"
        }
        
        email_data = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": [{"emailAddress": {"address": recipient}}]
            }
        }
        
        endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/sendMail"
        res = requests.post(endpoint, headers=headers, json=email_data)
        
        if res.status_code == 202:
            return True, "Email Transmitted"
        return False, f"Graph API Error: {res.text}"
        
    return False, "Token Acquisition Failed"
