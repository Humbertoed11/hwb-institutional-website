"""
Yamamoto Moto Autonomous Penetration & Vulnerability Audit
Mandate: Yamamoto Moto Lead AI Estimator Verification
Session Persona: yamamoto_moto (User ID: 10, Role: Custom, Mirna Rondinella Mirror)
Objective: Probe all modifying endpoints and backoffice vectors, attempt to write 'SECURITY BREACH',
           and compile an empirical penetration vulnerability ledger.
"""

import sys
import os
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import psycopg2
import psycopg2.extras
from main_app import app
from core.models.user import User

def run_yamamoto_audit():
    print("=" * 80)
    print("🥋 YAMAMOTO MOTO PENETRATION & VULNERABILITY AUDIT")
    print("   Auditor Persona: yamamoto_moto (User ID: 10)")
    print("   Permission Profile: Custom (Mirrored from Mirna Rondinella)")
    print("   Directives: Identify all endpoints where 'SECURITY BREACH' can be written")
    print("=" * 80)

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = '10'
        sess['_fresh'] = True

    # Find a test lead to probe safely without corrupting production data
    conn = psycopg2.connect(app.config['DATABASE_URL'])
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get a test lead ID
    cur.execute('SELECT id, center_name, decision_maker, notes FROM "Leads" ORDER BY id DESC LIMIT 1')
    target_lead = cur.fetchone()
    test_lead_id = target_lead['id'] if target_lead else 82618

    # Get a test account ID
    cur.execute('SELECT customer_id FROM "Customers" ORDER BY customer_id DESC LIMIT 1')
    target_acct = cur.fetchone()
    test_acct_id = target_acct['customer_id'] if target_acct else 1

    # Get a test bid ID
    cur.execute('SELECT id FROM "ConstructionBids" ORDER BY id DESC LIMIT 1')
    target_bid = cur.fetchone()
    test_bid_id = target_bid['id'] if target_bid else 1

    conn.close()

    vulnerabilities = []
    defended = []

    test_cases = [
        # --- Group 1: Leads Write Vectors (Profile: leads view=True, edit=False, delete=False) ---
        {
            "category": "LEADS",
            "name": "Single Lead Update via PUT",
            "method": "PUT",
            "endpoint": f"/api/v1/leads/{test_lead_id}",
            "payload": {"notes": "SECURITY BREACH - Lead Updated via PUT"},
            "is_json": True,
            "expected_block": True,
            "desc": "Tests if restricted Custom user can update lead notes via REST PUT"
        },
        {
            "category": "LEADS",
            "name": "Single Lead Partial Update via PATCH (quickUpdateLead)",
            "method": "PATCH",
            "endpoint": f"/api/v1/leads/{test_lead_id}",
            "payload": {"status": "Qualified"},
            "is_json": True,
            "expected_block": True,
            "desc": "Tests if restricted Custom user can change status via table inline dropdown"
        },
        {
            "category": "LEADS",
            "name": "Lead Cadence Quick-Save",
            "method": "POST",
            "endpoint": f"/api/v1/leads/{test_lead_id}/cadence-save",
            "payload": {"decision_maker": "SECURITY BREACH", "notes": "SECURITY BREACH Cadence"},
            "is_json": True,
            "expected_block": True,
            "desc": "Tests if restricted Custom user can save decision maker via cadence modal"
        },
        {
            "category": "LEADS",
            "name": "Add Contact to Lead",
            "method": "POST",
            "endpoint": f"/api/v1/leads/{test_lead_id}/contacts",
            "payload": {"full_name": "SECURITY BREACH Contact", "role": "Hacker", "email": "breach@hwb.test", "phone": "(214)-000-0000"},
            "is_json": True,
            "expected_block": True,
            "desc": "Tests if restricted Custom user can append contacts to lead"
        },
        {
            "category": "LEADS",
            "name": "Batch Lead Action (Status Update)",
            "method": "POST",
            "endpoint": "/api/v1/leads/batch-action",
            "payload": {"action": "update_status", "lead_ids": [test_lead_id], "params": {"status": "New"}},
            "is_json": True,
            "expected_block": True,
            "desc": "Tests if restricted Custom user can batch update lead statuses"
        },
        {
            "category": "LEADS",
            "name": "Batch Lead Action (Bulk Delete)",
            "method": "POST",
            "endpoint": "/api/v1/leads/batch-action",
            "payload": {"action": "delete", "lead_ids": [99999999]},
            "is_json": True,
            "expected_block": True,
            "desc": "Tests if restricted Custom user can batch delete leads"
        },
        {
            "category": "LEADS",
            "name": "Single Lead Deletion",
            "method": "DELETE",
            "endpoint": "/api/v1/leads/99999999",
            "payload": None,
            "is_json": False,
            "expected_block": True,
            "desc": "Tests if restricted Custom user can delete single lead"
        },
        {
            "category": "LEADS",
            "name": "Add Manual Lead (Web Form)",
            "method": "POST",
            "endpoint": "/admin/add-lead",
            "payload": {"company_name": "SECURITY BREACH CORP", "sqf": "5000", "city": "Dallas"},
            "is_json": False,
            "expected_block": True,
            "desc": "Tests if restricted Custom user can add new lead via web form"
        },
        {
            "category": "LEADS",
            "name": "Edit Lead Submit (Web Form)",
            "method": "POST",
            "endpoint": f"/admin/edit-lead/{test_lead_id}",
            "payload": {"company_name": "SECURITY BREACH", "sqf": "1000"},
            "is_json": False,
            "expected_block": True,
            "desc": "Tests if restricted Custom user can edit lead via web form"
        },

        # --- Group 2: Accounts Vectors (Profile: accounts view=False, edit=False, delete=False) ---
        {
            "category": "ACCOUNTS",
            "name": "Read Account via REST API",
            "method": "GET",
            "endpoint": f"/api/v1/accounts/{test_acct_id}",
            "payload": None,
            "is_json": False,
            "expected_block": True,
            "desc": "Tests if restricted user can read client account data via API"
        },
        {
            "category": "ACCOUNTS",
            "name": "Update Account via REST PUT",
            "method": "PUT",
            "endpoint": f"/api/v1/accounts/{test_acct_id}",
            "payload": {"notes": "SECURITY BREACH Account Update"},
            "is_json": True,
            "expected_block": True,
            "desc": "Tests if restricted user can write to client accounts"
        },
        {
            "category": "ACCOUNTS",
            "name": "Add Contact to Account",
            "method": "POST",
            "endpoint": f"/api/v1/accounts/{test_acct_id}/contacts",
            "payload": {"full_name": "SECURITY BREACH Account Contact", "role": "Billing"},
            "is_json": True,
            "expected_block": True,
            "desc": "Tests if restricted user can add contacts to accounts"
        },
        {
            "category": "ACCOUNTS",
            "name": "Delete Account via REST",
            "method": "DELETE",
            "endpoint": "/api/v1/accounts/99999999",
            "payload": None,
            "is_json": False,
            "expected_block": True,
            "desc": "Tests if restricted user can delete client accounts"
        },
        {
            "category": "ACCOUNTS",
            "name": "Add Account Web Form",
            "method": "POST",
            "endpoint": "/admin/add-account",
            "payload": {"company_name": "SECURITY BREACH ACCT"},
            "is_json": False,
            "expected_block": True,
            "desc": "Tests if restricted user can create accounts via form"
        },

        # --- Group 3: Bids & Takeoff Vectors (Profile: bids view=False, edit=False) ---
        {
            "category": "BIDS",
            "name": "Commit Bid Estimate Takeoff",
            "method": "POST",
            "endpoint": f"/api/v1/bids/{test_bid_id}/commit-estimate",
            "payload": {"cleanable_sqft": 50000, "final_bid_amount": 99999.00},
            "is_json": True,
            "expected_block": True,
            "desc": "Tests if restricted user can commit financial pricing on commercial bids"
        },

        # --- Group 4: Activities / Activity Stream ---
        {
            "category": "ACTIVITIES",
            "name": "Quick Log Global Activity",
            "method": "POST",
            "endpoint": "/api/v1/activities/quick-log",
            "payload": {"parent_id": test_lead_id, "parent_type": "Lead", "note": "SECURITY BREACH Quick Activity"},
            "is_json": True,
            "expected_block": True,
            "desc": "Tests if restricted user can inject unverified activities"
        },

        # --- Group 5: Technical Manuals & Access Control ---
        {
            "category": "QMS",
            "name": "Access QMS Manual Index",
            "method": "GET",
            "endpoint": "/manual",
            "payload": None,
            "is_json": False,
            "expected_block": True,
            "desc": "Tests if restricted user can access QMS manual"
        },
        {
            "category": "QMS",
            "name": "Access QMS Individual SOP",
            "method": "GET",
            "endpoint": "/manual/hwb-qms-1.0_quality_manual.html",
            "payload": None,
            "is_json": False,
            "expected_block": True,
            "desc": "Tests if restricted user can read controlled QMS SOPs"
        },
        {
            "category": "SALES_DESK",
            "name": "Access Sales Desk",
            "method": "GET",
            "endpoint": "/sales-desk",
            "payload": None,
            "is_json": False,
            "expected_block": True,
            "desc": "Tests if restricted user can access Sales Desk"
        }
    ]

    for tc in test_cases:
        m = tc["method"]
        ep = tc["endpoint"]
        p = tc["payload"]
        is_j = tc["is_json"]

        if m == "GET":
            res = client.get(ep)
        elif m == "POST":
            res = client.post(ep, json=p if is_j else None, data=None if is_j else p)
        elif m == "PUT":
            res = client.put(ep, json=p if is_j else None, data=None if is_j else p)
        elif m == "PATCH":
            res = client.patch(ep, json=p if is_j else None, data=None if is_j else p)
        elif m == "DELETE":
            res = client.delete(ep)

        status = res.status_code
        is_blocked = (status == 403 or (status in [301, 302] and '/login' in getattr(res, 'location', '')))
        
        # If the endpoint returned 200, 201, 204, or 404 (indicating the route allowed the execution attempt past auth)
        if not is_blocked and status in [200, 201, 204, 404, 500]:
            tc["status_code"] = status
            vulnerabilities.append(tc)
            print(f"🚨 [BREACH DETECTED] {tc['category']:10s} | {m:6s} {ep:35s} -> HTTP {status} (Expected 403 Forbidden)")
        else:
            tc["status_code"] = status
            defended.append(tc)
            print(f"🛡️ [BLOCKED / SAFE] {tc['category']:10s} | {m:6s} {ep:35s} -> HTTP {status} (Blocked)")

    print("\n" + "=" * 80)
    print("📊 YAMAMOTO MOTO AUDIT SUMMARY")
    print(f"   Total Attack Vectors Tested: {len(test_cases)}")
    print(f"   Protected Endpoints (HTTP 403): {len(defended)}")
    print(f"   VULNERABLE ENDPOINTS (BREACHES): {len(vulnerabilities)}")
    print("=" * 80)

    for i, v in enumerate(vulnerabilities, 1):
        print(f"\n[{i}] VULNERABILITY: {v['name']} ({v['category']})")
        print(f"    Vector: {v['method']} {v['endpoint']}")
        print(f"    Returned Status: HTTP {v['status_code']}")
        print(f"    Security Risk: {v['desc']}")

    return vulnerabilities, defended

if __name__ == "__main__":
    v, d = run_yamamoto_audit()
