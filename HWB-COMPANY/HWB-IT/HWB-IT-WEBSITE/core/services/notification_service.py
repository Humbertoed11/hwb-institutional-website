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


def dispatch_lead_notifications(lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Master dispatch coordinator. Executes direct email transmission
    and Telegram push notifications. Designed to run synchronously or
    inside the EnterpriseTaskQueue background worker.
    """
    results = {}
    print(f"[NOTIFY] Initiating dual-channel lead dispatch for: {lead_data.get('company')}", flush=True)

    # Channel 1: Telegram Push Alert
    tg_ok, tg_msg = send_lead_telegram_alert(lead_data)
    results["telegram"] = {"success": tg_ok, "detail": tg_msg}

    # Channel 2: Microsoft Graph Email Transmission
    em_ok, em_msg = send_lead_email_alert(lead_data)
    results["email"] = {"success": em_ok, "detail": em_msg}

    print(f"[NOTIFY] Dual-channel dispatch finished. Telegram: {tg_ok}, Email: {em_ok}", flush=True)
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


def dispatch_applicant_notifications(applicant_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Master dispatch coordinator for technician job applicants.
    Executes email transmission and Telegram push notifications.
    """
    results = {}
    print(f"[NOTIFY] Initiating dual-channel applicant dispatch for: {applicant_data.get('full_name')}", flush=True)

    tg_ok, tg_msg = send_applicant_telegram_alert(applicant_data)
    results["telegram"] = {"success": tg_ok, "detail": tg_msg}

    em_ok, em_msg = send_applicant_email_alert(applicant_data)
    results["email"] = {"success": em_ok, "detail": em_msg}

    print(f"[NOTIFY] Applicant dispatch finished. Telegram: {tg_ok}, Email: {em_ok}", flush=True)
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


def dispatch_subcontractor_notifications(partner_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Master dispatch coordinator for 1099 subcontractor cleaning crew registrations.
    Executes email transmission and Telegram push notifications.
    """
    results = {}
    print(f"[NOTIFY] Initiating dual-channel subcontractor dispatch for: {partner_data.get('company_name')}", flush=True)

    tg_ok, tg_msg = send_subcontractor_telegram_alert(partner_data)
    results["telegram"] = {"success": tg_ok, "detail": tg_msg}

    em_ok, em_msg = send_subcontractor_email_alert(partner_data)
    results["email"] = {"success": em_ok, "detail": em_msg}

    print(f"[NOTIFY] Subcontractor dispatch finished. Telegram: {tg_ok}, Email: {em_ok}", flush=True)
    return results
