"""
SigmaFidelity™ Microsoft Graph Calendar & Walkthrough Availability Engine
Standard: HWB-COM-001 & HWB-QMS-11.2 (Executive Observability & Calendar Synchronization)
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
import threading
import time
from datetime import date, datetime, time as dt_time, timedelta
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import msal
import requests
from flask import current_app

CHICAGO_TZ = ZoneInfo("America/Chicago")
WALKTHROUGH_DURATION_MINUTES: int = 45
WALKTHROUGH_TRAVEL_BUFFER_MINUTES: int = 60
BOOKABLE_START_HOUR: int = 9
BOOKABLE_END_HOUR: int = 16
SLOT_STEP_MINUTES: int = 30
GRAPH_SCHEDULE_CACHE_TTL_SECONDS: float = 60.0

_GRAPH_SCHEDULE_CACHE_LOCK = threading.Lock()
_GRAPH_SCHEDULE_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}

DFW_ROUTE_CORRIDORS: Dict[str, set] = {
    "north_collin": {
        "mckinney", "frisco", "allen", "plano", "prosper", "celina",
        "melissa", "anna", "princeton", "fairview", "lucas", "murphy",
        "wylie", "sachse", "richardson",
    },
    "denton_northwest": {
        "denton", "lewisville", "flower mound", "carrollton", "the colony",
        "little elm", "corinth", "argyle", "roanoke", "coppell",
        "grapevine", "southlake", "trophy club",
    },
    "dallas_central_east": {
        "dallas", "addison", "farmers branch", "irving", "garland",
        "mesquite", "rowlett", "rockwall", "forney", "sunnyvale",
        "highland park", "university park", "balch springs",
    },
    "mid_cities_tarrant": {
        "fort worth", "arlington", "grand prairie", "euless", "bedford",
        "hurst", "keller", "north richland hills", "haltom city",
        "mansfield", "burleson", "colleyville", "saginaw", "benbrook",
        "weatherford",
    },
    "south_ellis": {
        "waxahachie", "midlothian", "ennis", "red oak", "desoto",
        "cedar hill", "duncanville", "lancaster", "hutchins",
    },
}


def get_graph_calendar_credentials() -> Tuple[Optional[str], Optional[str], Optional[str], str]:
    """Retrieves Microsoft Graph credentials from Flask config or environment variables."""
    config = current_app.config if current_app else os.environ

    client_id = (
        (config.get("GRAPH_CLIENT_ID") if hasattr(config, "get") else None)
        or (config.get("GRAPH_API_PROD_APPLICATION_ID") if hasattr(config, "get") else None)
        or os.environ.get("GRAPH_CLIENT_ID")
        or os.environ.get("GRAPH_API_PROD_APPLICATION_ID")
    )

    client_secret = (
        (config.get("GRAPH_CLIENT_SECRET") if hasattr(config, "get") else None)
        or (config.get("GRAPH_API_PROD_SECRET_VALUE") if hasattr(config, "get") else None)
        or os.environ.get("GRAPH_CLIENT_SECRET")
        or os.environ.get("GRAPH_API_PROD_SECRET_VALUE")
    )

    tenant_id = (
        (config.get("GRAPH_TENANT_ID") if hasattr(config, "get") else None)
        or (config.get("GRAPH_API_PROD_TENANT_ID") if hasattr(config, "get") else None)
        or os.environ.get("GRAPH_TENANT_ID")
        or os.environ.get("GRAPH_API_PROD_TENANT_ID")
    )

    user_id = (
        (config.get("GRAPH_USER_ID") if hasattr(config, "get") else None)
        or os.environ.get("GRAPH_USER_ID")
        or os.environ.get("OFFICE365_USER_EMAIL")
        or "hdominguez@hwbcleaning.com"
    )

    return client_id, client_secret, tenant_id, user_id


def resolve_conductor_mailbox(conductor: Optional[str] = None) -> Tuple[str, str, bool]:
    """
    Maps a Walkthrough Conductor selection to an @hwbcleaning.com mailbox.
    Returns (mailbox_email, display_label, uses_m365_mailbox).
    """
    _, _, _, default_user = get_graph_calendar_credentials()
    raw = (conductor or "").strip()
    lower = raw.lower()
    if not raw or "humberto" in lower or lower == default_user.lower() or lower == "ceo":
        return default_user, "Humberto Dominguez (CEO)", True
    if "@hwbcleaning.com" in lower:
        return lower, raw, True
    return default_user, raw, False


def invalidate_calendar_availability_cache(mailbox: Optional[str] = None) -> None:
    """Clears cached Graph free/busy responses after booking, rescheduling, or cancelling."""
    with _GRAPH_SCHEDULE_CACHE_LOCK:
        if not mailbox:
            _GRAPH_SCHEDULE_CACHE.clear()
            return
        prefix = f"{mailbox.lower()}::"
        stale_keys = [k for k in _GRAPH_SCHEDULE_CACHE if k.startswith(prefix)]
        for key in stale_keys:
            _GRAPH_SCHEDULE_CACHE.pop(key, None)


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
            client_credential=client_secret,
        )
        result = app_msal.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        return result.get("access_token")
    except Exception as exc:
        print(f"[CALENDAR SERVICE] Token acquisition failed: {exc}", flush=True)
        return None


def _build_attendees_list(
    attendee_email: Optional[str] = None,
    attendee_name: Optional[str] = None,
    additional_attendees: Optional[list] = None,
) -> List[Dict[str, Any]]:
    """Normalizes primary and secondary attendee email records for Graph event payloads."""
    attendees_list: List[Dict[str, Any]] = []
    seen = set()
    if attendee_email and str(attendee_email).strip():
        clean_email = str(attendee_email).strip()
        if "@" in clean_email and clean_email.lower() not in seen:
            seen.add(clean_email.lower())
            attendees_list.append(
                {
                    "emailAddress": {
                        "address": clean_email,
                        "name": attendee_name or clean_email,
                    },
                    "type": "required",
                }
            )

    if additional_attendees:
        for att in additional_attendees:
            if isinstance(att, dict) and att.get("email"):
                clean_att = str(att["email"]).strip()
                if clean_att and "@" in clean_att and clean_att.lower() not in seen:
                    seen.add(clean_att.lower())
                    attendees_list.append(
                        {
                            "emailAddress": {
                                "address": clean_att,
                                "name": att.get("name") or clean_att,
                            },
                            "type": att.get("type", "required"),
                        }
                    )
            elif isinstance(att, str) and "@" in att:
                clean_att = att.strip()
                if clean_att.lower() not in seen:
                    seen.add(clean_att.lower())
                    attendees_list.append(
                        {
                            "emailAddress": {
                                "address": clean_att,
                                "name": clean_att,
                            },
                            "type": "required",
                        }
                    )
    return attendees_list


def create_calendar_event(
    subject: str,
    start_iso: str,
    end_iso: str,
    body_html: str,
    location_text: str = "",
    attendee_email: Optional[str] = None,
    attendee_name: Optional[str] = None,
    user_id: Optional[str] = None,
    additional_attendees: Optional[list] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Creates an official calendar event on Microsoft Outlook Calendar
    and optionally sends meeting invites to the lead attendee and sales rep.
    """
    token = get_calendar_graph_token()
    if not token:
        return False, "Failed to acquire Microsoft Graph OAuth2 token.", None

    _, _, _, default_user = get_graph_calendar_credentials()
    target_user = user_id or default_user

    endpoint = f"https://graph.microsoft.com/v1.0/users/{target_user}/events"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    event_payload: Dict[str, Any] = {
        "subject": subject,
        "body": {
            "contentType": "HTML",
            "content": body_html,
        },
        "start": {
            "dateTime": start_iso,
            "timeZone": "Central Standard Time",
        },
        "end": {
            "dateTime": end_iso,
            "timeZone": "Central Standard Time",
        },
        "location": {
            "displayName": location_text,
        },
    }

    attendees_list = _build_attendees_list(attendee_email, attendee_name, additional_attendees)
    if attendees_list:
        event_payload["attendees"] = attendees_list

    try:
        res = requests.post(endpoint, headers=headers, json=event_payload, timeout=12)
        if res.status_code in (200, 201):
            data = res.json()
            invalidate_calendar_availability_cache(target_user)
            return True, "Walkthrough appointment scheduled on Microsoft Outlook calendar.", data
        error_msg = f"Graph API HTTP {res.status_code}: {res.text[:200]}"
        print(f"[CALENDAR SERVICE] Event creation error: {error_msg}", flush=True)
        return False, error_msg, None
    except Exception as exc:
        print(f"[CALENDAR SERVICE] Request exception: {exc}", flush=True)
        return False, str(exc), None


def update_calendar_event(
    event_id: str,
    subject: str,
    start_iso: str,
    end_iso: str,
    body_html: str,
    location_text: str = "",
    attendee_email: Optional[str] = None,
    attendee_name: Optional[str] = None,
    user_id: Optional[str] = None,
    additional_attendees: Optional[list] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Updates an existing Microsoft Outlook event in place when rescheduling a walkthrough
    so zero orphaned duplicate invites remain on the calendar.
    """
    if not event_id:
        return False, "Missing event_id.", None

    token = get_calendar_graph_token()
    if not token:
        return False, "Failed to acquire Microsoft Graph OAuth2 token.", None

    _, _, _, default_user = get_graph_calendar_credentials()
    target_user = user_id or default_user

    endpoint = f"https://graph.microsoft.com/v1.0/users/{target_user}/events/{event_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    patch_payload: Dict[str, Any] = {
        "subject": subject,
        "body": {
            "contentType": "HTML",
            "content": body_html,
        },
        "start": {
            "dateTime": start_iso,
            "timeZone": "Central Standard Time",
        },
        "end": {
            "dateTime": end_iso,
            "timeZone": "Central Standard Time",
        },
        "location": {
            "displayName": location_text,
        },
    }
    attendees_list = _build_attendees_list(attendee_email, attendee_name, additional_attendees)
    if attendees_list:
        patch_payload["attendees"] = attendees_list

    try:
        res = requests.patch(endpoint, headers=headers, json=patch_payload, timeout=12)
        if res.status_code == 200:
            data = res.json()
            invalidate_calendar_availability_cache(target_user)
            return True, "Walkthrough appointment updated on Microsoft Outlook calendar.", data
        if res.status_code == 404:
            invalidate_calendar_availability_cache(target_user)
            return False, "EVENT_NOT_FOUND", None
        error_msg = f"Graph API HTTP {res.status_code}: {res.text[:200]}"
        print(f"[CALENDAR SERVICE] Event update error: {error_msg}", flush=True)
        return False, error_msg, None
    except Exception as exc:
        print(f"[CALENDAR SERVICE] Event update exception: {exc}", flush=True)
        return False, str(exc), None


def delete_calendar_event(
    event_id: str,
    user_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """Deletes a cancelled walkthrough event from Microsoft Outlook Calendar."""
    if not event_id:
        return True, "No external calendar event linked."

    token = get_calendar_graph_token()
    if not token:
        return False, "Failed to acquire Microsoft Graph OAuth2 token."

    _, _, _, default_user = get_graph_calendar_credentials()
    target_user = user_id or default_user
    endpoint = f"https://graph.microsoft.com/v1.0/users/{target_user}/events/{event_id}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        res = requests.delete(endpoint, headers=headers, timeout=12)
        invalidate_calendar_availability_cache(target_user)
        if res.status_code in (200, 204, 404):
            return True, "Outlook calendar invite removed."
        return False, f"Graph API HTTP {res.status_code}: {res.text[:200]}"
    except Exception as exc:
        return False, str(exc)


def _parse_local_datetime(dt_str: str) -> Optional[datetime]:
    """Parses an ISO datetime string returned under Central Standard Time into America/Chicago."""
    if not dt_str:
        return None
    cleaned = str(dt_str).strip().rstrip("Z")
    if "." in cleaned:
        cleaned = cleaned.split(".", 1)[0]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            naive = datetime.strptime(cleaned, fmt)
            return naive.replace(tzinfo=CHICAGO_TZ)
        except ValueError:
            continue
    return None


def _parse_lead_time_str(raw_time: Optional[str]) -> Tuple[int, int]:
    """Parses '10:00 AM' or '14:30' into (hour, minute), defaulting to (10, 0)."""
    if not raw_time:
        return 10, 0
    pt = str(raw_time).strip().upper()
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            parsed = datetime.strptime(pt, fmt)
            return parsed.hour, parsed.minute
        except ValueError:
            continue
    return 10, 0


def _format_12h(dt_obj: datetime) -> str:
    """Formats a datetime as '09:00 AM' / '01:30 PM' matching CRM dropdown values."""
    return dt_obj.strftime("%I:%M %p")


def _same_dfw_corridor(city_a: Optional[str], city_b: Optional[str]) -> bool:
    """Returns True when two DFW cities belong to the same city or neighboring route cluster."""
    ca = (city_a or "").strip().lower()
    cb = (city_b or "").strip().lower()
    if not ca or not cb:
        return False
    if ca == cb:
        return True
    for members in DFW_ROUTE_CORRIDORS.values():
        if ca in members and cb in members:
            return True
    return False


def _is_onsite_outlook_item(subject: str, location: str) -> bool:
    """
    Classifies server-side whether an Outlook schedule item represents an off-site visit
    requiring the 1-hour DFW travel buffer (without ever exposing private text to callers).
    """
    subj_l = (subject or "").strip().lower()
    loc_l = (location or "").strip().lower()
    if any(k in subj_l for k in ("walkthrough", "site visit", "building visit", "inspection", "facility tour")):
        return True
    if loc_l and not any(v in loc_l for v in ("microsoft teams", "zoom", "google meet", "phone", "call", "online", "virtual")):
        return True
    return False


def fetch_graph_free_busy_blocks(
    mailbox: str,
    window_start: datetime,
    window_end: datetime,
    bypass_cache: bool = False,
) -> Dict[str, Any]:
    """
    Queries Microsoft Exchange's native /calendar/getSchedule endpoint for Free/Busy intervals.
    Private subjects, attendees, and locations are stripped inside this function and never returned.
    """
    cache_key = f"{mailbox.lower()}::{window_start.strftime('%Y-%m-%d')}::{window_end.strftime('%Y-%m-%d')}"
    now_mono = time.monotonic()
    if not bypass_cache:
        with _GRAPH_SCHEDULE_CACHE_LOCK:
            cached = _GRAPH_SCHEDULE_CACHE.get(cache_key)
            if cached and (now_mono - cached[0]) < GRAPH_SCHEDULE_CACHE_TTL_SECONDS:
                return cached[1]

    token = get_calendar_graph_token()
    if not token:
        return {"connected": False, "blocks": [], "working_hours": None, "error": "GRAPH_TOKEN_UNAVAILABLE"}

    endpoint = f"https://graph.microsoft.com/v1.0/users/{mailbox}/calendar/getSchedule"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": 'outlook.timezone="Central Standard Time"',
    }
    payload = {
        "schedules": [mailbox],
        "startTime": {
            "dateTime": window_start.strftime("%Y-%m-%dT00:00:00"),
            "timeZone": "Central Standard Time",
        },
        "endTime": {
            "dateTime": window_end.strftime("%Y-%m-%dT23:59:59"),
            "timeZone": "Central Standard Time",
        },
        "availabilityViewInterval": 30,
    }

    try:
        res = requests.post(endpoint, headers=headers, json=payload, timeout=6)
        if res.status_code != 200:
            return {
                "connected": False,
                "blocks": [],
                "working_hours": None,
                "error": f"GRAPH_HTTP_{res.status_code}",
            }

        sched_list = res.json().get("value") or []
        sched = sched_list[0] if sched_list else {}
        if sched.get("error"):
            return {
                "connected": False,
                "blocks": [],
                "working_hours": None,
                "error": "GRAPH_SCHEDULE_ERROR",
            }

        sanitized_blocks: List[Dict[str, Any]] = []
        for item in sched.get("scheduleItems") or []:
            status_val = str(item.get("status") or "").strip().lower()
            if status_val in ("", "free"):
                continue
            s_dt = _parse_local_datetime((item.get("start") or {}).get("dateTime", ""))
            e_dt = _parse_local_datetime((item.get("end") or {}).get("dateTime", ""))
            if not s_dt or not e_dt or e_dt <= s_dt:
                continue
            needs_travel = _is_onsite_outlook_item(
                str(item.get("subject") or ""),
                str(item.get("location") or ""),
            )
            sanitized_blocks.append(
                {
                    "start": s_dt,
                    "end": e_dt,
                    "needs_travel_buffer": needs_travel,
                }
            )

        result = {
            "connected": True,
            "blocks": sanitized_blocks,
            "working_hours": sched.get("workingHours"),
            "error": None,
        }
        with _GRAPH_SCHEDULE_CACHE_LOCK:
            _GRAPH_SCHEDULE_CACHE[cache_key] = (now_mono, result)
        return result
    except Exception as exc:
        print(f"[CALENDAR SERVICE] getSchedule fallback notice: {exc}", flush=True)
        return {"connected": False, "blocks": [], "working_hours": None, "error": "GRAPH_NETWORK_TIMEOUT"}


def fetch_crm_walkthrough_blocks(
    conn: Any,
    start_date_iso: str,
    end_date_iso: str,
    exclude_lead_id: Optional[int] = None,
    exclude_account_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Loads active scheduled walkthroughs from PostgreSQL Leads and Customers so CRM territory hints ('Walkthrough · City'),
    1-hour travel buffers, and Microsoft Graph outage fallback operate with 100% continuity.
    """
    blocks: List[Dict[str, Any]] = []
    with conn.cursor() as cur:
        sql = """
            SELECT id, center_name, city, preferred_date, preferred_time, walkthrough_event_id
            FROM "Leads"
            WHERE preferred_date IS NOT NULL
              AND TRIM(CAST(preferred_date AS TEXT)) != ''
              AND SUBSTRING(TRIM(CAST(preferred_date AS TEXT)) FROM 1 FOR 10) >= %s
              AND SUBSTRING(TRIM(CAST(preferred_date AS TEXT)) FROM 1 FOR 10) <= %s
              AND COALESCE(is_converted, FALSE) = FALSE
              AND COALESCE(status, '') NOT IN (
                  'Not Interested', 'Unsubscribed', 'Do Not Call (DNC)',
                  'ARCHIVED', 'Walkthrough Completed'
              )
        """
        params: List[Any] = [start_date_iso, end_date_iso]
        if exclude_lead_id is not None:
            sql += " AND id != %s"
            params.append(int(exclude_lead_id))

        cur.execute(sql, tuple(params))
        for row in cur.fetchall():
            r_dict = dict(row) if isinstance(row, dict) else {
                "id": row[0],
                "center_name": row[1],
                "city": row[2],
                "preferred_date": row[3],
                "preferred_time": row[4],
                "walkthrough_event_id": row[5],
            }
            d_str = str(r_dict.get("preferred_date") or "").strip()[:10]
            try:
                d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            hr, mn = _parse_lead_time_str(r_dict.get("preferred_time"))
            s_dt = datetime.combine(d_obj, dt_time(hr, mn), tzinfo=CHICAGO_TZ)
            e_dt = s_dt + timedelta(minutes=WALKTHROUGH_DURATION_MINUTES)
            city_clean = (r_dict.get("city") or "").strip()
            blocks.append(
                {
                    "lead_id": r_dict.get("id"),
                    "start": s_dt,
                    "end": e_dt,
                    "city": city_clean,
                    "event_id": r_dict.get("walkthrough_event_id"),
                }
            )

        cur.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_name = 'Customers' AND column_name = 'visit_preferred_date' LIMIT 1;"
        )
        if cur.fetchone():
            acc_sql = """
                SELECT customer_id, company_name, city, visit_preferred_date, visit_preferred_time, visit_event_id
                FROM "Customers"
                WHERE visit_preferred_date IS NOT NULL
                  AND TRIM(CAST(visit_preferred_date AS TEXT)) != ''
                  AND SUBSTRING(TRIM(CAST(visit_preferred_date AS TEXT)) FROM 1 FOR 10) >= %s
                  AND SUBSTRING(TRIM(CAST(visit_preferred_date AS TEXT)) FROM 1 FOR 10) <= %s
                  AND COALESCE(status, 'Active') NOT IN ('Terminated', 'Canceled', 'ARCHIVED')
            """
            acc_params: List[Any] = [start_date_iso, end_date_iso]
            if exclude_account_id is not None:
                acc_sql += " AND customer_id != %s"
                acc_params.append(int(exclude_account_id))
            cur.execute(acc_sql, tuple(acc_params))
            for row in cur.fetchall():
                r_dict = dict(row) if isinstance(row, dict) else {
                    "customer_id": row[0],
                    "company_name": row[1],
                    "city": row[2],
                    "visit_preferred_date": row[3],
                    "visit_preferred_time": row[4],
                    "visit_event_id": row[5],
                }
                d_str = str(r_dict.get("visit_preferred_date") or "").strip()[:10]
                try:
                    d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                except ValueError:
                    continue
                hr, mn = _parse_lead_time_str(r_dict.get("visit_preferred_time"))
                s_dt = datetime.combine(d_obj, dt_time(hr, mn), tzinfo=CHICAGO_TZ)
                e_dt = s_dt + timedelta(minutes=WALKTHROUGH_DURATION_MINUTES)
                city_clean = (r_dict.get("city") or "").strip()
                blocks.append(
                    {
                        "account_id": r_dict.get("customer_id"),
                        "start": s_dt,
                        "end": e_dt,
                        "city": city_clean,
                        "event_id": r_dict.get("visit_event_id"),
                    }
                )
    return blocks


def _evaluate_slot_against_blocks(
    slot_start: datetime,
    slot_end: datetime,
    now_chicago: datetime,
    crm_blocks: List[Dict[str, Any]],
    graph_blocks: List[Dict[str, Any]],
) -> Tuple[bool, str, str]:
    """
    Evaluates a single [slot_start, slot_end] 45-minute walkthrough window against:
      1. Past clock cutoff (now + 15m)
      2. Direct CRM walkthrough overlap
      3. Direct Microsoft Outlook busy block overlap
      4. 1-Hour (60-minute) DFW Travel Buffer before & after all walkthroughs / off-site visits
    Returns (available, status_code, public_label).
    """
    if slot_start <= (now_chicago + timedelta(minutes=15)):
        return False, "past", "Past"

    buffer_delta = timedelta(minutes=WALKTHROUGH_TRAVEL_BUFFER_MINUTES)

    for wb in crm_blocks:
        if slot_start < wb["end"] and slot_end > wb["start"]:
            city_sfx = f" · {wb['city']}" if wb.get("city") else ""
            return False, "walkthrough", f"Walkthrough{city_sfx}"

    for gb in graph_blocks:
        if slot_start < gb["end"] and slot_end > gb["start"]:
            return False, "busy", "Busy"

    for wb in crm_blocks:
        if slot_start < (wb["end"] + buffer_delta) and (slot_end + buffer_delta) > wb["start"]:
            city_sfx = f" ({wb['city']})" if wb.get("city") else ""
            return False, "travel_buffer", f"1h Drive Buffer{city_sfx}"

    for gb in graph_blocks:
        if gb.get("needs_travel_buffer"):
            if slot_start < (gb["end"] + buffer_delta) and (slot_end + buffer_delta) > gb["start"]:
                return False, "travel_buffer", "1h Drive Buffer"

    return True, "open", "Open"


def get_next_business_days(anchor: date, count: int = 5) -> List[date]:
    """Returns `count` Monday–Friday business dates starting on or after `anchor`."""
    days_out: List[date] = []
    cursor = anchor
    while len(days_out) < max(1, min(count, 10)):
        if cursor.weekday() < 5:
            days_out.append(cursor)
        cursor += timedelta(days=1)
    return days_out


def _filter_self_graph_block(
    conn: Any,
    graph_blocks: List[Dict[str, Any]],
    exclude_lead_id: Optional[int] = None,
    exclude_account_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Strips a record's own existing Outlook event block when rescheduling in place."""
    if not graph_blocks or (exclude_lead_id is None and exclude_account_id is None):
        return graph_blocks
    filtered = list(graph_blocks)
    with conn.cursor() as cur:
        if exclude_lead_id is not None:
            cur.execute(
                'SELECT preferred_date, preferred_time, walkthrough_event_id FROM "Leads" WHERE id = %s;',
                (int(exclude_lead_id),),
            )
            erow = cur.fetchone()
            if erow:
                p_date = erow["preferred_date"] if isinstance(erow, dict) else erow[0]
                p_time = erow["preferred_time"] if isinstance(erow, dict) else erow[1]
                p_ev = erow["walkthrough_event_id"] if isinstance(erow, dict) else erow[2]
                if p_date and p_ev:
                    try:
                        ed_obj = datetime.strptime(str(p_date).strip()[:10], "%Y-%m-%d").date()
                        ehr, emn = _parse_lead_time_str(p_time)
                        es_dt = datetime.combine(ed_obj, dt_time(ehr, emn), tzinfo=CHICAGO_TZ)
                        ee_dt = es_dt + timedelta(minutes=WALKTHROUGH_DURATION_MINUTES)
                        filtered = [
                            gb for gb in filtered
                            if not (abs((gb["start"] - es_dt).total_seconds()) < 300 and abs((gb["end"] - ee_dt).total_seconds()) < 900)
                        ]
                    except ValueError:
                        pass
        if exclude_account_id is not None:
            cur.execute(
                "SELECT 1 FROM information_schema.columns WHERE table_name = 'Customers' AND column_name = 'visit_preferred_date' LIMIT 1;"
            )
            if cur.fetchone():
                cur.execute(
                    'SELECT visit_preferred_date, visit_preferred_time, visit_event_id FROM "Customers" WHERE customer_id = %s;',
                    (int(exclude_account_id),),
                )
                arow = cur.fetchone()
                if arow:
                    a_date = arow["visit_preferred_date"] if isinstance(arow, dict) else arow[0]
                    a_time = arow["visit_preferred_time"] if isinstance(arow, dict) else arow[1]
                    a_ev = arow["visit_event_id"] if isinstance(arow, dict) else arow[2]
                    if a_date and a_ev:
                        try:
                            ad_obj = datetime.strptime(str(a_date).strip()[:10], "%Y-%m-%d").date()
                            ahr, amn = _parse_lead_time_str(a_time)
                            as_dt = datetime.combine(ad_obj, dt_time(ahr, amn), tzinfo=CHICAGO_TZ)
                            ae_dt = as_dt + timedelta(minutes=WALKTHROUGH_DURATION_MINUTES)
                            filtered = [
                                gb for gb in filtered
                                if not (abs((gb["start"] - as_dt).total_seconds()) < 300 and abs((gb["end"] - ae_dt).total_seconds()) < 900)
                            ]
                        except ValueError:
                            pass
    return filtered


def get_walkthrough_availability(
    conn: Any,
    start_date_str: Optional[str] = None,
    days_count: int = 5,
    conductor: Optional[str] = None,
    target_city: Optional[str] = None,
    exclude_lead_id: Optional[int] = None,
    exclude_account_id: Optional[int] = None,
    bypass_cache: bool = False,
) -> Dict[str, Any]:
    """
    Computes a privacy-safe 5-business-day walkthrough availability grid combining live
    Microsoft Exchange getSchedule blocks, CRM walkthrough city hints, and a 1-hour travel buffer.
    """
    now_chicago = datetime.now(CHICAGO_TZ)
    anchor_date = now_chicago.date()
    if start_date_str:
        try:
            parsed_d = datetime.strptime(str(start_date_str).strip()[:10], "%Y-%m-%d").date()
            if parsed_d >= now_chicago.date():
                anchor_date = parsed_d
        except ValueError:
            pass

    business_days = get_next_business_days(anchor_date, count=days_count)
    first_day = business_days[0]
    last_day = business_days[-1]

    query_start_dt = datetime.combine(first_day - timedelta(days=1), dt_time(0, 0), tzinfo=CHICAGO_TZ)
    query_end_dt = datetime.combine(last_day + timedelta(days=1), dt_time(23, 59), tzinfo=CHICAGO_TZ)

    mailbox, conductor_label, uses_m365 = resolve_conductor_mailbox(conductor)
    crm_blocks = fetch_crm_walkthrough_blocks(
        conn,
        (first_day - timedelta(days=1)).strftime("%Y-%m-%d"),
        (last_day + timedelta(days=1)).strftime("%Y-%m-%d"),
        exclude_lead_id=exclude_lead_id,
        exclude_account_id=exclude_account_id,
    )

    graph_meta: Dict[str, Any] = {"connected": False, "blocks": [], "error": None}
    if uses_m365:
        graph_meta = fetch_graph_free_busy_blocks(
            mailbox,
            query_start_dt,
            query_end_dt,
            bypass_cache=bypass_cache,
        )
    graph_blocks: List[Dict[str, Any]] = graph_meta.get("blocks") or []
    if uses_m365 and (exclude_lead_id is not None or exclude_account_id is not None):
        graph_blocks = _filter_self_graph_block(
            conn,
            graph_blocks,
            exclude_lead_id=exclude_lead_id,
            exclude_account_id=exclude_account_id,
        )

    days_payload: List[Dict[str, Any]] = []
    for bday in business_days:
        day_iso = bday.strftime("%Y-%m-%d")
        day_crm_cities = [
            wb["city"] for wb in crm_blocks
            if wb["start"].date() == bday and wb.get("city")
        ]
        matched_city = next(
            (c for c in day_crm_cities if _same_dfw_corridor(c, target_city)),
            None,
        )

        slots_list: List[Dict[str, Any]] = []
        cursor_dt = datetime.combine(bday, dt_time(BOOKABLE_START_HOUR, 0), tzinfo=CHICAGO_TZ)
        end_limit_dt = datetime.combine(bday, dt_time(BOOKABLE_END_HOUR, 0), tzinfo=CHICAGO_TZ)

        open_count = 0
        while cursor_dt <= end_limit_dt:
            slot_end_dt = cursor_dt + timedelta(minutes=WALKTHROUGH_DURATION_MINUTES)
            is_open, code, pub_label = _evaluate_slot_against_blocks(
                cursor_dt,
                slot_end_dt,
                now_chicago,
                crm_blocks,
                graph_blocks,
            )
            if is_open:
                open_count += 1
            slots_list.append(
                {
                    "time_12h": _format_12h(cursor_dt),
                    "time_24h": cursor_dt.strftime("%H:%M"),
                    "end_12h": _format_12h(slot_end_dt),
                    "available": is_open,
                    "status": code,
                    "label": ("Nearby Route" if (is_open and matched_city) else pub_label),
                    "route_match": bool(is_open and matched_city),
                }
            )
            cursor_dt += timedelta(minutes=SLOT_STEP_MINUTES)

        days_payload.append(
            {
                "date": day_iso,
                "weekday_short": bday.strftime("%a"),
                "month_day": bday.strftime("%b %d").replace(" 0", " "),
                "open_count": open_count,
                "day_cities": list(dict.fromkeys(day_crm_cities)),
                "route_match_city": matched_city,
                "slots": slots_list,
            }
        )

    prev_anchor = max(now_chicago.date(), first_day - timedelta(days=7))
    next_anchor = last_day + timedelta(days=1)
    while next_anchor.weekday() >= 5:
        next_anchor += timedelta(days=1)

    return {
        "status": "success",
        "conductor": conductor_label,
        "calendar_source": (
            "microsoft_graph_live"
            if (uses_m365 and graph_meta.get("connected"))
            else ("crm_schedule_only" if not uses_m365 else "crm_fallback")
        ),
        "timezone": "America/Chicago",
        "duration_minutes": WALKTHROUGH_DURATION_MINUTES,
        "travel_buffer_minutes": WALKTHROUGH_TRAVEL_BUFFER_MINUTES,
        "bookable_window": "Mon–Fri, 9:00 AM – 4:00 PM CT",
        "target_city": (target_city or "").strip(),
        "prev_start_date": prev_anchor.strftime("%Y-%m-%d"),
        "next_start_date": next_anchor.strftime("%Y-%m-%d"),
        "can_go_prev": first_day > now_chicago.date(),
        "days": days_payload,
    }


def check_walkthrough_slot_conflict(
    conn: Any,
    preferred_date: str,
    preferred_time: Optional[str],
    conductor: Optional[str] = None,
    exclude_lead_id: Optional[int] = None,
    exclude_account_id: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Performs an authoritative real-time conflict check right before saving a walkthrough.
    Returns (is_valid, conflict_message_or_none).
    """
    date_clean = str(preferred_date or "").strip()[:10]
    try:
        target_day = datetime.strptime(date_clean, "%Y-%m-%d").date()
    except ValueError:
        return False, "Please select a valid walkthrough date (YYYY-MM-DD)."

    if target_day.weekday() >= 5:
        return False, "Building walkthroughs are scheduled Monday through Friday. Please select a weekday."

    hr, mn = _parse_lead_time_str(preferred_time)
    if hr < BOOKABLE_START_HOUR or (hr > BOOKABLE_END_HOUR) or (hr == BOOKABLE_END_HOUR and mn > 0):
        return False, "Walkthrough start times must be between 9:00 AM and 4:00 PM Central Time."

    now_chicago = datetime.now(CHICAGO_TZ)
    slot_start = datetime.combine(target_day, dt_time(hr, mn), tzinfo=CHICAGO_TZ)
    slot_end = slot_start + timedelta(minutes=WALKTHROUGH_DURATION_MINUTES)

    if slot_start <= now_chicago:
        return False, "Selected walkthrough time is in the past. Please choose an upcoming open slot."

    avail = get_walkthrough_availability(
        conn=conn,
        start_date_str=date_clean,
        days_count=1,
        conductor=conductor,
        exclude_lead_id=exclude_lead_id,
        exclude_account_id=exclude_account_id,
        bypass_cache=True,
    )
    days_list = avail.get("days") or []
    if not days_list:
        return True, None

    # Check exact or overlapping slot against live blocks
    mailbox, _, uses_m365 = resolve_conductor_mailbox(conductor)
    crm_blocks = fetch_crm_walkthrough_blocks(
        conn,
        (target_day - timedelta(days=1)).strftime("%Y-%m-%d"),
        (target_day + timedelta(days=1)).strftime("%Y-%m-%d"),
        exclude_lead_id=exclude_lead_id,
        exclude_account_id=exclude_account_id,
    )
    graph_blocks: List[Dict[str, Any]] = []
    if uses_m365:
        gm = fetch_graph_free_busy_blocks(
            mailbox,
            datetime.combine(target_day - timedelta(days=1), dt_time(0, 0), tzinfo=CHICAGO_TZ),
            datetime.combine(target_day + timedelta(days=1), dt_time(23, 59), tzinfo=CHICAGO_TZ),
            bypass_cache=True,
        )
        graph_blocks = gm.get("blocks") or []
        if exclude_lead_id is not None or exclude_account_id is not None:
            graph_blocks = _filter_self_graph_block(
                conn,
                graph_blocks,
                exclude_lead_id=exclude_lead_id,
                exclude_account_id=exclude_account_id,
            )

    is_open, code, pub_label = _evaluate_slot_against_blocks(
        slot_start,
        slot_end,
        now_chicago,
        crm_blocks,
        graph_blocks,
    )
    if not is_open:
        if code == "travel_buffer":
            return (
                False,
                f"{_format_12h(slot_start)} on {date_clean} falls inside the required 1-hour travel buffer ({pub_label}). Please select an open green slot.",
            )
        return (
            False,
            f"{_format_12h(slot_start)} on {date_clean} is unavailable ({pub_label}). Please select an open green slot.",
        )
    return True, None
