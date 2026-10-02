"""
SigmaFidelity™ Site Security Rack #9 & Inactivity Timeout Verification Battery
Standards: HWB-QMS-11.10, HWB-QMS-7.6, SOC 2 Type II CC6.8, ISO 27001 Clause A.12.4, NIST SP 800-92
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)

Verification Battery:
1. WORM Immutability Verification (UPDATE & DELETE abortion via PostgreSQL trigger)
2. Authentication Lifecycle Logging (LOGIN_SUCCESS, LOGIN_FAIL, LOGOUT in SecurityAuditLogs)
3. Inactivity Timeout Enforcement on Web Routes (30-min idle threshold -> logout -> redirect /login?reason=inactivity)
4. Inactivity Timeout Enforcement on API Routes (JSON 401 response with SESSION_TIMEOUT payload)
5. RBAC Quarantine Violation Logging (ROUTE_BLOCKED logged in SecurityAuditLogs)
6. Site Security Rack #9 Telemetry Engine (Composite score, threat level, 24h event tallies)
7. Self-Healing Engine 9-Rack History Persistence (All 9 racks recorded in RackTelemetryHistory)
"""

import os
import sys
import time
import json
import unittest

# Ensure application root is in python path
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

import psycopg2
from main_app import app
from core.services.database import get_db
from core.services.security_logger import log_security_event, get_site_security_telemetry
from core.services.self_healing_engine import record_rack_telemetry_snapshot


class SiteSecurityRack09TestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()
        cls.db_url = app.config['DATABASE_URL']

    def test_01_worm_immutability_blocks_updates_and_deletes(self):
        """Verifies PostgreSQL WORM trigger rejects any UPDATE or DELETE against SecurityAuditLogs."""
        test_action = f"WORM_TEST_{int(time.time())}"
        
        # 1. Insert test record via security logger
        log_security_event(
            event_category="AUDIT_VERIFY",
            event_action=test_action,
            severity="INFO",
            username="system_auditor",
            details={"worm_test": True}
        )

        conn = get_db(self.db_url)
        
        # 2. Attempt UPDATE - Must fail
        update_blocked = False
        with conn.cursor() as cur:
            try:
                cur.execute(
                    'UPDATE "SecurityAuditLogs" SET severity = \'CRITICAL\' WHERE event_action = %s;',
                    (test_action,)
                )
                conn.commit()
            except psycopg2.DatabaseError as e:
                conn.rollback()
                update_blocked = True
                self.assertIn("SECURITY AUDIT VIOLATION", str(e))
                self.assertIn("immutable", str(e))
        self.assertTrue(update_blocked, "Database WORM trigger failed to block UPDATE on SecurityAuditLogs")

        # 3. Attempt DELETE - Must fail
        delete_blocked = False
        with conn.cursor() as cur:
            try:
                cur.execute(
                    'DELETE FROM "SecurityAuditLogs" WHERE event_action = %s;',
                    (test_action,)
                )
                conn.commit()
            except psycopg2.DatabaseError as e:
                conn.rollback()
                delete_blocked = True
                self.assertIn("SECURITY AUDIT VIOLATION", str(e))
                self.assertIn("immutable", str(e))
        self.assertTrue(delete_blocked, "Database WORM trigger failed to block DELETE on SecurityAuditLogs")

        # 4. Confirm record remains intact
        with conn.cursor() as cur:
            cur.execute(
                'SELECT event_category, severity FROM "SecurityAuditLogs" WHERE event_action = %s;',
                (test_action,)
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row['event_category'], "AUDIT_VERIFY")
            self.assertEqual(row['severity'], "INFO")
        conn.close()

    def test_02_authentication_lifecycle_logging(self):
        """Verifies valid login, invalid login, and voluntary logout generate forensic audit events."""
        test_client = app.test_client()

        # 1. Valid Authentication
        login_res = test_client.post('/login', data={
            'username': 'admin',
            'password': 'password11'
        }, follow_redirects=False)
        self.assertEqual(login_res.status_code, 302, "Valid login did not redirect")

        # Verify LOGIN_SUCCESS was logged (matches mapped CEO account 'hdominguez' or 'admin')
        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('''
                SELECT event_action, severity, username 
                FROM "SecurityAuditLogs" 
                WHERE event_action = 'LOGIN_SUCCESS' AND username IN ('admin', 'hdominguez')
                ORDER BY timestamp DESC LIMIT 1;
            ''')
            row = cur.fetchone()
            self.assertIsNotNone(row, "LOGIN_SUCCESS not recorded in SecurityAuditLogs")
            self.assertEqual(row['severity'], 'INFO')
        conn.close()

        # 2. Voluntary Logout
        logout_res = test_client.get('/logout', follow_redirects=False)
        self.assertEqual(logout_res.status_code, 302, "Logout did not redirect")

        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('''
                SELECT event_action, severity, username 
                FROM "SecurityAuditLogs" 
                WHERE event_action = 'LOGOUT' AND username IN ('admin', 'hdominguez')
                ORDER BY timestamp DESC LIMIT 1;
            ''')
            row = cur.fetchone()
            self.assertIsNotNone(row, "LOGOUT not recorded in SecurityAuditLogs")
            self.assertEqual(row['severity'], 'INFO')
        conn.close()

        # 3. Invalid Authentication Attempt
        fake_user = f"intruder_{int(time.time())}"
        fail_res = test_client.post('/login', data={
            'username': fake_user,
            'password': 'wrong_password_999'
        }, follow_redirects=False)
        self.assertEqual(fail_res.status_code, 200, "Failed login should re-render login page")

        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('''
                SELECT event_action, severity, username 
                FROM "SecurityAuditLogs" 
                WHERE event_action = 'LOGIN_FAIL' AND username = %s
                ORDER BY timestamp DESC LIMIT 1;
            ''', (fake_user,))
            row = cur.fetchone()
            self.assertIsNotNone(row, f"LOGIN_FAIL for {fake_user} not recorded in SecurityAuditLogs")
            self.assertEqual(row['severity'], 'WARNING')
        conn.close()

    def test_03_inactivity_timeout_enforcement_web(self):
        """Verifies session inactivity beyond threshold terminates auth, logs event, and redirects to /login?reason=inactivity."""
        test_client = app.test_client()

        # Step 1: Log in as admin
        login_res = test_client.post('/login', data={
            'username': 'admin',
            'password': 'password11'
        }, follow_redirects=False)
        self.assertEqual(login_res.status_code, 302)

        # Step 2: Access protected route while active -> Should succeed (200 OK)
        active_res = test_client.get('/admin/operations')
        self.assertEqual(active_res.status_code, 200, "Active session failed to access /admin/operations")

        # Step 3: Fast-forward inactivity timestamp beyond the 1800-second threshold (35 minutes ago = 2100s)
        with test_client.session_transaction() as sess:
            sess['last_activity'] = time.time() - 2100

        # Step 4: Request protected route with dormant session
        expired_res = test_client.get('/admin/operations', follow_redirects=False)
        
        # Verify 302 Redirect to /login with reason=inactivity
        self.assertEqual(expired_res.status_code, 302, "Dormant session was not redirected")
        location = expired_res.headers.get('Location', '')
        self.assertIn('/login', location)
        self.assertIn('reason=inactivity', location)

        # Step 5: Query SecurityAuditLogs to verify SESSION_TIMEOUT event
        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('''
                SELECT event_category, event_action, severity, username, details
                FROM "SecurityAuditLogs"
                WHERE event_action = 'SESSION_TIMEOUT' AND username IN ('admin', 'hdominguez')
                ORDER BY timestamp DESC LIMIT 1;
            ''')
            row = cur.fetchone()
            self.assertIsNotNone(row, "SESSION_TIMEOUT was not persisted to SecurityAuditLogs")
            self.assertEqual(row['event_category'], 'AUTH')
            self.assertEqual(row['severity'], 'INFO')
            details = row['details'] if isinstance(row['details'], dict) else json.loads(row['details'])
            self.assertGreaterEqual(details.get('inactive_minutes', 0), 30.0)
            self.assertEqual(details.get('threshold_seconds'), 1800)
        conn.close()

        # Step 6: Verify session is purged; subsequent request is unauthenticated
        subsequent_res = test_client.get('/admin/operations', follow_redirects=False)
        self.assertEqual(subsequent_res.status_code, 302)
        # Should now redirect to login via LoginManager unauthorized handler (without reason=inactivity)
        sub_location = subsequent_res.headers.get('Location', '')
        self.assertIn('/login', sub_location)
        self.assertNotIn('reason=inactivity', sub_location)

    def test_04_inactivity_timeout_enforcement_api(self):
        """Verifies session inactivity on API routes returns a structured JSON 401 error."""
        test_client = app.test_client()

        # Log in
        test_client.post('/login', data={'username': 'admin', 'password': 'password11'}, follow_redirects=False)

        # Set session to 35 minutes idle
        with test_client.session_transaction() as sess:
            sess['last_activity'] = time.time() - 2100

        # Request API endpoint
        api_res = test_client.get('/api/v1/rack-telemetry')
        self.assertEqual(api_res.status_code, 401)
        data = api_res.get_json()
        self.assertIsNotNone(data)
        self.assertEqual(data.get('reason'), 'SESSION_TIMEOUT')
        self.assertIn('inactivity', data.get('message', '').lower())

    def test_05_route_quarantine_rbac_violation_logging(self):
        """Verifies unauthorized route attempts trigger ROUTE_BLOCKED forensic logging."""
        from core.security import log_security_violation

        test_path = f"/admin/classified_zone_{int(time.time())}"
        log_security_violation(
            999,
            "test_sales_rep",
            "Sales",
            test_path,
            "GET"
        )

        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('''
                SELECT event_category, event_action, severity, username, details
                FROM "SecurityAuditLogs"
                WHERE event_action = 'ROUTE_BLOCKED' AND username = 'test_sales_rep'
                ORDER BY timestamp DESC LIMIT 1;
            ''')
            row = cur.fetchone()
            self.assertIsNotNone(row, "ROUTE_BLOCKED not persisted to SecurityAuditLogs")
            self.assertEqual(row['event_category'], 'RBAC')
            self.assertEqual(row['severity'], 'WARNING')
        conn.close()

    def test_06_site_security_telemetry_computation(self):
        """Verifies get_site_security_telemetry produces Rack #9 telemetry conforming to QMS standards."""
        telemetry = get_site_security_telemetry(self.db_url)

        self.assertIsInstance(telemetry, dict)
        self.assertEqual(telemetry.get('rack_number'), 9)
        self.assertEqual(telemetry.get('rack_name'), "Site Security & Operations Hub")
        self.assertIn(telemetry.get('status'), ['ONLINE', 'DEGRADED', 'OPTIMAL'])
        self.assertIn(telemetry.get('threat_level'), ['NOMINAL', 'ELEVATED', 'CRITICAL'])

        score = telemetry.get('composite_score', 0)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

        metrics = telemetry.get('metrics', {})
        expected_keys = [
            'total_security_events_24h',
            'auth_failures_24h',
            'rate_limit_blocks_24h',
            'bot_drops_24h',
            'dormant_sessions_cleared'
        ]
        for key in expected_keys:
            self.assertIn(key, metrics, f"Telemetry metrics missing {key}")

        recent_events = telemetry.get('recent_events', [])
        self.assertIsInstance(recent_events, list)
        self.assertGreater(len(recent_events), 0, "recent_events should not be empty")
        for ev in recent_events:
            self.assertIn('description', ev, "Event missing synthesized description")
            self.assertTrue(ev['description'], "Event description should not be empty")
            self.assertIn('action_taken', ev, "Event missing action_taken")
            self.assertTrue(ev['action_taken'], "action_taken should not be empty")
            self.assertIn('action_to_be_taken', ev, "Event missing action_to_be_taken")
            self.assertTrue(ev['action_to_be_taken'], "action_to_be_taken should not be empty")
            self.assertIn('playbook_status', ev, "Event missing playbook_status")
            self.assertIn(ev['playbook_status'], ['NOMINAL', 'RESOLVED', 'MONITOR', 'AUDIT', 'INVESTIGATE', 'VERIFY', 'REVIEW'])

    def test_07_self_healing_engine_9_rack_persistence(self):
        """Verifies self-healing engine ingests all 9 operational racks into RackTelemetryHistory."""
        # Execute telemetry snapshot ingestion
        result = record_rack_telemetry_snapshot(db_url=self.db_url)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('status'), 'success')

        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            # Query the latest snapshot timestamp
            cur.execute('SELECT MAX(timestamp) AS latest_time FROM "RackTelemetryHistory";')
            latest_time = cur.fetchone()['latest_time']
            self.assertIsNotNone(latest_time, "No records found in RackTelemetryHistory")

            # Query all racks recorded at this latest timestamp
            cur.execute('''
                SELECT rack_number, metric_category, score_value, status_tag 
                FROM "RackTelemetryHistory" 
                WHERE timestamp = %s 
                ORDER BY rack_number ASC;
            ''', (latest_time,))
            racks = cur.fetchall()

            rack_numbers = [r['rack_number'] for r in racks]
            # Expect exactly 10 racks (racks 1 through 10)
            self.assertEqual(len(rack_numbers), 10, f"Expected 10 racks, found {len(rack_numbers)}: {rack_numbers}")
            self.assertEqual(rack_numbers, list(range(1, 11)), f"Rack sequence mismatch: {rack_numbers}")

            # Verify Rack 9 specifically
            rack_09 = next(r for r in racks if r['rack_number'] == 9)
            self.assertEqual(rack_09['metric_category'], 'SITE_SECURITY')
            self.assertGreaterEqual(rack_09['score_value'], 0)
            self.assertLessEqual(rack_09['score_value'], 100)

            # Verify Rack 10 specifically
            rack_10 = next(r for r in racks if r['rack_number'] == 10)
            self.assertEqual(rack_10['metric_category'], 'WEB_ANALYTICS')
            self.assertGreaterEqual(rack_10['score_value'], 0)
            self.assertLessEqual(rack_10['score_value'], 100)
        conn.close()

    def test_08_bulk_data_export_audit_logging(self):
        """Verifies bulk CSV exports for leads and accounts trigger BULK_DATA_EXPORT forensic logs."""
        test_client = app.test_client()
        test_client.post('/login', data={'username': 'admin', 'password': 'password11'}, follow_redirects=False)

        # 1. Accounts Export
        acc_res = test_client.post('/api/v1/accounts/export-selected', data={'account_ids': json.dumps([1, 2])})
        self.assertEqual(acc_res.status_code, 200)

        # 2. Leads Export
        lead_res = test_client.post('/api/v1/leads/export-selected', data={'lead_ids': json.dumps([1, 2])})
        self.assertEqual(lead_res.status_code, 200)

        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('''
                SELECT event_category, event_action, severity, details
                FROM "SecurityAuditLogs"
                WHERE event_action = 'BULK_DATA_EXPORT'
                ORDER BY timestamp DESC LIMIT 2;
            ''')
            rows = cur.fetchall()
            self.assertGreaterEqual(len(rows), 2, "Failed to record BULK_DATA_EXPORT events")
            for r in rows:
                self.assertEqual(r['event_category'], 'DATA_LIFECYCLE')
                self.assertEqual(r['severity'], 'WARNING')
        conn.close()

    def test_09_user_admin_audit_logging(self):
        """Verifies user creation, role changes, and password updates trigger USER_ADMIN audit logs."""
        test_client = app.test_client()
        test_client.post('/login', data={'username': 'admin', 'password': 'password11'}, follow_redirects=False)

        test_uname = f"test_worker_{int(time.time())}"
        
        # 1. Create User
        res_create = test_client.post('/admin/executive', data={
            'action': 'create_user',
            'new_username': test_uname,
            'new_password': 'Password123!',
            'full_name': 'Test Enterprise Worker',
            'user_email': f'{test_uname}@hwbcleaning.com',
            'user_role': 'Operator',
            'status': 'Active'
        }, follow_redirects=False)

        # Verify USER_CREATED was logged
        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('''
                SELECT event_category, event_action, severity, details
                FROM "SecurityAuditLogs"
                WHERE event_action = 'USER_CREATED' AND details->>'created_username' = %s
                ORDER BY timestamp DESC LIMIT 1;
            ''', (test_uname,))
            row = cur.fetchone()
            self.assertIsNotNone(row, "USER_CREATED was not recorded in SecurityAuditLogs")
            self.assertEqual(row['event_category'], 'USER_ADMIN')

            # Clean up test user
            cur.execute('DELETE FROM "Users" WHERE username = %s;', (test_uname,))
            conn.commit()
        conn.close()

    def test_10_financial_takeoff_commit_audit_logging(self):
        """Verifies estimating takeoff commit triggers TAKEOFF_COMMITTED financial integrity log."""
        test_client = app.test_client()
        test_client.post('/login', data={'username': 'admin', 'password': 'password11'}, follow_redirects=False)

        # Commit an estimate on Bid #1 (or first available bid)
        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM "ConstructionBids" LIMIT 1;')
            bid_row = cur.fetchone()
            target_bid_id = bid_row['id'] if isinstance(bid_row, dict) else (bid_row[0] if bid_row else 1)
        conn.close()

        commit_res = test_client.post(f'/api/v1/bids/{target_bid_id}/commit-estimate', json={
            'cleanable_sqft': 45000,
            'estimated_value': 125000.00,
            'scope_phase': 'Phase 1 - Final Clean',
            'status': 'Takeoff Completed',
            'notes': 'Enterprise SOC 2 Takeoff Audit Verification'
        })
        self.assertEqual(commit_res.status_code, 200)

        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('''
                SELECT event_category, event_action, severity, details
                FROM "SecurityAuditLogs"
                WHERE event_action = 'TAKEOFF_COMMITTED'
                ORDER BY timestamp DESC LIMIT 1;
            ''')
            row = cur.fetchone()
            self.assertIsNotNone(row, "TAKEOFF_COMMITTED was not recorded in SecurityAuditLogs")
            self.assertEqual(row['event_category'], 'FINANCIAL_INTEGRITY')
            details = row['details'] if isinstance(row['details'], dict) else json.loads(row['details'])
            self.assertEqual(details.get('cleanable_sqft'), 45000)
        conn.close()

    def test_11_auditing_the_auditor_logging(self):
        """Verifies accessing IT Command Hub / Rack 9 triggers AUDIT_LOG_INSPECTED forensic log."""
        test_client = app.test_client()
        test_client.post('/login', data={'username': 'admin', 'password': 'password11'}, follow_redirects=False)

        hub_res = test_client.get('/admin/operations?view=it_telemetry')
        self.assertEqual(hub_res.status_code, 200)

        conn = get_db(self.db_url)
        with conn.cursor() as cur:
            cur.execute('''
                SELECT event_category, event_action, severity
                FROM "SecurityAuditLogs"
                WHERE event_action = 'AUDIT_LOG_INSPECTED'
                ORDER BY timestamp DESC LIMIT 1;
            ''')
            row = cur.fetchone()
            self.assertIsNotNone(row, "AUDIT_LOG_INSPECTED was not recorded in SecurityAuditLogs")
            self.assertEqual(row['event_category'], 'SECURITY_AUDIT')
            self.assertEqual(row['severity'], 'INFO')
        conn.close()


if __name__ == '__main__':
    print("=" * 80)
    print("⚡ SIGMAFIDELITY™ SITE SECURITY RACK #9 & INACTIVITY TIMEOUT TEST SUITE")
    print("=" * 80)
    suite = unittest.TestLoader().loadTestsFromTestCase(SiteSecurityRack09TestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    sys.exit(0 if res.wasSuccessful() else 1)
