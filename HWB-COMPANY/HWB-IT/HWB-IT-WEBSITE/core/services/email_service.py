"""
SigmaFidelity™ Microsoft Graph Email Service
Standard: HWB-COM-001 (Official Letterhead)
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
import requests
import msal
from flask import current_app

def transmit_email(*args, **kwargs):
    """
    Transmits a professional email via Microsoft Graph API.
    Supports both signatures:
      transmit_email(recipient, subject, body_html)
      transmit_email(config, recipient, subject, body_html)
    """
    if len(args) == 4:
        config, recipient, subject, body_html = args
    elif len(args) == 3:
        recipient, subject, body_html = args
        config = current_app.config if current_app else os.environ
    else:
        config = kwargs.get('config', current_app.config if current_app else os.environ)
        recipient = kwargs.get('recipient')
        subject = kwargs.get('subject')
        body_html = kwargs.get('body_html')

    client_id = (config.get("GRAPH_CLIENT_ID") if hasattr(config, 'get') else None) or \
                (config.get("GRAPH_API_PROD_APPLICATION_ID") if hasattr(config, 'get') else None) or \
                os.environ.get("GRAPH_CLIENT_ID") or \
                os.environ.get("GRAPH_API_PROD_APPLICATION_ID")
    client_secret = (config.get("GRAPH_CLIENT_SECRET") if hasattr(config, 'get') else None) or \
                    (config.get("GRAPH_API_PROD_SECRET_VALUE") if hasattr(config, 'get') else None) or \
                    os.environ.get("GRAPH_CLIENT_SECRET") or \
                    os.environ.get("GRAPH_API_PROD_SECRET_VALUE")
    tenant_id = (config.get("GRAPH_TENANT_ID") if hasattr(config, 'get') else None) or \
                (config.get("GRAPH_API_PROD_TENANT_ID") if hasattr(config, 'get') else None) or \
                os.environ.get("GRAPH_TENANT_ID") or \
                os.environ.get("GRAPH_API_PROD_TENANT_ID")
    user_id = (config.get("GRAPH_USER_ID") if hasattr(config, 'get') else None) or \
              os.environ.get("GRAPH_USER_ID") or "hdominguez@hwbcleaning.com"

    if not all([tenant_id, client_id, client_secret]):
        print("[GRAPH] API Error: Missing configuration (Tenant/Client/Secret)", flush=True)
        return False, "Missing Credentials"

    authority = f"https://login.microsoftonline.com/{tenant_id}" 
    app_msal = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    
    result = app_msal.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        headers = {
            "Authorization": f"Bearer {result['access_token']}",
            "Content-Type": "application/json"
        }
        
        if isinstance(recipient, list):
            to_recipients = [{"emailAddress": {"address": str(r).strip()}} for r in recipient if r and str(r).strip()]
        elif isinstance(recipient, str):
            to_recipients = [{"emailAddress": {"address": str(r).strip()}} for r in recipient.split(',') if r and str(r).strip()]
        else:
            to_recipients = [{"emailAddress": {"address": str(recipient)}}]
            
        email_data = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": to_recipients
            }
        }
        
        endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/sendMail"
        try:
            res = requests.post(endpoint, headers=headers, json=email_data)
            if res.status_code == 202:
                print(f"[GRAPH] Email sent successfully to {recipient}", flush=True)
                return True, "Success"
            err_msg = f"Status {res.status_code}: {res.text}"
            print(f"[GRAPH] SEND FAILURE: {err_msg}", flush=True)
            return False, err_msg
        except Exception as e:
            print(f"[GRAPH] REQUEST FATAL: {e}", flush=True)
            return False, str(e)
        
    err_desc = result.get('error_description', 'Token Acquisition Failed')
    print(f"[GRAPH] AUTH FAILURE: {err_desc}", flush=True)
    return False, err_desc
