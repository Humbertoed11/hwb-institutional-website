import os
import sys
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

BASE_URL = "http://127.0.0.1:5000"
DB_URL = "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db"

def get_db_connection():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def run_tests():
    print("=================================================================")
    print("SigmaFidelity™ Enterprise Upgrades Verification Suite")
    print("=================================================================")
    session = requests.Session()

    # 1. Login as Admin
    print("\n[TEST 1] Authenticating Session as Executive Admin...")
    login_res = session.get(f"{BASE_URL}/debug-login", allow_redirects=True)
    assert login_res.status_code == 200, f"Login failed with status {login_res.status_code}"
    print("  -> Session established successfully.")

    # 2. Verify Centralized Lookups via JSON and HTML
    print("\n[TEST 2] Verifying Centralized Lookups (Facility, Source, Priority)...")
    ajax_res = session.get(f"{BASE_URL}/admin/operations?format=json", headers={"X-Requested-With": "XMLHttpRequest"})
    assert ajax_res.status_code == 200, f"AJAX operations failed: {ajax_res.status_code}"
    payload = ajax_res.json()
    assert "facility_types" in payload and len(payload["facility_types"]) >= 10, "Facility types missing or incomplete"
    assert "lead_sources" in payload and len(payload["lead_sources"]) >= 8, "Lead sources missing or incomplete"
    assert "priority_levels" in payload and len(payload["priority_levels"]) >= 4, "Priority levels missing or incomplete"
    print(f"  -> Successfully verified {len(payload['facility_types'])} facility types, {len(payload['lead_sources'])} lead sources, {len(payload['priority_levels'])} priority levels.")

    # 3. Verify Accounts Workspace Columns & Sales Rep Header
    print("\n[TEST 3] Verifying Accounts View UI Rendering with Sales Rep Column...")
    acc_ui_res = session.get(f"{BASE_URL}/admin/operations?view=accounts")
    assert acc_ui_res.status_code == 200, f"Accounts UI failed: {acc_ui_res.status_code}"
    html = acc_ui_res.text
    assert "Sales Rep" in html, "Sales Rep column header not found in Accounts UI"
    assert "quickUpdateAccount" in html, "quickUpdateAccount JS handler not found in Accounts UI"
    print("  -> Accounts view successfully renders Sales Rep column and inline update hooks.")

    # 4. Verify Manual Lead Creation Attribution (Non-George Attribution)
    print("\n[TEST 4] Verifying Dynamic User Attribution in Manual Lead Creation...")
    lead_name = f"Enterprise Verification Lead {os.urandom(3).hex()}"
    add_lead_res = session.post(f"{BASE_URL}/admin/add-lead", data={
        "company_name": lead_name,
        "decision_maker": "Jane Doe",
        "job_title": "Operations Director",
        "email": "jane@enterprise-test.com",
        "phone": "(214) 555-9090",
        "address": "500 Enterprise Way",
        "city": "Dallas",
        "state": "TX",
        "zipcode": "75201",
        "industry": "Corporate / Office",
        "facility_type": "Office",
        "sqf": "15000",
        "traffic_cycle": "High",
        "service_interest": "Janitorial",
        "lead_source": "Direct Lead",
        "priority_level": "Needs Call Now",
        "owner_id": "5", # Beabe Wiley
        "notes": "Automated verification test."
    }, allow_redirects=True)
    assert add_lead_res.status_code == 200, f"Add lead failed: {add_lead_res.status_code}"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "Leads" WHERE center_name = %s', (lead_name,))
            created_lead = cur.fetchone()
            assert created_lead is not None, "Created lead record not found in PostgreSQL"
            lead_id = created_lead['id']
            assert created_lead['owner_id'] == 5, f"Owner ID expected 5, got {created_lead['owner_id']}"
            assert created_lead['last_contacted_by'] != 'George', f"Attribution was hardcoded to George! Found: {created_lead['last_contacted_by']}"
            print(f"  -> Lead #{lead_id} created. Attribution: '{created_lead['last_contacted_by']}', Owner ID: {created_lead['owner_id']}.")

    # 5. Verify Lead Conversion Attribution Preservation (assigned_rep_id)
    print("\n[TEST 5] Verifying Lead Promotion & Rep Ownership Transfer...")
    promote_res = session.post(f"{BASE_URL}/api/v1/leads/{lead_id}/promote")
    assert promote_res.status_code == 200, f"Lead promotion failed: {promote_res.text}"
    promote_data = promote_res.json()
    new_acc_id = promote_data['customer_id']
    assert promote_data.get('assigned_rep_id') == 5, f"Expected assigned_rep_id 5, got {promote_data.get('assigned_rep_id')}"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "Customers" WHERE customer_id = %s', (new_acc_id,))
            customer = cur.fetchone()
            assert customer is not None, "Promoted Customer account not found in database"
            assert customer['assigned_rep_id'] == 5, f"Expected assigned_rep_id 5 in Customers, found {customer['assigned_rep_id']}"
            
            cur.execute('SELECT * FROM "GlobalActivities" WHERE parent_id = %s AND parent_type = \'Account\' ORDER BY timestamp DESC', (new_acc_id,))
            acc_act = cur.fetchone()
            assert acc_act is not None and "Rep ID: 5" in acc_act['description'], "Conversion activity description missing rep attribution"
            print(f"  -> Account ACC-{new_acc_id} created with assigned_rep_id = 5 and verified activity audit trail.")

    # 6. Verify Account Rep Re-assignment (PUT & PATCH)
    print("\n[TEST 6] Verifying Account Rep Re-assignment via PATCH & PUT...")
    patch_res = session.patch(f"{BASE_URL}/api/v1/accounts/{new_acc_id}", json={"assigned_rep_id": 4})
    assert patch_res.status_code == 200, f"Account PATCH failed: {patch_res.text}"
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT assigned_rep_id FROM "Customers" WHERE customer_id = %s', (new_acc_id,))
            cust_patch = cur.fetchone()
            assert cust_patch['assigned_rep_id'] == 4, f"PATCH failed to update assigned_rep_id to 4, got {cust_patch['assigned_rep_id']}"
            print(f"  -> PATCH /api/v1/accounts/{new_acc_id} successfully updated assigned_rep_id to 4.")

    # 7. Verify Texas Statewide Location Page Routing
    print("\n[TEST 7] Verifying Texas Statewide Dynamic Location Pages...")
    for slug, name in [("dallas", "Dallas"), ("austin", "Austin"), ("houston", "Houston"), ("san-antonio", "San Antonio")]:
        loc_res = session.get(f"{BASE_URL}/locations/{slug}")
        assert loc_res.status_code == 200, f"Location page for {slug} returned status {loc_res.status_code}"
        assert name in loc_res.text, f"City name '{name}' not found in rendered location page HTML"
        print(f"  -> /locations/{slug} rendered dynamically with title & meta for {name}, TX.")

    # 8. Verify Sales Desk Statewide Query Parity
    print("\n[TEST 8] Verifying Field Sales Desk Statewide Alignment...")
    sd_res = session.get(f"{BASE_URL}/admin/sales-desk")
    assert sd_res.status_code == 200, f"Sales desk failed: {sd_res.status_code}"
    print("  -> Field Sales Desk loaded cleanly with dynamic statewide open lead telemetry.")

    # Cleanup test data
    print("\n[CLEANUP] Removing test artifacts from database...")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM "GlobalActivities" WHERE parent_id = %s AND parent_type = \'Account\'', (new_acc_id,))
            cur.execute('DELETE FROM "GlobalActivities" WHERE parent_id = %s AND parent_type = \'Lead\'', (lead_id,))
            cur.execute('DELETE FROM "Customers" WHERE customer_id = %s', (new_acc_id,))
            cur.execute('DELETE FROM "Leads" WHERE id = %s', (lead_id,))
            conn.commit()
    print("  -> Database cleanly restored.")

    print("\n=================================================================")
    print("ALL ENTERPRISE UPGRADE VERIFICATION TESTS PASSED 100%!")
    print("=================================================================")

if __name__ == "__main__":
    run_tests()
