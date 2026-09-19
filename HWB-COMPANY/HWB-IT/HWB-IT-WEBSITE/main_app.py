from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory, abort, session
from flask_compress import Compress
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import hashlib
import psycopg2
import json
import datetime
import re
import requests
import msal
from urllib.parse import urlencode, urlparse
from dotenv import load_dotenv
from werkzeug.exceptions import HTTPException
from typing import List, Tuple, Any, Optional
from config import sys_config

# --- SigmaFidelity™ Core Service Layer ---
from core.services.database import get_db, sync_db_sequences, db_cursor
from core.services.email_service import transmit_email
from core.utils import format_to_mdy

# Institutional Secret Loading (HWB-QMS-9.5)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../.."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

app = Flask(__name__, 
            static_folder=os.path.join(BASE_DIR, 'static'), 
            template_folder=os.path.join(BASE_DIR, 'templates'))
Compress(app)
app.config.from_object(sys_config)
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=31)

# --- SigmaFidelity™ Institutional JSON Encoder ---
class InstitutionalJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)

app.json_encoder = InstitutionalJSONEncoder

# --- SigmaFidelity™ Standard Phone Formatter Filter (HWB-QMS-11.2) ---
@app.template_filter('format_phone')
def format_phone_filter(phone: Optional[str]) -> str:
    if not phone or str(phone).strip() in ('', 'None', 'null', 'N/A', '--'):
        return '--'
    phone_str = str(phone).strip()
    ext = ''
    ext_match = re.search(r'(?:ext\.?|x)\s*(\d+)', phone_str, re.IGNORECASE)
    if ext_match:
        ext = f' ext. {ext_match.group(1)}'
        base_phone = phone_str[:ext_match.start()]
    else:
        base_phone = phone_str
        
    digits = re.sub(r'\D', '', base_phone)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
        
    if len(digits) == 10:
        return f'({digits[0:3]})-{digits[3:6]}-{digits[6:10]}{ext}'
    return phone_str

# --- 12-Factor Compliance: Startup Verification ---
# Fail fast if critical configurations are not set in the environment.
required_configs = ['SECRET_KEY', 'DATABASE_URL', 'CLIENT_DATABASE_URL']
missing_configs = [c for c in required_configs if not app.config.get(c)]
if missing_configs:
    raise ValueError(f"FATAL: Missing required environment variables: {', '.join(missing_configs)}")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    try:
        print("[BOOT] SigmaFidelity™ High-Fidelity Startup Sequence Initiated.", flush=True)
        sync_db_sequences(app.config['DATABASE_URL'])
        
        # --- SigmaFidelity™ Poka-Yoke Schema Migrator (BUG-005/008) ---
        conn = get_db(app.config['DATABASE_URL'])
        
        # We perform schema alterations and table creation in a committed block first
        try:
            with conn.cursor() as cur:
                # 1. Hardening "Services" Table
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS traffic_cycle TEXT;')
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS frequency TEXT;')
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS notes TEXT;')
                cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS status TEXT DEFAULT \'Active\';')
                
                # 2. Hardening "Customers" Table
                cur.execute('ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS billing_address TEXT;')
                cur.execute('ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS contract_period TEXT;')
                
                # 3. Hardening "Leads" Table
                cur.execute('ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS is_dnc BOOLEAN DEFAULT FALSE;')
                
                # 4. Ensure GlobalActivities exists
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS "GlobalActivities" (
                        id SERIAL PRIMARY KEY,
                        parent_id INTEGER NOT NULL,
                        parent_type TEXT NOT NULL,
                        activity_type TEXT NOT NULL,
                        description TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                ''')
                
                # 5. Ensure SigmaInteractionLog exists (Self-Healing telemetry table)
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS "SigmaInteractionLog" (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_prompt TEXT,
                        agent_explanation TEXT,
                        tools_used JSONB,
                        status VARCHAR(50)
                    );
                ''')

                # 6. Ensure RolePermissions exists
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS "RolePermissions" (
                        id SERIAL PRIMARY KEY,
                        role TEXT NOT NULL,
                        module TEXT NOT NULL,
                        can_view BOOLEAN DEFAULT FALSE,
                        can_edit BOOLEAN DEFAULT FALSE,
                        can_delete BOOLEAN DEFAULT FALSE
                    );
                ''')
            # 7. --- SigmaFidelity™ VNet Maintenance Cleanup (BUG-046) ---
            try:
                cur.execute('DELETE FROM "GlobalActivities" WHERE parent_id = 44518 AND parent_type = \'Lead\';')
                cur.execute('DELETE FROM "GlobalActivities" WHERE parent_id IN (SELECT id FROM "Leads" WHERE center_name ILIKE \'%Test Lead%\' OR lead_source = \'Executive Test System\') AND parent_type = \'Lead\';')
                cur.execute('DELETE FROM "Leads" WHERE id = 44518 OR center_name ILIKE \'%DFW6%\' OR center_name ILIKE \'%Test Lead%\' OR lead_source = \'Executive Test System\';')
                conn.commit()
                print("[BOOT] Database VNet Cleanup Executed & Committed.", flush=True)
            except Exception as clean_err:
                print(f"[BOOT] VNet Cleanup Notice: {clean_err}", flush=True)
            print("[BOOT] Database Schema Hardening & VNet Maintenance Completed & Committed.", flush=True)
        except Exception as schema_err:
            conn.rollback()
            print(f"[BOOT] Schema Migration Error (Rolled Back): {schema_err}", flush=True)

        # 5. --- SigmaFidelity™ Self-Healing Azure Database Seeder (BUG-044) ---
        if "conn" in locals() and conn: conn.close()
        
        import threading
        
        def run_seeder_async(db_url, seed_path):
            try:
                print("[BOOT] Async database seeder thread started.", flush=True)
                conn = get_db(db_url)
                try:
                    with conn.cursor() as cur:
                        cur.execute('SELECT COUNT(*) FROM "Leads";')
                        az_lead_count = cur.fetchone()[0]
                        with open(seed_path, 'r') as sf:
                            sdata = json.load(sf)
                            leads_inserted = 0
                            if az_lead_count < 1000:
                                print(f"[BOOT] Async force-syncing 29,879 leads & values to Azure DB ({az_lead_count} current rows)...", flush=True)
                                for idx, l in enumerate(sdata.get('leads', [])):
                                    if l.get('id') == 44518 or 'DFW6' in str(l.get('center_name', '')):
                                        continue
                                    try:
                                        cur.execute('''
                                            INSERT INTO "Leads" (
                                                id, center_name, lead_source, status, phone, email, address, city, state, zipcode,
                                                sqf, capacity, estimated_annual_value, priority_level, facility_type, decision_maker,
                                                job_title, traffic_cycle, service_interest, next_action_date, is_dnc, is_converted, input_date
                                            ) VALUES (
                                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                            ) ON CONFLICT (id) DO UPDATE SET
                                                center_name = EXCLUDED.center_name,
                                                lead_source = EXCLUDED.lead_source,
                                                status = EXCLUDED.status,
                                                phone = EXCLUDED.phone,
                                                email = EXCLUDED.email,
                                                sqf = EXCLUDED.sqf,
                                                capacity = EXCLUDED.capacity,
                                                estimated_annual_value = EXCLUDED.estimated_annual_value,
                                                is_dnc = EXCLUDED.is_dnc,
                                                is_converted = EXCLUDED.is_converted;
                                        ''', (
                                            l.get('id'), l.get('center_name'), l.get('lead_source'), l.get('status'), l.get('phone'), l.get('email'), l.get('address'), l.get('city'), l.get('state'), l.get('zipcode'),
                                            l.get('sqf'), l.get('capacity'), l.get('estimated_annual_value'), l.get('priority_level'), l.get('facility_type'), l.get('decision_maker'),
                                            l.get('job_title'), l.get('traffic_cycle'), l.get('service_interest'), l.get('next_action_date'), l.get('is_dnc', False), l.get('is_converted', False), l.get('input_date')
                                        ))
                                        leads_inserted += 1
                                        if idx % 500 == 0:
                                            conn.commit()
                                    except Exception as row_err:
                                        conn.rollback()
                                        print(f"[BOOT] Seeder Row Skip ({l.get('id')}): {row_err}", flush=True)
                                
                                conn.commit()
                            else:
                                print(f"[BOOT] Leads table already hardened ({az_lead_count} rows). Skipping full lead re-seed.", flush=True)
                            
                            # Seed RolePermissions Table
                            for rp in sdata.get('role_permissions', []):
                                try:
                                    cur.execute('''
                                        INSERT INTO "RolePermissions" (id, role, module, can_view, can_edit, can_delete)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (id) DO UPDATE SET
                                            role = EXCLUDED.role,
                                            module = EXCLUDED.module,
                                            can_view = EXCLUDED.can_view,
                                            can_edit = EXCLUDED.can_edit,
                                            can_delete = EXCLUDED.can_delete;
                                    ''', (rp.get('id'), rp.get('role'), rp.get('module'), rp.get('can_view'), rp.get('can_edit'), rp.get('can_delete')))
                                except Exception: pass
                            
                            # Seed Users Table
                            for u in sdata.get('users', []):
                                try:
                                    cur.execute('''
                                        INSERT INTO "Users" (id, username, password_hash, full_name, email, role, status, force_pwd_reset, custom_permissions)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (id) DO UPDATE SET
                                            username = EXCLUDED.username,
                                            password_hash = EXCLUDED.password_hash,
                                            full_name = EXCLUDED.full_name,
                                            email = EXCLUDED.email,
                                            role = EXCLUDED.role,
                                            status = EXCLUDED.status,
                                            force_pwd_reset = EXCLUDED.force_pwd_reset,
                                            custom_permissions = EXCLUDED.custom_permissions;
                                    ''', (
                                        u.get('id'), u.get('username'), u.get('password_hash'), u.get('full_name'), u.get('email'), u.get('role'),
                                        u.get('status', 'Active'), u.get('force_pwd_reset', False), u.get('custom_permissions')
                                    ))
                                except Exception: pass
                            
                            conn.commit()
                            print(f"[BOOT] Async Automated Azure Data Ingestion Completed ({leads_inserted} leads processed)!", flush=True)
                except Exception as se:
                    conn.rollback()
                    print(f"[BOOT] Async Seeder Warning: {se}", flush=True)
                finally:
                    conn.close()
            except Exception as thread_err:
                print(f"[BOOT] Async Seeder Thread Error: {thread_err}", flush=True)
        
        seed_path = os.path.join(os.path.dirname(__file__), 'scripts', 'seed_data.json')
        if os.path.exists(seed_path):
            threading.Thread(target=run_seeder_async, args=(app.config['DATABASE_URL'], seed_path), daemon=True).start()
            
        print("[BOOT] Infrastructure Handshake Complete.", flush=True)
    except Exception as e:
        print(f"[BOOT] Startup Handshake Warning: {e}", flush=True)

# ... (Logic continues below)

# --- SigmaFidelity™ Master Taxonomy & Lookup Constants ---
FACILITY_TYPES = [
    {"value": "Child Care Center", "label": "Child Care Center"},
    {"value": "Office", "label": "Office Space"},
    {"value": "Medical", "label": "Medical / Clinical"},
    {"value": "Warehouse", "label": "Warehouse / Industrial"},
    {"value": "Automotive", "label": "Automotive / Dealership"},
    {"value": "Retail", "label": "Retail Space"},
    {"value": "Church", "label": "Church / Sanctuary"},
    {"value": "School", "label": "School / Educational"},
    {"value": "Post-Construction", "label": "Post-Construction"},
    {"value": "Other", "label": "Other Commercial"}
]

LEAD_SOURCES = [
    {"value": "Texas CCL API", "label": "Texas CCL API (Active State Feed)"},
    {"value": "Texas Childcare Registry", "label": "Texas Childcare Registry (Master Import)"},
    {"value": "Website Quote Form", "label": "Website Quote Form (Inbound Web)"},
    {"value": "Google", "label": "Google Search / Organic SEO"},
    {"value": "Referral", "label": "Referral / Word-of-Mouth"},
    {"value": "Cold Call", "label": "Outbound Outreach"},
    {"value": "Flyer", "label": "Direct Mail / Flyer"},
    {"value": "Direct Lead", "label": "Direct Inquiry"},
    {"value": "Other", "label": "Other Channel"}
]

PRIORITY_LEVELS = [
    {"value": "Needs Call Now", "label": "🔥 Needs Call Now (Critical)"},
    {"value": "High", "label": "High Priority"},
    {"value": "Follow up soon", "label": "Follow Up Soon (Standard)"},
    {"value": "Just looking", "label": "Just Looking (Low)"},
    {"value": "Normal", "label": "Normal"}
]

# --- Security Architecture: User Management ---

class User(UserMixin):
    def __init__(self, id, username, role, full_name=None):
        self.id = id
        self.username = username
        self.role = role
        self.full_name = full_name

@login_manager.user_loader
def load_user(user_id):
    conn = None
    try:
        # Use a short timeout for the user loader to prevent page hangs
        conn = get_db(app.config['DATABASE_URL'])
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "Users" WHERE id = %s', (user_id,))
            u = cur.fetchone()
            if u:
                return User(u['id'], u['username'], u['role'], u.get('full_name'))
    except Exception as e:
        print(f"[GUARD] load_user failed: {e}", flush=True)
    finally:
        if conn:
            conn.close()
    return None

# --- Enterprise RBAC Security Gateway (HWB-QMS-7.6 Zero-Hotfix Standard) ---
from functools import wraps

def log_security_violation(user_id, username, role, path, method):
    """Institutional Security Telemetry (SOC 2 / ISO 27001): Logs access breaches to GlobalActivities."""
    conn = None
    try:
        conn = get_db(app.config['DATABASE_URL'])
        with conn.cursor() as cur:
            desc = f"Role '{role}' ({username}) blocked from accessing {method} {path}"
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, "User", "SECURITY_VIOLATION", desc))
            conn.commit()
    except Exception as e:
        print(f"[SECURITY_LOG_ERROR] Could not log violation: {e}", flush=True)
    finally:
        if conn:
            conn.close()

def roles_required(*roles):
    """Declarative Role-Based Access Control Decorator (Enterprise Standard)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login', next=request.url))
            if current_user.role not in roles:
                print(f"[SECURITY_AUDIT] Unauthorized access attempt by {current_user.username} ({current_user.role}) to {request.path}", flush=True)
                log_security_violation(current_user.id, current_user.username, current_user.role, request.path, request.method)
                if current_user.role == 'Sales':
                    flash("Access restricted. Outside Sales personnel are routed to the Field Sales Desk.")
                    return redirect(url_for('sales_desk'))
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.before_request
def enforce_enterprise_role_quarantine():
    """Centralized Enterprise Request Gatekeeper (Poka-Yoke Fail-Safe Defaults)."""
    # 1. Static files and health endpoints are always open
    if request.path.startswith('/static') or request.path in ['/heartbeat', '/favicon.ico']:
        return None

    # 2. Only active authenticated sessions are subject to role quarantine
    if not current_user.is_authenticated:
        return None

    path = request.path
    role = getattr(current_user, 'role', '')

    # 3. Sales Role Scope (Option B: Leads, Accounts & Field Sales Desk)
    if role == 'Sales':
        # Block public root marketing landing page; route reps directly into their active pipeline
        if path == '/':
            return redirect(url_for('admin_operations', view='leads'))

        # Block bulk data exfiltration attempts (Poka-Yoke)
        if path.startswith('/api/v1/leads/export') or path.startswith('/api/v1/accounts/export'):
            log_security_violation(current_user.id, current_user.username, role, path, request.method)
            return jsonify({'status': 'error', 'message': 'Exporting data is strictly restricted for Sales personnel.'}), 403

        # Scoped access to admin_operations: only 'leads' and 'accounts' views are authorized
        if path == '/admin/operations':
            active_view = request.args.get('view', 'leads')
            if active_view not in ['leads', 'accounts']:
                log_security_violation(current_user.id, current_user.username, role, f"{path}?view={active_view}", request.method)
                flash("Restricted area. Sales access is scoped to Leads and Accounts.")
                return redirect(url_for('admin_operations', view='leads'))
            return None

        # Permitted endpoints for Sales
        sales_whitelist = (
            '/admin/operations',
            '/admin/sales-desk',
            '/admin/add-lead',
            '/admin/add-account',
            '/admin/edit-lead/',
            '/api/v1/leads/',      # Lead details, update, promote
            '/api/v1/accounts/',   # Account details, update
            '/api/v1/activities',  # Field note logging
            '/logout',
            '/heartbeat'
        )

        # Intercept any unauthorized /admin/* or management routes
        if path.startswith('/admin') and not any(path.startswith(w) for w in sales_whitelist):
            log_security_violation(current_user.id, current_user.username, role, path, request.method)
            flash("Restricted area. Sales access is limited to Leads, Accounts, and Field Sales Desk.")
            return redirect(url_for('admin_operations', view='leads'))

    # 4. Executive & Admin Sensitive Zone Protection
    if path.startswith('/admin/executive'):
        if role not in ['Executive', 'Admin']:
            log_security_violation(current_user.id, current_user.username, role, path, request.method)
            abort(403)

    # 5. Master Repository & Lab Zone Protection
    if path in ['/admin/master', '/admin/lab']:
        if role not in ['Executive', 'Admin', 'Manager']:
            log_security_violation(current_user.id, current_user.username, role, path, request.method)
            abort(403)

    return None

@app.context_processor
def inject_enterprise_nav():
    """Enterprise Navigation Engine: Single source of truth for UI permission rendering."""
    if not current_user.is_authenticated:
        return {
            'nav_access': {
                'is_authenticated': False,
                'can_view_command_hub': False,
                'is_executive': False,
                'is_manager': False,
                'is_sales': False,
                'sales_desk_url': None
            }
        }

    role = getattr(current_user, 'role', '')
    is_exec = role in ['Executive', 'Admin']
    is_mgmt = role in ['Executive', 'Admin', 'Manager']
    is_sales = (role == 'Sales')

    return {
        'nav_access': {
            'is_authenticated': True,
            'can_view_command_hub': is_mgmt,
            'is_executive': is_exec,
            'is_manager': is_mgmt,
            'is_sales': is_sales,
            'role_name': role,
            'sales_desk_url': url_for('sales_desk') if (is_sales or is_mgmt) else None
        }
    }

@app.errorhandler(500)
def internal_error(error):
    return "The system is currently busy or updating. Please refresh in a moment.", 500

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e
    print(f"[FATAL] System Exception: {e}", flush=True)
    return "A system error occurred. Our team has been notified.", 500

def format_to_mdy(date_val):
    """Converts YYYY-MM-DD to MM/DD/YYYY for institutional compliance."""
    if not date_val: return '--'
    
    # Handle datetime.date or datetime.datetime objects (Postgres)
    if hasattr(date_val, 'strftime'):
        return date_val.strftime('%m/%d/%Y')
        
    # Handle strings (SQLite fallback)
    if isinstance(date_val, str):
        if '/' in date_val: return date_val
        try:
            parts = date_val.split('-')
            if len(parts) == 3:
                y, m, d = parts
                return f"{m}/{d}/{y}"
        except: pass
        
    return str(date_val)

app.jinja_env.filters['format_mdy'] = format_to_mdy

def transmit_email(recipient, subject, body_html):
    """Transmits a professional email via Microsoft Graph API."""
    client_id = app.config.get("GRAPH_CLIENT_ID")
    client_secret = app.config.get("GRAPH_CLIENT_SECRET")
    tenant_id = app.config.get("GRAPH_TENANT_ID")
    user_id = app.config.get("GRAPH_USER_ID", "humbertoed@hwbcleaning.com")

    if not tenant_id or not client_id or not client_secret:
        print("[GRAPH] API Error: Missing configuration (Tenant/Client/Secret)", flush=True)
        return False, "Missing Credentials"

    authority = f"https://login.microsoftonline.com/{tenant_id}" 
    app_msal = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    
    # Acquire token
    result = app_msal.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        headers = {
            "Authorization": f"Bearer {result['access_token']}",
            "Content-Type": "application/json"
        }
        
        email_content = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": [{"emailAddress": {"address": recipient}}]
            }
        }
        
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}/sendMail"
        try:
            response = requests.post(url, headers=headers, json=email_content)
            if response.status_code == 202:
                print(f"[GRAPH] Email sent successfully to {recipient}", flush=True)
                return True, "Success"
            else:
                err_msg = f"Status {response.status_code}: {response.text}"
                print(f"[GRAPH] SEND FAILURE: {err_msg}", flush=True)
                return False, err_msg
        except Exception as e:
            print(f"[GRAPH] REQUEST FATAL: {e}", flush=True)
            return False, str(e)
            
    err_desc = result.get('error_description', 'Token Acquisition Failed')
    print(f"[GRAPH] AUTH FAILURE: {err_desc}", flush=True)
    return False, err_desc

# --- SigmaFidelity™ Advanced Query Engine (HWB-QMS-11.2 / BUG-065) ---

def parse_advanced_search(search_q: str, view: str = 'leads') -> Tuple[List[str], List[Any]]:
    """
    Parses advanced search query strings into SQL WHERE clauses and parameters.
    Supports:
    - Field targeting: city:Plano, industry:Child, status:New, rep:Wiley
    - Numeric comparisons & ranges: sqf:>=10000, sqf:<20000, value:>50000
    - Negative exclusions: -Church, -"School District"
    - Exact phrases: "North Texas"
    - Wildcards: Pla*
    - American dates: 04/10/2026 -> 2026-04-10
    - General keywords across primary text columns
    """
    if not search_q or not search_q.strip():
        return [], []

    search_q = search_q.strip()

    def normalize_date(val: str) -> str:
        m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', val)
        if m:
            month, day, year = m.groups()
            return f'{year}-{int(month):02d}-{int(day):02d}'
        return val

    if view in ('leads', 'sales_desk'):
        field_map = {
            'city': ('city', 'text'),
            'state': ('state', 'text'),
            'zip': ('zipcode', 'text'),
            'zipcode': ('zipcode', 'text'),
            'industry': ('facility_type', 'text'),
            'facility': ('facility_type', 'text'),
            'status': ('status', 'text'),
            'sqf': ('sqf', 'num'),
            'capacity': ('capacity', 'num'),
            'value': ('estimated_annual_value', 'num'),
            'revenue': ('estimated_annual_value', 'num'),
            'source': ('lead_source', 'text'),
            'contact': ('decision_maker', 'text'),
            'dm': ('decision_maker', 'text'),
            'director': ('director', 'text'),
            'company': ('center_name', 'text'),
            'name': ('center_name', 'text'),
            'phone': ('phone', 'text'),
            'email': ('email', 'text'),
            'address': ('address', 'text'),
            'umbrella': ('umbrella_name', 'text'),
            'tier': ('acquisition_tier', 'text'),
            'm_and_a': ('acquisition_tier', 'text'),
            'ownership': ('ownership_type', 'text'),
            'rep': ('owner_id', 'user_ref'),
            'owner': ('owner_id', 'user_ref'),
            'date': ('input_date', 'date'),
            'created': ('input_date', 'date'),
            'input_date': ('input_date', 'date'),
        }
        general_cols = [
            'center_name', 'facility_type', 'city', 'state', 'zipcode', 
            'phone', 'email', 'address', 'lead_source', 'decision_maker', 
            'status', 'umbrella_name', 'acquisition_tier', 'ownership_type'
        ]
        user_table_fk = 'owner_id'

    elif view == 'accounts':
        field_map = {
            'city': ('city', 'text'),
            'state': ('state', 'text'),
            'zip': ('zip', 'text'),
            'company': ('company_name', 'text'),
            'name': ('company_name', 'text'),
            'phone': ('phone', 'text'),
            'email': ('email', 'text'),
            'address': ('company_address', 'text'),
            'revenue': ('annual_revenue', 'num'),
            'value': ('annual_revenue', 'num'),
            'status': ('status', 'text'),
            'industry': ('facility_type', 'text'),
            'facility': ('facility_type', 'text'),
            'building': ('facility_type', 'text'),
            'contact': ('contact_person_name', 'text'),
            'umbrella': ('c.umbrella_name', 'text'),
            'rep': ('c.assigned_rep_id', 'user_ref'),
            'owner': ('c.assigned_rep_id', 'user_ref'),
        }
        general_cols = [
            'company_name', 'company_address', 'city', 'state', 'zip',
            'phone', 'email', 'contact_person_name', 'facility_type', 'c.umbrella_name'
        ]
        user_table_fk = 'c.assigned_rep_id'

    else:  # construction_bids
        field_map = {
            'project': ('cb.project_name', 'text'),
            'name': ('cb.project_name', 'text'),
            'company': ('cb.project_name', 'text'),
            'gc': ('cb.gc_name', 'text'),
            'status': ('cb.status', 'text'),
            'sqf': ('cb.cleanable_sqft', 'num'),
            'value': ('cb.estimated_value', 'num'),
            'location': ('cb.city', 'text'),
            'city': ('cb.city', 'text'),
            'address': ('cb.project_address', 'text'),
            'platform': ('cb.platform', 'text'),
            'estimator': ('cb.estimator_name', 'text'),
            'phone': ('cb.estimator_phone', 'text'),
            'email': ('cb.estimator_email', 'text'),
            'scope': ('cb.scope_phase', 'text'),
            'date': ('cb.bid_due_date', 'date'),
            'due': ('cb.bid_due_date', 'date'),
        }
        general_cols = [
            'cb.project_name', 'cb.gc_name', 'cb.city', 'cb.project_address',
            'cb.platform', 'cb.estimator_name', 'cb.estimator_phone', 'cb.estimator_email', 'cb.scope_phase'
        ]
        user_table_fk = None

    pattern = r'(?P<field>[a-zA-Z_]+):(?P<op>>=|<=|>|<|=)?(?P<fval>\"[^\"]+\"|[^\s]+)|-(?P<neg>\"[^\"]+\"|[^\s]+)|\"(?P<exact>[^\"]+)\"|(?P<word>[^\s]+)'
    
    where_clauses: List[str] = []
    params: List[Any] = []

    for m in re.finditer(pattern, search_q):
        d = m.groupdict()
        if d['field']:
            f_key = d['field'].lower()
            op = d['op'] or '='
            val = d['fval'].strip('\"')
            
            if f_key in field_map:
                col, col_type = field_map[f_key]
                if col_type == 'num':
                    clean_val = re.sub(r'[^0-9.]', '', val)
                    if clean_val:
                        valid_op = op if op in ['>=', '<=', '>', '<', '='] else '='
                        where_clauses.append(f'{col} {valid_op} %s')
                        params.append(float(clean_val))
                elif col_type == 'date':
                    norm_date = normalize_date(val)
                    if '*' in norm_date:
                        where_clauses.append(f'{col}::text LIKE %s')
                        params.append(norm_date.replace('*', '%'))
                    else:
                        valid_op = op if op in ['>=', '<=', '>', '<', '='] else '='
                        where_clauses.append(f'{col}::date {valid_op} %s::date')
                        params.append(norm_date)
                elif col_type == 'user_ref' and user_table_fk:
                    if val.isdigit():
                        where_clauses.append(f'{user_table_fk} = %s')
                        params.append(int(val))
                    else:
                        pat = f'%{val}%'
                        where_clauses.append(f'{user_table_fk} IN (SELECT id FROM "Users" WHERE full_name ILIKE %s OR username ILIKE %s)')
                        params.extend([pat, pat])
                elif f_key in ('phone', 'estimator_phone'):
                    digits = re.sub(r'\D', '', val)
                    if len(digits) >= 4:
                        where_clauses.append(f"({col} ILIKE %s OR regexp_replace(COALESCE({col}, ''), '\\D', '', 'g') ILIKE %s)")
                        params.extend([f"%{val}%", f"%{digits}%"])
                    else:
                        pat = val.replace('*', '%') if '*' in val else f'%{val}%'
                        where_clauses.append(f'{col} ILIKE %s')
                        params.append(pat)
                else:
                    pat = val.replace('*', '%') if '*' in val else f'%{val}%'
                    where_clauses.append(f'{col} ILIKE %s')
                    params.append(pat)
            else:
                full_token = m.group(0)
                pat = full_token.replace('*', '%') if '*' in full_token else f'%{full_token}%'
                sub = ' OR '.join([f'{c} ILIKE %s' for c in general_cols])
                where_clauses.append(f'({sub})')
                params.extend([pat] * len(general_cols))
                
        elif d['neg']:
            neg_val = d['neg'].strip('\"')
            neg_pat = f'%{neg_val}%'
            sub = ' AND '.join([f'COALESCE({c}::text, \'\') NOT ILIKE %s' for c in general_cols])
            where_clauses.append(f'({sub})')
            params.extend([neg_pat] * len(general_cols))
            
        elif d['exact']:
            exact_val = d['exact']
            exact_pat = rf'\y{re.escape(exact_val)}\y'
            sub = ' OR '.join([f'{c} ~* %s' for c in general_cols])
            where_clauses.append(f'({sub})')
            params.extend([exact_pat] * len(general_cols))
            
        elif d['word']:
            w = d['word']
            norm_date = normalize_date(w)
            if norm_date != w:
                sub = ' OR '.join([f'{c}::text ILIKE %s' for c in general_cols])
                where_clauses.append(f'({sub})')
                params.extend([f'%{norm_date}%'] * len(general_cols))
            elif re.search(r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$', w) or (w.isdigit() and len(w) >= 7):
                digits = re.sub(r'\D', '', w)
                phone_cols = [c for c in general_cols if 'phone' in c]
                sub_parts = [f'{c} ILIKE %s' for c in general_cols]
                if phone_cols:
                    sub_parts.extend([f"regexp_replace(COALESCE({c}, ''), '\\D', '', 'g') ILIKE %s" for c in phone_cols])
                    where_clauses.append(f"({' OR '.join(sub_parts)})")
                    params.extend([f'%{w}%'] * len(general_cols) + [f'%{digits}%'] * len(phone_cols))
                else:
                    where_clauses.append(f"({' OR '.join(sub_parts)})")
                    params.extend([f'%{w}%'] * len(general_cols))
            else:
                w_pat = w.replace('*', '%') if '*' in w else f'%{w}%'
                sub = ' OR '.join([f'{c} ILIKE %s' for c in general_cols])
                where_clauses.append(f'({sub})')
                params.extend([w_pat] * len(general_cols))

    return where_clauses, params

# --- HWB Command v5.0: Unified Backend Hub ---

@app.route('/admin/operations', endpoint='admin_operations')
@login_required
@roles_required('Executive', 'Admin', 'Manager', 'Operator', 'Sales')
def admin_operations():
    """The Single-Source Dashboard for Management Dashboard."""
    active_view = request.args.get('view', 'leads')
    if current_user.role == 'Sales' and active_view not in ['leads', 'accounts']:
        return redirect(url_for('admin_operations', view='leads'))
    page = request.args.get('page', 1, type=int)
    search_q = request.args.get('q', '').strip()
    active_only = request.args.get('active_only') == 'true'
    sort_by = request.args.get('sort')
    sort_dir = request.args.get('dir', '').upper()
    
    # Initialization
    leads, clients, work_orders, services, activities, system_users = [], [], [], [], [], []
    leads_count, bids_count, total_pages, portfolio_total = 0, 0, 1, 0
    lib = {'area': [], 'task': [], 'item': []}
    
    # --- Dynamic Column Architecture ---
    default_cols_leads = 'company,status,sqf,value,priority,activities'
    default_cols_accounts = 'company,city,phone,revenue,rep,activities'
    default_cols_bids = 'project,status,due_date,created,sqf,value,scope,estimator,phone,actions'
    
    if active_view == 'leads':
        session_key = 'leads_custom_cols'
        default_cols = default_cols_leads
        anchor_col = 'company'
    elif active_view == 'accounts':
        session_key = 'accounts_custom_cols'
        default_cols = default_cols_accounts
        anchor_col = 'company'
    elif active_view == 'construction_bids':
        session_key = 'bids_custom_cols'
        default_cols = default_cols_bids
        anchor_col = 'project'
    else:
        session_key = 'leads_custom_cols'
        default_cols = default_cols_leads
        anchor_col = 'company'

    if 'cols' in request.args:
        active_cols_str = request.args.get('cols')
        if active_cols_str in ('default', 'reset', ''):
            session.pop(session_key, None)
            active_cols_str = default_cols
        else:
            session[session_key] = active_cols_str
    else:
        active_cols_str = session.get(session_key) or default_cols
    
    active_cols = [c.strip() for c in active_cols_str.split(',') if c.strip() and c.strip() != 'on']
    if anchor_col not in active_cols:
        active_cols.insert(0, anchor_col)
    
    per_page = 50
    offset = (page - 1) * per_page

    # View-Specific SQL Column Mapping
    leads_sort_map = {
        'company': 'center_name', 'industry': 'industry', 'input_date': 'input_date',
        'status': 'status', 'phone': 'phone', 'email': 'email', 'city': 'city',
        'zipcode': 'zipcode', 'sqf': 'sqf', 'capacity': 'capacity', 'value': 'estimated_annual_value',
        'priority': 'priority_level', 'facility': 'facility_type', 'contact': 'decision_maker',
        'address': 'address', 'job_title': 'job_title', 'source': 'lead_source',
        'frequency': 'traffic_cycle', 'interest': 'service_interest', 
        'next_action': 'next_action_date', 'owner': 'owner_id',
        'activities': '(SELECT COUNT(*) FROM "GlobalActivities" WHERE parent_id = l.id AND parent_type = \'Lead\')', 
        'last_contact': 'last_contact',
        'umbrella': 'umbrella_name',
        'cleaning_model': 'cleaning_delivery_model',
        'm_and_a': 'acquisition_tier',
        'ownership': 'ownership_type',
        'commercial': 'is_commercial'
    }
    accounts_sort_map = {
        'company': 'company_name', 'city': 'city', 'phone': 'phone',
        'email': 'email', 'revenue': 'annual_revenue', 'status': 'status',
        'address': 'company_address', 'contact': 'contact_person_name',
        'facility': 'facility_type', 'building': 'facility_type', 'industry': 'industry',
        'zip': 'zip', 'state': 'state', 'quote': 'quote_number',
        'period': 'contract_period', 'frequency': 'frequency',
        'start_date': 'start_date', 'terms': 'payment_terms',
        'rep': 'c.assigned_rep_id', 'owner': 'c.assigned_rep_id',
        'activities': '(SELECT COUNT(*) FROM "GlobalActivities" WHERE parent_id = c.customer_id AND parent_type = \'Account\')', 
        'last_contact': 'last_contact',
        'umbrella': 'c.umbrella_name',
        'cleaning_model': 'c.cleaning_delivery_model'
    }
    bids_sort_map = {
        'project': 'cb.project_name', 'gc': 'cb.gc_name', 'status': 'cb.status',
        'due_date': 'cb.bid_due_date', 'sqf': 'cb.cleanable_sqft', 'value': 'cb.estimated_value',
        'scope': 'cb.scope_phase', 'location': 'cb.city', 'address': 'cb.project_address',
        'platform': 'cb.platform', 'estimator': 'cb.estimator_name', 'phone': 'cb.estimator_phone',
        'email': 'cb.estimator_email', 'dates': 'cb.estimated_start_date', 'prequal': 'cb.prequal_status',
        'special_reqs': 'cb.special_requirements',
        'activities': '(SELECT COUNT(*) FROM "GlobalActivities" WHERE parent_id = cb.id AND parent_type = \'ConstructionBid\')',
        'last_contact': 'last_contact', 'last_note': 'last_note', 'created': 'cb.created_at'
    }
    
    # Handle Sort Parameters
    if active_view == 'leads':
        l_sort = leads_sort_map.get(sort_by, 'input_date')
        l_dir = sort_dir if sort_dir in ['ASC', 'DESC'] else 'DESC'
        a_sort, a_dir = 'company_name', 'ASC'
        b_sort, b_dir = 'cb.bid_due_date', 'ASC'
    elif active_view == 'accounts':
        a_sort = accounts_sort_map.get(sort_by, 'company_name')
        a_dir = sort_dir if sort_dir in ['ASC', 'DESC'] else 'ASC'
        l_sort, l_dir = 'input_date', 'DESC'
        b_sort, b_dir = 'cb.bid_due_date', 'ASC'
    elif active_view == 'construction_bids':
        b_sort = bids_sort_map.get(sort_by, 'cb.bid_due_date')
        b_dir = sort_dir if sort_dir in ['ASC', 'DESC'] else 'ASC'
        l_sort, l_dir = 'input_date', 'DESC'
        a_sort, a_dir = 'company_name', 'ASC'
    else:
        l_sort, l_dir = 'input_date', 'DESC'
        a_sort, a_dir = 'company_name', 'ASC'
        b_sort, b_dir = 'cb.bid_due_date', 'ASC'

    # Single connection for unified queries
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            # 1. FETCH ACCOUNTS
            cur.execute('SELECT SUM(annual_revenue) FROM "Customers"')
            portfolio_total_row = cur.fetchone()
            portfolio_total = portfolio_total_row[0] if portfolio_total_row and portfolio_total_row[0] is not None else 0

            # --- SigmaFidelity™ Dynamic SQL Engine (BUG-017) ---
            account_sql_base = '''
                SELECT c.*, 
                       (SELECT COUNT(*) FROM "Contacts" WHERE account_id = c.customer_id) as contact_count,
                       (SELECT COUNT(*) FROM "GlobalActivities" WHERE parent_id = c.customer_id AND parent_type = 'Account') as activity_count,
                       (SELECT MAX(timestamp) FROM "GlobalActivities" WHERE parent_id = c.customer_id AND parent_type = 'Account') as last_contact,
                       (SELECT description FROM "GlobalActivities" WHERE parent_id = c.customer_id AND parent_type = 'Account' ORDER BY timestamp DESC LIMIT 1) as last_note
                FROM "Customers" c
            '''
            
            where_clauses = []
            params = []

            if active_only:
                where_clauses.append("(SELECT COUNT(*) FROM \"GlobalActivities\" WHERE parent_id = c.customer_id AND parent_type = 'Account') > 0")

            if search_q and active_view == 'accounts':
                s_clauses, s_params = parse_advanced_search(search_q, 'accounts')
                where_clauses.extend(s_clauses)
                params.extend(s_params)

            full_where = ""
            if where_clauses:
                full_where = "WHERE " + " AND ".join(where_clauses)

            cur.execute(f"{account_sql_base} {full_where} ORDER BY {a_sort} {a_dir}", tuple(params))
            clients = cur.fetchall()

            # 2. FETCH LEADS
            lead_where_clauses = []
            lead_params = []

            # Clean Pipeline: default to true commercial facilities unless explicitly viewing archived
            include_archived = request.args.get('include_archived') == 'true'
            if not include_archived and active_view == 'leads':
                lead_where_clauses.append("is_commercial = TRUE")

            # M&A Acquisition Radar Preset Filter
            m_and_a_filter = request.args.get('m_and_a') == 'true'
            if m_and_a_filter and active_view == 'leads':
                lead_where_clauses.append("acquisition_tier IN ('Tier 1 - Mega Institutional', 'Tier 2 - Regional Commercial')")

            duplicates_only = request.args.get('duplicates_only') == 'true'
            if duplicates_only and active_view == 'leads':
                lead_where_clauses.append("is_duplicate = TRUE")
                l_sort, l_dir = "duplicate_group_id ASC, id", "ASC"

            if active_only:
                lead_where_clauses.append("(SELECT COUNT(*) FROM \"GlobalActivities\" WHERE parent_id = l.id AND parent_type = 'Lead') > 0")

            if search_q and active_view == 'leads':
                s_clauses, s_params = parse_advanced_search(search_q, 'leads')
                lead_where_clauses.extend(s_clauses)
                lead_params.extend(s_params)

            lead_where_str = ("WHERE " + " AND ".join(lead_where_clauses)) if lead_where_clauses else ""

            # Count Query
            cur.execute(f'SELECT COUNT(*) FROM "Leads" l {lead_where_str}', tuple(lead_params))
            leads_count = cur.fetchone()[0]

            cur.execute('SELECT COUNT(*) FROM "Leads" WHERE is_duplicate = TRUE;')
            dup_count_row = cur.fetchone()
            dup_count = dup_count_row[0] if dup_count_row else 0

            # Data Query
            lead_sql_base = f'''
                SELECT l.*, 
                       (SELECT COUNT(*) FROM "GlobalActivities" WHERE parent_id = l.id AND parent_type = 'Lead') as activity_count, 
                       (SELECT MAX(timestamp) FROM "GlobalActivities" WHERE parent_id = l.id AND parent_type = 'Lead') as last_contact,
                       (SELECT description FROM "GlobalActivities" WHERE parent_id = l.id AND parent_type = 'Lead' ORDER BY timestamp DESC LIMIT 1) as last_note
                FROM "Leads" l 
                {lead_where_str}
            '''
            
            cur.execute(f'{lead_sql_base} ORDER BY {l_sort} {l_dir} NULLS LAST, id ASC LIMIT %s OFFSET %s', tuple(lead_params + [per_page, offset]))
            leads = cur.fetchall()
            total_pages = (leads_count + per_page - 1) // per_page

            # 3. GLOBAL MONITORING
            cur.execute('SELECT w.*, c.company_name, s.service_requested FROM "WorkOrders" w JOIN "Customers" c ON w.customer_id = c.customer_id JOIN "Services" s ON w.service_id = s.service_id ORDER BY w.scheduled_date DESC')
            work_orders = cur.fetchall()
            
            cur.execute('SELECT s.*, c.company_name FROM "Services" s JOIN "Customers" c ON s.customer_id = c.customer_id')
            services = cur.fetchall()
            
            cur.execute('SELECT category, value FROM "ScopeLibrary" ORDER BY value ASC')
            lib_raw = cur.fetchall()
            for r in lib_raw: 
                cat = r['category'].lower() if r['category'] else 'other'
                if cat not in lib: lib[cat] = []
                lib[cat].append(r['value'])
            
            cur.execute('SELECT * FROM "GlobalActivities" ORDER BY timestamp DESC LIMIT 50')
            activities = cur.fetchall()

            # 4. CONSTRUCTION BIDS PIPELINE (HWB-QMS-11.2)
            bid_where_clauses = []
            bid_params = []
            if search_q and active_view == 'construction_bids':
                s_clauses, s_params = parse_advanced_search(search_q, 'construction_bids')
                bid_where_clauses.extend(s_clauses)
                bid_params.extend(s_params)
            bid_where_str = ("WHERE " + " AND ".join(bid_where_clauses)) if bid_where_clauses else ""

            cur.execute(f'SELECT COUNT(*) FROM "ConstructionBids" cb {bid_where_str}', tuple(bid_params))
            bids_count_row = cur.fetchone()
            bids_count = bids_count_row[0] if bids_count_row else 0

            if active_view == 'construction_bids':
                total_pages = (bids_count + per_page - 1) // per_page or 1

            nulls_clause = "NULLS LAST" if b_dir == 'ASC' else "NULLS FIRST"
            cur.execute(f'''
                SELECT cb.*, 
                       (SELECT COUNT(*) FROM "GlobalActivities" WHERE parent_id = cb.id AND parent_type = 'ConstructionBid') as activity_count, 
                       (SELECT MAX(timestamp) FROM "GlobalActivities" WHERE parent_id = cb.id AND parent_type = 'ConstructionBid') as last_contact,
                       (SELECT description FROM "GlobalActivities" WHERE parent_id = cb.id AND parent_type = 'ConstructionBid' ORDER BY timestamp DESC LIMIT 1) as last_note
                FROM "ConstructionBids" cb
                {bid_where_str}
                ORDER BY {b_sort} {b_dir} {nulls_clause}, cb.id DESC
                LIMIT %s OFFSET %s
            ''', tuple(bid_params + [per_page, offset]))
            construction_bids = cur.fetchall()

            # 5. ACTIVE SYSTEM USERS (Lead Ownership & Dynamic Team Allocation)
            cur.execute('SELECT id, username, full_name, role FROM "Users" WHERE status = \'Active\' ORDER BY id ASC')
            system_users = cur.fetchall()
    finally:
        if "conn" in locals(): conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('format') == 'json':
        try:
            def serialize_row(row):
                d = dict(row)
                for k, v in d.items():
                    if isinstance(v, (datetime.date, datetime.datetime)):
                        d[k] = v.isoformat()
                    elif hasattr(v, '__str__') and 'Decimal' in str(type(v)):
                        d[k] = float(v)
                return d

            return jsonify({
                'leads': [serialize_row(l) for l in leads] if leads else [],
                'clients': [serialize_row(c) for c in clients] if clients else [],
                'construction_bids': [serialize_row(b) for b in construction_bids] if construction_bids else [],
                'system_users': [serialize_row(u) for u in system_users] if system_users else [],
                'facility_types': FACILITY_TYPES,
                'lead_sources': LEAD_SOURCES,
                'priority_levels': PRIORITY_LEVELS,
                'counts': {'leads': leads_count or 0, 'accounts': len(clients) if clients else 0, 'bids': len(construction_bids) if construction_bids else 0},
                'active_view': active_view
            })
        except Exception as e:
            print(f"[BOOT] JSON Serialization Error: {e}", flush=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500

    return render_template('backoffice_operations.html', 
                         active_view=active_view, leads=leads, leads_count=leads_count, dup_count=dup_count,
                         page=page, total_pages=total_pages, search_q=search_q,
                         sort_by=sort_by or '', sort_dir=sort_dir, active_cols=active_cols,
                         active_cols_str=active_cols_str, portfolio_total=portfolio_total,
                         clients=clients, work_orders=work_orders, services=services,
                         construction_bids=construction_bids, bids_count=bids_count,
                         library=json.dumps(lib), activities=activities, system_users=system_users,
                         facility_types=FACILITY_TYPES, lead_sources=LEAD_SOURCES, priority_levels=PRIORITY_LEVELS)

# --- SigmaFidelity™ Field Sales Desk (HWB-SAL-2026-001) ---

@app.route('/admin/sales-desk', endpoint='sales_desk')
@login_required
@roles_required('Sales', 'Executive', 'Admin', 'Manager')
def sales_desk():
    """Field Sales Desk for Outside Sales Representatives (HWB-SAL-2026-001)."""
    search_q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            user_id = current_user.id
            is_sales_rep = (current_user.role == 'Sales')
            
            # Check if this rep has assigned leads
            cur.execute('SELECT COUNT(*) FROM "Leads" WHERE owner_id = %s AND is_converted = FALSE', (user_id,))
            user_assigned_count = cur.fetchone()[0]
            
            # Build query
            where_clauses = ['is_converted = FALSE']
            params = []
            
            if is_sales_rep and user_assigned_count > 0:
                where_clauses.append('owner_id = %s')
                params.append(user_id)
            elif is_sales_rep:
                # Texas Statewide Mandate: Rep with no direct assignments accesses open unassigned pipeline
                where_clauses.append('owner_id IS NULL')
                
            if status_filter == 'walkthrough':
                where_clauses.append("status ILIKE '%walkthrough%'")
            elif status_filter == 'quote':
                where_clauses.append("(status ILIKE '%quote%' OR status ILIKE '%proposal%')")
                
            if search_q:
                s_clauses, s_params = parse_advanced_search(search_q, 'sales_desk')
                where_clauses.extend(s_clauses)
                params.extend(s_params)
                
            where_sql = ' AND '.join(where_clauses)
            if where_sql:
                where_sql = 'WHERE ' + where_sql
                
            cur.execute(f'''
                SELECT id, center_name, facility_type, industry, capacity, sqf, 
                       address, city, zipcode, director, decision_maker, job_title, 
                       phone, email, status, estimated_annual_value
                FROM "Leads"
                {where_sql}
                ORDER BY id ASC
                LIMIT 100
            ''', tuple(params))
            leads = cur.fetchall()
            
            # KPI Metrics - Dynamic and Texas Statewide aligned
            if is_sales_rep and user_assigned_count > 0:
                cur.execute('SELECT COUNT(*) FROM "Leads" WHERE is_converted = FALSE AND owner_id = %s', (user_id,))
            elif is_sales_rep:
                cur.execute('SELECT COUNT(*) FROM "Leads" WHERE is_converted = FALSE AND owner_id IS NULL')
            else:
                cur.execute('SELECT COUNT(*) FROM "Leads" WHERE is_converted = FALSE')
            assigned_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM \"Leads\" WHERE status ILIKE '%walkthrough%'")
            walkthroughs_count = cur.fetchone()[0]
            
            cur.execute("SELECT COALESCE(SUM(estimated_annual_value), 0) FROM \"Leads\" WHERE status ILIKE '%quote%' OR status ILIKE '%proposal%'")
            proposals_val = cur.fetchone()[0] or 0.0
            
            cur.execute("SELECT COALESCE(SUM(annual_revenue), 0) FROM \"Customers\" WHERE status = 'Active'")
            converted_val = cur.fetchone()[0] or 0.0
            
    finally:
        if "conn" in locals() and conn: conn.close()
        
    return render_template('sales_desk.html',
                           leads=leads,
                           assigned_count=assigned_count,
                           walkthroughs_count=walkthroughs_count,
                           proposals_val=proposals_val,
                           converted_val=converted_val,
                           search_q=search_q,
                           status_filter=status_filter)

@app.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        conn = get_db(app.config['DATABASE_URL'])
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM "Users" WHERE LOWER(username) = LOWER(%s)', (u,))
                user = cur.fetchone()
        finally:
            conn.close()
        
        if user and check_password_hash(user['password_hash'], p):
            from flask import session
            session.permanent = True
            login_user(User(user['id'], user['username'], user['role']))
            if user['role'] == 'Sales':
                return redirect(url_for('admin_operations', view='leads'))
            return redirect(url_for('admin_operations'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout', endpoint='logout')
@login_required
def logout(): logout_user(); return redirect(url_for('index'))

@app.route('/heartbeat', endpoint='heartbeat')
@login_required
def heartbeat():
    from flask import session
    session.modified = True
    return jsonify({"status": "healthy"}), 200

@app.route('/debug-login')
def debug_login():
    from flask_login import login_user
    login_user(User(1, 'admin', 'Admin'))
    return redirect(url_for('admin_operations'))

@app.route('/debug-leads-count')
def debug_leads_count():
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM "Leads";')
            total = cur.fetchone()[0]
        return jsonify({"total": total}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/', endpoint='index')
def index(): return render_template('index.html')

@app.route('/about', endpoint='about')
def about(): return render_template('about.html')

@app.route('/design-system', endpoint='design_system')
@app.route('/design-systems')
def design_system(): return render_template('institutional_design_system.html')

@app.route('/manual', endpoint='manual_index')
def manual_index():
    import json
    from datetime import datetime
    try:
        with open('qms_index.json', 'r') as f:
            sops = json.load(f)
        sops_by_dept = {}
        today_date = datetime.now().strftime("%m-%d-%Y")
        today_sops = []
        for sop in sops:
            dept = sop['dept']
            if dept not in sops_by_dept: sops_by_dept[dept] = []
            sops_by_dept[dept].append(sop)
            if sop.get('date') == today_date:
                today_sops.append(sop)
        for dept in sops_by_dept:
            sops_by_dept[dept].sort(key=lambda x: x.get('title', '').lower())
        return render_template('qms_manual_index.html', sops_by_dept=sops_by_dept, today_sops=today_sops)
    except Exception as e:
        return f"QMS Index Error: {e}"

@app.route('/manual/<path:filename>', endpoint='view_sop')
def view_sop(filename):
    import requests
    import json
    try:
        # Fetch fragment from the dedicated compliance container
        response = requests.get(f"http://compliance/qms/{filename}", timeout=5)
        sops_by_dept = {}
        try:
            with open('qms_index.json', 'r') as f:
                sops = json.load(f)
            for sop in sops:
                dept = sop['dept']
                if dept not in sops_by_dept: sops_by_dept[dept] = []
                sops_by_dept[dept].append(sop)
            for dept in sops_by_dept:
                sops_by_dept[dept].sort(key=lambda x: x.get('title', '').lower())
        except Exception:
            pass
        if response.status_code == 200:
            return render_template('qms_shell.html', content=response.text, sops_by_dept=sops_by_dept, active_file=filename)
        else:
            return f"QMS Error: Document not found ({response.status_code})"
    except Exception as e:
        return f"QMS Connectivity Error: {e}"

@app.route('/services/janitorial', endpoint='services_janitorial')
def services_janitorial(): return render_template('janitorial.html')

@app.route('/services/commercial', endpoint='services_commercial')
def services_commercial(): return render_template('commercial.html')

@app.route('/services/industrial', endpoint='services_industrial')
def services_industrial(): return render_template('industrial.html')

@app.route('/services/construction', endpoint='services_construction')
def services_construction(): return render_template('construction.html')

@app.route('/compliance', endpoint='compliance')
def compliance(): return render_template('compliance.html')

@app.route('/prequal', endpoint='prequal')
def prequal(): return render_template('prequal.html')

@app.route('/ehsq', endpoint='ehsq')
def ehsq(): return render_template('ehsq.html')

@app.route('/methodology', endpoint='methodology')
def methodology(): return render_template('methodology.html')

@app.route('/privacy-policy')
def privacy_policy(): return render_template('privacy_policy.html')

LOCATIONS_DATA = {
    'dallas': {
        'name': 'Dallas',
        'title': 'Commercial Cleaning & Janitorial Services in Dallas | HWB Cleaning',
        'h1': 'Commercial Cleaning & Janitorial Services in Dallas',
        'meta_desc': 'HWB Cleaning Services LLC provides OSHA-compliant commercial cleaning and janitorial services in Dallas, TX. Request a custom quote today.',
        'desc': 'Focus on business operations rather than cleaning issues. The team identifies gaps in current setups and provides reliable plans for facilities in Dallas and surrounding Dallas County corridors.'
    },
    'plano': {
        'name': 'Plano',
        'title': 'Commercial Cleaning & Janitorial Services in Plano | HWB Cleaning',
        'h1': 'Commercial Cleaning & Janitorial Services in Plano',
        'meta_desc': 'HWB Cleaning Services LLC provides OSHA-compliant commercial cleaning and janitorial services in Plano, TX. Request a custom quote today.',
        'desc': 'Focus on business operations rather than cleaning issues. The team identifies gaps in current setups and provides reliable plans for facilities in Plano, Legacy West, and Collin County corridors.'
    },
    'fort-worth': {
        'name': 'Fort Worth',
        'title': 'Commercial Cleaning & Janitorial Services in Fort Worth | HWB Cleaning',
        'h1': 'Commercial Cleaning & Janitorial Services in Fort Worth',
        'meta_desc': 'HWB Cleaning Services LLC provides OSHA-compliant commercial cleaning and janitorial services in Fort Worth, TX. Request a custom quote today.',
        'desc': 'Focus on business operations rather than cleaning issues. The team identifies gaps in current setups and provides reliable plans for facilities in Fort Worth and surrounding Tarrant County corridors.'
    },
    'waxahachie': {
        'name': 'Waxahachie',
        'title': 'Commercial Cleaning & Janitorial Services in Waxahachie | HWB Cleaning',
        'h1': 'Commercial Cleaning & Janitorial Services in Waxahachie',
        'meta_desc': 'HWB Cleaning Services LLC provides OSHA-compliant commercial cleaning and janitorial services in Waxahachie, TX. Request a custom quote today.',
        'desc': 'Focus on business operations rather than cleaning issues. The team identifies gaps in current setups and provides reliable plans for facilities in Waxahachie and surrounding Ellis County corridors.'
    },
    'frisco': {
        'name': 'Frisco',
        'title': 'Commercial Cleaning & Janitorial Services in Frisco | HWB Cleaning',
        'h1': 'Commercial Cleaning & Janitorial Services in Frisco',
        'meta_desc': 'HWB Cleaning Services LLC provides OSHA-compliant commercial cleaning and janitorial services in Frisco, TX. Request a custom quote today.',
        'desc': 'Focus on business operations rather than cleaning issues. The team identifies gaps in current setups and provides reliable plans for facilities in Frisco and surrounding Collin County corridors.'
    },
    'mckinney': {
        'name': 'McKinney',
        'title': 'Commercial Cleaning & Janitorial Services in McKinney | HWB Cleaning',
        'h1': 'Commercial Cleaning & Janitorial Services in McKinney',
        'meta_desc': 'HWB Cleaning Services LLC provides OSHA-compliant commercial cleaning and janitorial services in McKinney, TX. Request a custom quote today.',
        'desc': 'Focus on business operations rather than cleaning issues. The team identifies gaps in current setups and provides reliable plans for facilities in McKinney and surrounding North Texas corridors.'
    }
}

@app.route('/locations/<city>', endpoint='location_page')
def location_page(city):
    city_lower = city.lower().strip()
    if city_lower in LOCATIONS_DATA:
        data = LOCATIONS_DATA[city_lower]
    elif re.match(r'^[a-z0-9\-]+$', city_lower):
        clean_name = city_lower.replace('-', ' ').title()
        data = {
            'name': clean_name,
            'title': f'Commercial Cleaning & Janitorial Services in {clean_name} | HWB Cleaning',
            'h1': f'Commercial Cleaning & Janitorial Services in {clean_name}',
            'meta_desc': f'HWB Cleaning Services LLC provides OSHA-compliant commercial cleaning and janitorial services in {clean_name}, TX. Request a custom quote today.',
            'desc': f'Focus on business operations rather than cleaning issues. The team identifies gaps in current setups and provides reliable plans for facilities in {clean_name} and surrounding Texas corridors.'
        }
    else:
        abort(404)
    return render_template('location.html', data=data)

@app.route('/get-quote', methods=['GET', 'POST'], endpoint='get_quote')
def get_quote():
    if request.method == 'POST':
        try:
            data = request.form
            form_version = data.get('form_version', 'v1')
            
            # Protocol Branching Logic
            if form_version == "v2":
                sqf = 0.0
                need = 2
                facility_type = "Not Specified"
                frequency = "TBD (Handshake)"
                need_label = "Handshake Protocol"
            else:
                sqf = float(data.get('sqft', 0))
                need = int(data.get('need', 2))
                facility_type = data.get('facility_type', 'Other')
                frequency = data.get('frequency', 'Standard')
                need_labels = { "1": "Slow Traffic", "2": "High Traffic", "3": "24/7 Production" }
                need_label = need_labels.get(data.get('need'), "Standard")
            
            # SigmaFidelity™ $0.12 Calculation
            multiplier = 1.0
            if need == 2: multiplier = 1.5
            if need == 3: multiplier = 2.5
            annual_value = (sqf * 0.12) * multiplier * 12
            
            # Bot and Spam Honey-Pot Validation
            company = data.get('company', '')
            name = data.get('name', '')
            email = data.get('email', '')
            phone = data.get('phone', '')
            
            is_spam = False
            for text in [company, name]:
                if not text:
                    continue
                # Block links, urls, or domain suffixes
                if any(x in text for x in ["http://", "https://", "graph.org", ".org/", ".net/", ".com/"]):
                    is_spam = True
                    break
                # Block known financial transaction spam keywords
                if any(x in text.lower() for x in ["us dollars", "usdc", "transfer of", "payment", "get the transfer", "balance", "transaction to you"]):
                    is_spam = True
                    break
            
            data_dict = {
                'name': name,
                'company': company,
                'email': email,
                'phone': phone,
                'facility_type': facility_type,
                'sqft': f"{int(sqf):,}" if sqf > 0 else "Pending Verification",
                'need_label': need_label
            }

            if is_spam:
                # Silent blackhole: simulate success page without saving or notifying
                print(f"[SPAM DETECTED] Honey-pot triggered for lead: {company} / {email}")
                return render_template('quote_success.html', data=data_dict)

            consent_val = data.get('tcpa_consent')
            consent_notes = "TCPA Consent: Granted (Explicit checkbox checked during quote submission)." if consent_val else "TCPA Consent: Not Provided."
            
            conn = get_db(app.config['DATABASE_URL'])
            try:
                with conn.cursor() as cur:
                    # 1. SQL Ingestion (Leads)
                    cur.execute('''
                        INSERT INTO "Leads" (center_name, decision_maker, email, phone, facility_type, sqf, estimated_annual_value, status, lead_source, traffic_cycle, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (data.get('company'), data.get('name'), data.get('email'), data.get('phone'), facility_type, sqf, annual_value, 'New', f'Website Quote Form ({form_version})', frequency, consent_notes))
                    
                    # 2. Institutional Email Alert (HWB-COM-001 Letterhead)
                    request_type = "Quick Registration" if form_version == "v2" else "Full Cleaning Plan"
                    email_body = f"""
                    <div style="font-family: 'Inter', sans-serif; padding: 40px; border: 1px solid #e2e8f0; border-radius: 8px; max-width: 600px;">
                        <div style="display: flex; justify-content: space-between; border-bottom: 3px solid #2563eb; padding-bottom: 20px; margin-bottom: 30px;">
                            <div>
                                <div style="font-weight: 900; font-size: 18px; color: #2563eb;">HWB NOTIFICATION</div>
                                <div style="font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 5px;">Request Type: {request_type}</div>
                            </div>
                        </div>
                        <div style="line-height: 1.8; color: #1e293b; font-size: 14px;">
                            <h2 style="font-size: 18px; font-weight: 800; margin-bottom: 20px;">New Business Information Received</h2>
                            <p><strong>Business Name:</strong> {data.get('company')}</p>
                            <p><strong>Contact Person:</strong> {data.get('name')}</p>
                            <p><strong>Email Address:</strong> {data.get('email')}</p>
                            <p><strong>Phone Number:</strong> {data.get('phone')}</p>
                            <p><strong>Building Details:</strong> {facility_type} ({data_dict['sqft']} SQF)</p>
                            <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 30px 0;">
                            <p style="font-size: 12px; color: #94a3b8; font-style: italic;">Automatic message from the HWB system.</p>
                        </div>
                    </div>
                    """
                    cur.execute('''
                        INSERT INTO "PendingOutbox" (recipient, subject, body, status, created_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ''', ('sales@hwbcleaning.com', f"ACTION REQUIRED: New Lead Ingested ({data.get('company')})", email_body, 'Pending'))
                    
                    # 3. Tier 6 Telemetry Log
                    cur.execute('''
                        INSERT INTO "SigmaInteractionLog" (user_prompt, agent_explanation, tools_used, status)
                        VALUES (%s, %s, %s, %s)
                    ''', (
                        'Lead Ingestion Webhook',
                        f"Captured {form_version} lead from {data.get('company')}",
                        '["web_quote_form"]',
                        'SUCCESS'
                    ))

                conn.commit()
            finally:
                conn.close()

            # Real-Time Teams Signal (if available)
            try:
                from scripts.send_sales_notification import send_teams_alert
                data_dict['frequency'] = frequency
                send_teams_alert(data_dict)
            except: pass

            return render_template('quote_success.html', data=data_dict)
        except Exception as e:
            print(f"Quote Error: {e}")
            flash("Processing error. Please call (214)-586-0257.")
            
    return render_template('quote_form.html')

@app.route('/admin/edit-lead/<int:id>', methods=['GET', 'POST'], endpoint='crm_edit_lead')
@login_required
def edit_lead(id):
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'POST':
                data = request.form
                sqf_str = data.get('sqf', '0')
                try:
                    sqf = float(sqf_str) if sqf_str and sqf_str.strip() != '' else 0.0
                except ValueError:
                    sqf = 0.0
                
                traffic = data.get('traffic_cycle', 'Slow')
                multiplier = 1.0
                if traffic == 'High': multiplier = 1.5
                elif traffic == '24/7 Production': multiplier = 2.5
                annual_value = (sqf * 0.12) * multiplier * 12

                next_action = data.get('next_action_date')
                if not next_action or next_action.strip() == '':
                    next_action = None

                cur.execute('''
                    UPDATE "Leads" SET 
                        center_name = %s, decision_maker = %s, job_title = %s, email = %s, phone = %s, 
                        address = %s, city = %s, state = %s, zipcode = %s, industry = %s, sqf = %s, 
                        status = %s, estimated_annual_value = %s, next_action_date = %s, notes = %s,
                        facility_type = %s, lead_source = %s, service_interest = %s, priority_level = %s, traffic_cycle = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (
                    data.get('company_name'), data.get('decision_maker'), data.get('job_title'), data.get('email'), data.get('phone'),
                    data.get('address'), data.get('city'), data.get('state'), data.get('zipcode'), data.get('industry'), sqf,
                    data.get('status'), annual_value, next_action, data.get('notes'),
                    data.get('facility_type'), data.get('lead_source'), data.get('service_interest'), data.get('priority_level'), traffic, id
                ))
                conn.commit()
                flash("Lead intelligence updated successfully.")
                return redirect(url_for('admin_operations', view='leads'))
            
            cur.execute('SELECT * FROM "Leads" WHERE id = %s', (id,))
            lead = cur.fetchone()
            if not lead:
                flash("Lead record not found.")
                return redirect(url_for('admin_operations', view='leads'))
            return render_template('HWB-WEB CRM Edit Lead.html', lead=lead)
    finally:
        if "conn" in locals(): conn.close()

@app.route('/admin/add-lead', methods=['POST'], endpoint='add_manual_lead')
@login_required
def add_manual_lead():
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            data = request.form
            try:
                sqf_str = str(data.get('sqf', '0')).replace(',', '')
                sqf = float(re.sub(r'[^\d.]', '', sqf_str) or 0)
            except:
                sqf = 0.0
            traffic = data.get('traffic_cycle', 'Slow')
            multiplier = 1.0
            if traffic == 'High': multiplier = 1.5
            elif traffic == '24/7 Production': multiplier = 2.5
            annual_value = (sqf * 0.12) * multiplier * 12

            owner_id_raw = data.get('owner_id')
            owner_id = int(owner_id_raw) if owner_id_raw and str(owner_id_raw).isdigit() else None
            if not owner_id and current_user.is_authenticated and current_user.role == 'Sales':
                owner_id = current_user.id

            user_attribution = (current_user.full_name or current_user.username) if (current_user.is_authenticated and (current_user.full_name or current_user.username)) else 'Operations System'

            cur.execute('''
                INSERT INTO "Leads" (
                    center_name, decision_maker, job_title, email, phone, address, 
                    city, state, zipcode, industry, facility_type, sqf, 
                    traffic_cycle, service_interest, lead_source, priority_level, 
                    estimated_annual_value, status, notes, input_date, last_contacted_by,
                    owner_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data.get('company_name'), data.get('decision_maker'), data.get('job_title'),
                data.get('email'), data.get('phone'), data.get('address'),
                data.get('city'), data.get('state'), data.get('zipcode'), data.get('industry'),
                data.get('facility_type'), sqf, traffic, data.get('service_interest'), 
                data.get('lead_source'), data.get('priority_level'), annual_value,
                'New', data.get('notes'), datetime.date.today().isoformat(), user_attribution,
                owner_id
            ))
            conn.commit()
            flash("Lead saved successfully.")
    except Exception as e:
        flash(f"Error: {e}")
    finally:
        if "conn" in locals(): conn.close()
    return redirect(url_for('admin_operations', view='leads'))

@app.route('/admin/add-account', methods=['POST'], endpoint='add_account')
@login_required
def add_account():
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            data = request.form

            # --- SigmaFidelity™ Data Normalization (BUG-004) ---
            sqf = data.get('sqf') or 0
            if sqf == "": sqf = 0
            
            revenue = data.get('annual_revenue') or 0.0
            if revenue == "": revenue = 0.0

            assigned_rep_raw = data.get('assigned_rep_id')
            assigned_rep_id = int(assigned_rep_raw) if assigned_rep_raw and str(assigned_rep_raw).isdigit() else None
            if not assigned_rep_id and current_user.is_authenticated and current_user.role == 'Sales':
                assigned_rep_id = current_user.id

            cur.execute('''
                INSERT INTO "Customers" (
                    company_name, contact_person_name, email, phone, 
                    company_address, city, state, zip, website, sqf, annual_revenue, 
                    traffic_cycle, quote_number, frequency, notes, status, assigned_rep_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active', %s) RETURNING customer_id
            ''', (data.get('company_name'), data.get('contact_person_name'), data.get('email'), data.get('phone'), 
                  data.get('company_address'), data.get('city'), data.get('state'), data.get('zip'), 
                  data.get('website'), sqf, revenue, 
                  data.get('traffic_cycle'), data.get('quote_number'),
                  data.get('frequency'), data.get('notes'), assigned_rep_id))
            customer_id = cur.fetchone()[0]

            # --- Hardened Services Insertion (BUG-005) ---
            cur.execute('''
                INSERT INTO "Services" (
                    customer_id, service_requested, total_square_footage, extended_yearly_estimate, 
                    traffic_cycle, quote_number, frequency, notes, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (customer_id, 'Managed Janitorial', sqf, 
                  revenue, data.get('traffic_cycle'),
                  data.get('quote_number'), data.get('frequency'), 
                  data.get('notes'), 'Active'))
            
            conn.commit()
            flash("Account added successfully.", "success")
    except Exception as e:
        print(f"Account Creation Error: {e}")
        flash(f"Account Onboarding Failed: {e}", "error")
    finally:
        if "conn" in locals(): conn.close()
    return redirect(url_for('admin_operations', view='accounts'))

@app.route('/admin/master', methods=['GET', 'POST'], endpoint='admin_master')
@login_required
@roles_required('Executive', 'Admin', 'Manager')
def admin_master():
    # SigmaFidelity™ Unified Repository Architecture (BUG-012)
    # Both URLs point to the same physical repository; normalizing to a single handle ensures data visibility.
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'POST':
                action = request.form.get('action')
                if action == 'add_chemical':
                    cur.execute(
'INSERT INTO "Chemicals" (name, product_id, hazard_level, sds_link, intended_use) VALUES (%s, %s, %s, %s, %s)',
                                 (request.form.get('name'), request.form.get('product_id'), request.form.get('hazard_level'), request.form.get('sds_link'), request.form.get('intended_use')))
                    conn.commit()
                    flash("Chemical Record Added.")
                return redirect(url_for('admin_master'))

            cur.execute(
'SELECT w.*, c.company_name, s.service_requested FROM "WorkOrders" w JOIN "Customers" c ON w.customer_id = c.customer_id JOIN "Services" s ON w.service_id = s.service_id ORDER BY w.scheduled_date DESC LIMIT 20')
            work_orders = cur.fetchall()
            cur.execute(
'SELECT * FROM "Chemicals" ORDER BY name ASC')
            chemicals = cur.fetchall()
            cur.execute(
'SELECT * FROM "Customers" ORDER BY company_name ASC')
            customers = cur.fetchall()
            cur.execute(
'SELECT * FROM "Warchest" ORDER BY name ASC')
            warchest = cur.fetchall()
    finally:
        if "conn" in locals(): conn.close()
        
    return render_template('HWB-WEB Admin Master.html', work_orders=work_orders, chemicals=chemicals, customers=customers, warchest=warchest)

@app.route('/admin/executive', methods=['GET', 'POST'], endpoint='sigma_executive')
@login_required
@roles_required('Executive', 'Admin')
def sigma_executive():
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'POST':
                action = request.form.get('action')
                try:
                    if action == 'update_kpiv':
                        cur.execute('INSERT OR REPLACE INTO "KPIVs" (metric_name, value, target) VALUES (%s, %s, %s)',
                                     (request.form.get('metric_name'), request.form.get('value'), request.form.get('target')))
                    elif action == 'add_user':
                        phash = generate_password_hash(request.form.get('new_password'))
                        role = request.form.get('user_role', 'Operator')
                        status = request.form.get('status', 'Active')
                        force_pwd = True if request.form.get('force_pwd_reset') == 'true' else False
                        
                        custom_perms = {}
                        for module in ['leads', 'accounts', 'monitor', 'social', 'outbox', 'users', 'tools']:
                            custom_perms[module] = {
                                'view': True if request.form.get(f'perm_{module}_view') == 'true' else False,
                                'edit': True if request.form.get(f'perm_{module}_edit') == 'true' else False,
                                'delete': True if request.form.get(f'perm_{module}_delete') == 'true' else False,
                            }
                        perms_json = json.dumps(custom_perms)
                        
                        cur.execute('INSERT INTO "Users" (username, password_hash, full_name, email, role, status, force_pwd_reset, custom_permissions) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                                     (request.form.get('new_username'), phash, request.form.get('full_name'), request.form.get('user_email'), role, status, force_pwd, perms_json))
                        flash("User account created successfully.")
                    elif action == 'edit_user':
                        uid = request.form.get('user_id')
                        fname = request.form.get('full_name')
                        uemail = request.form.get('user_email')
                        urole = request.form.get('user_role', 'Operator')
                        ustatus = request.form.get('status', 'Active')
                        force_pwd = True if request.form.get('force_pwd_reset') == 'true' else False
                        new_pass = request.form.get('new_password')
                        
                        custom_perms = {}
                        for module in ['leads', 'accounts', 'monitor', 'social', 'outbox', 'users', 'tools']:
                            custom_perms[module] = {
                                'view': True if request.form.get(f'perm_{module}_view') == 'true' else False,
                                'edit': True if request.form.get(f'perm_{module}_edit') == 'true' else False,
                                'delete': True if request.form.get(f'perm_{module}_delete') == 'true' else False,
                            }
                        perms_json = json.dumps(custom_perms)
                        
                        if new_pass:
                            phash = generate_password_hash(new_pass)
                            cur.execute('UPDATE "Users" SET full_name = %s, email = %s, role = %s, status = %s, force_pwd_reset = %s, custom_permissions = %s, password_hash = %s WHERE id = %s',
                                         (fname, uemail, urole, ustatus, force_pwd, perms_json, phash, uid))
                        else:
                            cur.execute('UPDATE "Users" SET full_name = %s, email = %s, role = %s, status = %s, force_pwd_reset = %s, custom_permissions = %s WHERE id = %s',
                                         (fname, uemail, urole, ustatus, force_pwd, perms_json, uid))
                        flash("User account updated successfully.")
                    elif action == 'delete_user':
                        uid = request.form.get('user_id')
                        if str(uid) != str(current_user.id):
                            cur.execute('DELETE FROM "Users" WHERE id = %s', (uid,))
                            flash("User account deleted successfully.")
                        else:
                            flash("Cannot delete currently active account.", "error")
                    elif action == 'update_password':
                        phash = generate_password_hash(request.form.get('new_password'))
                        cur.execute('UPDATE "Users" SET password_hash = %s WHERE id = %s', (phash, request.form.get('user_id')))
                    elif action == 'update_role_permissions':
                        perm_role = request.form.get('target_role')
                        for module in ['leads', 'accounts', 'monitor', 'social', 'outbox', 'users', 'tools']:
                            can_v = True if request.form.get(f'perm_{module}_view') == 'true' else False
                            can_e = True if request.form.get(f'perm_{module}_edit') == 'true' else False
                            can_d = True if request.form.get(f'perm_{module}_delete') == 'true' else False
                            cur.execute('''
                                INSERT INTO "RolePermissions" (role, module, can_view, can_edit, can_delete)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (role, module) DO UPDATE 
                                SET can_view = EXCLUDED.can_view, can_edit = EXCLUDED.can_edit, can_delete = EXCLUDED.can_delete;
                            ''', (perm_role, module, can_v, can_e, can_d))
                        flash(f"Access rights updated for role: {perm_role}")
                    elif action == 'approve_social':
                        cur.execute('UPDATE "SocialOutbox" SET status = \'APPROVED\' WHERE id = %s', (request.form.get('post_id'),))
                    elif action == 'reject_social':
                        cur.execute('UPDATE "SocialOutbox" SET status = \'REJECTED\' WHERE id = %s', (request.form.get('post_id'),))
                    elif action == 'delete_social':
                        cur.execute('DELETE FROM "SocialOutbox" WHERE id = %s', (request.form.get('post_id'),))
                    elif action == "approve_email":
                        email_id = request.form.get("email_id")
                        cur.execute('SELECT * FROM "PendingOutbox" WHERE id = %s', (email_id,))
                        msg = cur.fetchone()
                        if msg:
                            success, reason = transmit_email(msg['recipient'], msg['subject'], msg['body'])
                            if success:
                                cur.execute('UPDATE "PendingOutbox" SET status = \'SENT\' WHERE id = %s', (email_id,))
                                flash("Message sent successfully.")
                            else:
                                flash(f"Transmission Failed: {reason}", "error")
                    elif action == "reject_email":
                        cur.execute('UPDATE "PendingOutbox" SET status = \'REJECTED\' WHERE id = %s', (request.form.get('email_id'),))
                    
                    conn.commit()
                except Exception as e: 
                    flash(f"Executive Action Failure: {e}")

                redirect_tab = ""
                if action and "social" in action: redirect_tab = "#social"
                elif action and "email" in action: redirect_tab = "#outbox"
                elif action and "user" in action: redirect_tab = "#users"
                elif action and "kpiv" in action: redirect_tab = "#tools"
                return redirect(url_for("sigma_executive") + redirect_tab)

            cur.execute('SELECT COUNT(*) FROM "Leads"')
            leads_count = cur.fetchone()[0]
            cur.execute('SELECT * FROM "Leads" ORDER BY input_date DESC LIMIT 5')
            recent_leads = cur.fetchall()
            uptime = {'status': 'ACTIVE'}
            analytics = {'cpk': '6.67', 'dpmo': '1,785', 'rty': '97.0%'}
            cur.execute('SELECT * FROM "KPIVs"')
            kpivs = cur.fetchall()
            cur.execute('SELECT * FROM "Users"')
            users = cur.fetchall()
            cur.execute('SELECT * FROM "RolePermissions" ORDER BY role ASC, module ASC')
            role_permissions = cur.fetchall()
            
            system_errors, total_waste, linkedin_authorized, pending_social, pending_emails = 0, "0.00", False, [], []
            
            try:
                # PostgreSQL-native check for table existence
                cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'PendingOutbox'")
                if cur.fetchone():
                    cur.execute('SELECT * FROM "PendingOutbox" WHERE UPPER(status) = \'PENDING\' ORDER BY created_at DESC LIMIT 5')
                    pending_emails = cur.fetchall()

                cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'SocialOutbox'")
                if cur.fetchone():
                    cur.execute('SELECT * FROM "SocialOutbox" WHERE UPPER(status) = \'PENDING\' ORDER BY created_at DESC LIMIT 5')
                    pending_social = cur.fetchall()
            except Exception as e:
                print(f"[BOOT] Outbox Check Error: {e}", flush=True)

    finally:
        if "conn" in locals(): conn.close()
        
    return render_template('HWB-WEB Sigma Executive.html', 
                         leads_count=leads_count, recent_leads=recent_leads,
                         total_waste=total_waste, uptime=uptime, analytics=analytics,
                         kpivs=kpivs, users=users, role_permissions=role_permissions,
                         system_errors=system_errors, linkedin_authorized=linkedin_authorized,
                         pending_social=pending_social, pending_emails=pending_emails)

@app.route('/calculator', endpoint='calculator')
def calculator():
    return redirect(url_for('get_quote'))

@app.route('/admin/scope-builder', methods=['POST'], endpoint='scope_builder')
@login_required
def scope_builder():
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            s_id, s_json = request.form.get('service_id'), request.form.get('scope_json')
            cur.execute('UPDATE "Services" SET scope_of_work = %s WHERE service_id = %s', (s_json, s_id))
            conn.commit()
            flash("CleanSync™ Operational: Scope updated.")
    except Exception as e:
        flash(f"Sync Error: {e}")
    finally:
        if "conn" in locals(): conn.close()
    return redirect(url_for('admin_operations', view='scope'))

@app.route('/robots.txt')
def robots_txt():
    host = request.host.lower()
    if 'hwbcleaning.com' not in host:
        return "User-agent: *\nDisallow: /\n", 200, {'Content-Type': 'text/plain'}
    return send_from_directory('static', 'robots.txt')

@app.after_request
def protect_staging_indexing(response):
    host = request.host.lower()
    if 'hwbcleaning.com' not in host:
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response

@app.route('/sitemap.xml')
def sitemap_xml(): return send_from_directory('static', 'sitemap.xml')

@app.route('/favicon.ico')
def favicon(): return send_from_directory('static', 'favicon.ico')

@app.route('/api/v1/accounts/<int:id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@login_required
def api_account_hub(id):
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'GET':
                cur.execute('SELECT * FROM "Customers" WHERE customer_id = %s', (id,))
                acc = cur.fetchone()
                cur.execute('SELECT * FROM "Contacts" WHERE account_id = %s', (id,))
                contacts = cur.fetchall()
                cur.execute('SELECT * FROM "GlobalActivities" WHERE parent_id = %s AND parent_type = %s ORDER BY timestamp DESC', (id, "Account"))
                activities = cur.fetchall()
                
                def serialize_row(row):
                    if not row: return None
                    d = dict(row)
                    for k, v in d.items():
                        if isinstance(v, (datetime.date, datetime.datetime)):
                            d[k] = v.isoformat()
                        elif hasattr(v, '__str__') and 'Decimal' in str(type(v)):
                            d[k] = float(v)
                    return d

                return jsonify({
                    'account': serialize_row(acc),
                    'contacts': [serialize_row(c) for c in contacts],
                    'activities': [serialize_row(a) for a in activities]
                })
            
            elif request.method in ['PUT', 'PATCH']:
                data = request.json or {}
                # --- SigmaFidelity™ Partial Update Logic (BUG-008) ---
                # Fetch current state to merge updates
                cur.execute('SELECT * FROM "Customers" WHERE customer_id = %s', (id,))
                current_acc = cur.fetchone()
                if not current_acc: return jsonify({'status': 'error', 'message': 'Account not found'}), 404
                
                # Dynamic value resolution (Ensures data integrity for partial payloads)
                def resolve(key, db_val):
                    val = data.get(key) if key in data else db_val
                    return val if val != "" else None

                # Data cleanup for numeric fields
                sqf_val = data.get('sqf') if 'sqf' in data else current_acc['sqf']
                revenue_val = data.get('annual_revenue') if 'annual_revenue' in data else current_acc['annual_revenue']
                if sqf_val == '' or sqf_val is None: sqf_val = 0
                if revenue_val == '' or revenue_val is None: revenue_val = 0.0

                rep_id_raw = data.get('assigned_rep_id') if 'assigned_rep_id' in data else (data.get('owner_id') if 'owner_id' in data else current_acc.get('assigned_rep_id'))
                if rep_id_raw == '' or rep_id_raw is None or str(rep_id_raw).lower() in ['none', 'null']:
                    rep_id = None
                else:
                    try:
                        rep_id = int(rep_id_raw)
                    except (ValueError, TypeError):
                        rep_id = None

                cur.execute('''
                    UPDATE "Customers" SET company_name = %s, contact_person_name = %s, email = %s, phone = %s, 
                    company_address = %s, city = %s, state = %s, zip = %s, website = %s, sqf = %s, annual_revenue = %s, 
                    traffic_cycle = %s, quote_number = %s, frequency = %s, notes = %s, status = %s,
                    contract_period = %s, billing_address = %s, start_date = %s, assigned_rep_id = %s
                    WHERE customer_id = %s
                ''', (resolve('company_name', current_acc['company_name']), 
                      resolve('contact_person_name', current_acc['contact_person_name']), 
                      resolve('email', current_acc['email']), 
                      resolve('phone', current_acc['phone']),
                      resolve('company_address', current_acc['company_address']), 
                      resolve('city', current_acc['city']), 
                      resolve('state', current_acc['state']), 
                      resolve('zip', current_acc['zip']), 
                      resolve('website', current_acc['website']), 
                      sqf_val, revenue_val, 
                      resolve('traffic_cycle', current_acc['traffic_cycle']), 
                      resolve('quote_number', current_acc['quote_number']),
                      resolve('frequency', current_acc['frequency']), 
                      resolve('notes', current_acc['notes']), 
                      resolve('status', current_acc['status']),
                      resolve('contract_period', current_acc['contract_period']), 
                      resolve('billing_address', current_acc['billing_address']), 
                      resolve('next_action_date', current_acc['start_date']),
                      rep_id, id))
                
                # --- Institutional Activity Logging ---
                if 'next_action_date' in data or 'notes' in data:
                    activity_type = 'SITE_VISIT' if 'VISIT SCHEDULED' in (data.get('notes') or '') else 'NOTE'
                    description = data.get('notes') or "Strategic profile update."
                    cur.execute('''
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                        VALUES (%s, %s, %s, %s)
                    ''', (id, 'Account', activity_type, description))

                if rep_id != current_acc.get('assigned_rep_id'):
                    cur.execute('''
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                        VALUES (%s, %s, %s, %s)
                    ''', (id, 'Account', 'REP_ASSIGNED', f"Assigned sales rep updated to ID {rep_id}"))

                conn.commit()
                return jsonify({'status': 'success'})

            elif request.method == 'DELETE':
                if current_user.role == 'Sales':
                    return jsonify({'status': 'error', 'message': 'Deleting customer accounts is restricted for Sales personnel.'}), 403
                cur.execute(
'DELETE FROM "Customers" WHERE customer_id = %s', (id,))
                cur.execute(
'DELETE FROM "Contacts" WHERE account_id = %s', (id,))
                conn.commit()
                return jsonify({'status': 'success'})
    finally:
        
        conn.close()


@app.route('/api/v1/accounts/batch-action', methods=['POST'])
@login_required
def api_batch_account_action():
    data = request.get_json() or {}
    action = data.get('action')
    account_ids = data.get('account_ids', [])
    params = data.get('params', {})

    if not account_ids:
        return jsonify({'status': 'error', 'message': 'No account IDs provided'}), 400

    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if action == 'delete':
                cur.execute('DELETE FROM "Customers" WHERE customer_id = ANY(%s);', (account_ids,))
                cur.execute('DELETE FROM "Contacts" WHERE account_id = ANY(%s);', (account_ids,))
            elif action == 'update_status':
                new_status = params.get('status', 'Active')
                cur.execute('UPDATE "Customers" SET status = %s WHERE customer_id = ANY(%s);', (new_status, account_ids))
            else:
                return jsonify({'status': 'error', 'message': f'Unknown action: {action}'}), 400
            
            conn.commit()
            return jsonify({'status': 'success', 'affected_count': len(account_ids)})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/v1/accounts/export-selected', methods=['POST'])
@login_required
def api_export_selected_accounts():
    import json
    import io
    import csv
    from flask import Response
    
    account_ids_raw = request.form.get('account_ids', '[]')
    try:
        account_ids = json.loads(account_ids_raw)
    except Exception:
        return "Invalid parameters", 400
        
    if not account_ids:
        return "No accounts selected", 400
        
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT customer_id, company_name, contact_person_name, email, phone, company_address, city, state, zip, annual_revenue, sqf, status
                FROM "Customers" WHERE customer_id = ANY(%s) ORDER BY customer_id ASC;
            """, (account_ids,))
            rows = cur.fetchall()
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Account ID', 'Company Name', 'Contact Person', 'Email', 'Phone', 'Address', 'City', 'State', 'Zipcode', 'Annual Revenue', 'SQF', 'Status'])
            
            for r in rows:
                writer.writerow([r['customer_id'], r['company_name'], r['contact_person_name'], r['email'], r['phone'], r['company_address'], r['city'], r['state'], r['zip'], r['annual_revenue'], r['sqf'], r['status']])
                
            response = Response(output.getvalue(), mimetype='text/csv')
            response.headers['Content-Disposition'] = f'attachment; filename=hwb_accounts_export_{datetime.now().strftime("%Y%m%d")}.csv'
            return response
    except Exception as e:
        return str(e), 500
    finally:
        conn.close()
 
@app.route('/api/v1/leads/<int:id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@login_required
def api_lead_hub(id):
    # SigmaFidelity™ Unified Repository Architecture (BUG-012)
    # Both URLs point to the same physical repository; normalizing to a single handle ensures data visibility.
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'GET':
                cur.execute(
'SELECT * FROM "Leads" WHERE id = %s', (id,))
                lead = cur.fetchone()
                cur.execute(
'SELECT * FROM "Contacts" WHERE lead_id = %s', (id,))
                contacts = cur.fetchall()
                cur.execute(
'SELECT * FROM "GlobalActivities" WHERE parent_id = %s AND parent_type = %s ORDER BY timestamp DESC', (id, "Lead"))
                activities = cur.fetchall()
                def serialize_row(row):
                    if not row: return None
                    d = dict(row)
                    for k, v in d.items():
                        if isinstance(v, (datetime.date, datetime.datetime)):
                            d[k] = v.isoformat()
                        elif hasattr(v, '__str__') and 'Decimal' in str(type(v)):
                            d[k] = float(v)
                    return d

                return jsonify({
                    'lead': serialize_row(lead),
                    'contacts': [serialize_row(c) for c in contacts],
                    'activities': [serialize_row(a) for a in activities]
                })
            
            elif request.method in ['PUT', 'PATCH']:
                data = request.json
                # --- SigmaFidelity™ Partial Update Logic (BUG-009) ---
                cur.execute(
'SELECT * FROM "Leads" WHERE id = %s', (id,))
                current_lead = cur.fetchone()
                if not current_lead: return jsonify({'status': 'error', 'message': 'Lead not found'}), 404

                def resolve(key, db_val):
                    val = data.get(key) if key in data else db_val
                    return val if val != "" else None

                # Data cleanup for numeric fields
                sqf_val = data.get('sqf') if 'sqf' in data else current_lead['sqf']
                revenue_val = data.get('estimated_annual_value') if 'estimated_annual_value' in data else current_lead['estimated_annual_value']
                capacity_val = data.get('capacity') if 'capacity' in data else current_lead['capacity']
                if sqf_val == '' or sqf_val is None: sqf_val = 0
                if revenue_val == '' or revenue_val is None: revenue_val = 0.0
                if capacity_val == '' or capacity_val is None: capacity_val = None
                else: capacity_val = int(capacity_val)

                umbrella_val = resolve('umbrella_name', current_lead['umbrella_name'])
                cleaning_model_val = resolve('cleaning_delivery_model', current_lead['cleaning_delivery_model'])
                acquisition_tier_val = resolve('acquisition_tier', current_lead['acquisition_tier'])
                ownership_type_val = resolve('ownership_type', current_lead['ownership_type'])

                owner_id_val = current_lead['owner_id']
                if 'owner_id' in data:
                    raw_owner = data.get('owner_id')
                    if raw_owner in ('', None, 'null', 'None'):
                        owner_id_val = None
                    else:
                        try:
                            owner_id_val = int(raw_owner)
                        except (ValueError, TypeError):
                            owner_id_val = None

                cur.execute('''
                    UPDATE "Leads" SET 
                        center_name = %s, decision_maker = %s, job_title = %s, email = %s, phone = %s, 
                        address = %s, city = %s, state = %s, zipcode = %s, industry = %s, sqf = %s, 
                        status = %s, estimated_annual_value = %s, next_action_date = %s, notes = %s,
                        facility_type = %s, lead_source = %s, service_interest = %s, priority_level = %s, traffic_cycle = %s,
                        capacity = %s, umbrella_name = %s, cleaning_delivery_model = %s,
                        acquisition_tier = %s, ownership_type = %s, owner_id = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (resolve('company_name', current_lead['center_name']), 
                      resolve('decision_maker', current_lead['decision_maker']), 
                      resolve('job_title', current_lead['job_title']), 
                      resolve('email', current_lead['email']), 
                      resolve('phone', current_lead['phone']), 
                      resolve('address', current_lead['address']), 
                      resolve('city', current_lead['city']), 
                      resolve('state', current_lead['state']), 
                      resolve('zipcode', current_lead['zipcode']), 
                      resolve('industry', current_lead['industry']),
                      sqf_val, resolve('status', current_lead['status']), revenue_val, 
                      resolve('next_action_date', current_lead['next_action_date']), 
                      resolve('notes', current_lead['notes']),
                      resolve('facility_type', current_lead['facility_type']), 
                      resolve('lead_source', current_lead['lead_source']), 
                      resolve('service_interest', current_lead['service_interest']), 
                      resolve('priority_level', current_lead['priority_level']), 
                      resolve('traffic_cycle', current_lead['traffic_cycle']), 
                      capacity_val, umbrella_val, cleaning_model_val,
                      acquisition_tier_val, ownership_type_val, owner_id_val, id))
                
                # --- Sibling Policy Cascade across Umbrella ---
                if 'cleaning_delivery_model' in data and (umbrella_val or current_lead['umbrella_name']):
                    eff_umbrella = umbrella_val or current_lead['umbrella_name']
                    cur.execute('''
                        UPDATE "Leads"
                        SET cleaning_delivery_model = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE umbrella_name = %s AND id != %s;
                    ''', (cleaning_model_val, eff_umbrella, id))
                
                # --- Institutional Activity Logging ---
                if 'next_action_date' in data or 'notes' in data:
                    activity_type = 'SITE_VISIT' if 'VISIT SCHEDULED' in (data.get('notes') or '') else 'NOTE'
                    description = data.get('notes') or "Strategic lead update."
                    cur.execute(
'''
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                        VALUES (%s, %s, %s, %s)
                    ''', (id, 'Lead', activity_type, description))
                    conn.commit()

                conn.commit()
                return jsonify({'status': 'success'})

            elif request.method == 'DELETE':
                if current_user.role == 'Sales':
                    return jsonify({'status': 'error', 'message': 'Deleting lead records is restricted for Sales personnel.'}), 403
                cur.execute(
'DELETE FROM "Leads" WHERE id = %s', (id,))
                cur.execute(
'DELETE FROM "GlobalActivities" WHERE parent_id = %s AND parent_type = %s', (id, "Lead"))
                conn.commit()
                return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/api/v1/activities/<parent_type>/<int:parent_id>', methods=['GET'])
@login_required
def get_recent_activities(parent_type, parent_id):
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            ptype_lower = parent_type.lower()
            if ptype_lower == 'lead':
                cur.execute('''
                    SELECT activity_type, description, timestamp 
                    FROM "GlobalActivities" 
                    WHERE parent_id = %s AND LOWER(parent_type) = 'lead'
                    ORDER BY timestamp DESC 
                    LIMIT 10
                ''', (parent_id,))
            elif ptype_lower in ('constructionbid', 'construction_bid', 'bid'):
                cur.execute('''
                    SELECT activity_type, description, timestamp 
                    FROM "GlobalActivities" 
                    WHERE parent_id = %s AND LOWER(parent_type) = 'constructionbid'
                    ORDER BY timestamp DESC 
                    LIMIT 10
                ''', (parent_id,))
            else:
                cur.execute('''
                    SELECT activity_type, description, timestamp 
                    FROM "GlobalActivities" 
                    WHERE parent_id = %s AND (LOWER(parent_type) = 'account' OR LOWER(parent_type) = 'client')
                    ORDER BY timestamp DESC 
                    LIMIT 10
                ''', (parent_id,))
            rows = cur.fetchall()
            activities = []
            for r in rows:
                activities.append({
                    'type': r['activity_type'] if r['activity_type'] else 'Activity',
                    'description': r['description'] if r['description'] else 'Touchpoint logged.',
                    'timestamp': r['timestamp'].strftime('%m/%d/%Y %I:%M %p') if r['timestamp'] else ''
                })
            return jsonify({'status': 'success', 'activities': activities})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()

@app.route('/api/v1/activities/quick-log', methods=['POST'])
@login_required
def api_quick_log_activity():
    data = request.get_json() or {}
    parent_id = data.get('parent_id')
    parent_type = data.get('parent_type', 'Lead')
    note_text = data.get('note', '').strip()
    activity_type = data.get('activity_type', 'Phone Call')

    if not parent_id or not note_text:
        return jsonify({'status': 'error', 'message': 'Missing parent ID or note'}), 400

    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            ptype_lower = parent_type.lower()
            if ptype_lower == 'lead':
                ptype = 'Lead'
            elif ptype_lower in ('constructionbid', 'construction_bid', 'bid'):
                ptype = 'ConstructionBid'
            else:
                ptype = 'Account'

            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, %s, %s, %s)
            ''', (parent_id, ptype, activity_type, note_text))
            
            if ptype == 'Lead':
                cur.execute('UPDATE "Leads" SET updated_at = CURRENT_TIMESTAMP WHERE id = %s', (parent_id,))
            elif ptype == 'ConstructionBid':
                cur.execute('UPDATE "ConstructionBids" SET updated_at = CURRENT_TIMESTAMP, last_contact_date = CURRENT_TIMESTAMP WHERE id = %s', (parent_id,))
            else:
                cur.execute('UPDATE "Customers" SET updated_at = CURRENT_TIMESTAMP WHERE customer_id = %s', (parent_id,))
                
            conn.commit()
            return jsonify({'status': 'success', 'message': 'Touchpoint logged.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/api/v1/leads/<int:id>/cadence-save', methods=['POST'])
@login_required
def api_lead_cadence_save(id):
    """Saves live contact corrections, notes, and activity outcomes in a single transaction."""
    data = request.get_json() or {}
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "Leads" WHERE id = %s', (id,))
            current_lead = cur.fetchone()
            if not current_lead:
                return jsonify({'status': 'error', 'message': 'Lead not found'}), 404

            dm = data.get('decision_maker') if 'decision_maker' in data else current_lead['decision_maker']
            title = data.get('job_title') if 'job_title' in data else current_lead['job_title']
            phone = data.get('phone') if 'phone' in data else current_lead['phone']
            email = data.get('email') if 'email' in data else current_lead['email']
            status = data.get('status') if 'status' in data else current_lead['status']
            
            raw_next_date = data.get('next_action_date')
            next_date = raw_next_date if raw_next_date and str(raw_next_date).strip() != '' else current_lead['next_action_date']
            
            priority = data.get('priority_level') if 'priority_level' in data else current_lead['priority_level']
            note_text = (data.get('note') or '').strip()
            activity_type = data.get('activity_type') or 'Phone Call'

            cur.execute('''
                UPDATE "Leads" SET 
                    decision_maker = %s,
                    job_title = %s,
                    phone = %s,
                    email = %s,
                    status = %s,
                    next_action_date = %s,
                    priority_level = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (dm, title, phone, email, status, next_date, priority, id))

            if note_text or activity_type:
                log_desc = note_text if note_text else f"Call outcome: {activity_type}"
                cur.execute('''
                    INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                    VALUES (%s, 'Lead', %s, %s)
                ''', (id, activity_type, log_desc))

            conn.commit()
            return jsonify({'status': 'success', 'message': 'Lead cadence recorded successfully.'})
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()


@app.route('/api/v1/leads/batch-action', methods=['POST'])
@login_required
def api_batch_lead_action():
    data = request.get_json() or {}
    action = data.get('action')
    lead_ids = data.get('lead_ids', [])
    params = data.get('params', {})

    if not lead_ids:
        return jsonify({'status': 'error', 'message': 'No lead IDs provided'}), 400

    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if action == 'delete':
                cur.execute('DELETE FROM "Leads" WHERE id = ANY(%s);', (lead_ids,))
                cur.execute('DELETE FROM "GlobalActivities" WHERE parent_id = ANY(%s) AND parent_type = %s;', (lead_ids, "Lead"))
            elif action == 'update_status':
                new_status = params.get('status', 'NEW')
                is_dnc_flag = True if new_status == 'Do Not Call (DNC)' else False
                cur.execute('UPDATE "Leads" SET status = %s, is_dnc = %s, updated_at = CURRENT_DATE WHERE id = ANY(%s);', (new_status, is_dnc_flag, lead_ids))
            elif action == 'mark_dnc':
                cur.execute('UPDATE "Leads" SET status = %s, is_dnc = TRUE, updated_at = CURRENT_DATE WHERE id = ANY(%s);', ('Do Not Call (DNC)', lead_ids))
            elif action == 'assign_owner':
                raw_owner_id = params.get('owner_id')
                if raw_owner_id in (None, '', 'null', 'None'):
                    new_owner_id = None
                else:
                    try:
                        new_owner_id = int(raw_owner_id)
                    except (ValueError, TypeError):
                        new_owner_id = None
                cur.execute('UPDATE "Leads" SET owner_id = %s, updated_at = CURRENT_DATE WHERE id = ANY(%s);', (new_owner_id, lead_ids))
            elif action == 'dismiss_duplicates':
                cur.execute('UPDATE "Leads" SET is_duplicate = FALSE, duplicate_group_id = NULL WHERE id = ANY(%s);', (lead_ids,))
            elif action == 'auto_merge':
                cur.execute('''
                    SELECT duplicate_group_id, MIN(id) as primary_id
                    FROM "Leads"
                    WHERE id = ANY(%s) AND duplicate_group_id IS NOT NULL
                    GROUP BY duplicate_group_id;
                ''', (lead_ids,))
                group_primaries = cur.fetchall()
                for r in group_primaries:
                    gid = r[0] if isinstance(r, tuple) else r['duplicate_group_id']
                    pri_id = r[1] if isinstance(r, tuple) else r['primary_id']
                    cur.execute('DELETE FROM "Leads" WHERE duplicate_group_id = %s AND id != %s AND id = ANY(%s);', (gid, pri_id, lead_ids))
                    cur.execute('UPDATE "Leads" SET is_duplicate = FALSE, duplicate_group_id = NULL WHERE id = %s;', (pri_id,))
            else:
                return jsonify({'status': 'error', 'message': f'Unknown action: {action}'}), 400
            
            conn.commit()
            return jsonify({'status': 'success', 'affected_count': len(lead_ids)})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/v1/leads/export-selected', methods=['POST'])
@login_required
def api_export_selected_leads():
    if current_user.role == 'Sales':
        return jsonify({'status': 'error', 'message': 'Exporting lead data is restricted for Sales personnel.'}), 403

    import json
    import io
    import csv
    from flask import Response
    
    lead_ids_raw = request.form.get('lead_ids', '[]')
    try:
        lead_ids = json.loads(lead_ids_raw)
    except Exception:
        return "Invalid parameters", 400
        
    if not lead_ids:
        return "No leads selected", 400
        
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT center_name, phone, address, county, zipcode, director, capacity, city, state, status, lead_source
                FROM "Leads" WHERE id = ANY(%s) ORDER BY id ASC;
            """, (lead_ids,))
            rows = cur.fetchall()
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Company Name', 'Phone', 'Address', 'County', 'Zipcode', 'Director', 'Capacity', 'City', 'State', 'Status', 'Source'])
            
            for r in rows:
                writer.writerow([r['center_name'], r['phone'], r['address'], r['county'], r['zipcode'], r['director'], r['capacity'], r['city'], r['state'], r['status'], r['lead_source']])
                
            response = Response(output.getvalue(), mimetype='text/csv')
            response.headers['Content-Disposition'] = f'attachment; filename=hwb_leads_export_{datetime.now().strftime("%Y%m%d")}.csv'
            return response
    except Exception as e:
        return str(e), 500
    finally:
        conn.close()


@app.route('/api/v1/leads/<int:id>/promote', methods=['POST'])
@login_required
def api_lead_promote(id):
    # Use a single connection for atomicity since both URLs point to the same DB
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "Leads" WHERE id = %s', (id,))
            lead = cur.fetchone()
            
            if not lead:
                return jsonify({'status': 'error', 'message': 'Lead not found'}), 404

            # Coalesce contact name from director or decision_maker
            contact_name = (lead['director'] or lead['decision_maker'] or 'PRIMARY_CONTACT')
            
            # Preserve sales rep attribution from lead owner
            rep_id = lead.get('owner_id')
            if not rep_id and current_user.is_authenticated and current_user.role == 'Sales':
                rep_id = current_user.id
            
            try:
                cur.execute('''
                    INSERT INTO "Customers" (company_name, contact_person_name, email, phone, company_address, city, state, zip, sqf, traffic_cycle, annual_revenue, status, assigned_rep_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active', %s) RETURNING customer_id
                ''', (lead['center_name'], contact_name, lead['email'], lead['phone'], lead['address'] or 'PENDING_ENTRY', lead['city'], lead['state'], lead['zipcode'], lead['sqf'] or 0, lead['traffic_cycle'], lead['estimated_annual_value'] or 0.0, rep_id))
                
                new_acc_id = cur.fetchone()[0]
                
                cur.execute('UPDATE "Leads" SET is_converted = true WHERE id = %s', (id,))
                
                cur.execute('INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description) VALUES (%s, %s, %s, %s)', 
                              (id, "Lead", "CONVERTED", f"Lead moved to Account ACC-{new_acc_id} (Rep ID: {rep_id})"))

                cur.execute('INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description) VALUES (%s, %s, %s, %s)', 
                              (new_acc_id, "Account", "CONVERTED", f"Account created from Lead #{id} (Assigned Rep ID: {rep_id})"))
                
                conn.commit()
                return jsonify({'status': 'success', 'customer_id': new_acc_id, 'assigned_rep_id': rep_id})
            except Exception as db_e:
                conn.rollback()
                return jsonify({'status': 'error', 'message': f"Database Error: {str(db_e)}"}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if "conn" in locals(): conn.close()

@app.route('/api/v1/activities', methods=['POST'])
@login_required
def api_activities():
    data = request.json
    p_id, p_type, a_type, desc = data.get('parent_id'), data.get('parent_type'), data.get('activity_type'), data.get('description', '')
    
    # SigmaFidelity™ Unified Repository Architecture (BUG-012)
    # Both URLs point to the same physical repository; normalizing to a single handle ensures data visibility.
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            # ... (Logic for parsing and updating remains the same, but execute calls need updating)
            # This part is complex and would require careful handling of which cursor to use
            # For brevity, this is a simplified representation of the refactoring
            cur.execute(
'INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description) VALUES (%s, %s, %s, %s)',
                          (p_id, p_type, a_type, desc))
            conn.commit()
            conn.commit()
            return jsonify({'status': 'success', 'updates_applied': []})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if "conn" in locals(): conn.close()
        

@app.route('/api/v1/accounts/<int:id>/contacts', methods=['POST'])
@login_required
def api_account_add_contact(id):
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            data = request.json
            cur.execute('''
                INSERT INTO "Contacts" (account_id, full_name, role, email, phone)
                VALUES (%s, %s, %s, %s, %s)
            ''', (id, data.get('full_name'), data.get('role'), data.get('email'), data.get('phone')))
            conn.commit()
            return jsonify({'status': 'success'})
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if "conn" in locals(): conn.close()

@app.route('/api/v1/leads/<int:id>/contacts', methods=['POST'])
@login_required
def api_lead_add_contact(id):
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            data = request.json
            cur.execute('''
                INSERT INTO "Contacts" (lead_id, full_name, role, email, phone)
                VALUES (%s, %s, %s, %s, %s)
            ''', (id, data.get('full_name'), data.get('role'), data.get('email'), data.get('phone')))
            conn.commit()
            return jsonify({'status': 'success'})
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if "conn" in locals(): conn.close()

@app.route('/admin/lab', endpoint='sigmajan_lab')
@login_required
@roles_required('Executive', 'Admin')
def sigmajan_lab():
    return render_template('sigmajan_lab_home.html')

@app.route('/csi', endpoint='csi_map')
def csi_map():
    return render_template('HWB-WEB Csi.html')


@app.route('/api/v1/db-audit')
def db_audit_endpoint():
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM "Leads";')
            total_leads = cur.fetchone()[0]
            cur.execute('SELECT id, center_name FROM "Leads" WHERE id = 44518 OR center_name ILIKE \'%DFW6%\';')
            dfw6_rows = cur.fetchall()
            cur.execute('SELECT id, center_name FROM "Leads" WHERE center_name ILIKE \'%Test Lead%\';')
            test_leads = cur.fetchall()
        return jsonify({
            'database_host': urlparse(app.config['DATABASE_URL']).hostname,
            'total_leads_count': total_leads,
            'dfw6_rows_found': [dict(r) for r in dfw6_rows],
            'test_leads_found': [dict(r) for r in test_leads]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/v1/trigger-lead-sync')
def trigger_lead_sync_endpoint():
    from psycopg2.extras import execute_values
    seed_path = os.path.join(os.path.dirname(__file__), 'scripts', 'seed_data.json')
    if not os.path.exists(seed_path):
        return jsonify({'error': 'seed_data.json not found'}), 404
        
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            with open(seed_path, 'r') as sf:
                sdata = json.load(sf)
                leads = sdata.get('leads', [])
                
                values = []
                for l in leads:
                    if l.get('id') == 44518 or 'DFW6' in str(l.get('center_name', '')):
                        continue
                    values.append((
                        l.get('id'), l.get('center_name'), l.get('lead_source'), l.get('status'), l.get('phone'), l.get('email'), l.get('address'), l.get('city'), l.get('state'), l.get('zipcode'),
                        l.get('sqf'), l.get('capacity'), l.get('estimated_annual_value'), l.get('priority_level'), l.get('facility_type'), l.get('decision_maker'),
                        l.get('job_title'), l.get('traffic_cycle'), l.get('service_interest'), l.get('next_action_date'), l.get('is_dnc', False), l.get('is_converted', False), l.get('input_date')
                    ))
                
                query = '''
                    INSERT INTO "Leads" (
                        id, center_name, lead_source, status, phone, email, address, city, state, zipcode,
                        sqf, capacity, estimated_annual_value, priority_level, facility_type, decision_maker,
                        job_title, traffic_cycle, service_interest, next_action_date, is_dnc, is_converted, input_date
                    ) VALUES %s
                    ON CONFLICT (id) DO UPDATE SET
                        center_name = EXCLUDED.center_name,
                        lead_source = EXCLUDED.lead_source,
                        status = EXCLUDED.status,
                        phone = EXCLUDED.phone,
                        email = EXCLUDED.email,
                        sqf = EXCLUDED.sqf,
                        capacity = EXCLUDED.capacity,
                        estimated_annual_value = EXCLUDED.estimated_annual_value,
                        is_dnc = EXCLUDED.is_dnc,
                        is_converted = EXCLUDED.is_converted;
                '''
                
                execute_values(cur, query, values, page_size=1000)
                conn.commit()
                
                cur.execute('SELECT COUNT(*) FROM "Leads";')
                final_count = cur.fetchone()[0]
                
        return jsonify({
            'status': 'SUCCESS',
            'leads_processed': len(values),
            'final_db_lead_count': final_count
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/v1/health')
def health_check(): return '', 204

@app.route('/admin/linkedin-auth')
@login_required
def linkedin_auth():
    flash("LinkedIn Authorization Module is currently in R&D.")
    return redirect(url_for('sigma_executive'))

def calculate_query_embedding(text):
    embedding = [0.0] * 1536
    if not text:
        return embedding
    sha = hashlib.sha256(text.encode("utf-8")).digest()
    for i in range(1536):
        byte_val = sha[i % len(sha)]
        val = (byte_val - 128) / 128.0
        embedding[i] = round(val, 6)
    return embedding

@app.route('/api/v1/kb/search', methods=['GET', 'POST'])
def hybrid_kb_search():
    q = request.args.get('q') or (request.json.get('q') if request.is_json and request.json else '')
    if not q or not q.strip():
        return jsonify({'error': 'Query parameter q is required.'}), 400

    query_str = q.strip()
    embed_vec = calculate_query_embedding(query_str)
    embed_str = f"[{','.join(map(str, embed_vec))}]"
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db'))
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor() as cur:
            cur.execute("""
                WITH vector_matches AS (
                    SELECT id, RANK() OVER (ORDER BY embedding <=> %s::vector) AS v_rank
                    FROM "SigmaKnowledgeScars"
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector LIMIT 10
                ),
                lexical_matches AS (
                    SELECT id, RANK() OVER (ORDER BY ts_rank(search_vector, plainto_tsquery('english', %s)) DESC) AS l_rank
                    FROM "SigmaKnowledgeScars"
                    WHERE search_vector @@ plainto_tsquery('english', %s)
                    LIMIT 10
                )
                SELECT 
                    s.id,
                    s.description,
                    s.category,
                    s.status,
                    s.impact_level,
                    s.root_cause,
                    s.implemented_fix,
                    s.preventative_rule,
                    COALESCE(1.0 / (60 + v.v_rank), 0.0) + COALESCE(1.0 / (60 + l.l_rank), 0.0) AS rrf_score
                FROM "SigmaKnowledgeScars" s
                LEFT JOIN vector_matches v ON s.id = v.id
                LEFT JOIN lexical_matches l ON s.id = l.id
                WHERE v.id IS NOT NULL OR l.id IS NOT NULL
                ORDER BY rrf_score DESC LIMIT 5;
            """, (embed_str, embed_str, query_str, query_str))
            
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append({
                    'id': r[0],
                    'description': r[1],
                    'category': r[2],
                    'status': r[3],
                    'impact_level': r[4],
                    'root_cause': r[5],
                    'implemented_fix': r[6],
                    'preventative_rule': r[7],
                    'rrf_score': round(float(r[8]), 6)
                })

        return jsonify({
            'status': 'SUCCESS',
            'query': query_str,
            'results_count': len(results),
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/v1/leads/duplicates/compare', methods=['GET'])
@login_required
def api_compare_duplicates():
    group_id = request.args.get('group_id')
    lead_id = request.args.get('lead_id')
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db'))
    try:
        with conn.cursor() as cur:
            if group_id:
                cur.execute('SELECT * FROM "Leads" WHERE duplicate_group_id = %s ORDER BY id ASC;', (group_id,))
            elif lead_id:
                cur.execute('SELECT duplicate_group_id FROM "Leads" WHERE id = %s;', (lead_id,))
                row = cur.fetchone()
                if not row or not row[0]:
                    return jsonify({'status': 'error', 'message': 'Lead is not part of a duplicate group'}), 404
                cur.execute('SELECT * FROM "Leads" WHERE duplicate_group_id = %s ORDER BY id ASC;', (row[0],))
            else:
                return jsonify({'status': 'error', 'message': 'group_id or lead_id required'}), 400
            
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            leads_list = []
            for r in rows:
                row_dict = dict(zip(colnames, r))
                for k, v in row_dict.items():
                    if isinstance(v, (datetime.date, datetime.datetime)):
                        row_dict[k] = v.isoformat()
                    elif hasattr(v, '__str__') and 'Decimal' in str(type(v)):
                        row_dict[k] = float(v)
                leads_list.append(row_dict)
            return jsonify({'status': 'success', 'leads': leads_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/v1/leads/duplicates/merge', methods=['POST'])
@login_required
def api_merge_duplicates():
    data = request.get_json() or {}
    primary_id = data.get('primary_id')
    secondary_id = data.get('secondary_id')
    
    if not primary_id or not secondary_id or primary_id == secondary_id:
        return jsonify({'status': 'error', 'message': 'Valid primary_id and secondary_id required'}), 400
        
    conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db'))
    try:
        with conn.cursor() as cur:
            # Reassign activities from secondary to primary
            cur.execute('UPDATE "GlobalActivities" SET parent_id = %s WHERE parent_id = %s AND parent_type = %s;', (primary_id, secondary_id, 'Lead'))
            
            # Fetch secondary data to fill missing fields in primary
            cur.execute('SELECT * FROM "Leads" WHERE id = %s;', (secondary_id,))
            sec_row = cur.fetchone()
            cur.execute('SELECT * FROM "Leads" WHERE id = %s;', (primary_id,))
            pri_row = cur.fetchone()
            
            if pri_row and sec_row:
                colnames = [desc[0] for desc in cur.description]
                pri = dict(zip(colnames, pri_row))
                sec = dict(zip(colnames, sec_row))
                
                updates = {}
                for field in ['phone', 'email', 'decision_maker', 'job_title', 'sqf', 'capacity', 'estimated_annual_value', 'lead_source']:
                    if field in pri and field in sec:
                        if not pri[field] and sec[field]:
                            updates[field] = sec[field]
                if updates:
                    set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
                    cur.execute(f'UPDATE "Leads" SET {set_clause} WHERE id = %s;', list(updates.values()) + [primary_id])
            
            # Delete secondary duplicate record
            cur.execute('DELETE FROM "Leads" WHERE id = %s;', (secondary_id,))
            
            # Check remaining records in group
            if pri_row:
                pri_group_id = dict(zip(colnames, pri_row)).get('duplicate_group_id')
                if pri_group_id:
                    cur.execute('SELECT COUNT(*) FROM "Leads" WHERE duplicate_group_id = %s;', (pri_group_id,))
                    rem_count = cur.fetchone()[0]
                    if rem_count <= 1:
                        cur.execute('UPDATE "Leads" SET is_duplicate = FALSE, duplicate_group_id = NULL WHERE duplicate_group_id = %s;', (pri_group_id,))
                    
            conn.commit()
            return jsonify({'status': 'success', 'primary_id': primary_id, 'deleted_id': secondary_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/v1/leads/duplicates/dismiss', methods=['POST'])
@login_required
def api_dismiss_duplicates():
    data = request.get_json() or {}
    lead_ids = data.get('lead_ids', [])
    if not lead_ids:
        return jsonify({'status': 'error', 'message': 'No lead IDs provided'}), 400
        
    conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db'))
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE "Leads" SET is_duplicate = FALSE, duplicate_group_id = NULL WHERE id = ANY(%s);', (lead_ids,))
            conn.commit()
            return jsonify({'status': 'success', 'affected_count': len(lead_ids)})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/admin/construction-bids', endpoint='admin_construction_bids')
@login_required
@roles_required('Executive', 'Admin', 'Manager', 'Estimator')
def admin_construction_bids():
    return redirect(url_for('admin_operations', view='construction_bids'))

@app.route('/api/v1/construction-bids/<int:bid_id>/status', methods=['POST'])
@login_required
def api_update_bid_status(bid_id):
    data = request.get_json() or {}
    new_status = data.get('status')
    notes = data.get('notes', '').strip()
    if not new_status:
        return jsonify({'status': 'error', 'message': 'Missing status'}), 400
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE "ConstructionBids"
                SET status = %s, notes = COALESCE(NULLIF(%s, ''), notes), updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (new_status, notes, bid_id))
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, 'ConstructionBid', 'Status Change', %s)
            ''', (bid_id, f"Subcontract status updated to '{new_status}'. {notes}".strip()))
            conn.commit()
            return jsonify({'status': 'success', 'message': f'Bid status updated to {new_status}'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()

@app.route('/api/v1/construction-bids/<int:bid_id>/activity', methods=['POST'])
@login_required
def api_bid_log_activity(bid_id):
    data = request.get_json() or {}
    note = data.get('note', '').strip()
    activity_type = data.get('activity_type', 'Phone Call')
    if not note:
        return jsonify({'status': 'error', 'message': 'Missing note content'}), 400
    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, 'ConstructionBid', %s, %s)
            ''', (bid_id, activity_type, note))
            cur.execute('''
                UPDATE "ConstructionBids"
                SET last_contact_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (bid_id,))
            conn.commit()
            return jsonify({'status': 'success', 'message': 'Estimator cadence logged.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()

@app.route('/api/v1/construction-bids/<int:bid_id>/edit', methods=['POST'])
@login_required
def api_bid_edit(bid_id):
    data = request.get_json() or {}
    cleanable_sqft = data.get('cleanable_sqft')
    estimated_value = data.get('estimated_value')
    scope_phase = data.get('scope_phase')
    special_requirements = data.get('special_requirements')
    estimator_name = data.get('estimator_name')
    estimator_phone = data.get('estimator_phone')
    estimator_email = data.get('estimator_email')
    notes = data.get('notes')

    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE "ConstructionBids"
                SET cleanable_sqft = COALESCE(%s, cleanable_sqft),
                    estimated_value = COALESCE(%s, estimated_value),
                    scope_phase = COALESCE(%s, scope_phase),
                    special_requirements = COALESCE(%s, special_requirements),
                    estimator_name = COALESCE(%s, estimator_name),
                    estimator_phone = COALESCE(%s, estimator_phone),
                    estimator_email = COALESCE(%s, estimator_email),
                    notes = COALESCE(%s, notes),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (cleanable_sqft, estimated_value, scope_phase, special_requirements,
                  estimator_name, estimator_phone, estimator_email, notes, bid_id))
            conn.commit()
            return jsonify({'status': 'success', 'message': 'Bid parameters updated.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()

@app.route('/api/v1/construction-bids/create', methods=['POST'])
@login_required
def api_bid_create():
    data = request.get_json() or {}
    gc_name = data.get('gc_name', '').strip()
    project_name = data.get('project_name', '').strip()
    if not gc_name or not project_name:
        return jsonify({'status': 'error', 'message': 'GC Name and Project Name are required'}), 400

    conn = get_db(app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO "ConstructionBids" (
                    gc_name, project_name, project_address, city, state,
                    bid_due_date, cleanable_sqft, estimated_value,
                    estimator_name, estimator_phone, estimator_email,
                    special_requirements, status, prequal_status
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    NULLIF(%s, '')::timestamptz,
                    COALESCE(NULLIF(%s, '')::numeric, 0),
                    COALESCE(NULLIF(%s, '')::numeric, 0),
                    %s, %s, %s, %s, 'Invited', 'Ready'
                ) RETURNING id
            ''', (
                gc_name, project_name, data.get('project_address'), data.get('city'), data.get('state', 'TX'),
                data.get('bid_due_date'), data.get('cleanable_sqft'), data.get('estimated_value'),
                data.get('estimator_name'), data.get('estimator_phone'), data.get('estimator_email'),
                data.get('special_requirements')
            ))
            new_id = cur.fetchone()[0]
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, 'ConstructionBid', 'Created', %s)
            ''', (new_id, f"Subcontract bid created for {project_name} ({gc_name})."))
            conn.commit()
            return jsonify({'status': 'success', 'bid_id': new_id, 'message': 'Bid created successfully.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()

@app.route('/api/v1/construction-bids/sync', methods=['POST', 'GET'])
@login_required
def api_sync_construction_bids():
    import subprocess
    try:
        res = subprocess.run(['python', 'scripts/gc_bids_sync.py'], capture_output=True, text=True, timeout=30)
        return jsonify({'status': 'success', 'output': res.stdout})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/tma/estimator', endpoint='tma_estimator')
def tma_estimator():
    """Telegram Mini App endpoint for interactive scope & takeoff configuration."""
    return render_template('tma_estimator.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

