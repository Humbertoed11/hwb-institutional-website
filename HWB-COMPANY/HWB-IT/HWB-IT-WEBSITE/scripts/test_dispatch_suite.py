"""
Test Suite: SigmaFidelity™ Internal Work Order Dispatch & Execution Engine
Standard: HWB-QMS-11.2 High-Impact Verification Protocol
"""

import os
import json
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# We test using Flask's test client inside the app context
from main_app import app
from core.models.user import User

print("=======================================================")
print("  Running Test Suite: Internal Dispatch & Work Orders")
print("=======================================================")

with app.test_client() as client:
    with app.app_context():
        # Log in as admin user (e.g. humberto / id 1)
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'
            sess['_fresh'] = True

        # 1. Test GET /api/v1/dispatch/work-orders
        print("\n[1] Testing GET /api/v1/dispatch/work-orders...")
        resp = client.get('/api/v1/dispatch/work-orders')
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.get_json()
        print(f"    ✓ Found {data['count']} existing work orders.")
        for wo in data['work_orders']:
            print(f"      - WO #{wo['work_order_id']} | Facility: {wo['company_name']} | Status: {wo['status']} | Tech: {wo.get('tech_first_name')} {wo.get('tech_last_name')}")

        # 2. Test POST /api/v1/dispatch/work-orders (Create new dispatch)
        print("\n[2] Testing POST /api/v1/dispatch/work-orders...")
        new_order_payload = {
            "customer_id": 4, # Bosanna LLC (Collin College Frisco Campus)
            "service_type": "Terminal Restroom Sanitation",
            "scheduled_date": datetime.now().strftime("%Y-%m-%d"),
            "shift_window": "Evening Shift (6:00 PM – 11:00 PM)",
            "scheduled_time": "18:30",
            "assigned_technician_id": 3, # Gonzalo Bolanos (HWB-EMP-1002)
            "dock_ingress_instructions": "Dock Ingress: Access loading bay via 9700 Wade Blvd, Frisco, TX 75035. Present Texas DPS FACT badge.",
            "security_access_code": "KEY-FOB-BAY-04",
            "crew_notes": "TIPS #260102 High-touch academic terminal disinfection protocol.",
            "status": "Scheduled"
        }
        resp = client.post('/api/v1/dispatch/work-orders', json=new_order_payload)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.data}"
        create_data = resp.get_json()
        new_wo_id = create_data['work_order_id']
        print(f"    ✓ Successfully created Work Order #{new_wo_id}")

        # 3. Test GET single work order
        print(f"\n[3] Testing GET /api/v1/dispatch/work-orders/{new_wo_id}...")
        resp = client.get(f'/api/v1/dispatch/work-orders/{new_wo_id}')
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        wo_detail = resp.get_json()['work_order']
        print(f"    ✓ Retrieved WO #{new_wo_id} detail:")
        print(f"      - Facility: {wo_detail['company_name']}")
        print(f"      - Assigned Tech: {wo_detail['tech_first_name']} {wo_detail['tech_last_name']} ({wo_detail['tech_employee_number']})")
        print(f"      - DPS Cleared Date: {wo_detail['tech_dps_clearance']}")
        assert wo_detail['tech_first_name'] == 'Gonzalo', "Assigned tech should be Gonzalo"

        # 4. Test Quick Reassign to Carlos Mendoza (ID 2)
        print(f"\n[4] Testing POST /api/v1/dispatch/work-orders/{new_wo_id}/assign to Carlos Mendoza (ID 2)...")
        resp = client.post(f'/api/v1/dispatch/work-orders/{new_wo_id}/assign', json={"technician_id": 2})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assign_data = resp.get_json()
        print(f"    ✓ Reassign response: {assign_data['message']}")
        assert assign_data['technician_name'] == 'Carlos Mendoza'
        assert assign_data['dps_cleared'] == True

        # 5. Test Status Transition to 'In Progress' (Verify auto-stamped actual_start_time)
        print(f"\n[5] Testing status transition to 'In Progress'...")
        resp = client.post(f'/api/v1/dispatch/work-orders/{new_wo_id}/transition', json={"status": "In Progress"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        # Verify timestamp
        resp = client.get(f'/api/v1/dispatch/work-orders/{new_wo_id}')
        started_wo = resp.get_json()['work_order']
        print(f"    ✓ Work Order status: {started_wo['status']}")
        print(f"    ✓ Actual Start Time: {started_wo['actual_start_time']}")
        assert started_wo['actual_start_time'] is not None, "Start time should be auto-stamped"

        # 6. Test Status Transition to 'COMPLETED' (Verify auto-stamped actual_end_time)
        print(f"\n[6] Testing status transition to 'COMPLETED'...")
        resp = client.post(f'/api/v1/dispatch/work-orders/{new_wo_id}/transition', json={"status": "COMPLETED"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        # Verify timestamp
        resp = client.get(f'/api/v1/dispatch/work-orders/{new_wo_id}')
        completed_wo = resp.get_json()['work_order']
        print(f"    ✓ Work Order status: {completed_wo['status']}")
        print(f"    ✓ Actual End Time: {completed_wo['actual_end_time']}")
        assert completed_wo['actual_end_time'] is not None, "End time should be auto-stamped"

        # 7. Test Operations Backoffice HTML Rendering for ?view=monitor
        print("\n[7] Testing GET /admin/operations?view=monitor HTML rendering...")
        resp = client.get('/admin/operations?view=monitor')
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        html = resp.data.decode('utf-8')
        assert 'Internal Dispatch &amp; Shift Execution Hub' in html or 'Internal Dispatch & Shift Execution Hub' in html, "Page must include new Dispatch Hub title"
        assert 'modal-dispatch-create' in html, "Page must include create modal"
        assert 'modal-dispatch-detail' in html, "Page must include detail modal"
        assert 'Collin College Frisco Campus' in html or 'Bosanna LLC' in html, "Page must render Collin College / Bosanna work orders"
        print("    ✓ Backoffice Operations ?view=monitor rendered cleanly with 200 OK and all dispatch elements!")

print("\n=======================================================")
print("  ✓ ALL TEST CASES PASSED SUCCESSFULLY (7/7)")
print("=======================================================\n")
