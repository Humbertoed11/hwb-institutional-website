#!/usr/bin/env python3
"""
Dispatch Official HWB Logo Package to Mirna Rondinella via Microsoft Graph API
Governance: Executive Directive 2026-09-19 (CEO Humberto Dominguez)
Author: George (Systems Architect)
"""

import os
import sys
import base64
import json
import requests
import msal
import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

CID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TID = os.getenv("GRAPH_API_PROD_TENANT_ID")
USER_EMAIL = "hdominguez@hwbcleaning.com"
RECIPIENT_EMAIL = "mrondinella@hwbcleaning.com"

LOGO_PATH = os.path.join(BASE_DIR, "static", "1-hwb-cleaning-services-llc-logo-plano-tx.png")
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = "/app/static/1-hwb-cleaning-services-llc-logo-plano-tx.png"
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/1-hwb-cleaning-services-llc-logo-plano-tx.png"

def get_graph_token():
    authority = f"https://login.microsoftonline.com/{TID}"
    cca = msal.ConfidentialClientApplication(CID, authority=authority, client_credential=SECRET)
    result = cca.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return result.get("access_token")

def send_logo_email():
    print(f"[GRAPH API] Acquiring token for tenant {TID}...")
    token = get_graph_token()
    if not token:
        print("[ERROR] Failed to acquire Graph API token.")
        return False

    if not os.path.exists(LOGO_PATH):
        print(f"[ERROR] Logo file not found at: {LOGO_PATH}")
        return False

    with open(LOGO_PATH, "rb") as f:
        logo_bytes = f.read()
    logo_b64 = base64.b64encode(logo_bytes).decode("utf-8")

    html_content = """
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h2 style="color: #0f172a; margin: 0 0 8px 0; font-size: 20px; font-weight: 700;">HWB Cleaning Services LLC</h2>
            <p style="color: #64748b; margin: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">Official Brand Assets & Corporate Identity</p>
        </div>
        <div style="border-top: 1px solid #f1f5f9; padding-top: 18px; margin-bottom: 20px; color: #334155; font-size: 14px; line-height: 1.6;">
            <p>Hola Mirna,</p>
            <p>Following your operational request via Telegram, attached is the official high-resolution corporate logo file for <strong>HWB Cleaning Services LLC</strong> (Plano / DFW Headquarters).</p>
            <div style="background-color: #f8fafc; border-left: 4px solid #0284c7; padding: 14px 18px; border-radius: 4px; margin: 20px 0;">
                <p style="margin: 0 0 6px 0; font-weight: 600; color: #0f172a;">Attached Asset Details:</p>
                <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #475569;">
                    <li><strong>File:</strong> <code>1-hwb-cleaning-services-llc-logo-plano-tx.png</code></li>
                    <li><strong>Format:</strong> High-Resolution PNG with Alpha Transparency</li>
                    <li><strong>Standard:</strong> HWB-COM-002 Brand Identity & Letterhead Standard</li>
                </ul>
            </div>
            <p>If you require horizontal banners, vector SVG formats, or specific sizes for badges or uniform embroidery, please let us know.</p>
        </div>
        <div style="border-top: 1px solid #f1f5f9; padding-top: 16px; font-size: 12px; color: #94a3b8; text-align: left;">
            <p style="margin: 0 0 4px 0; font-weight: 600; color: #64748b;">Humberto Dominguez, CEO</p>
            <p style="margin: 0 0 2px 0;">HWB Cleaning Services LLC</p>
            <p style="margin: 0 0 2px 0;">101 E Park Blvd, Suite 600, Plano, TX 75074</p>
            <p style="margin: 0;"><a href="mailto:hdominguez@hwbcleaning.com" style="color: #0284c7; text-decoration: none;">hdominguez@hwbcleaning.com</a> | (214) 586-0257</p>
        </div>
    </div>
    """

    endpoint = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/sendMail"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    email_payload = {
        "message": {
            "subject": "Official HWB Cleaning Services Logo Assets",
            "body": {
                "contentType": "HTML",
                "content": html_content
            },
            "toRecipients": [
                {"emailAddress": {"address": RECIPIENT_EMAIL, "name": "Mirna Rondinella"}}
            ],
            "attachments": [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": "1-hwb-cleaning-services-llc-logo-plano-tx.png",
                    "contentType": "image/png",
                    "contentBytes": logo_b64
                }
            ]
        },
        "saveToSentItems": True
    }

    print(f"[GRAPH API] Dispatching email to {RECIPIENT_EMAIL} via {USER_EMAIL}...")
    res = requests.post(endpoint, headers=headers, json=email_payload, timeout=30)
    print(f"[GRAPH API] HTTP Status: {res.status_code}")
    
    if res.status_code in [200, 202]:
        print("✓ [SUCCESS] Email dispatched successfully to Mirna Rondinella!")
        
        # Update Outbox Record 47 in PostgreSQL
        db_url = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
        if "@localhost" in db_url and os.path.exists("/.dockerenv"):
            db_url = db_url.replace("@localhost", "@db")
        elif "@localhost" in db_url:
            # Fallback if outside container
            pass

        try:
            conn = psycopg2.connect(db_url)
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE "PendingOutbox"
                    SET recipient = %s,
                        subject = 'Official HWB Cleaning Services Logo Assets',
                        status = 'SENT',
                        body = %s
                    WHERE id = 47;
                """, (RECIPIENT_EMAIL, html_content))
                conn.commit()
            conn.close()
            print("✓ [OUTBOX UPDATED] Record #47 updated to status 'SENT' with recipient mrondinella@hwbcleaning.com.")
        except Exception as dbe:
            print(f"[WARN] Database update notice: {dbe}")

        return True
    else:
        print(f"[ERROR] Graph API rejected email: {res.text}")
        return False

if __name__ == "__main__":
    success = send_logo_email()
    sys.exit(0 if success else 1)
