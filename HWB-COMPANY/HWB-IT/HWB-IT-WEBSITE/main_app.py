"""
SigmaFidelity™ Enterprise Web Application Core
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
import json
import datetime
import threading
from typing import Optional
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, abort, session
from flask_compress import Compress
from flask_login import LoginManager, current_user
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from config import sys_config
from core.models.user import User
from core.services.database import get_db, sync_db_sequences
from core.services.sanitizer import clean_phone, clean_currency, clean_sqft, clean_zip, clean_email, clean_city
from core.services.search import parse_advanced_search
from core.services.email_service import transmit_email
from core.security import roles_required, log_security_violation
from core.constants import FACILITY_TYPES, LEAD_SOURCES, PRIORITY_LEVELS, CORPORATE_INFO
from core.utils import format_to_mdy
from core.services.bot_defense import generate_form_security_token
from database.schema_engine import apply_system_migrations
from blueprints import (
    telemetry_bp,
    bids_bp,
    auth_bp,
    public_bp,
    operations_bp,
    crm_api_bp,
    academy_bp,
    partner_bp,
    mobile_api_bp,
    register_blueprint_hub
)

# Institutional Secret Loading (HWB-QMS-9.5)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../.."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

app = Flask(__name__, 
            static_folder=os.path.join(BASE_DIR, 'static'), 
            template_folder=os.path.join(BASE_DIR, 'templates'))
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
Compress(app)
app.config.from_object(sys_config)
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=31)

# --- Register Enterprise Blueprints via Blueprint Hub ---
register_blueprint_hub(app, telemetry_bp)
register_blueprint_hub(app, bids_bp)
register_blueprint_hub(app, auth_bp)
register_blueprint_hub(app, public_bp)
register_blueprint_hub(app, operations_bp)
register_blueprint_hub(app, crm_api_bp)
register_blueprint_hub(app, academy_bp)
register_blueprint_hub(app, partner_bp)
register_blueprint_hub(app, mobile_api_bp)

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
    formatted = clean_phone(str(phone))
    return formatted if formatted else str(phone).strip()

app.jinja_env.filters['format_mdy'] = format_to_mdy

# --- 12-Factor Compliance: Startup Verification ---
required_configs = ['SECRET_KEY', 'DATABASE_URL', 'CLIENT_DATABASE_URL']
missing_configs = [c for c in required_configs if not app.config.get(c)]
if missing_configs:
    raise ValueError(f"FATAL: Missing required environment variables: {', '.join(missing_configs)}")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.unauthorized_handler
def unauthorized_callback():
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': 'Authentication session expired. Please reload and log in.'}), 401
    return redirect(url_for('login', next=request.url))

@login_manager.user_loader
def load_user(user_id):
    conn = None
    try:
        conn = get_db(app.config['DATABASE_URL'])
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "Users" WHERE id = %s', (user_id,))
            u = cur.fetchone()
            if u:
                role = u.get('role') or ('Executive' if u.get('username') in ['admin', 'hdominguez'] else 'Operator')
                return User(u['id'], u['username'], role, u.get('full_name'), u.get('custom_permissions'))
    except Exception as e:
        print(f"[GUARD] load_user failed: {e}", flush=True)
    finally:
        if conn:
            conn.close()
    return None

# --- Boot & Infrastructure Handshake Sequence ---
with app.app_context():
    try:
        print("[BOOT] SigmaFidelity™ High-Fidelity Startup Sequence Initiated.", flush=True)

        # Unified Async Background Startup Thread (Zero-Lock Contention, Instant Gunicorn Port Binding)
        def run_async_infrastructure_boot(db_url, seed_path):
            try:
                print("[BOOT] Unified async infrastructure boot thread started.", flush=True)
                sync_db_sequences(db_url)
                
                # 1. Schema Migrations (Runs first to establish tables and columns)
                conn = get_db(db_url)
                try:
                    apply_system_migrations(conn, db_url=db_url)
                    print("[BOOT] Database Schema Migrations & Indexes Verified & Committed.", flush=True)
                except Exception as schema_err:
                    print(f"[BOOT] Schema Migration Notice: {schema_err}", flush=True)
                finally:
                    if conn:
                        conn.close()

                # 2. Database Seeder (Runs second to guarantee table locks are completely released)
                if os.path.exists(seed_path):
                    try:
                        conn_seeder = get_db(db_url)
                        try:
                            with conn_seeder.cursor() as cur:
                                cur.execute('SELECT COUNT(*) FROM "Leads";')
                                az_lead_count = cur.fetchone()[0]
                                with open(seed_path, 'r') as sf:
                                    sdata = json.load(sf)
                                    leads_inserted = 0
                                    if az_lead_count < 1000:
                                        print(f"[BOOT] Async force-syncing leads to DB ({az_lead_count} current rows)...", flush=True)
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
                                                    l.get('id'), l.get('center_name'), l.get('lead_source'), l.get('status'),
                                                    clean_phone(l.get('phone')) or l.get('phone'),
                                                    clean_email(l.get('email')) or l.get('email'),
                                                    l.get('address'),
                                                    clean_city(l.get('city')) or l.get('city'),
                                                    l.get('state'),
                                                    clean_zip(l.get('zipcode')) or l.get('zipcode'),
                                                    l.get('sqf'), l.get('capacity'), l.get('estimated_annual_value'), l.get('priority_level'), l.get('facility_type'), l.get('decision_maker'),
                                                    l.get('job_title'), l.get('traffic_cycle'), l.get('service_interest'), l.get('next_action_date'), l.get('is_dnc', False), l.get('is_converted', False), l.get('input_date')
                                                ))
                                                leads_inserted += 1
                                                if idx % 500 == 0:
                                                    conn_seeder.commit()
                                            except Exception:
                                                conn_seeder.rollback()
                                        conn_seeder.commit()
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
                                        except Exception:
                                            pass
                                    
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
                                        except Exception:
                                            pass
                                    
                                    conn_seeder.commit()
                                    print(f"[BOOT] Async Automated Azure Data Ingestion Completed ({leads_inserted} leads processed)!", flush=True)
                        except Exception as se:
                            conn_seeder.rollback()
                            print(f"[BOOT] Async Seeder Warning: {se}", flush=True)
                        finally:
                            conn_seeder.close()
                    except Exception as thread_err:
                        print(f"[BOOT] Async Seeder Thread Error: {thread_err}", flush=True)

                # 3. Autonomous Inbound GC / Institutional Bids Initial Sync
                try:
                    from scripts.gc_bids_sync import sync_inbound_graph_bids
                    conn_sync = get_db(db_url)
                    try:
                        sync_inbound_graph_bids(conn_sync)
                    finally:
                        conn_sync.close()
                except Exception as sync_err:
                    print(f"[BOOT] Initial Inbound Deal Sync Notice: {sync_err}", flush=True)

                print("[BOOT] Infrastructure Handshake Complete.", flush=True)
            except Exception as e:
                print(f"[BOOT] Startup Handshake Warning: {e}", flush=True)

        def run_autonomous_deal_sync_daemon(db_url):
            import time
            while True:
                time.sleep(900)  # Check every 15 minutes
                try:
                    from scripts.gc_bids_sync import sync_inbound_graph_bids
                    conn_loop = get_db(db_url)
                    try:
                        sync_inbound_graph_bids(conn_loop)
                    finally:
                        conn_loop.close()
                except Exception as loop_err:
                    print(f"[DEAL SYNC DAEMON] Error: {loop_err}", flush=True)

        seed_path = os.path.join(os.path.dirname(__file__), 'scripts', 'seed_data.json')
        threading.Thread(target=run_async_infrastructure_boot, args=(app.config['DATABASE_URL'], seed_path), daemon=True).start()
        threading.Thread(target=run_autonomous_deal_sync_daemon, args=(app.config['DATABASE_URL'],), daemon=True).start()
    except Exception as e:
        print(f"[BOOT] Startup Handshake Warning: {e}", flush=True)

# --- Enterprise RBAC Request Gatekeeper (Poka-Yoke Fail-Safe Defaults) ---
@app.before_request
def enforce_enterprise_role_quarantine():
    """Centralized Enterprise Request Gatekeeper (Poka-Yoke Fail-Safe Defaults)."""
    if request.path.startswith('/static') or request.path in ['/heartbeat', '/favicon.ico', '/robots.txt', '/sitemap.xml']:
        return None

    if not current_user.is_authenticated:
        return None

    path = request.path
    role = getattr(current_user, 'role', '')

    # Sales Role Scope (Option B: Leads, Accounts & Field Sales Desk)
    if role == 'Sales':
        if path == '/':
            return redirect(url_for('admin_operations', view='leads'))

        if path.startswith('/api/v1/leads/export') or path.startswith('/api/v1/accounts/export'):
            log_security_violation(current_user.id, current_user.username, role, path, request.method)
            return jsonify({'status': 'error', 'message': 'Exporting data is strictly restricted for Sales personnel.'}), 403

        if path == '/admin/operations':
            active_view = request.args.get('view', 'leads')
            if active_view not in ['leads', 'accounts']:
                log_security_violation(current_user.id, current_user.username, role, f"{path}?view={active_view}", request.method)
                flash("Restricted area. Sales access is scoped to Leads and Accounts.")
                return redirect(url_for('admin_operations', view='leads'))
            return None

        sales_whitelist = (
            '/admin/operations',
            '/admin/sales-desk',
            '/sales-desk',
            '/admin/add-lead',
            '/admin/add-account',
            '/admin/edit-lead/',
            '/api/v1/leads/',
            '/api/v1/accounts/',
            '/api/v1/activities',
            '/logout',
            '/heartbeat'
        )

        if path.startswith('/admin') and not any(path.startswith(w) for w in sales_whitelist):
            log_security_violation(current_user.id, current_user.username, role, path, request.method)
            flash("Restricted area. Sales access is limited to Leads, Accounts, and Field Sales Desk.")
            return redirect(url_for('admin_operations', view='leads'))

    # Executive & Admin Sensitive Zone Protection
    if path.startswith('/admin/executive'):
        if role not in ['Executive', 'Admin']:
            log_security_violation(current_user.id, current_user.username, role, path, request.method)
            abort(403)

    # Master Repository & Lab Zone Protection
    if path in ['/admin/master', '/admin/lab']:
        if role not in ['Executive', 'Admin', 'Manager']:
            log_security_violation(current_user.id, current_user.username, role, path, request.method)
            abort(403)

    return None

# --- Enterprise Navigation Context Processor ---
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
    is_mgmt = role in ['Executive', 'Admin', 'Manager', 'Operator']
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

@app.context_processor
def inject_corporate_info():
    """Injects verified empirical corporate identity across all templates."""
    return {'corp_info': CORPORATE_INFO}

@app.context_processor
def inject_security_utilities():
    """Injects enterprise bot defense and form security token generator across all templates."""
    return {
        'get_form_security_token': generate_form_security_token
    }

# --- Standardized Error Handlers ---
@app.errorhandler(500)
def internal_error(error):
    return "The system is currently busy or updating. Please refresh in a moment.", 500

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e
    print(f"[FATAL] System Exception: {e}", flush=True)
    return "A system error occurred. Our team has been notified.", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
