"""
SigmaFidelity™ Real-Time Lead Notification Service
Standard: HWB-QMS-7.6 Enterprise Architecture & High-Velocity Telemetry
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
import requests
from typing import Dict, Any, Tuple
from core.services.email_service import transmit_email
from core.services.sanitizer import clean_phone, clean_email

def get_active_telegram_recipients() -> list:
    """
    Collects all authorized Telegram Chat IDs from environment and PostgreSQL Users table.
    Ensures multi-user dispatch to CEO Humberto Dominguez, Mirna Rondinella, and key operations staff.
    """
    recipients = set()
    # 1. Environment variable fallback (supports single or comma-delimited string)
    env_ids = os.environ.get("TELEGRAM_CHAT_ID", "8564340073")
    for cid in env_ids.split(","):
        cid = cid.strip()
        if cid:
            recipients.add(cid)

    # 2. Database query for active users with linked Telegram Chat IDs
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        try:
            import psycopg2
            conn = psycopg2.connect(db_url)
            with conn.cursor() as cur:
                cur.execute('SELECT telegram_chat_id FROM "Users" WHERE status = \'Active\' AND telegram_chat_id IS NOT NULL AND telegram_chat_id != \'\';')
                for row in cur.fetchall():
                    if row[0]:
                        recipients.add(str(row[0]).strip())
            conn.close()
        except Exception as e:
            print(f"[NOTIFY_DEBUG] DB telegram recipients query skipped: {e}", flush=True)

    return list(recipients)


def send_lead_telegram_alert(lead_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Transmits an instant push notification to authorized team members
    via the Georgebytes Telegram bot gateway.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_ids = get_active_telegram_recipients()

    if not bot_token:
        print("[NOTIFY_WARN] TELEGRAM_BOT_TOKEN not configured in environment.", flush=True)
        return False, "Missing Bot Token"

    if not chat_ids:
        print("[NOTIFY_WARN] No active Telegram recipients configured.", flush=True)
        return False, "No Recipients Configured"

    company = lead_data.get("company") or "Unknown Facility"
    name = lead_data.get("name") or "Website Visitor"
    phone = clean_phone(lead_data.get("phone")) or lead_data.get("phone") or "Not Provided"
    email = clean_email(lead_data.get("email")) or lead_data.get("email") or "Not Provided"
    facility_type = lead_data.get("facility_type") or "Commercial Property"
    sqft = lead_data.get("sqft") or "Pending Verification"
    frequency = lead_data.get("frequency") or lead_data.get("traffic_cycle") or "Pending Review"
    annual_val = lead_data.get("annual_value", 0)

    val_display = f"${int(annual_val):,}" if annual_val and float(annual_val) > 0 else "Pending Scoping"

    message = (
        "🚨 *NEW INCOMING WEBSITE LEAD*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏢 *Company:* {company}\n"
        f"👤 *Contact:* {name}\n"
        f"📞 *Phone:* `{phone}`\n"
        f"✉️ *Email:* {email}\n"
        f"🏭 *Facility:* {facility_type} ({sqft} SQF)\n"
        f"🔄 *Frequency:* {frequency}\n"
        f"💰 *Est. Annual Value:* {val_display}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚡ _Lead captured live via https://hwbcleaning.com/get-quote_"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    delivered_count = 0
    last_error = ""

    for target_chat_id in chat_ids:
        payload = {
            "chat_id": target_chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                print(f"[NOTIFY] Telegram alert sent to {target_chat_id} for lead: {company}", flush=True)
                delivered_count += 1
            else:
                last_error = f"Telegram HTTP {res.status_code}: {res.text}"
                print(f"[NOTIFY_WARN] Failed to send to {target_chat_id}: {last_error}", flush=True)
        except Exception as e:
            last_error = f"Telegram Exception: {e}"
            print(f"[NOTIFY_WARN] Error sending to {target_chat_id}: {last_error}", flush=True)

    if delivered_count > 0:
        return True, "Success"
    return False, last_error or "Delivery Failed"


def send_lead_email_alert(lead_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Transmits an instant high-fidelity HTML email alert to executive inboxes
    via Microsoft Graph API.
    """
    company = lead_data.get("company") or "Unknown Facility"
    name = lead_data.get("name") or "Website Visitor"
    phone = clean_phone(lead_data.get("phone")) or lead_data.get("phone") or "Not Provided"
    email = clean_email(lead_data.get("email")) or lead_data.get("email") or "Not Provided"
    facility_type = lead_data.get("facility_type") or "Commercial Facility"
    sqft = lead_data.get("sqft") or "Pending Verification"
    frequency = lead_data.get("frequency") or lead_data.get("traffic_cycle") or "Pending Review"
    form_version = lead_data.get("form_version", "v1")
    annual_val = lead_data.get("annual_value", 0)

    val_display = f"${int(annual_val):,}" if annual_val and float(annual_val) > 0 else "Pending Scoping"
    request_type = "Quick Registration (2-Step)" if form_version == "v2" else "Full Janitorial Scope"

    recipients = ["hdominguez@hwbcleaning.com", "sales@hwbcleaning.com"]
    # Include primary personal inbox for CEO redundancy if needed
    personal_inbox = os.environ.get("CEO_PERSONAL_EMAIL", "humbertoed@gmail.com")
    if personal_inbox and personal_inbox not in recipients:
        recipients.append(personal_inbox)

    subject = f"🔥 ACTION REQUIRED: New Lead Ingested - {company} ({facility_type})"

    body_html = f"""
    <div style="font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; padding: 30px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; max-width: 620px; margin: 0 auto; color: #0f172a;">
        <div style="border-bottom: 3px solid #2563eb; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-weight: 900; font-size: 20px; color: #2563eb; letter-spacing: -0.02em;">HWB CLEANING SERVICES</div>
                <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.12em; margin-top: 4px; font-weight: 700;">Instant Lead Capture Engine</div>
            </div>
            <div style="background-color: #dbeafe; color: #1e40af; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 9999px;">
                {request_type}
            </div>
        </div>

        <div style="background-color: #ffffff; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 24px;">
            <h2 style="font-size: 16px; font-weight: 800; color: #0f172a; margin-top: 0; margin-bottom: 16px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
                Prospective Customer Information
            </h2>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px; line-height: 1.6;">
                <tr>
                    <td style="padding: 6px 0; color: #64748b; width: 38%; font-weight: 600;">Business Name:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{company}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Contact Person:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{name}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Phone Number:</td>
                    <td style="padding: 6px 0;">
                        <a href="tel:{phone}" style="color: #2563eb; font-weight: 700; text-decoration: none;">📞 {phone}</a>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Email Address:</td>
                    <td style="padding: 6px 0;">
                        <a href="mailto:{email}" style="color: #2563eb; font-weight: 700; text-decoration: none;">✉️ {email}</a>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Facility Type:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{facility_type}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Estimated Footprint:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{sqft} SQF</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Cleaning Frequency:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{frequency}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Est. Annual Value:</td>
                    <td style="padding: 6px 0; color: #16a34a; font-weight: 800; font-size: 15px;">{val_display}</td>
                </tr>
            </table>
        </div>

        <div style="text-align: center; margin-bottom: 24px;">
            <a href="tel:{phone}" style="display: inline-block; background-color: #2563eb; color: #ffffff; padding: 12px 28px; border-radius: 6px; font-weight: 700; font-size: 14px; text-decoration: none; margin-right: 12px;">
                Call Lead Immediately
            </a>
            <a href="https://hwbcleaning.com/admin/operations?view=leads" style="display: inline-block; background-color: #ffffff; color: #334155; border: 1px solid #cbd5e1; padding: 12px 24px; border-radius: 6px; font-weight: 600; font-size: 14px; text-decoration: none;">
                View in CRM
            </a>
        </div>

        <div style="font-size: 12px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 16px;">
            SigmaFidelity™ Autonomous Lead Routing Engine • Real-Time Notification System
        </div>
    </div>
    """

    return transmit_email(recipients, subject, body_html)


def send_lead_receipt_email(lead_data: Dict[str, Any], is_repeat: bool = False) -> Tuple[bool, str]:
    """
    Sends an automated quote confirmation receipt email to the prospective client
    with their Reference Code (LEAD-#00XXX).
    """
    client_email = clean_email(lead_data.get("email"))
    if not client_email or client_email.endswith((".test", ".local", ".invalid", "@example.com")):
        return False, "No routable client email provided"

    company = lead_data.get("company") or "Your Facility"
    contact = lead_data.get("name") or "Facility Manager"
    ref_code = lead_data.get("reference_code") or f"LEAD-#{int(lead_data.get('lead_id') or 0):05d}"
    frequency = lead_data.get("frequency") or "Custom Cleaning Schedule"
    city = lead_data.get("city") or "DFW Metroplex"

    if is_repeat:
        subject = f"HWB Cleaning Services — Quote Request Updated ({ref_code})"
        headline = "Your Existing Quote Request Has Been Updated"
        intro = (
            f"Hello {contact}, we already had an active commercial cleaning request on file for "
            f"<strong>{company}</strong>. We have updated your existing record with your latest building details."
        )
    else:
        subject = f"HWB Cleaning Services — Quote Request Received ({ref_code})"
        headline = "We Have Received Your Commercial Cleaning Request"
        intro = (
            f"Hello {contact}, thank you for requesting a commercial cleaning quote for "
            f"<strong>{company}</strong>. Our estimating team has logged your facility details and is preparing your options."
        )

    body_html = f"""
    <div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
        <div style="border-bottom: 3px solid #2563eb; padding-bottom: 16px; margin-bottom: 24px;">
            <div style="font-size: 11px; font-weight: 800; color: #2563eb; text-transform: uppercase; letter-spacing: 0.1em;">HWB Cleaning Services LLC &bull; Commercial Estimating</div>
            <h2 style="margin: 6px 0 0 0; font-size: 20px; font-weight: 800; color: #0f172a;">{headline}</h2>
        </div>
        <p style="font-size: 14px; line-height: 1.6; color: #334155;">{intro}</p>
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <div style="font-size: 12px; color: #64748b; font-weight: 700; text-transform: uppercase;">Quote Reference Number</div>
            <div style="font-size: 18px; font-weight: 900; color: #0f172a; margin-top: 4px;">{ref_code}</div>
            <div style="font-size: 13px; color: #475569; margin-top: 8px;">
                <strong>Facility:</strong> {company} ({city})<br>
                <strong>Requested Schedule:</strong> {frequency}
            </div>
        </div>
        <p style="font-size: 13px; line-height: 1.6; color: #475569;">
            Need immediate assistance or want to schedule a site walkthrough right away? Call our commercial desk directly at <strong>(214)-586-0257</strong>.
        </p>
    </div>
    """
    return transmit_email([client_email], subject, body_html)


def dispatch_lead_notifications(lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Master dispatch coordinator. Executes direct email transmission
    and Telegram push notifications. Suppresses duplicate internal alerts
    when a repeat submission updates an existing lead, while still sending
    the client an updated confirmation receipt.
    """
    results = {}
    is_repeat = bool(lead_data.get("is_repeat", False))
    print(f"[NOTIFY] Initiating lead dispatch for: {lead_data.get('company')} (is_repeat={is_repeat})", flush=True)

    if not is_repeat:
        # Channel 1: Telegram Push Alert
        tg_ok, tg_msg = send_lead_telegram_alert(lead_data)
        results["telegram"] = {"success": tg_ok, "detail": tg_msg}

        # Channel 2: Microsoft Graph Email Transmission to Staff
        em_ok, em_msg = send_lead_email_alert(lead_data)
        results["email"] = {"success": em_ok, "detail": em_msg}
    else:
        results["telegram"] = {"success": True, "detail": "Suppressed duplicate staff alert on repeat lead update"}
        results["email"] = {"success": True, "detail": "Suppressed duplicate staff email on repeat lead update"}

    # Channel 3: Confirmation Receipt to Prospective Client
    rec_ok, rec_msg = send_lead_receipt_email(lead_data, is_repeat=is_repeat)
    results["client_receipt"] = {"success": rec_ok, "detail": rec_msg}

    print(f"[NOTIFY] Lead dispatch finished. Results: {results}", flush=True)
    return results


def send_applicant_telegram_alert(applicant_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Transmits an instant push notification for a new technician job application
    via the Georgebytes Telegram bot gateway to CEO Humberto Dominguez and staff.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_ids = get_active_telegram_recipients()

    if not bot_token:
        print("[NOTIFY_WARN] TELEGRAM_BOT_TOKEN not configured in environment.", flush=True)
        return False, "Missing Bot Token"

    if not chat_ids:
        print("[NOTIFY_WARN] No active Telegram recipients configured.", flush=True)
        return False, "No Recipients Configured"

    full_name = applicant_data.get("full_name") or "New Applicant"
    phone = clean_phone(applicant_data.get("phone")) or applicant_data.get("phone") or "Not Provided"
    email = clean_email(applicant_data.get("email")) or applicant_data.get("email") or "Not Provided"
    city = applicant_data.get("city") or "DFW Metro"
    desired_role = applicant_data.get("desired_role") or "Commercial Cleaning Technician"
    desired_shift = applicant_data.get("desired_shift") or "Night"
    experience = applicant_data.get("experience_level") or "1-2 Years"
    has_transport = "Yes (Reliable Vehicle)" if applicant_data.get("has_transportation") else "No Personal Vehicle"
    authorized_us = "Yes (Authorized)" if applicant_data.get("authorized_to_work_us") else "Pending Verification"
    language = applicant_data.get("preferred_language") or "English"
    notes = applicant_data.get("notes") or "Submitted via online application."
    applicant_id = applicant_data.get("applicant_id") or "NEW"
    is_sales = any(k in (desired_role or '').lower() for k in ['sales', 'account executive', 'b2b', 'representative'])
    alert_header = "💼 *NEW COMMERCIAL SALES APPLICANT*" if is_sales else "🚨 *NEW CLEANING TECHNICIAN APPLICANT*"

    message = (
        f"{alert_header}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Candidate:* {full_name}\n"
        f"📞 *Phone:* `{phone}`\n"
        f"✉️ *Email:* {email}\n"
        f"📍 *Location:* {city}, TX\n"
        f"💼 *Role:* {desired_role}\n"
        f"⏰ *Shift:* {desired_shift}\n"
        f"⭐ *Experience:* {experience}\n"
        f"🚗 *Vehicle:* {has_transport}\n"
        f"🪪 *Work Auth:* {authorized_us}\n"
        f"🗣️ *Language:* {language}\n"
        f"📝 *Notes:* {notes}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Applicant Code:* APP-#{applicant_id}\n"
        "⚡ _Application captured live via https://hwbcleaning.com/work-with-us_"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    delivered_count = 0
    last_error = ""

    for target_chat_id in chat_ids:
        payload = {
            "chat_id": target_chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                print(f"[NOTIFY] Telegram alert sent to {target_chat_id} for applicant: {full_name}", flush=True)
                delivered_count += 1
            else:
                last_error = f"Telegram HTTP {res.status_code}: {res.text}"
                print(f"[NOTIFY_WARN] Failed to send to {target_chat_id}: {last_error}", flush=True)
        except Exception as e:
            last_error = f"Telegram Exception: {e}"
            print(f"[NOTIFY_WARN] Error sending to {target_chat_id}: {last_error}", flush=True)

    if delivered_count > 0:
        return True, "Success"
    return False, last_error or "Delivery Failed"


def send_applicant_email_alert(applicant_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Transmits an instant high-fidelity HTML email alert to executive inboxes
    via Microsoft Graph API for cleaning technician job applicants.
    """
    full_name = applicant_data.get("full_name") or "New Applicant"
    phone = clean_phone(applicant_data.get("phone")) or applicant_data.get("phone") or "Not Provided"
    email = clean_email(applicant_data.get("email")) or applicant_data.get("email") or "Not Provided"
    city = applicant_data.get("city") or "DFW Metro"
    desired_role = applicant_data.get("desired_role") or "Commercial Cleaning Technician"
    desired_shift = applicant_data.get("desired_shift") or "Night"
    experience = applicant_data.get("experience_level") or "1-2 Years"
    has_transport = "Yes (Reliable Vehicle)" if applicant_data.get("has_transportation") else "No Personal Vehicle"
    authorized_us = "Yes (Authorized)" if applicant_data.get("authorized_to_work_us") else "Pending Verification"
    language = applicant_data.get("preferred_language") or "English"
    notes = applicant_data.get("notes") or "Submitted via online application."
    applicant_id = applicant_data.get("applicant_id") or "NEW"
    is_sales = any(k in (desired_role or '').lower() for k in ['sales', 'account executive', 'b2b', 'representative'])

    recipients = ["hdominguez@hwbcleaning.com", "sales@hwbcleaning.com"]
    personal_inbox = os.environ.get("CEO_PERSONAL_EMAIL", "humbertoed@gmail.com")
    if personal_inbox and personal_inbox not in recipients:
        recipients.append(personal_inbox)

    if is_sales:
        subject = f"💼 ACTION REQUIRED: New Sales & Revenue Applicant - {full_name} ({desired_role})"
        badge_label = "Sales & Growth Team"
        badge_bg = "#eff6ff"
        badge_color = "#1e40af"
        header_color = "#2563eb"
        title_header = "Commercial Sales Candidate Details"
    else:
        subject = f"🔥 ACTION REQUIRED: New Technician Applicant - {full_name} ({desired_role})"
        badge_label = "W-2 Candidate"
        badge_bg = "#d1fae5"
        badge_color = "#065f46"
        header_color = "#059669"
        title_header = "Technician Applicant Details"

    body_html = f"""
    <div style="font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; padding: 30px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; max-width: 620px; margin: 0 auto; color: #0f172a;">
        <div style="border-bottom: 3px solid {header_color}; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-weight: 900; font-size: 20px; color: #0f172a; letter-spacing: -0.02em;">HWB CLEANING SERVICES</div>
                <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.12em; margin-top: 4px; font-weight: 700;">Workforce Intake Gateway</div>
            </div>
            <div style="background-color: {badge_bg}; color: {badge_color}; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 9999px;">
                {badge_label}
            </div>
        </div>

        <div style="background-color: #ffffff; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; margin-bottom: 16px;">
                <h2 style="font-size: 16px; font-weight: 800; color: #0f172a; margin: 0;">
                    {title_header}
                </h2>
                <span style="font-size: 12px; font-weight: 800; color: {header_color}; background: {badge_bg}; padding: 2px 8px; border-radius: 4px;">APP-#{applicant_id}</span>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px; line-height: 1.6;">
                <tr>
                    <td style="padding: 6px 0; color: #64748b; width: 38%; font-weight: 600;">Candidate Name:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{full_name}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Phone Number:</td>
                    <td style="padding: 6px 0;">
                        <a href="tel:{phone}" style="color: #059669; font-weight: 700; text-decoration: none;">📞 {phone}</a>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Email Address:</td>
                    <td style="padding: 6px 0;">
                        <a href="mailto:{email}" style="color: #059669; font-weight: 700; text-decoration: none;">✉️ {email}</a>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Location:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{city}, TX</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Desired Position:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{desired_role}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Desired Shift:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{desired_shift} Shift</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Commercial Experience:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{experience}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Reliable Transport:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{has_transport}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">US Work Authorization:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{authorized_us}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Preferred Language:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{language}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Applicant Notes:</td>
                    <td style="padding: 6px 0; color: #334155; font-style: italic;">{notes}</td>
                </tr>
            </table>
        </div>

        <div style="text-align: center; margin-bottom: 24px;">
            <a href="tel:{phone}" style="display: inline-block; background-color: #059669; color: #ffffff; padding: 12px 28px; border-radius: 6px; font-weight: 700; font-size: 14px; text-decoration: none; margin-right: 12px;">
                Call Candidate
            </a>
            <a href="https://hwbcleaning.com/admin/operations?view=workforce" style="display: inline-block; background-color: #ffffff; color: #334155; border: 1px solid #cbd5e1; padding: 12px 24px; border-radius: 6px; font-weight: 600; font-size: 14px; text-decoration: none;">
                View in Workforce Hub
            </a>
        </div>

        <div style="font-size: 12px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 16px;">
            SigmaFidelity™ Autonomous Workforce Routing Engine • Real-Time Notification System
        </div>
    </div>
    """
    return transmit_email(recipients, subject, body_html)


def send_applicant_receipt_email(applicant_data: Dict[str, Any], is_repeat: bool = False) -> Tuple[bool, str]:
    """
    Sends an automated confirmation receipt directly to the job applicant's inbox
    so they have proof of application and do not submit duplicate forms.
    """
    email = clean_email(applicant_data.get("email"))
    if not email or email.endswith((".test", ".local", ".invalid", "@example.com")):
        return False, "Skipped non-routable or missing applicant email"

    full_name = applicant_data.get("full_name") or "Applicant"
    desired_role = applicant_data.get("desired_role") or "Commercial Cleaning Technician"
    desired_shift = applicant_data.get("desired_shift") or "Night"
    city = applicant_data.get("city") or "DFW Metroplex"
    applicant_id = applicant_data.get("applicant_id") or "0001"
    registered_date = applicant_data.get("registered_date") or "Today"
    ref_code = f"APP-#{int(applicant_id):04d}" if str(applicant_id).isdigit() else f"APP-#{applicant_id}"

    if is_repeat:
        subject = f"HWB Cleaning Services — Application Already on File & Updated ({ref_code})"
        banner_title = "Existing Application Recognized & Updated"
        intro_text = (
            f"We already have your application on file as of <strong>{registered_date}</strong> "
            f"(Reference <strong>{ref_code}</strong>). Instead of creating a duplicate record, "
            "we have updated your existing candidate profile with your latest information."
        )
    else:
        subject = f"HWB Cleaning Services — Job Application Received ({ref_code})"
        banner_title = "Application Received & On File"
        intro_text = (
            f"Thank you for applying with <strong>HWB Cleaning Services LLC</strong>. "
            f"Your candidate profile has been saved in our hiring system under Reference <strong>{ref_code}</strong>."
        )

    body_html = f"""
    <div style="font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; padding: 30px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; max-width: 600px; margin: 0 auto; color: #0f172a;">
        <div style="border-bottom: 3px solid #059669; padding-bottom: 16px; margin-bottom: 24px;">
            <div style="font-weight: 900; font-size: 20px; color: #0f172a;">HWB CLEANING SERVICES LLC</div>
            <div style="font-size: 12px; color: #059669; font-weight: 700; margin-top: 4px;">{banner_title} • {ref_code}</div>
        </div>
        <div style="background-color: #ffffff; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; font-size: 14px; line-height: 1.6;">
            <p style="margin-top: 0;">Hello <strong>{full_name}</strong>,</p>
            <p>{intro_text}</p>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin: 16px 0;">
                <tr>
                    <td style="padding: 6px 0; color: #64748b; width: 42%; font-weight: 600;">Reference Number:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 800;">{ref_code}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Position Applied For:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{desired_role}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Preferred Shift & City:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{desired_shift} Shift • {city}, TX</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Application Status:</td>
                    <td style="padding: 6px 0; color: #059669; font-weight: 700;">Active / In Hiring Review</td>
                </tr>
            </table>
            <p style="margin-bottom: 0; color: #475569;">
                <strong>What happens next:</strong> You do not need to submit another application. Our hiring supervisors review active profiles as routes open in your area and will reach out to you directly if a matching shift is available.
            </p>
        </div>
        <div style="font-size: 12px; color: #64748b; text-align: center;">
            HWB Cleaning Services LLC • (214)-586-0257 • sales@hwbcleaning.com
        </div>
    </div>
    """
    return transmit_email([email], subject, body_html)


def dispatch_applicant_notifications(applicant_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Master dispatch coordinator for technician job applicants.
    Executes email transmission, Telegram push notifications, and candidate confirmation receipt.
    """
    results = {}
    is_repeat = bool(applicant_data.get("is_repeat", False))
    print(f"[NOTIFY] Initiating applicant dispatch for: {applicant_data.get('full_name')} (repeat={is_repeat})", flush=True)

    if not is_repeat:
        tg_ok, tg_msg = send_applicant_telegram_alert(applicant_data)
        results["telegram"] = {"success": tg_ok, "detail": tg_msg}

        em_ok, em_msg = send_applicant_email_alert(applicant_data)
        results["email"] = {"success": em_ok, "detail": em_msg}
    else:
        results["telegram"] = {"success": True, "detail": "Suppressed duplicate alert for existing applicant"}
        results["email"] = {"success": True, "detail": "Suppressed duplicate internal alert for existing applicant"}

    rc_ok, rc_msg = send_applicant_receipt_email(applicant_data, is_repeat=is_repeat)
    results["applicant_receipt"] = {"success": rc_ok, "detail": rc_msg}

    print(f"[NOTIFY] Applicant dispatch finished. Repeat: {is_repeat}, Receipt: {rc_ok}", flush=True)
    return results


def send_subcontractor_telegram_alert(partner_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Transmits an instant push notification for a new 1099 cleaning subcontractor
    via the Georgebytes Telegram bot gateway to CEO Humberto Dominguez and staff.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_ids = get_active_telegram_recipients()

    if not bot_token:
        print("[NOTIFY_WARN] TELEGRAM_BOT_TOKEN not configured in environment.", flush=True)
        return False, "Missing Bot Token"

    if not chat_ids:
        print("[NOTIFY_WARN] No active Telegram recipients configured.", flush=True)
        return False, "No Recipients Configured"

    company_name = partner_data.get("company_name") or "New Trade Partner"
    contact_name = partner_data.get("contact_name") or "Trade Principal"
    phone = clean_phone(partner_data.get("phone")) or partner_data.get("phone") or "Not Provided"
    email = clean_email(partner_data.get("email")) or partner_data.get("email") or "Not Provided"
    city = partner_data.get("city") or "DFW Metro"
    crew_size = partner_data.get("crew_size") or 2
    specialties = partner_data.get("specialties") or "Commercial Cleaning"
    hourly_rate = partner_data.get("hourly_rate_range") or "Negotiable"
    dwc83_status = "Agreed / Signed ✓" if partner_data.get("dwc83_agreed") or partner_data.get("dwc83_signed") else "Pending Agreement"
    notes = partner_data.get("notes") or "Registered via 1099 partner portal."
    partner_id = partner_data.get("partner_id") or "NEW"

    message = (
        "🚨 *NEW 1099 SUBCONTRACTOR REGISTERED*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏢 *Company:* {company_name}\n"
        f"👤 *Contact:* {contact_name}\n"
        f"📞 *Phone:* `{phone}`\n"
        f"✉️ *Email:* {email}\n"
        f"📍 *Operating Hub:* {city}, TX\n"
        f"👥 *Crew Size:* {crew_size} Cleaners\n"
        f"🛠️ *Specialties:* {specialties}\n"
        f"💵 *Target Rate:* {hourly_rate}\n"
        f"📄 *TX DWC-83:* {dwc83_status}\n"
        f"📝 *Notes:* {notes}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Partner Code:* SUB-#{partner_id}\n"
        "⚡ _Subcontractor registered live via https://hwbcleaning.com/work-with-us_"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    delivered_count = 0
    last_error = ""

    for target_chat_id in chat_ids:
        payload = {
            "chat_id": target_chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                print(f"[NOTIFY] Telegram alert sent to {target_chat_id} for subcontractor: {company_name}", flush=True)
                delivered_count += 1
            else:
                last_error = f"Telegram HTTP {res.status_code}: {res.text}"
                print(f"[NOTIFY_WARN] Failed to send to {target_chat_id}: {last_error}", flush=True)
        except Exception as e:
            last_error = f"Telegram Exception: {e}"
            print(f"[NOTIFY_WARN] Error sending to {target_chat_id}: {last_error}", flush=True)

    if delivered_count > 0:
        return True, "Success"
    return False, last_error or "Delivery Failed"


def send_subcontractor_email_alert(partner_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Transmits an instant high-fidelity HTML email alert to executive inboxes
    via Microsoft Graph API for 1099 cleaning crew subcontractor registrations.
    """
    company_name = partner_data.get("company_name") or "New Trade Partner"
    contact_name = partner_data.get("contact_name") or "Trade Principal"
    phone = clean_phone(partner_data.get("phone")) or partner_data.get("phone") or "Not Provided"
    email = clean_email(partner_data.get("email")) or partner_data.get("email") or "Not Provided"
    city = partner_data.get("city") or "DFW Metro"
    crew_size = partner_data.get("crew_size") or 2
    specialties = partner_data.get("specialties") or "Commercial Cleaning"
    hourly_rate = partner_data.get("hourly_rate_range") or "Negotiable"
    dwc83_status = "Agreed / Signed ✓" if partner_data.get("dwc83_agreed") or partner_data.get("dwc83_signed") else "Pending Agreement"
    notes = partner_data.get("notes") or "Registered via 1099 partner portal."
    partner_id = partner_data.get("partner_id") or "NEW"

    recipients = ["hdominguez@hwbcleaning.com", "sales@hwbcleaning.com"]
    personal_inbox = os.environ.get("CEO_PERSONAL_EMAIL", "humbertoed@gmail.com")
    if personal_inbox and personal_inbox not in recipients:
        recipients.append(personal_inbox)

    subject = f"🤝 ACTION REQUIRED: New 1099 Subcontractor Crew - {company_name} ({crew_size} Cleaners)"

    body_html = f"""
    <div style="font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; padding: 30px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; max-width: 620px; margin: 0 auto; color: #0f172a;">
        <div style="border-bottom: 3px solid #7c3aed; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-weight: 900; font-size: 20px; color: #0f172a; letter-spacing: -0.02em;">HWB CLEANING SERVICES</div>
                <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.12em; margin-top: 4px; font-weight: 700;">Subcontractor Trade Network</div>
            </div>
            <div style="background-color: #ede9fe; color: #6d28d9; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 9999px;">
                1099 Partner Crew
            </div>
        </div>

        <div style="background-color: #ffffff; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; margin-bottom: 16px;">
                <h2 style="font-size: 16px; font-weight: 800; color: #0f172a; margin: 0;">
                    Trade Partner Registration Details
                </h2>
                <span style="font-size: 12px; font-weight: 800; color: #7c3aed; background: #ede9fe; padding: 2px 8px; border-radius: 4px;">SUB-#{partner_id}</span>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px; line-height: 1.6;">
                <tr>
                    <td style="padding: 6px 0; color: #64748b; width: 38%; font-weight: 600;">Company Legal Name:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{company_name}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Primary Contact:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{contact_name}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Phone Number:</td>
                    <td style="padding: 6px 0;">
                        <a href="tel:{phone}" style="color: #7c3aed; font-weight: 700; text-decoration: none;">📞 {phone}</a>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Email Address:</td>
                    <td style="padding: 6px 0;">
                        <a href="mailto:{email}" style="color: #7c3aed; font-weight: 700; text-decoration: none;">✉️ {email}</a>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Operating Hub:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{city}, TX</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Crew Capacity:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{crew_size} Cleaners</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Trade Specialties:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{specialties}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Rate Range:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{hourly_rate}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Texas DWC-83 Agreement:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{dwc83_status}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Trade Notes:</td>
                    <td style="padding: 6px 0; color: #334155; font-style: italic;">{notes}</td>
                </tr>
            </table>
        </div>

        <div style="text-align: center; margin-bottom: 24px;">
            <a href="tel:{phone}" style="display: inline-block; background-color: #7c3aed; color: #ffffff; padding: 12px 28px; border-radius: 6px; font-weight: 700; font-size: 14px; text-decoration: none; margin-right: 12px;">
                Call Trade Partner
            </a>
            <a href="https://hwbcleaning.com/admin/operations?view=workforce" style="display: inline-block; background-color: #ffffff; color: #334155; border: 1px solid #cbd5e1; padding: 12px 24px; border-radius: 6px; font-weight: 600; font-size: 14px; text-decoration: none;">
                View in Subcontractors Hub
            </a>
        </div>

        <div style="font-size: 12px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 16px;">
            SigmaFidelity™ Autonomous Workforce Routing Engine • Real-Time Notification System
        </div>
    </div>
    """
    return transmit_email(recipients, subject, body_html)


def send_subcontractor_receipt_email(partner_data: Dict[str, Any], is_repeat: bool = False) -> Tuple[bool, str]:
    """
    Sends an automated confirmation receipt directly to the subcontractor's inbox
    with their Partner Reference ID and W-9 / COI submission instructions.
    """
    email = clean_email(partner_data.get("email"))
    if not email or email.endswith((".test", ".local", ".invalid", "@example.com")):
        return False, "Skipped non-routable or missing partner email"

    company_name = partner_data.get("company_name") or "Trade Partner"
    contact_name = partner_data.get("contact_name") or "Partner"
    city = partner_data.get("city") or "Texas"
    crew_size = partner_data.get("crew_size") or 2
    specialties = partner_data.get("specialties") or "Post-Construction Cleaning"
    partner_id = partner_data.get("partner_id") or "0001"
    registered_date = partner_data.get("registered_date") or "Today"
    partner_status = partner_data.get("partner_status") or "Vetting / In Review"
    ref_code = f"SUB-#{int(partner_id):04d}" if str(partner_id).isdigit() else f"SUB-#{partner_id}"

    if is_repeat:
        subject = f"HWB Cleaning Services — Subcontractor Profile Already Registered & Updated ({ref_code})"
        banner_title = "Existing Partner Profile Recognized & Updated"
        intro_text = (
            f"Your company (<strong>{company_name}</strong>) is already registered in the "
            f"HWB Cleaning Services Subcontractor Partner Network as of <strong>{registered_date}</strong> "
            f"(Partner Reference <strong>{ref_code}</strong>). Instead of creating a duplicate entry, "
            "we have merged your latest crew capacity and specialty selections into your active partner record."
        )
    else:
        subject = f"HWB Cleaning Services — Subcontractor Partner Registration Confirmed ({ref_code})"
        banner_title = "Subcontractor Partner Registration Confirmed"
        intro_text = (
            f"Thank you for registering <strong>{company_name}</strong> with the "
            f"<strong>HWB Cleaning Services LLC</strong> Subcontractor Partner Network. "
            f"Your business is now on file under Partner Reference <strong>{ref_code}</strong>."
        )

    body_html = f"""
    <div style="font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; padding: 30px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; max-width: 600px; margin: 0 auto; color: #0f172a;">
        <div style="border-bottom: 3px solid #2563eb; padding-bottom: 16px; margin-bottom: 24px;">
            <div style="font-weight: 900; font-size: 20px; color: #0f172a;">HWB CLEANING SERVICES LLC</div>
            <div style="font-size: 12px; color: #2563eb; font-weight: 700; margin-top: 4px;">{banner_title} • {ref_code}</div>
        </div>
        <div style="background-color: #ffffff; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; font-size: 14px; line-height: 1.6;">
            <p style="margin-top: 0;">Hello <strong>{contact_name}</strong>,</p>
            <p>{intro_text}</p>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin: 16px 0;">
                <tr>
                    <td style="padding: 6px 0; color: #64748b; width: 42%; font-weight: 600;">Partner Reference ID:</td>
                    <td style="padding: 6px 0; color: #2563eb; font-weight: 800;">{ref_code}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Company Name:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{company_name}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Base City & Crew Size:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{city}, TX • {crew_size} Crew Members</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Trade Specialties:</td>
                    <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{specialties}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Roster Status:</td>
                    <td style="padding: 6px 0; color: #16a34a; font-weight: 700;">{partner_status}</td>
                </tr>
            </table>
            <div style="background-color: #f8fafc; border-left: 4px solid #2563eb; padding: 12px 16px; border-radius: 4px; margin-top: 16px;">
                <strong style="color: #0f172a;">Next Steps for Project Dispatch:</strong><br>
                You do not need to submit the web form again. To complete your compliance file for upcoming bids, please reply to <a href="mailto:sales@hwbcleaning.com" style="color: #2563eb; font-weight: 700;">sales@hwbcleaning.com</a> with your <strong>W-9 Form</strong> and <strong>Certificate of Insurance (COI)</strong> referencing <strong>{ref_code}</strong>.
            </div>
        </div>
        <div style="font-size: 12px; color: #64748b; text-align: center;">
            HWB Cleaning Services LLC • (214)-586-0257 • sales@hwbcleaning.com
        </div>
    </div>
    """
    return transmit_email([email], subject, body_html)


def dispatch_subcontractor_notifications(partner_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Master dispatch coordinator for 1099 subcontractor cleaning crew registrations.
    Executes email transmission, Telegram push notifications, and partner confirmation receipt.
    """
    results = {}
    is_repeat = bool(partner_data.get("is_repeat", False))
    print(f"[NOTIFY] Initiating subcontractor dispatch for: {partner_data.get('company_name')} (repeat={is_repeat})", flush=True)

    if not is_repeat:
        tg_ok, tg_msg = send_subcontractor_telegram_alert(partner_data)
        results["telegram"] = {"success": tg_ok, "detail": tg_msg}

        em_ok, em_msg = send_subcontractor_email_alert(partner_data)
        results["email"] = {"success": em_ok, "detail": em_msg}
    else:
        results["telegram"] = {"success": True, "detail": "Suppressed duplicate alert for existing subcontractor"}
        results["email"] = {"success": True, "detail": "Suppressed duplicate internal alert for existing subcontractor"}

    rc_ok, rc_msg = send_subcontractor_receipt_email(partner_data, is_repeat=is_repeat)
    results["partner_receipt"] = {"success": rc_ok, "detail": rc_msg}

    print(f"[NOTIFY] Subcontractor dispatch finished. Repeat: {is_repeat}, Receipt: {rc_ok}", flush=True)
    return results

