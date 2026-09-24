"""
HWB-COMPANY / SigmaFidelity™ Industrial Bidding Engine
Script: gc_bids_sync.py
Standard: HWB-QMS-11.2 (Industrial Operations Architecture)
Authority: George (Systems Architect) | Approval: Humberto Dominguez (CEO)

Functions:
1. Provisions PostgreSQL table "ConstructionBids" with industrial schema.
2. Ingests and synchronizes inbound General Contractor ITBs from Microsoft Graph API.
3. Calculates cleanable square footage and estimated subcontract values based on empirical rate matrix.
"""

import os
import re
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import msal
from dotenv import load_dotenv
from core.services.gc_vetting_engine import GCVettingEngine

# Load Environment Secrets
load_dotenv('.env')

DB_URL = os.getenv('DATABASE_URL')
CID = os.getenv('GRAPH_API_PROD_APPLICATION_ID')
SECRET = os.getenv('GRAPH_API_PROD_SECRET_VALUE')
TID = os.getenv('GRAPH_API_PROD_TENANT_ID')
USER_EMAIL = os.getenv('OFFICE365_USER_EMAIL', 'hdominguez@hwbcleaning.com')

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS "ConstructionBids" (
    id SERIAL PRIMARY KEY,
    gc_name VARCHAR(255) NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    project_address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50) DEFAULT 'TX',
    zipcode VARCHAR(20),
    bid_due_date TIMESTAMP WITH TIME ZONE,
    estimated_start_date DATE,
    estimated_end_date DATE,
    cleanable_sqft NUMERIC DEFAULT 0,
    estimated_value NUMERIC DEFAULT 0,
    scope_phase VARCHAR(150) DEFAULT 'Rough, Final & Touch-Up Clean',
    special_requirements TEXT,
    estimator_name VARCHAR(150),
    estimator_title VARCHAR(100),
    estimator_email VARCHAR(150),
    estimator_phone VARCHAR(50),
    platform VARCHAR(100) DEFAULT 'BuildingConnected',
    rfp_url TEXT,
    plan_url TEXT,
    status VARCHAR(50) DEFAULT 'Invited',
    prequal_status VARCHAR(50) DEFAULT 'Ready',
    last_contact_date TIMESTAMP WITH TIME ZONE,
    next_action VARCHAR(255),
    next_action_date DATE,
    notes TEXT,
    email_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gc_bids_status ON "ConstructionBids" (status);
CREATE INDEX IF NOT EXISTS idx_gc_bids_due_date ON "ConstructionBids" (bid_due_date);
CREATE INDEX IF NOT EXISTS idx_gc_bids_gc_name ON "ConstructionBids" (gc_name);
"""

def init_db(conn):
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    conn.commit()
    print("[SigmaFidelity] ConstructionBids table initialized successfully.")

def get_graph_token():
    if not CID or not SECRET or not TID:
        print("[SigmaFidelity] Warning: Graph API credentials missing.")
        return None
    authority = f"https://login.microsoftonline.com/{TID}"
    app = msal.ConfidentialClientApplication(CID, authority=authority, client_credential=SECRET)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return result.get('access_token')

def seed_verified_bids(conn):
    """Seed the verified high-priority commercial bids into PostgreSQL."""
    verified_records = [
        {
            "gc_name": "Weekes Construction, Inc.",
            "project_name": "Barnes & Noble 3631 - Epic W. Towne Crossing",
            "project_address": "3166 State Highway 161",
            "city": "Grand Prairie",
            "state": "TX",
            "zipcode": "75052",
            "bid_due_date": "2026-09-14 14:00:00-05",
            "estimated_start_date": "2026-11-09",
            "estimated_end_date": "2027-03-12",
            "cleanable_sqft": 18500,
            "estimated_value": 7200.00,
            "scope_phase": "Final Clean & White Glove Clean at Turnover",
            "special_requirements": "All bids must be submitted on company letterhead, include completed bid form, and be uploaded via BuildingConnected. High-visibility retail standard.",
            "estimator_name": "Amber Duhon",
            "estimator_title": "Bid Coordinator",
            "estimator_email": "anewland@weekesconstruction.com",
            "estimator_phone": "864-875-0521",
            "platform": "BuildingConnected",
            "rfp_url": "https://app.buildingconnected.com",
            "plan_url": "BuildingConnected File Tab",
            "status": "Invited",
            "prequal_status": "Ready",
            "next_action": "Submit CSI 01 74 23 Proposal & Call Amber Duhon",
            "next_action_date": "2026-09-08",
            "notes": "Retail anchor buildout. Grand Prairie is adjacent to Arlington home base. White glove turnover inspection required.",
            "email_id": "WEEKES-BN-3631-20260904"
        },
        {
            "gc_name": "Novel Builders",
            "project_name": "Stacked Industrial (5 Shell Buildings)",
            "project_address": "751 E Rendon Crowley Rd",
            "city": "Burleson",
            "state": "TX",
            "zipcode": "76028",
            "bid_due_date": "2026-09-11 14:00:00-05",
            "estimated_start_date": "2026-10-15",
            "estimated_end_date": "2027-02-28",
            "cleanable_sqft": 167500,
            "estimated_value": 28475.00,
            "scope_phase": "Phase 1 Rough Scrape, Phase 2 Final Scrub, Exterior Glazing",
            "special_requirements": "Owner requires cost breakouts: 1. Sitework, 2. Off-Site / TXDOT Work, 3. Building (Breakouts for each building 1 through 5). Exclude concrete panel staining (panels are painted per addendum).",
            "estimator_name": "Austin Addis / Jennifer Dye",
            "estimator_title": "Junior Estimator / Bid Admin",
            "estimator_email": "aaddis@novelbuilders.com",
            "estimator_phone": "214-884-8810",
            "platform": "BuildingConnected / Planroom",
            "rfp_url": "https://app.buildingconnected.com/rfps/6a04a873f87d45e03b697d69_bid",
            "plan_url": "https://www.novelbuildersplanroom.com?accesskey=F20C07186B#projects/505850",
            "status": "Plans Downloaded",
            "prequal_status": "Ready",
            "next_action": "Execute 5-Building Breakout Takeoff & Send Bid Package",
            "next_action_date": "2026-09-08",
            "notes": "Buildings 1 & 2: 30,240 SF each. Buildings 3 & 4: 32,760 SF each. Building 5: 45,360 SF. Total 167,500 SF tilt-wall industrial shell.",
            "email_id": "NOVEL-STACKED-20260904"
        },
        {
            "gc_name": "Novel Builders",
            "project_name": "Princeton Micro Hospital - Preliminary Bid",
            "project_address": "Highway 380 Corridor",
            "city": "Princeton",
            "state": "TX",
            "zipcode": "75407",
            "bid_due_date": "2026-09-18 14:00:00-05",
            "estimated_start_date": "2026-12-01",
            "estimated_end_date": "2027-06-30",
            "cleanable_sqft": 42000,
            "estimated_value": 14700.00,
            "scope_phase": "Hospital Grade Terminal Rough & Final Clean",
            "special_requirements": "Medical grade HEPA filtration, operating room sterile protocols, microfiber wall wipe down, vinyl floor 4-coat wax.",
            "estimator_name": "Novel Estimating Team",
            "estimator_title": "Lead Estimator",
            "estimator_email": "estimating@novelbuilders.com",
            "estimator_phone": "214-884-8810",
            "platform": "Novel Planroom",
            "rfp_url": "https://www.novelbuildersplanroom.com",
            "plan_url": "https://www.novelbuildersplanroom.com",
            "status": "Invited",
            "prequal_status": "Ready",
            "next_action": "Download Architectural Set & Review Terminal Clean Spec",
            "next_action_date": "2026-09-10",
            "notes": "Healthcare facility command. High-margin sanitization requirement.",
            "email_id": "NOVEL-PRINCETON-20260903"
        },
        {
            "gc_name": "Source Building Group",
            "project_name": "UTSW CUH 4.219 Microbiology Lab",
            "project_address": "6201 Harry Hines Blvd",
            "city": "Dallas",
            "state": "TX",
            "zipcode": "75390",
            "bid_due_date": "2026-09-08 17:00:00-05",
            "estimated_start_date": "2026-10-01",
            "estimated_end_date": "2026-11-15",
            "cleanable_sqft": 6500,
            "estimated_value": 4800.00,
            "scope_phase": "Biosafety Lab Decontamination & Final Clean",
            "special_requirements": "Hospital badging, negative air machine monitoring, stainless steel pass-through sanitization, epoxy floor scrub.",
            "estimator_name": "Colton Bennett / Sai Chevuru",
            "estimator_title": "Estimator",
            "estimator_email": "cbennett@sourcebuildinggroup.com",
            "estimator_phone": "817-529-2815",
            "platform": "BuildingConnected",
            "rfp_url": "https://app.buildingconnected.com",
            "plan_url": "BuildingConnected",
            "status": "Invited",
            "prequal_status": "Ready",
            "next_action": "Verify Badging Requirements & Follow Up with Colton Bennett",
            "next_action_date": "2026-09-08",
            "notes": "UT Southwestern Medical Center cleanroom / lab retrofit.",
            "email_id": "SOURCE-UTSW-20260904"
        },
        {
            "gc_name": "MYCON General Contractors",
            "project_name": "Hillside Student Building Remodel",
            "project_address": "DFW Metroplex Campus",
            "city": "Dallas",
            "state": "TX",
            "zipcode": "75201",
            "bid_due_date": "2026-09-08 12:00:00-05",
            "estimated_start_date": "2026-09-20",
            "estimated_end_date": "2026-11-01",
            "cleanable_sqft": 14000,
            "estimated_value": 4200.00,
            "scope_phase": "Post-Remodel Rough, Restrooms & VCT Strip/Wax",
            "special_requirements": "Multi-story educational facility. Stairwell glass, acoustic ceiling tile wipe down, restroom fixture descaling.",
            "estimator_name": "Ryan Porter",
            "estimator_title": "Senior Estimator",
            "estimator_email": "rporter@mycon.com",
            "estimator_phone": "972-529-2444",
            "platform": "BuildingConnected",
            "rfp_url": "https://app.buildingconnected.com",
            "plan_url": "BuildingConnected",
            "status": "Invited",
            "prequal_status": "Ready",
            "next_action": "Submit Standard CSI 01 74 23 Bid & Follow Up with Ryan Porter",
            "next_action_date": "2026-09-08",
            "notes": "MYCON is a top-tier Texas GC with over $500M annual commercial volume.",
            "email_id": "MYCON-HILLSIDE-20260904"
        }
    ]

    with conn.cursor() as cur:
        for r in verified_records:
            cur.execute("""
                INSERT INTO "ConstructionBids" (
                    gc_name, project_name, project_address, city, state, zipcode,
                    bid_due_date, estimated_start_date, estimated_end_date,
                    cleanable_sqft, estimated_value, scope_phase, special_requirements,
                    estimator_name, estimator_title, estimator_email, estimator_phone,
                    platform, rfp_url, plan_url, status, prequal_status,
                    next_action, next_action_date, notes, email_id
                ) VALUES (
                    %(gc_name)s, %(project_name)s, %(project_address)s, %(city)s, %(state)s, %(zipcode)s,
                    %(bid_due_date)s, %(estimated_start_date)s, %(estimated_end_date)s,
                    %(cleanable_sqft)s, %(estimated_value)s, %(scope_phase)s, %(special_requirements)s,
                    %(estimator_name)s, %(estimator_title)s, %(estimator_email)s, %(estimator_phone)s,
                    %(platform)s, %(rfp_url)s, %(plan_url)s, %(status)s, %(prequal_status)s,
                    %(next_action)s, %(next_action_date)s, %(notes)s, %(email_id)s
                )
                ON CONFLICT (email_id) DO UPDATE SET
                    bid_due_date = EXCLUDED.bid_due_date,
                    cleanable_sqft = EXCLUDED.cleanable_sqft,
                    estimated_value = EXCLUDED.estimated_value,
                    scope_phase = EXCLUDED.scope_phase,
                    special_requirements = EXCLUDED.special_requirements,
                    estimator_email = EXCLUDED.estimator_email,
                    estimator_phone = EXCLUDED.estimator_phone,
                    updated_at = CURRENT_TIMESTAMP;
            """, r)
    conn.commit()
    print(f"[SigmaFidelity] Successfully seeded {len(verified_records)} active commercial construction bids.")

def sync_inbound_graph_bids(conn):
    token = get_graph_token()
    if not token:
        print("[SigmaFidelity] Skipping Graph API sync - no token available.")
        return

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    url = f'https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/messages'
    params = {
        '$filter': 'receivedDateTime ge 2026-07-01T00:00:00Z',
        '$select': 'id,subject,from,receivedDateTime,bodyPreview',
        '$top': '100',
        '$orderby': 'receivedDateTime desc'
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=20)
        if res.status_code != 200:
            print(f"[SigmaFidelity] Graph API returned status {res.status_code}: {res.text}")
            return
        messages = res.json().get('value', [])
        print(f"[SigmaFidelity] Scanned {len(messages)} recent emails for new GC bid invites.")

        gc_terms = ['buildingconnected', 'planroom', 'reproconnect', 'final clean', 'rough clean', 'construction clean', 'invitation to bid', 'itb', 'bid due', 'subcontractor bid']

        new_gc_bids = 0
        with conn.cursor() as cur:
            for m in messages:
                subj = m.get('subject', '')
                sender_info = m.get('from', {}).get('emailAddress', {})
                sender = sender_info.get('address', '')
                name = sender_info.get('name', '')
                body = m.get('bodyPreview', '')
                msg_id = m.get('id')
                recv_dt = m.get('receivedDateTime')

                combined = f"{subj} {sender} {name} {body}".lower()
                if any(term in combined for term in gc_terms):
                    cur.execute('SELECT id FROM "ConstructionBids" WHERE email_id = %s;', (msg_id,))
                    exists = cur.fetchone()
                    if not exists:
                        platform = 'BuildingConnected' if 'buildingconnected' in combined else 'Planroom'
                        cur.execute('''
                            INSERT INTO "ConstructionBids" (
                                gc_name, project_name, platform, status, email_id, notes,
                                estimator_name, estimator_email, created_at, updated_at
                            ) VALUES (%s, %s, %s, 'Invited', %s, %s, %s, %s, COALESCE(%s::timestamptz, NOW()), NOW())
                            RETURNING id;
                        ''', (
                            name or sender,
                            subj[:200],
                            platform,
                            msg_id,
                            f"Inbound solicitation email: {body[:300]}",
                            name,
                            sender,
                            recv_dt
                        ))
                        new_id = cur.fetchone()[0]
                        cur.execute('''
                            INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                            VALUES (%s, 'ConstructionBid', 'Email Ingested', %s)
                        ''', (new_id, f"Auto-ingested ITB email: {subj}"))
                        new_gc_bids += 1
                        print(f"[SigmaFidelity] Ingested new GC Bid #{new_id}: {subj[:50]} from {sender}")

            conn.commit()
            print(f"[SigmaFidelity] Sync completed: {new_gc_bids} new GC bids ingested.")

            # Option 1 Standard: Run 4-Point Vetting & Autonomous Profile Completer
            print("[SigmaFidelity] Executing Autonomous 4-Point Vetting & Profile Completer on bids...")
            enrich_summary = GCVettingEngine.enrich_all_bids(DB_URL)
            print(f"[SigmaFidelity] Vetting & Enrichment summary: {enrich_summary.get('enriched_count')} bids updated. Breakdown: {enrich_summary.get('tier_breakdown')}")
    except Exception as e:
        conn.rollback()
        print(f"[SigmaFidelity] Error during Graph API sync: {e}")

if __name__ == '__main__':
    conn = psycopg2.connect(DB_URL)
    try:
        init_db(conn)
        seed_verified_bids(conn)
        sync_inbound_graph_bids(conn)
    finally:
        conn.close()
    print("[SigmaFidelity] GC Bids Sync Execution Complete.")
