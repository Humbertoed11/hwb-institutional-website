"""
SigmaFidelity™ Daycare Calendar Audit & Lead Activity Synchronizer
Standard: HWB-QMS-11.2 (Industrial Operations Architecture)
Authority: Humberto Dominguez (CEO) | Architect: George (Systems Architect & mbB)

Functions:
1. Queries Microsoft Graph API calendarView for Humberto Dominguez across 2024 and 2025.
2. Filters all appointments and walkthroughs set for daycares, preschools, and Montessori academies.
3. Matches each appointment against the PostgreSQL "Leads" database (by phone, address, or center name).
4. Inserts any unindexed facility into "Leads" with full empirical metadata.
5. Injects verified field notes, appointment dates, and director contacts into "Leads.notes".
6. Logs each site visit into "GlobalActivities" for permanent executive traceability.
"""

import os
import re
import datetime
from typing import Dict, Any, List, Optional, Tuple
import requests
import msal
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
from dotenv import load_dotenv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.services.sanitizer import clean_phone, clean_zip

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
CID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TID = os.getenv("GRAPH_API_PROD_TENANT_ID")
USER_EMAIL = os.getenv("OFFICE365_USER_EMAIL", "hdominguez@hwbcleaning.com")

def get_graph_token() -> Optional[str]:
    if not CID or not SECRET or not TID:
        return None
    authority = f"https://login.microsoftonline.com/{TID}"
    app = msal.ConfidentialClientApplication(CID, authority=authority, client_credential=SECRET)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return result.get('access_token')

def fetch_calendar_events(start_iso: str, end_iso: str) -> List[Dict[str, Any]]:
    token = get_graph_token()
    if not token:
        raise RuntimeError("Failed to acquire Microsoft Graph API access token.")

    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/calendarView"
    params = {
        "startDateTime": start_iso,
        "endDateTime": end_iso,
        "$select": "id,subject,start,end,location,bodyPreview,body,isCancelled",
        "$top": "100"
    }

    all_events = []
    while url:
        res = requests.get(url, headers=headers, params=params if url.startswith("https://graph.microsoft.com/v1.0/users/") and "?" not in url else None)
        if res.status_code != 200:
            print(f"[GRAPH WARNING] Status {res.status_code}: {res.text}")
            break
        data = res.json()
        batch = data.get("value", [])
        all_events.extend(batch)
        url = data.get("@odata.nextLink")
        params = None

    return all_events

def is_daycare_event(ev: Dict[str, Any]) -> bool:
    subj = ev.get("subject", "")
    loc = ev.get("location", {}).get("displayName", "")
    body = ev.get("bodyPreview", "")
    text = f"{subj} {loc} {body}".lower()

    keywords = [
        "academy", "montessori", "child", "kid", "preschool", "daycare", "learning",
        "primrose", "goddard", "kiddie", "xplor", "courtyard", "school", "day out", "child care"
    ]
    exclusions = [
        "dallas college", "bellas leadership", "sales meeting", "trade show", "insperity",
        "elevator guy", "boiler inspection", "insurance adjustor", "b2b business owners",
        "beabie birthday", "dentist", "doctor"
    ]

    if any(ex in text for ex in exclusions):
        return False
    return any(k in text for k in keywords)

def clean_body_text(raw_html: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_event_details(ev: Dict[str, Any]) -> Dict[str, Any]:
    subj = ev.get("subject", "")
    start_dt = ev.get("start", {}).get("dateTime", "")[:10]
    start_time = ev.get("start", {}).get("dateTime", "")[11:16]
    loc_obj = ev.get("location", {})
    loc_name = loc_obj.get("displayName", "")
    addr_obj = loc_obj.get("address", {}) or {}

    raw_body = ev.get("body", {}).get("content", "") or ev.get("bodyPreview", "")
    clean_body = clean_body_text(raw_body)
    comb = f"{subj} {loc_name} {clean_body}"

    # Extract street address, city, zipcode
    street = addr_obj.get("street")
    city = addr_obj.get("city")
    zipcode = addr_obj.get("postalCode")

    if not street:
        m_addr = re.search(r'(\d{3,5}\s+[A-Za-z0-9\s.,#-]+(?:Expressway|Expy|Parkway|Pkwy|Blvd|Boulevard|Street|St|Road|Rd|Ave|Avenue|Lane|Ln|Trail|Trl|Dr|Drive|Ct|Court))', comb, re.I)
        if m_addr:
            street = m_addr.group(1).strip()

    if not city:
        for c in ["Plano", "Frisco", "McKinney", "Allen", "Prosper", "Celina", "Carrollton", "Princeton", "Lewisville", "Dallas"]:
            if re.search(rf'\b{c}\b', comb, re.I):
                city = c
                break

    if not zipcode:
        m_z = re.search(r'\b(75\d{3})\b', comb)
        if m_z:
            zipcode = m_z.group(1)

    # Extract phone
    m_p = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', comb)
    phone = clean_phone(m_p.group(0)) if m_p else None

    # Extract contact person / director
    contact = None
    m_dir = re.search(r'(?:Director|DM|Assistant Director|front desk|Mrs\.|Miss|Hanan|Trish|Holly|Monica|Heather|Reena|Deena|Lisa|Luxmi|Maya|Nita|Kryan|Micah|Ruby|Ann|Anabel|Cristina|Angela|Dina|Courtney|Naida|Abby|Brittney|Kaietry|Karen|Nesasia|Mimi|Ashton)\s*[:\-–]?\s*([A-Za-z]+)?', comb, re.I)
    if m_dir:
        contact = m_dir.group(0).strip()

    return {
        "event_id": ev.get("id"),
        "date": start_dt,
        "time": start_time,
        "subject": subj,
        "location_str": loc_name or street or "Plano / Collin County",
        "street": street,
        "city": city or "Plano",
        "zipcode": zipcode,
        "phone": phone,
        "contact": contact,
        "body_notes": clean_body[:500]
    }

def match_lead(cur, parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # 1. Match by exact phone
    if parsed.get("phone"):
        cur.execute('''
            SELECT id, center_name, address, city, phone, director, notes
            FROM "Leads"
            WHERE phone = %s OR phone ILIKE %s
            LIMIT 1;
        ''', (parsed["phone"], f"%{parsed['phone'][-8:]}%"))
        r = cur.fetchone()
        if r:
            return dict(r)

    # 2. Match by exact street address
    street = parsed.get("street")
    city = parsed.get("city")
    if street:
        m_num = re.search(r'^(\d+)', street.strip())
        m_name = re.search(r'^\d+\s+([A-Za-z]+)', street.strip())
        if m_num and m_name:
            cur.execute('''
                SELECT id, center_name, address, city, phone, director, notes
                FROM "Leads"
                WHERE address ILIKE %s AND address ILIKE %s
                LIMIT 1;
            ''', (f"%{m_num.group(1)}%", f"%{m_name.group(1)}%"))
            r = cur.fetchone()
            if r:
                return dict(r)

    # 3. Match by center name + city
    subj = parsed.get("subject", "")
    # Clean leading words
    name_clean = re.sub(r'^(?:NC\s*-\s*|Canceled:\s*|Hanan Director\s*-\s*|Maya Walk Through\s*)', '', subj, flags=re.I)
    name_clean = re.split(r'[-–(:]', name_clean)[0].strip()
    if len(name_clean) >= 4:
        cur.execute('''
            SELECT id, center_name, address, city, phone, director, notes
            FROM "Leads"
            WHERE center_name ILIKE %s AND (city ILIKE %s OR %s IS NULL)
            ORDER BY id ASC
            LIMIT 1;
        ''', (f"%{name_clean}%", f"%{city}%" if city else None, city))
        r = cur.fetchone()
        if r:
            return dict(r)

    return None

def sync_daycare_appointments():
    print("\n==================================================================", flush=True)
    print("  SigmaFidelity: Daycare Calendar Audit & Lead Activity Sync", flush=True)
    print("==================================================================", flush=True)

    # Scan 2024-01-01 through 2025-12-31
    events = fetch_calendar_events("2024-01-01T00:00:00Z", "2025-12-31T23:59:59Z")
    print(f"Total Calendar Events Audited (2024-2025): {len(events)}", flush=True)

    daycare_events = [ev for ev in events if is_daycare_event(ev)]
    print(f"Total Verified Daycare Appointments Found: {len(daycare_events)}\n", flush=True)

    conn = psycopg2.connect(DB_URL)
    results = []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for ev in daycare_events:
                parsed = parse_event_details(ev)
                lead = match_lead(cur, parsed)

                lead_id = None
                center_name = None
                action = "Updated Existing Lead"

                if lead:
                    lead_id = lead["id"]
                    center_name = lead["center_name"]
                else:
                    # Insert newly discovered daycare into Leads
                    action = "Created New Lead"
                    new_center_name = re.sub(r'^(?:NC\s*-\s*|Canceled:\s*|Hanan Director\s*-\s*)', '', parsed["subject"], flags=re.I)
                    new_center_name = re.split(r'[-–(:]', new_center_name)[0].strip()
                    if not new_center_name or len(new_center_name) < 4:
                        new_center_name = parsed["location_str"]

                    cur.execute('''
                        INSERT INTO "Leads" (
                            center_name, address, city, state, zipcode, phone, director,
                            facility_type, industry, commercial_status, status, lead_source,
                            last_contacted_by, preferred_date, input_date, updated_at
                        ) VALUES (
                            %s, %s, %s, 'TX', %s, %s, %s,
                            'Daycare', 'Daycare', 'Commercial', 'Site Visit Scheduled', 'Executive Calendar Visit',
                            'Humberto Dominguez', %s, CURRENT_DATE, CURRENT_DATE
                        ) RETURNING id;
                    ''', (
                        new_center_name,
                        parsed.get("street") or parsed.get("location_str"),
                        parsed.get("city") or "Plano",
                        parsed.get("zipcode"),
                        parsed.get("phone"),
                        parsed.get("contact"),
                        parsed["date"]
                    ))
                    lead_id = cur.fetchone()["id"]
                    center_name = new_center_name
                    lead = {"notes": ""}

                # Append note if not already present
                existing_notes = (lead.get("notes") or "").strip()
                visit_tag = f"[CALENDAR VISIT: {parsed['date']}]"
                new_note_entry = f"{visit_tag} {parsed['subject']} | Location: {parsed['location_str']} | Notes: {parsed['body_notes']}"

                if visit_tag not in existing_notes:
                    updated_notes = f"{existing_notes}\n{new_note_entry}".strip() if existing_notes else new_note_entry
                    cur.execute('''
                        UPDATE "Leads"
                        SET notes = %s,
                            last_contacted_by = 'Humberto Dominguez',
                            preferred_date = %s,
                            phone = COALESCE(phone, %s),
                            director = COALESCE(NULLIF(director, ''), %s),
                            updated_at = CURRENT_DATE
                        WHERE id = %s;
                    ''', (updated_notes, parsed["date"], parsed.get("phone"), parsed.get("contact"), lead_id))

                    # Log to GlobalActivities
                    cur.execute('''
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description, timestamp)
                        VALUES (%s, 'Lead', 'Calendar Site Visit', %s, %s::timestamptz);
                    ''', (
                        lead_id,
                        f"Appointment for Humberto Dominguez: {parsed['subject']} ({parsed['location_str']}). Field Notes: {parsed['body_notes']}",
                        f"{parsed['date']} {parsed['time']}:00Z"
                    ))

                results.append({
                    "date": parsed["date"],
                    "time": parsed["time"],
                    "subject": parsed["subject"],
                    "daycare": center_name,
                    "city": parsed.get("city"),
                    "lead_id": lead_id,
                    "action": action,
                    "phone": parsed.get("phone"),
                    "contact": parsed.get("contact")
                })

            conn.commit()

        print(f"--- Successfully Processed & Synchronized {len(results)} Daycare Appointments ---")
        return results

    except Exception as e:
        conn.rollback()
        print(f"FAILED: Daycare sync encountered error: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    sync_daycare_appointments()
