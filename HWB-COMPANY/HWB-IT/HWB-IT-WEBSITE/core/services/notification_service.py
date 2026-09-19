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

def send_lead_telegram_alert(lead_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Transmits an instant push notification to CEO Humberto Dominguez's
    mobile device via the Georgebytes Telegram bot gateway.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "8564340073")

    if not bot_token:
        print("[NOTIFY_WARN] TELEGRAM_BOT_TOKEN not configured in environment.", flush=True)
        return False, "Missing Bot Token"

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
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        res = requests.post(url, json=payload, timeout=8)
        if res.status_code == 200:
            print(f"[NOTIFY] Telegram alert sent to {chat_id} for lead: {company}", flush=True)
            return True, "Success"
        err_msg = f"Telegram HTTP {res.status_code}: {res.text}"
        print(f"[NOTIFY_WARN] {err_msg}", flush=True)
        return False, err_msg
    except Exception as e:
        err_msg = f"Telegram Exception: {e}"
        print(f"[NOTIFY_WARN] {err_msg}", flush=True)
        return False, err_msg


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
