"""
SigmaFidelity™ Microsoft Graph Calendar Service
Standard: HWB-COM-001 & HWB-QMS-11.2 (Executive Observability & Calendar Synchronization)
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import requests
import msal
from flask import current_app


def get_graph_calendar_credentials() -> Tuple[Optional[str], Optional[str], Optional[str], str]:
    """Retrieves Microsoft Graph credentials from Flask config or environment variables."""
    config = current_app.config if current_app else os.environ

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
              os.environ.get("GRAPH_USER_ID") or \
              os.environ.get("OFFICE365_USER_EMAIL") or \
              "hdominguez@hwbcleaning.com"

    return client_id, client_secret, tenant_id, user_id


def get_calendar_graph_token() -> Optional[str]:
    """Acquires a confidential client OAuth2 token from Microsoft Graph API."""
    client_id, client_secret, tenant_id, _ = get_graph_calendar_credentials()
    if not all([client_id, client_secret, tenant_id]):
        print("[CALENDAR SERVICE] Error: Missing Microsoft Graph credentials in environment.", flush=True)
        return None

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    try:
        app_msal = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=client_secret
        )
        result = app_msal.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        return result.get("access_token")
    except Exception as e:
        print(f"[CALENDAR SERVICE] Token acquisition failed: {e}", flush=True)
        return None


def create_calendar_event(
    subject: str,
    start_iso: str,
    end_iso: str,
    body_html: str,
    location_text: str = "",
    attendee_email: Optional[str] = None,
    attendee_name: Optional[str] = None,
    user_id: Optional[str] = None,
    additional_attendees: Optional[list] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Creates an official calendar event on Humberto Dominguez's Microsoft Outlook Calendar
    and optionally sends meeting invites to the lead attendee and remote rep attendees.
    """
    token = get_calendar_graph_token()
    if not token:
        return False, "Failed to acquire Microsoft Graph OAuth2 token.", None

    _, _, _, default_user = get_graph_calendar_credentials()
    target_user = user_id or default_user

    endpoint = f"https://graph.microsoft.com/v1.0/users/{target_user}/events"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    event_payload: Dict[str, Any] = {
        "subject": subject,
        "body": {
            "contentType": "HTML",
            "content": body_html
        },
        "start": {
            "dateTime": start_iso,
            "timeZone": "Central Standard Time"
        },
        "end": {
            "dateTime": end_iso,
            "timeZone": "Central Standard Time"
        },
        "location": {
            "displayName": location_text
        }
    }

    attendees_list = []
    if attendee_email and str(attendee_email).strip():
        clean_email = str(attendee_email).strip()
        if '@' in clean_email:
            attendees_list.append({
                "emailAddress": {
                    "address": clean_email,
                    "name": attendee_name or clean_email
                },
                "type": "required"
            })

    if additional_attendees:
        for att in additional_attendees:
            if isinstance(att, dict) and att.get("email"):
                clean_att = str(att["email"]).strip()
                if clean_att and '@' in clean_att:
                    attendees_list.append({
                        "emailAddress": {
                            "address": clean_att,
                            "name": att.get("name") or clean_att
                        },
                        "type": att.get("type", "required")
                    })
            elif isinstance(att, str) and '@' in att:
                clean_att = att.strip()
                attendees_list.append({
                    "emailAddress": {
                        "address": clean_att,
                        "name": clean_att
                    },
                    "type": "required"
                })

    if attendees_list:
        event_payload["attendees"] = attendees_list

    try:
        res = requests.post(endpoint, headers=headers, json=event_payload, timeout=20)
        if res.status_code in [200, 201]:
            data = res.json()
            return True, "Walkthrough appointment scheduled on Microsoft Outlook calendar.", data
        error_msg = f"Graph API HTTP {res.status_code}: {res.text[:200]}"
        print(f"[CALENDAR SERVICE] Event creation error: {error_msg}", flush=True)
        return False, error_msg, None
    except Exception as e:
        print(f"[CALENDAR SERVICE] Request exception: {e}", flush=True)
        return False, str(e), None
