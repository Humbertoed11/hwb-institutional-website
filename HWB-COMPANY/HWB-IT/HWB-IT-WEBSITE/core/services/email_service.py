"""
SigmaFidelity™ Microsoft Graph Email Service
Standard: HWB-COM-001 (Official Letterhead)
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
import re
import base64
import requests
import msal
from flask import current_app

UNSUB_URL_REGEX = re.compile(r'https://(?:www\.)?hwbcleaning\.com/unsubscribe(?:/[A-Za-z0-9_-]+)?', re.IGNORECASE)


def build_rfc8058_headers(body_html: str = "", campaign_mode: bool = False) -> list:
    """
    Builds IETF RFC 8058 & RFC 2369 native One-Click List-Unsubscribe headers
    for Microsoft Graph internetMessageHeaders whenever an email contains an
    unsubscribe link or is sent in campaign_mode.
    """
    raw_body = body_html or ""
    match = UNSUB_URL_REGEX.search(raw_body)
    if not match and not campaign_mode and '/unsubscribe' not in raw_body:
        return []
    unsub_url = match.group(0) if match else "https://www.hwbcleaning.com/unsubscribe"
    return [
        {
            "name": "List-Unsubscribe",
            "value": f"<{unsub_url}>, <mailto:info@hwbcleaning.com?subject=Unsubscribe>"
        },
        {
            "name": "List-Unsubscribe-Post",
            "value": "List-Unsubscribe=One-Click"
        }
    ]

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
                    P.O. Box 38465, Dallas, TX 75238<br>
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

    # Enterprise Outbound Suppression Gate: Check permanent EmailSuppressionList AND Leads DNC/Unsubscribed flags
    is_test_proof = str(subject or "").strip().startswith("[TEST PROOF]")
    try:
        db_url = (config.get("DATABASE_URL") if hasattr(config, 'get') else None) or os.environ.get("DATABASE_URL")
        if db_url and recipient and not is_test_proof:
            import psycopg2
            raw_addrs = recipient if isinstance(recipient, list) else str(recipient).split(',')
            clean_addrs = [str(r).strip().lower() for r in raw_addrs if r and '@' in str(r)]
            if clean_addrs:
                s_conn = psycopg2.connect(db_url)
                with s_conn.cursor() as s_cur:
                    s_cur.execute('SELECT email_lower, reason FROM "EmailSuppressionList" WHERE email_lower = ANY(%s) LIMIT 1;', (clean_addrs,))
                    sup_row = s_cur.fetchone()
                    if sup_row:
                        s_conn.close()
                        print(f"[GRAPH SUPPRESSION GATE] Blocked outbound email to {sup_row[0]} ({sup_row[1]})", flush=True)
                        return False, f"Suppressed ({sup_row[1]}): {sup_row[0]}"

                    s_cur.execute('''
                        SELECT LOWER(TRIM(email)), status, COALESCE(is_dnc, FALSE), COALESCE(email_hygiene_status, '')
                        FROM "Leads"
                        WHERE LOWER(TRIM(email)) = ANY(%s)
                          AND (
                              COALESCE(is_dnc, FALSE) = TRUE
                              OR status IN ('Do Not Call (DNC)', 'Unsubscribed')
                              OR UPPER(COALESCE(email_hygiene_status, '')) = 'DO_NOT_EMAIL'
                          )
                        LIMIT 1;
                    ''', (clean_addrs,))
                    lead_sup = s_cur.fetchone()
                    if lead_sup:
                        s_conn.close()
                        reason_lbl = lead_sup[1] or ('DNC' if lead_sup[2] else lead_sup[3]) or 'DO_NOT_EMAIL'
                        print(f"[GRAPH SUPPRESSION GATE] Blocked outbound email to CRM-suppressed lead {lead_sup[0]} ({reason_lbl})", flush=True)
                        return False, f"Suppressed (CRM {reason_lbl}): {lead_sup[0]}"
                s_conn.close()
    except Exception as sup_err:
        print(f"[GRAPH SUPPRESSION CHECK NOTICE] {sup_err}", flush=True)

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

        stream_type = str(kwargs.get('stream_type') or ('marketing' if campaign_mode else 'transactional')).strip().lower()
        sender_name = kwargs.get('sender_name') or ("HWB Cleaning Services LLC" if stream_type == 'transactional' else "Humberto Dominguez — HWB Cleaning Services")
        reply_to_addr = kwargs.get('reply_to') or user_id

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

        tracking_token = kwargs.get('tracking_token', None)
        request_read_receipt = kwargs.get('request_read_receipt', False)
        bcc = kwargs.get('bcc', None)
        # Only inject open-tracking pixels when tracking_token is explicitly provided (never auto-injected on transactional partner/client receipts)
        if tracking_token and f"/pixel/{tracking_token}.gif" not in (body_html or "") and f"/open/{tracking_token}.gif" not in (body_html or ""):
            pixel_tag = f'<img src="https://www.hwbcleaning.com/api/v1/telemetry/pixel/{tracking_token}.gif" alt="" width="1" height="1" style="display:none;width:1px;height:1px;border:0;" />'
            body_html = f"{body_html or ''}{pixel_tag}"

        # Ensure full <!DOCTYPE html> compliance structure for zero SpamAssassin MIME_HTML_ONLY / malformed-HTML penalty
        raw_html = (body_html or "").strip()
        if raw_html and not raw_html.lower().startswith("<!doctype") and "<html" not in raw_html.lower():
            safe_title = re.sub(r'[<>"]', '', str(subject or "HWB Cleaning Services LLC"))
            body_html = (
                "<!DOCTYPE html>"
                '<html lang="en"><head><meta charset="UTF-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
                f"<title>{safe_title}</title></head>"
                '<body style="margin:0;padding:16px;background-color:#f8fafc;color:#0f172a;'
                "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;\">"
                f"{raw_html}</body></html>"
            )

        email_data = {
            "message": {
                "subject": subject,
                "importance": "normal",
                "from": {
                    "emailAddress": {
                        "name": sender_name,
                        "address": user_id,
                    }
                },
                "replyTo": [
                    {
                        "emailAddress": {
                            "name": "HWB Cleaning Services LLC",
                            "address": reply_to_addr,
                        }
                    }
                ],
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": to_recipients
            },
            "saveToSentItems": True
        }
        if bcc:
            if isinstance(bcc, list):
                bcc_list = [{"emailAddress": {"address": str(b).strip()}} for b in bcc if b and str(b).strip()]
            else:
                bcc_list = [{"emailAddress": {"address": str(b).strip()}} for b in str(bcc).split(',') if b and str(b).strip()]
            if bcc_list:
                email_data["message"]["bccRecipients"] = bcc_list
        if request_read_receipt:
            email_data["message"]["isDeliveryReceiptRequested"] = True
            email_data["message"]["isReadReceiptRequested"] = True
        if stream_type == 'marketing' or '/unsubscribe' in (body_html or ''):
            rfc8058_headers = build_rfc8058_headers(body_html=body_html, campaign_mode=campaign_mode)
            if rfc8058_headers:
                email_data["message"]["internetMessageHeaders"] = rfc8058_headers
        if attachments:
            email_data["message"]["attachments"] = attachments
        
        endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/sendMail"
        try:
            res = requests.post(endpoint, headers=headers, json=email_data)
            if res.status_code == 400 and "InvalidInternetMessageHeader" in res.text and "internetMessageHeaders" in email_data["message"]:
                email_data["message"]["internetMessageHeaders"] = [
                    {
                        "name": h["name"] if h["name"].lower().startswith("x-") else f"X-{h['name']}",
                        "value": h["value"],
                    }
                    for h in email_data["message"]["internetMessageHeaders"]
                ]
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
