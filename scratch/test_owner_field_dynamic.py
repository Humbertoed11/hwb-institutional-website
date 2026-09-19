"""
Automated Dynamic Lead Owner Verification Suite
Verifies:
1. Dynamic population of system_users from PostgreSQL Users table
2. Inline select contains real database users (Humberto Dominguez, Field Sales Executive, Beabe Wiley)
3. PATCH /api/v1/leads/<id> updates owner_id in database
4. Bulk action assign_owner assigns leads to bwiley (id=5) and unassigns
"""
import requests

BASE_URL = "http://localhost:5000"

def test_dynamic_lead_owner():
    print("=== STARTING DYNAMIC LEAD OWNER VERIFICATION SUITE ===")
    sess = requests.Session()
    
    # 1. Login as Executive
    r_login = sess.get(f"{BASE_URL}/debug-login", allow_redirects=False)
    assert r_login.status_code == 302
    print("  [PASS] Logged in as Executive")

    # 2. Fetch Leads View HTML
    r_leads = sess.get(f"{BASE_URL}/admin/operations?view=leads&cols=company,status,owner")
    assert r_leads.status_code == 200
    html = r_leads.text

    # Verify SYSTEM_USERS_MAP is present and populated with real users
    assert "SYSTEM_USERS_MAP" in html
    assert "Beabe Wiley" in html
    assert "Field Sales Executive" in html
    assert "Humberto Dominguez" in html
    assert "Silas Sync" not in html
    assert "Lauri Tells" not in html
    print("  [PASS] HTML rendered with live database users (Beabe Wiley, Field Sales Executive, Humberto Dominguez)")
    print("  [PASS] Hardcoded synthetic users (Silas Sync, Lauri Tells) completely eliminated")

    # 3. Test Single Lead Quick Update (PATCH /api/v1/leads/<id>)
    test_lead_id = 74448  # Existing test lead
    print(f"\n--- Testing Single Lead PATCH owner_id on Lead #{test_lead_id} ---")
    
    # Assign to Beabe Wiley (id=5)
    r_patch = sess.patch(f"{BASE_URL}/api/v1/leads/{test_lead_id}", json={"owner_id": 5})
    assert r_patch.status_code == 200
    assert r_patch.json().get('status') == 'success'
    
    # Verify in Lead API
    r_get = sess.get(f"{BASE_URL}/api/v1/leads/{test_lead_id}")
    lead_data = r_get.json()['lead']
    assert lead_data['owner_id'] == 5
    print("  [PASS] Single lead PATCH successfully updated owner_id to 5 (Beabe Wiley)")

    # Unassign single lead
    r_patch_unassign = sess.patch(f"{BASE_URL}/api/v1/leads/{test_lead_id}", json={"owner_id": ""})
    assert r_patch_unassign.status_code == 200
    r_get2 = sess.get(f"{BASE_URL}/api/v1/leads/{test_lead_id}")
    assert r_get2.json()['lead']['owner_id'] is None
    print("  [PASS] Single lead PATCH successfully unassigned owner_id (None)")

    # 4. Test Bulk Assign Action
    print(f"\n--- Testing Bulk Action assign_owner on Lead #{test_lead_id} ---")
    r_bulk = sess.post(f"{BASE_URL}/api/v1/leads/batch-action", json={
        "action": "assign_owner",
        "lead_ids": [test_lead_id],
        "params": {"owner_id": 5}
    })
    assert r_bulk.status_code == 200
    r_get3 = sess.get(f"{BASE_URL}/api/v1/leads/{test_lead_id}")
    assert r_get3.json()['lead']['owner_id'] == 5
    print("  [PASS] Bulk assign_owner successfully assigned lead to 5 (Beabe Wiley)")

    # Bulk Unassign
    r_bulk_unassign = sess.post(f"{BASE_URL}/api/v1/leads/batch-action", json={
        "action": "assign_owner",
        "lead_ids": [test_lead_id],
        "params": {"owner_id": None}
    })
    assert r_bulk_unassign.status_code == 200
    r_get4 = sess.get(f"{BASE_URL}/api/v1/leads/{test_lead_id}")
    assert r_get4.json()['lead']['owner_id'] is None
    print("  [PASS] Bulk assign_owner successfully unassigned lead")

    print("\n=== ALL DYNAMIC LEAD OWNER TESTS PASSED (100% SUCCESS) ===")

if __name__ == '__main__':
    test_dynamic_lead_owner()
