"""
SigmaFidelity™ Microsoft Graph Email Service
Standard: HWB-COM-001 (Official Letterhead)
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
import base64
import requests
import msal
from flask import current_app

def get_official_logo_bytes():
    """Locates and returns the official HWB logo bytes (the modern brand mark used on the current webpage)."""
    candidates = [
        "/app/static/img/logo_signature.png",
        "/app/static/logo_signature.png",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "img", "logo_signature.png")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "logo_signature.png")),
        "/app/static/logo_standard.png",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "logo_standard.png"))
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
    return None

def build_executive_signature_html(officer="humberto", title=None, campaign_mode=False):
    """
    Builds the standardized corporate signature block per HWB-COM-001 v2.1.0.
    Uses cid:hwblogo for zero-block rendering in Microsoft Outlook and mobile clients.
    Engineered with explicit HTML attributes (width/height) to prevent Microsoft Word (MSO) engine stretching.
    Supports campaign_mode=True to render 'Owner & Operator' for outbound daycare/B2B marketing.
    """
    if str(officer).lower().startswith("m"):
        name = "Mirna Rondinella"
        default_title = "President"
        email = "mrondinella@hwbcleaning.com"
        phone_direct = "(214) 586-0257"
    else:
        name = "Humberto Dominguez"
        default_title = "Owner & Operator" if campaign_mode else "Chief Executive Officer"
        email = "hdominguez@hwbcleaning.com"
        phone_direct = "(972) 800-7808"

    effective_title = title if title else default_title

    return f"""
    <table width="560" cellpadding="0" cellspacing="0" border="0" style="width: 560px; max-width: 560px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 13px; color: #1e293b; margin-top: 24px; border-top: 2px solid #0f172a; padding-top: 16px; border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
        <tr>
            <td width="150" style="width: 150px; vertical-align: middle; padding-right: 20px; border-right: 1.5px solid #cbd5e1;">
                <img src="cid:hwblogo" width="135" height="53" alt="HWB Cleaning Services LLC" style="width: 135px; height: 53px; display: block; border: 0; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic;" />
            </td>
            <td width="410" style="width: 410px; vertical-align: top; padding-left: 20px; line-height: 1.45;">
                <div style="font-size: 15px; font-weight: 700; color: #0f172a;">{name}</div>
                <div style="font-size: 12px; font-weight: 600; color: #2563eb; text-transform: uppercase; letter-spacing: 0.04em;">{effective_title}</div>
                <div style="margin-top: 6px; font-size: 12px; color: #475569;">
                    <strong style="color: #0f172a;">HWB Cleaning Services LLC</strong><br>
                    3342 FM 1827 Ste 8d, McKinney, TX 75071<br>
                    Office: (214) 586-0257 | Direct: {phone_direct}<br>
                    Email: <a href="mailto:{email}" style="color: #2563eb; text-decoration: none; font-weight: 500;">{email}</a> | 
                    Web: <a href="https://www.hwbcleaning.com" style="color: #2563eb; text-decoration: none; font-weight: 500;">www.hwbcleaning.com</a>
                </div>
            </td>
        </tr>
    </table>
    """

def transmit_email(*args, **kwargs):
    """
    Transmits a professional email via Microsoft Graph API.
    Supports:
      transmit_email(recipient, subject, body_html, attach_signature=False, attachments=None)
      transmit_email(config, recipient, subject, body_html, ...)
    """
    attach_signature = kwargs.get('attach_signature', False)
    extra_attachments = kwargs.get('attachments', []) or []
    officer = kwargs.get('officer', 'humberto')
    title = kwargs.get('title', None)
    campaign_mode = kwargs.get('campaign_mode', False)

    if len(args) >= 4:
        config, recipient, subject, body_html = args[:4]
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
            
        if attach_signature:
            body_html = f"{body_html}<br>{build_executive_signature_html(officer=officer, title=title, campaign_mode=campaign_mode)}"

        attachments = list(extra_attachments)
        if "cid:hwblogo" in (body_html or ""):
            logo_bytes = get_official_logo_bytes()
            if logo_bytes:
                attachments.append({
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": "logo_official.png",
                    "contentType": "image/png",
                    "contentBytes": base64.b64encode(logo_bytes).decode("utf-8"),
                    "contentId": "hwblogo",
                    "isInline": True
                })

        email_data = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": to_recipients
            }
        }
        if attachments:
            email_data["message"]["attachments"] = attachments
        
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
