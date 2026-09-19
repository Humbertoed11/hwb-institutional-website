"""
Automated Enterprise RBAC & Security Gateway Verification Suite (Option B Standard)
Standard: HWB-QMS-7.6 Enterprise Zero-Hotfix Mandate
"""
import requests

BASE_URL = "http://localhost:5000"

def run_rbac_test():
    print("=== STARTING ENTERPRISE RBAC VERIFICATION SUITE (OPTION B) ===")
    
    # -------------------------------------------------------------
    # TEST SUITE 1: Sales Representative (Bwiley / sales_field, Role = 'Sales')
    # -------------------------------------------------------------
    print("\n--- 1. Testing Sales Representative (Role = 'Sales') ---")
    sales_sess = requests.Session()
    
    # 1. Authenticate as sales representative
    login_resp = sales_sess.post(f"{BASE_URL}/login", data={
        "username": "sales_field",
        "password": "FieldSales2026!"
    }, allow_redirects=False)
    
    print(f"Login Response: {login_resp.status_code}, Redirects to: {login_resp.headers.get('Location')}")
    assert login_resp.status_code == 302
    assert login_resp.headers.get('Location') == '/admin/operations?view=leads'
    print("  [PASS] Sales login lands directly in /admin/operations?view=leads")

    # 2. Probe Root Homepage '/'
    r_root = sales_sess.get(f"{BASE_URL}/", allow_redirects=False)
    print(f"Root '/' Probe: HTTP {r_root.status_code}, Location: {r_root.headers.get('Location')}")
    assert r_root.status_code == 302
    assert r_root.headers.get('Location') == '/admin/operations?view=leads'
    print("  [PASS] Sales visiting '/' is kept in workflow at /admin/operations?view=leads")

    # 3. Access Authorized Leads View: /admin/operations?view=leads
    r_leads = sales_sess.get(f"{BASE_URL}/admin/operations?view=leads", allow_redirects=False)
    print(f"Leads View Access: HTTP {r_leads.status_code}")
    assert r_leads.status_code == 200
    leads_html = r_leads.text
    # Verify Option B Streamline Navigation
    assert "Field Sales Desk" in leads_html
    assert "GC Bids" not in leads_html
    assert "Work Monitor" not in leads_html
    assert "/admin/executive" not in leads_html
    assert "onclick=\"exportSelectedLeads()\"" not in leads_html
    print("  [PASS] Leads view loaded with Option B clean tabs (GC Bids/Executive/Export hidden)")

    # 4. Access Authorized Accounts View: /admin/operations?view=accounts
    r_accs = sales_sess.get(f"{BASE_URL}/admin/operations?view=accounts", allow_redirects=False)
    print(f"Accounts View Access: HTTP {r_accs.status_code}")
    assert r_accs.status_code == 200
    accs_html = r_accs.text
    assert "onclick=\"exportSelectedAccounts()\"" not in accs_html
    print("  [PASS] Accounts view loaded with Export button hidden")

    # 5. Access Dedicated Mobile Cockpit Bridge: /admin/sales-desk
    r_desk = sales_sess.get(f"{BASE_URL}/admin/sales-desk", allow_redirects=False)
    print(f"Field Sales Desk Access: HTTP {r_desk.status_code}")
    assert r_desk.status_code == 200
    print("  [PASS] Sales Desk bridge accessible (HTTP 200 OK)")

    # 6. Unauthorized Sub-View Probes: construction_bids & monitor
    r_bids = sales_sess.get(f"{BASE_URL}/admin/operations?view=construction_bids", allow_redirects=False)
    print(f"GC Bids Sub-view Probe: HTTP {r_bids.status_code}, Location: {r_bids.headers.get('Location')}")
    assert r_bids.status_code == 302
    assert r_bids.headers.get('Location') == '/admin/operations?view=leads'
    print("  [PASS] Unauthorized GC Bids view blocked & redirected to leads")

    r_mon = sales_sess.get(f"{BASE_URL}/admin/operations?view=monitor", allow_redirects=False)
    print(f"Work Monitor Sub-view Probe: HTTP {r_mon.status_code}, Location: {r_mon.headers.get('Location')}")
    assert r_mon.status_code == 302
    assert r_mon.headers.get('Location') == '/admin/operations?view=leads'
    print("  [PASS] Unauthorized Work Monitor view blocked & redirected to leads")

    # 7. Unauthorized Route Probes: /admin/executive & /admin/master
    r_exec = sales_sess.get(f"{BASE_URL}/admin/executive", allow_redirects=False)
    print(f"/admin/executive Probe: HTTP {r_exec.status_code}, Location: {r_exec.headers.get('Location')}")
    assert r_exec.status_code in [302, 403]
    print("  [PASS] /admin/executive blocked & quarantined")

    # 8. Data Protection Locks: Export & Delete
    r_exp = sales_sess.post(f"{BASE_URL}/api/v1/leads/export-selected", json={"lead_ids": [44545]}, allow_redirects=False)
    print(f"Leads CSV Export Probe: HTTP {r_exp.status_code}")
    assert r_exp.status_code == 403
    print("  [PASS] Bulk CSV Export denied (HTTP 403 Forbidden)")

    r_del = sales_sess.delete(f"{BASE_URL}/api/v1/leads/44545", allow_redirects=False)
    print(f"Lead Deletion Probe: HTTP {r_del.status_code}")
    assert r_del.status_code == 403
    print("  [PASS] Lead deletion denied (HTTP 403 Forbidden)")

    # -------------------------------------------------------------
    # TEST SUITE 2: Executive User (Role = 'Executive' / 'Admin')
    # -------------------------------------------------------------
    print("\n--- 2. Testing Executive User (Role = 'Executive' / 'Admin') ---")
    exec_sess = requests.Session()
    
    r_debug = exec_sess.get(f"{BASE_URL}/debug-login", allow_redirects=False)
    assert r_debug.status_code == 302
    
    # Executive visiting /admin/operations?view=leads
    r_exec_leads = exec_sess.get(f"{BASE_URL}/admin/operations?view=leads", allow_redirects=False)
    print(f"Executive Leads View: HTTP {r_exec_leads.status_code}")
    assert r_exec_leads.status_code == 200
    exec_html = r_exec_leads.text
    # Executive sees the full suite
    assert "GC Bids" in exec_html
    assert "Work Monitor" in exec_html
    assert "/admin/executive" in exec_html
    assert "onclick=\"exportSelectedLeads()\"" in exec_html
    print("  [PASS] Executive has full access to all corporate tabs and Export tools")

    # Executive visiting /admin/executive
    r_exec_panel = exec_sess.get(f"{BASE_URL}/admin/executive", allow_redirects=False)
    print(f"Executive Panel: HTTP {r_exec_panel.status_code}")
    assert r_exec_panel.status_code == 200
    print("  [PASS] Executive panel accessible (HTTP 200 OK)")

    print("\n=== ALL ENTERPRISE RBAC AUDIT CHECKS PASSED (100% SUCCESS) ===")

if __name__ == '__main__':
    run_rbac_test()
