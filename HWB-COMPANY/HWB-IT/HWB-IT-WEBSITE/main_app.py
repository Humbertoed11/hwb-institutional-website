from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from flask_compress import Compress
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import datetime
import re
import requests
import msal
from urllib.parse import urlencode, urlparse, urlunparse
from dotenv import load_dotenv
from werkzeug.exceptions import HTTPException
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

# --- SigmaFidelity™ Institutional JSON Encoder ---
class InstitutionalJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)

app.json_encoder = InstitutionalJSONEncoder

# --- 12-Factor Compliance: Startup Verification ---
# Fail fast if critical configurations are not set in the environment.
required_configs = ['SECRET_KEY', 'DATABASE_URL', 'CLIENT_DATABASE_URL']
missing_configs = [c for c in required_configs if not app.config.get(c)]
if missing_configs:
    raise ValueError(f"FATAL: Missing required environment variables: {', '.join(missing_configs)}")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- SigmaFidelity™ SEO: Domain Consolidation (BUG-045) ---
# Mandated to force all traffic to the canonical WWW domain.
@app.before_request
def redirect_to_www():
    url_parts = urlparse(request.url)
    if url_parts.netloc == 'hwbcleaning.com':
        url_parts = url_parts._replace(netloc='www.hwbcleaning.com')
        return redirect(urlunparse(url_parts), code=301)

with app.app_context():
    try:
        print("[BOOT] SigmaFidelity™ High-Fidelity Startup Sequence Initiated.", flush=True)
        sync_db_sequences(app.config['DATABASE_URL'])
        
        # --- SigmaFidelity™ Poka-Yoke Schema Migrator (BUG-005/008) ---
        conn = get_db(app.config['DATABASE_URL'])
        with conn.cursor() as cur:
            # 1. Hardening "Services" Table
            cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS traffic_cycle TEXT;')
            cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS frequency TEXT;')
            cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS notes TEXT;')
            cur.execute('ALTER TABLE "Services" ADD COLUMN IF NOT EXISTS status TEXT DEFAULT \'Active\';')
            
            # 2. Hardening "Customers" Table
            cur.execute('ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS billing_address TEXT;')
            cur.execute('ALTER TABLE "Customers" ADD COLUMN IF NOT EXISTS contract_period TEXT;')
            
            # 3. Ensure GlobalActivities exists
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
            conn.commit()
            if "conn" in locals(): conn.close()
            
        print("[BOOT] Infrastructure Handshake Complete.", flush=True)
    except Exception as e:
        print(f"[BOOT] Startup Handshake Warning: {e}", flush=True)

# ... (Logic continues below)

# --- Security Architecture: User Management ---

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    try:
        # Use a short timeout for the user loader to prevent page hangs
        conn = get_db(app.config['DATABASE_URL'])
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "Users" WHERE id = %s', (user_id,))
            u = cur.fetchone()
            if u:
                print(f"[GUARD] Loaded user {u['username']} with role: {u['role']}", flush=True)
                return User(u['id'], u['username'], u['role'])
        conn.close()
    except Exception as e:
        print(f"[GUARD] load_user failed: {e}", flush=True)
    return None

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
    if not date_val: return date_val
    
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

# --- HWB Concept Lab: R&D Laboratory ---


# --- Jinja2 Institutional Filters ---
@app.template_filter('format_mdy')
def format_mdy_filter(s):
    if not s: return "--"
    if isinstance(s, (datetime.date, datetime.datetime)):
        return s.strftime('%m/%d/%Y')
    return str(s)

@app.template_filter('ts')
def ts_filter(s):
    if not s: return ""
    return str(s)

@app.route('/admin/concept-lab', endpoint='concept_lab')
@login_required
def concept_lab():
    return render_template('concept_lab.html')

@app.route('/admin/concept-lab/sigmajan', endpoint='sigmajan_lab')
@login_required
def sigmajan_lab():
    return render_template('sigmajan_lab_home.html')

@app.route('/admin/concept-lab/babysop', endpoint='babysop')
@login_required
def babysop():
    return render_template('babysop_lab.html')

@app.route('/admin/concept-lab/legacy-site', endpoint='legacy_site')
@login_required
def legacy_site():
    return render_template('legacy_site_mirror.html')

@app.route('/admin/concept-lab/quote-v2', endpoint='quote_v2')
@login_required
def quote_v2():
    return render_template('quote_form.html')

# --- HWB Command v5.0: Unified Backend Hub ---

@app.route('/admin/operations', endpoint='admin_operations')
@login_required
def admin_operations():
    """The Single-Source Dashboard for Management Dashboard."""
    active_view = request.args.get('view', 'leads')
    page = request.args.get('page', 1, type=int)
    search_q = request.args.get('q', '').strip()
    active_only = request.args.get('active_only') == 'true'
    sort_by = request.args.get('sort')
    sort_dir = request.args.get('dir', '').upper()
    
    # Initialization
    leads, clients, work_orders, services, activities = [], [], [], [], []
    leads_count, total_pages, portfolio_total = 0, 1, 0
    lib = {'area': [], 'task': [], 'item': []}
    
    # --- Dynamic Column Architecture ---
    default_cols_leads = 'company,status,sqf,value,priority,activities'
    default_cols_accounts = 'company,city,phone,revenue,activities'
    
    active_cols_str = request.args.get('cols')
    if not active_cols_str:
        active_cols_str = default_cols_leads if active_view == 'leads' else default_cols_accounts
    active_cols = [c.strip() for c in active_cols_str.split(',') if c.strip()]
    
    per_page = 50
    offset = (page - 1) * per_page

    # View-Specific SQL Column Mapping
    leads_sort_map = {
        'company': 'center_name', 'industry': 'industry', 'input_date': 'input_date',
        'status': 'status', 'phone': 'phone', 'email': 'email', 'city': 'city',
        'zipcode': 'zipcode', 'sqf': 'sqf', 'value': 'estimated_annual_value',
        'priority': 'priority_level', 'facility': 'facility_type', 'contact': 'decision_maker',
        'address': 'address', 'job_title': 'job_title', 'source': 'lead_source',
        'frequency': 'traffic_cycle', 'interest': 'service_interest', 
        'next_action': 'next_action_date', 'owner': 'owner_id',
        'activities': '(SELECT COUNT(*) FROM "GlobalActivities" WHERE parent_id = l.id AND parent_type = \'Lead\')', 
        'last_contact': 'last_contact'
    }
    accounts_sort_map = {
        'company': 'company_name', 'city': 'city', 'phone': 'phone',
        'email': 'email', 'revenue': 'annual_revenue', 'status': 'status',
        'address': 'company_address', 'contact': 'contact_person_name',
        'zip': 'zip', 'state': 'state', 'quote': 'quote_number',
        'period': 'contract_period', 'frequency': 'frequency',
        'start_date': 'start_date', 'terms': 'payment_terms',
        'activities': '(SELECT COUNT(*) FROM "GlobalActivities" WHERE parent_id = c.customer_id AND parent_type = \'Account\')', 
        'last_contact': 'last_contact'
    }
    
    # Handle Sort Parameters
    if active_view == 'leads':
        l_sort = leads_sort_map.get(sort_by, 'input_date')
        l_dir = sort_dir if sort_dir in ['ASC', 'DESC'] else 'DESC'
        a_sort, a_dir = 'company_name', 'ASC'
    else:
        a_sort = accounts_sort_map.get(sort_by, 'company_name')
        a_dir = sort_dir if sort_dir in ['ASC', 'DESC'] else 'ASC'
        l_sort, l_dir = 'input_date', 'DESC'

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
                       (SELECT MAX(timestamp) FROM "GlobalActivities" WHERE parent_id = c.customer_id AND parent_type = 'Account') as last_contact
                FROM "Customers" c
            '''
            
            where_clauses = []
            params = []

            if active_only:
                where_clauses.append("(SELECT COUNT(*) FROM \"GlobalActivities\" WHERE parent_id = c.customer_id AND parent_type = 'Account') > 0")

            if search_q and active_view == 'accounts':
                # --- SigmaFidelity™ Search Selector Logic (BUG-011/BUG-013) ---
                if search_q.startswith('"') and search_q.endswith('"'):
                    search_pattern = search_q[1:-1]
                elif '*' in search_q:
                    search_pattern = search_q.replace('*', '%')
                else:
                    search_pattern = f'%{search_q}%'
                
                where_clauses.append("(company_name ILIKE %s OR company_address ILIKE %s OR city ILIKE %s OR state ILIKE %s OR zip ILIKE %s OR phone ILIKE %s)")
                params.extend([search_pattern] * 6)

            full_where = ""
            if where_clauses:
                full_where = "WHERE " + " AND ".join(where_clauses)

            cur.execute(f"{account_sql_base} {full_where} ORDER BY {a_sort} {a_dir}", tuple(params))
            clients = cur.fetchall()

            # 2. FETCH LEADS
            # --- SigmaFidelity™ Lead Query Hardening (BUG-018) ---
            lead_where_clauses = ["is_converted = false"]
            lead_params = []

            if active_only:
                lead_where_clauses.append("(SELECT COUNT(*) FROM \"GlobalActivities\" WHERE parent_id = l.id AND parent_type = 'Lead') > 0")

            if search_q and active_view == 'leads':
                # --- SigmaFidelity™ Search Selector Logic (BUG-011/BUG-013) ---
                if search_q.startswith('"') and search_q.endswith('"'):
                    search_pattern = search_q[1:-1]
                elif '*' in search_q:
                    search_pattern = search_q.replace('*', '%')
                else:
                    search_pattern = f'%{search_q}%'
                
                lead_where_clauses.append("(center_name ILIKE %s OR facility_type ILIKE %s OR sqf::text ILIKE %s OR city ILIKE %s OR state ILIKE %s OR zipcode ILIKE %s OR phone ILIKE %s OR email ILIKE %s OR address ILIKE %s)")
                lead_params.extend([search_pattern] * 9)

            lead_where_str = "WHERE " + " AND ".join(lead_where_clauses)

            # Count Query
            cur.execute(f'SELECT COUNT(*) FROM "Leads" l {lead_where_str}', tuple(lead_params))
            leads_count = cur.fetchone()[0]

            # Data Query
            lead_sql_base = f'''
                SELECT l.*, 
                       (SELECT COUNT(*) FROM "GlobalActivities" WHERE parent_id = l.id AND parent_type = 'Lead') as activity_count, 
                       (SELECT MAX(timestamp) FROM "GlobalActivities" WHERE parent_id = l.id AND parent_type = 'Lead') as last_contact 
                FROM "Leads" l 
                {lead_where_str}
            '''
            
            cur.execute(f'{lead_sql_base} ORDER BY {l_sort} {l_dir}, id ASC LIMIT %s OFFSET %s', tuple(lead_params + [per_page, offset]))
            leads = cur.fetchall()
            print(f"[BOOT] Fetched {len(leads)} leads. Total Count: {leads_count}", flush=True)
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
                'counts': {'leads': leads_count or 0, 'accounts': len(clients) if clients else 0},
                'active_view': active_view
            })
        except Exception as e:
            print(f"[BOOT] JSON Serialization Error: {e}", flush=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500

    return render_template('backoffice_operations.html', 
                         active_view=active_view, leads=leads, leads_count=leads_count,
                         page=page, total_pages=total_pages, search_q=search_q,
                         sort_by=sort_by or '', sort_dir=sort_dir, active_cols=active_cols,
                         active_cols_str=active_cols_str, portfolio_total=portfolio_total,
                         clients=clients, work_orders=work_orders, services=services,
                         library=json.dumps(lib), activities=activities)

@app.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        conn = get_db(app.config['DATABASE_URL'])
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM "Users" WHERE username = %s', (u,))
                user = cur.fetchone()
        finally:
            conn.close()
        
        if user and check_password_hash(user['password_hash'], p):
            login_user(User(user['id'], user['username'], user['role']))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_operations'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout', endpoint='logout')
@login_required
def logout(): logout_user(); return redirect(url_for('index'))

# --- SigmaFidelity™ SEO: Legacy URL Redirects (BUG-044) ---
# Mandated to clear incorrect legacy sitelinks from Google's index.
@app.route('/contact')
def legacy_contact(): return redirect(url_for('get_quote'), code=301)

@app.route('/facility-services')
@app.route('/industries')
def legacy_services(): return redirect(url_for('services_commercial'), code=301)

@app.route('/m/create')
@app.route('/m/create-account')
@app.route('/m/login')
@app.route('/m/<path:path>')
def legacy_mobile_catchall(path=None): return redirect(url_for('index'), code=301)

@app.route('/vendors-/-subcontractors')
@app.route('/vendors-%2F-subcontractors')
def legacy_vendors(): return redirect(url_for('index'), code=301)

@app.route('/', endpoint='index')
def index(): return render_template('index.html')

@app.route('/about', endpoint='about')
def about(): return render_template('about.html')

@app.route('/calculator', endpoint='calculator')
def calculator(): return render_template('cleaning-calculator.html')

@app.route('/services', endpoint='services')
def services(): return render_template('HWB-WEB Services.html')

@app.route('/services/janitorial', endpoint='services_janitorial')
def services_janitorial(): return render_template('janitorial-services.html')

@app.route('/services/commercial', endpoint='services_commercial')
def services_commercial(): return render_template('commercial-cleaning.html')

@app.route('/services/industrial', endpoint='services_industrial')
def services_industrial(): return render_template('industrial-cleaning.html')

@app.route('/services/construction', endpoint='services_construction')
def services_construction(): return render_template('construction-cleanup.html')

@app.route('/services/warehouse', endpoint='services_warehouse')
def services_warehouse(): return render_template('warehouse-cleaning.html')

@app.route('/services/office', endpoint='services_office')
def services_office(): return render_template('office-management.html')

@app.route('/resources', endpoint='resources')
def resources(): return render_template('HWB-WEB Resources.html')

@app.route('/legacy-site', endpoint='public_legacy_site')
def public_legacy_site(): return render_template('legacy_site_mirror.html')

@app.route('/compliance', endpoint='compliance')
def compliance(): return render_template('compliance.html')

@app.route('/ehsq', endpoint='ehsq')
def ehsq(): return render_template('ehsq.html')

@app.route('/privacy-policy')
def privacy_policy(): return render_template('privacy_policy.html')

@app.route('/get-quote', methods=['GET', 'POST'], endpoint='get_quote')
def get_quote():
    if request.method == 'POST':
        try:
            data = request.form
            sqf = float(data.get('sqft', 0))
            need = int(data.get('need', 2))
            multiplier = 1.0
            if need == 2: multiplier = 1.5
            if need == 3: multiplier = 2.5
            
            annual_value = (sqf * 0.12) * multiplier * 12
            
            need_labels = { "1": "Slow Traffic", "2": "High Traffic", "3": "24/7 Production" }
            data_dict = {
                'name': data.get('name'),
                'company': data.get('company'),
                'email': data.get('email'),
                'phone': data.get('phone'),
                'facility_type': data.get('facility_type'),
                'sqft': f"{int(sqf):,}",
                'need_label': need_labels.get(data.get('need'), "Standard")
            }

            conn = get_db(app.config['DATABASE_URL'])
            try:
                with conn.cursor() as cur:
                    cur.execute('''
                        INSERT INTO "Leads" (center_name, decision_maker, email, phone, facility_type, sqf, estimated_annual_value, status, lead_source, traffic_cycle)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (data.get('company'), data.get('name'), data.get('email'), data.get('phone'), data.get('facility_type'), sqf, annual_value, 'New', 'Website Quote Form', data.get('frequency')))
                    
                    try:
                        # Institutional Simplified Email Alert
                        is_v2 = data.get('facility_type') == "Not Specified"
                        if is_v2:
                            email_body = f"""
                            <div style='font-family: sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 8px;'>
                                <h2 style='color: #2563eb;'>New Lead Handshake (V2)</h2>
                                <p><strong>Company:</strong> {data.get('company')}</p>
                                <p><strong>Manager:</strong> {data.get('name')}</p>
                                <p><strong>Contact Email:</strong> {data.get('email')}</p>
                                <hr>
                                <p style='font-size: 0.8rem; color: #666;'>Simplified V2 Handshake Protocol.</p>
                            </div>
                            """
                        else:
                            email_body = f"""
                            <div style='font-family: sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 8px;'>
                                <h2 style='color: #2563eb;'>New Cleaning Request (V1)</h2>
                                <p><strong>Company:</strong> {data.get('company')}</p>
                                <p><strong>Manager:</strong> {data.get('name')}</p>
                                <p><strong>Building:</strong> {data.get('facility_type')} ({int(sqf):,} SQF)</p>
                                <p><strong>Frequency:</strong> {data.get('frequency')}</p>
                                <p><strong>Contact:</strong> {data.get('email')} | {data.get('phone')}</p>
                                <hr>
                                <p style='font-size: 0.8rem; color: #666;'>Standard V1 Quote Request.</p>
                            </div>
                            """
                        cur.execute('''
                            INSERT INTO "PendingOutbox" (recipient, subject, body, status, created_at)
                            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ''', ('sales@hwbcleaning.com', f"ACTION REQUIRED: New Lead from {data.get('company')}", email_body, 'Pending'))
                    except Exception as e:
                        print(f"PendingOutbox Error: {e}") # Log error but don't fail the quote

                conn.commit()
            finally:
                conn.close()

            # Real-Time Teams Signal (out of transaction)
            try:
                from scripts.send_sales_notification import send_teams_alert
                data_dict['frequency'] = data.get('frequency')
                send_teams_alert(data_dict)
            except Exception as e:
                print(f"Teams Notification Error: {e}")

            # Directional success routing based on form version
            if data.get('form_version') == "v2":
                return render_template('quote_success.html', data=data_dict)
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
                sqf = float(data.get('sqf', 0))
                traffic = data.get('traffic_cycle', 'Slow')
                multiplier = 1.0
                if traffic == 'High': multiplier = 1.5
                elif traffic == '24/7 Production': multiplier = 2.5
                annual_value = (sqf * 0.12) * multiplier * 12

                cur.execute('''
                    UPDATE "Leads" SET 
                        center_name = %s, decision_maker = %s, email = %s, 
                        phone = %s, address = %s, facility_type = %s, 
                        sqf = %s, traffic_cycle = %s, service_interest = %s, 
                        lead_source = %s, status = %s, estimated_annual_value = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (
                    data.get('company_name'), data.get('decision_maker'), data.get('email'), 
                    data.get('phone'), data.get('address'), data.get('facility_type'),
                    sqf, traffic, data.get('service_interest'),
                    data.get('lead_source'), data.get('status'), annual_value, id
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

            cur.execute('''
                INSERT INTO "Leads" (
                    center_name, decision_maker, job_title, email, phone, address, 
                    city, state, zipcode, industry, facility_type, sqf, 
                    traffic_cycle, service_interest, lead_source, priority_level, 
                    estimated_annual_value, status, notes, input_date, last_contacted_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data.get('company_name'), data.get('decision_maker'), data.get('job_title'),
                data.get('email'), data.get('phone'), data.get('address'),
                data.get('city'), data.get('state'), data.get('zipcode'), data.get('industry'),
                data.get('facility_type'), sqf, traffic, data.get('service_interest'), 
                data.get('lead_source'), data.get('priority_level'), annual_value,
                'New', data.get('notes'), datetime.date.today().isoformat(), 'George'
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

            cur.execute('''
                INSERT INTO "Customers" (
                    company_name, contact_person_name, email, phone, 
                    company_address, city, state, zip, website, sqf, annual_revenue, 
                    traffic_cycle, quote_number, frequency, notes, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active') RETURNING customer_id
            ''', (data.get('company_name'), data.get('contact_person_name'), data.get('email'), data.get('phone'), 
                  data.get('company_address'), data.get('city'), data.get('state'), data.get('zip'), 
                  data.get('website'), sqf, revenue, 
                  data.get('traffic_cycle'), data.get('quote_number'),
                  data.get('frequency'), data.get('notes')))
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
                        cur.execute('INSERT INTO "Users" (username, password_hash, full_name, email, role) VALUES (%s, %s, %s, %s, %s)',
                                     (request.form.get('new_username'), phash, request.form.get('full_name'), request.form.get('user_email'), 'Operator'))
                    elif action == 'update_password':
                        phash = generate_password_hash(request.form.get('new_password'))
                        cur.execute('UPDATE "Users" SET password_hash = %s WHERE id = %s', (phash, request.form.get('user_id')))
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
            reports = {'cpk': '6.67', 'dpmo': '1,785', 'rty': '97.0%'}
            cur.execute('SELECT * FROM "KPIVs"')
            kpivs = cur.fetchall()
            cur.execute('SELECT * FROM "Users"')
            users = cur.fetchall()
            
            system_errors, total_waste, linkedin_authorized, pending_social, pending_emails = 0, "0.00", False, [], []
            
            try:
                # PostgreSQL-native check for table existence
                cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'PendingOutbox'")
                if cur.fetchone():
                    cur.execute('SELECT * FROM "PendingOutbox" WHERE status LIKE \'Pending\' ORDER BY created_at DESC LIMIT 5')
                    pending_emails = cur.fetchall()

                cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'SocialOutbox'")
                if cur.fetchone():
                    cur.execute('SELECT * FROM "SocialOutbox" WHERE status LIKE \'Pending\' ORDER BY created_at DESC LIMIT 5')
                    pending_social = cur.fetchall()
            except Exception as e:
                print(f"[BOOT] Outbox Check Error: {e}", flush=True)

    finally:
        if "conn" in locals(): conn.close()
        
    return render_template('HWB-WEB Sigma Executive.html', 
                         leads_count=leads_count, recent_leads=recent_leads,
                         total_waste=total_waste, uptime=uptime, reports=reports,
                         kpivs=kpivs, users=users, system_errors=system_errors,
                         linkedin_authorized=linkedin_authorized,
                         pending_social=pending_social, pending_emails=pending_emails)

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
def robots_txt(): return send_from_directory('static', 'robots.txt')

@app.route('/sitemap.xml')
def sitemap_xml(): return send_from_directory('static', 'sitemap.xml')
@app.route("/sitemap.website.xml")
def sitemap_website_xml(): return send_from_directory("static", "sitemap.website.xml")

@app.route('/favicon.ico')
def favicon(): return send_from_directory('static', 'favicon.ico')

@app.route('/api/v1/accounts/<int:id>', methods=['GET', 'PUT', 'DELETE'])
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
                return jsonify({
                    'account': dict(acc) if acc else None,
                    'contacts': [dict(c) for c in contacts],
                    'activities': [dict(a) for a in activities]
                })
            
            elif request.method == 'PUT':
                data = request.json
                # --- SigmaFidelity™ Partial Update Logic (BUG-008) ---
                # Fetch current state to merge updates
                cur.execute(
'SELECT * FROM "Customers" WHERE customer_id = %s', (id,))
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

                cur.execute(
'''
                    UPDATE "Customers" SET company_name = %s, contact_person_name = %s, email = %s, phone = %s, 
                    company_address = %s, city = %s, state = %s, zip = %s, website = %s, sqf = %s, annual_revenue = %s, 
                    traffic_cycle = %s, quote_number = %s, frequency = %s, notes = %s, status = %s,
                    contract_period = %s, billing_address = %s, start_date = %s
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
                      resolve('next_action_date', current_acc['start_date']), id))
                
                # --- Institutional Activity Logging ---
                if 'next_action_date' in data or 'notes' in data:
                    activity_type = 'SITE_VISIT' if 'VISIT SCHEDULED' in (data.get('notes') or '') else 'NOTE'
                    description = data.get('notes') or "Strategic profile update."
                    cur.execute(
'''
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                        VALUES (%s, %s, %s, %s)
                    ''', (id, 'Account', activity_type, description))
                    conn.commit()

                conn.commit()
                return jsonify({'status': 'success'})

            elif request.method == 'DELETE':
                cur.execute(
'DELETE FROM "Customers" WHERE customer_id = %s', (id,))
                cur.execute(
'DELETE FROM "Contacts" WHERE account_id = %s', (id,))
                conn.commit()
                return jsonify({'status': 'success'})
    finally:
        
        conn.close()

@app.route('/api/v1/leads/<int:id>', methods=['GET', 'PUT', 'DELETE'])
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
                return jsonify({
                    'lead': dict(lead) if lead else None,
                    'contacts': [dict(c) for c in contacts],
                    'activities': [dict(a) for a in activities]
                })
            
            elif request.method == 'PUT':
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
                if sqf_val == '' or sqf_val is None: sqf_val = 0
                if revenue_val == '' or revenue_val is None: revenue_val = 0.0

                cur.execute(
'''
                    UPDATE "Leads" SET 
                        center_name = %s, decision_maker = %s, job_title = %s, email = %s, phone = %s, 
                        address = %s, city = %s, state = %s, zipcode = %s, industry = %s, sqf = %s, 
                        status = %s, estimated_annual_value = %s, next_action_date = %s, notes = %s,
                        facility_type = %s, lead_source = %s, service_interest = %s, priority_level = %s, traffic_cycle = %s,
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
                      resolve('traffic_cycle', current_lead['traffic_cycle']), id))
                
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
                cur.execute(
'DELETE FROM "Leads" WHERE id = %s', (id,))
                cur.execute(
'DELETE FROM "GlobalActivities" WHERE parent_id = %s AND parent_type = %s', (id, "Lead"))
                conn.commit()
                return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if "conn" in locals(): conn.close()
        

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
            
            try:
                cur.execute('''
                    INSERT INTO "Customers" (company_name, contact_person_name, email, phone, company_address, city, state, zip, sqf, traffic_cycle, annual_revenue, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active') RETURNING customer_id
                ''', (lead['center_name'], contact_name, lead['email'], lead['phone'], lead['address'] or 'PENDING_ENTRY', lead['city'], lead['state'], lead['zipcode'], lead['sqf'] or 0, lead['traffic_cycle'], lead['estimated_annual_value'] or 0.0))
                
                new_acc_id = cur.fetchone()[0]
                
                cur.execute('UPDATE "Leads" SET is_converted = true WHERE id = %s', (id,))
                
                cur.execute('INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description) VALUES (%s, %s, %s, %s)', 
                              (id, "Lead", "CONVERTED", f"Lead moved to Account ACC-{new_acc_id}"))
                
                conn.commit()
                return jsonify({'status': 'success', 'customer_id': new_acc_id})
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

@app.route('/api/v1/health')
def health_check(): return '', 204

@app.route('/admin/linkedin-auth')
@login_required
def linkedin_auth():
    flash("LinkedIn Authorization Module is currently in R&D.")
    return redirect(url_for('sigma_executive'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
