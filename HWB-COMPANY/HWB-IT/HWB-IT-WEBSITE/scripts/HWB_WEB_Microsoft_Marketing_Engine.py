import os
import requests
import msal
import sqlite3
import base64
from datetime import datetime
from dotenv import load_dotenv

# Load Institutional Secrets (HWB-QMS-9.5)
load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")
SENDER_EMAIL = "humbertoed@hwbcleaning.com"

# Institutional Logo Path (SEO Optimized)
LOGO_PATH = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/hwb-cleaning-services-llc-logo-plano-tx.png"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

# DB_PATH = "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db"
# High-Fidelity Absolute Path Mandate
DB_PATH = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db"

class MicrosoftMarketingEngine:
    def __init__(self):
        self.app = msal.ConfidentialClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            client_credential=CLIENT_SECRET,
        )
        self._ensure_outbox_table()

    def _ensure_outbox_table(self):
        """Ensures the PendingOutbox table exists for the approval workflow."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS PendingOutbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient TEXT,
                    subject TEXT,
                    body TEXT,
                    created_at DATETIME,
                    status TEXT DEFAULT 'PENDING'
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"DEBUG: Outbox table initialization failed: {str(e)}")

    def get_access_token(self):
        """Retrieves an OAuth2 access token for the Microsoft Graph API."""
        result = self.app.acquire_token_for_client(scopes=SCOPE)
        if "access_token" in result:
            return result["access_token"]
        else:
            error_msg = result.get('error_description', result.get('error', 'Unknown Error'))
            raise Exception(f"MS-Graph Auth Failure: {error_msg}")

    def log_activity(self, activity_name, hours=0.1, category="Marketing outreach"):
        """Logs the marketing activity to the institutional database."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ActivityLog (date, activity_name, hours, category) VALUES (?, ?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d"), activity_name, hours, category)
            )
            conn.commit()
            conn.close()
            print(f"DEBUG: Activity logged: {activity_name}")
        except Exception as e:
            print(f"DEBUG: Database logging failed: {str(e)}")

    def wrap_with_letterhead(self, recipient_name, subject, body_content, date_str=None):
        """Wraps the given content in the official HWB-COM-001 letterhead template with inline logo."""
        if not date_str:
            date_str = datetime.now().strftime("%B %d, %Y")
        
        # Institutional Letterhead Template (HWB-COM-001) using cid:logo
        letterhead = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .letterhead {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; max-width: 800px; margin: 0 auto; border: 1px solid #eee; padding: 40px; }}
                .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #004aad; padding-bottom: 20px; margin-bottom: 30px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #004aad; text-transform: uppercase; }}
                .institutional-title {{ text-align: right; font-size: 12px; color: #666; line-height: 1.4; }}
                .content {{ line-height: 1.6; min-height: 400px; }}
                .footer {{ margin-top: 50px; border-top: 1px solid #eee; padding-top: 20px; text-align: center; font-size: 11px; color: #999; }}
                .motto {{ font-weight: bold; color: #004aad; margin-bottom: 5px; }}
            </style>
        </head>
        <body>
            <div class="letterhead">
                <div class="header">
                    <div class="logo">
                        <img src="cid:hwblogo" alt="HWB Cleaning Services LLC" height="60">
                        <br><span style="font-size: 14px; letter-spacing: 2px;">SIGMAFIDELITY™</span>
                    </div>
                    <div class="institutional-title">
                        <b>HWB Cleaning Services LLC</b><br>
                        Institutional Division | SaaS Ecosystem<br>
                        Plano, Texas | DFW Metroplex<br>
                        <a href="https://www.hwbcleaning.com" style="color: #004aad; text-decoration: none;">www.hwbcleaning.com</a>
                    </div>
                </div>
                
                <div class="content">
                    <div style="margin-bottom: 30px;">
                        <b>Date:</b> {date_str}<br>
                        <b>To:</b> {recipient_name}<br>
                        <b>Subject:</b> {subject}
                    </div>
                    {body_content}
                </div>

                <div class="footer">
                    <div class="motto">FIDELITY. SAFETY. RESPECT.</div>
                    © {datetime.now().year} HWB Cleaning Services LLC. All Rights Reserved.<br>
                    ISO 9001:2015 Certified | Operational Excellence Guaranteed.
                </div>
            </div>
        </body>
        </html>
        """
        return letterhead

    def send_marketing_email(self, to_email, subject, html_content, bypass_approval=False):
        """
        Stages an email for approval by default. 
        If bypass_approval is True (CEO manual override), it sends immediately.
        NOTE: All emails should be wrapped with wrap_with_letterhead first.
        """
        if bypass_approval:
            return self._dispatch_email(to_email, subject, html_content)
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO PendingOutbox (recipient, subject, body, created_at) VALUES (?, ?, ?, ?)",
                (to_email, subject, html_content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()
            print(f"STAGED: Email to {to_email} awaiting approval.")
            return True
        except Exception as e:
            print(f"DEBUG: Email staging failed: {str(e)}")
            return False

    def _dispatch_email(self, to_email, subject, html_content):
        """Transmits a high-fidelity marketing email via Microsoft Graph with inline attachments."""
        token = self.get_access_token()
        endpoint = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/sendMail"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Encode Logo for CID attachment
        try:
            with open(LOGO_PATH, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"WARNING: Could not encode logo for attachment: {str(e)}")
            encoded_string = ""
        
        email_body = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_content
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ],
                "attachments": [
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": "hwb-logo.png",
                        "contentType": "image/png",
                        "contentBytes": encoded_string,
                        "contentId": "hwblogo",
                        "isInline": True
                    }
                ]
            }
        }
        
        response = requests.post(endpoint, headers=headers, json=email_body)
        
        if response.status_code == 202:
            print(f"SUCCESS: Email sent to {to_email}")
            self.log_activity(f"Marketing email sent to {to_email}: {subject}")
            return True
        else:
            print(f"FAILURE: Status {response.status_code} - {response.text}")
            return False

    def list_pending_emails(self):
        """Retrieves all emails currently awaiting approval."""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            pending = cursor.execute("SELECT * FROM PendingOutbox WHERE status = 'PENDING'").fetchall()
            conn.close()
            return [dict(p) for p in pending]
        except Exception as e:
            print(f"DEBUG: Failed to list pending emails: {str(e)}")
            return []

    def approve_and_send(self, email_id):
        """Approves a staged email and dispatches it via Microsoft Graph."""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            email = cursor.execute("SELECT * FROM PendingOutbox WHERE id = ?", (email_id,)).fetchone()
            
            if email:
                print(f"APPROVING: Dispatching email {email_id} to {email['recipient']}...")
                success = self._dispatch_email(email['recipient'], email['subject'], email['body'])
                if success:
                    cursor.execute("UPDATE PendingOutbox SET status = 'SENT' WHERE id = ?", (email_id,))
                    conn.commit()
                conn.close()
                return success
            else:
                print(f"ERROR: Email ID {email_id} not found.")
                conn.close()
                return False
        except Exception as e:
            print(f"DEBUG: Approval/dispatch failed: {str(e)}")
            return False

    def create_calendar_event(self, subject, start_time, end_time, attendees=None, body=""):
        """Creates a calendar event on the institutional Microsoft Graph account."""
        token = self.get_access_token()
        endpoint = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/events"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        event_data = {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body
            },
            "start": {
                "dateTime": start_time,
                "timeZone": "America/Chicago"
            },
            "end": {
                "dateTime": end_time,
                "timeZone": "America/Chicago"
            }
        }
        
        if attendees:
            event_data["attendees"] = [
                {"emailAddress": {"address": email}, "type": "required"}
                for email in attendees
            ]
        
        response = requests.post(endpoint, headers=headers, json=event_data)
        
        if response.status_code == 201:
            print(f"SUCCESS: Calendar event '{subject}' created.")
            self.log_activity(f"Calendar event created: {subject}", hours=1.0, category="Administrative")
            return True
        else:
            print(f"FAILURE: Status {response.status_code} - {response.text}")
            return False

if __name__ == "__main__":
    # Institutional Test Execution
    engine = MicrosoftMarketingEngine()
    test_html = """
    <html>
    <body>
        <h2 style='color: #004aad;'>SigmaFidelity™ Service Excellence</h2>
        <p>This is an automated test of the HWB Cleaning Services LLC marketing engine.</p>
        <p><b>Fidelity. Safety. Respect.</b></p>
        <hr>
        <p style='font-size: 0.8rem; color: #666;'>HWB Cleaning Services LLC | Institutional Marketing Division</p>
    </body>
    </html>
    """
    # By default, this will now STAGE the email
    engine.send_marketing_email("humbertoed@gmail.com", "SigmaFidelity™ Marketing Engine Test", test_html)
