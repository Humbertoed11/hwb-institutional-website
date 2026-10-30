"""
SigmaFidelity™ Enterprise Web Application Core
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
import json
import time
import hashlib
import datetime
import threading
from typing import Optional
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, abort, session
from flask_compress import Compress
from flask_login import LoginManager, current_user, logout_user
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

# Mask backend server signature to prevent gunicorn disclosure (SO-COM-001-DIR-05)
try:
    import gunicorn
    gunicorn.SERVER_SOFTWARE = 'Cloudflare'
    from gunicorn.http import wsgi
    wsgi.SERVER = 'Cloudflare'
except Exception:
    pass

from config import sys_config
from core.models.user import User
from core.services.database import get_db, sync_db_sequences
from core.services.sanitizer import clean_phone, clean_currency, clean_sqft, clean_zip, clean_email, clean_city
from core.services.search import parse_advanced_search
from core.services.email_service import transmit_email
from core.security import roles_required, log_security_violation
from core.constants import FACILITY_TYPES, LEAD_SOURCES, PRIORITY_LEVELS, CORPORATE_INFO, MODULE_REGISTRY
from core.utils import format_to_mdy
from core.services.bot_defense import generate_form_security_token
from core.services.version_service import get_version_info
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
    accounting_bp,
    register_blueprint_hub
)
from blueprints.ai_employee_api import ai_employee_bp

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
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 604800  # 7-day browser & edge cache for static files
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=12)
app.config['SESSION_INACTIVITY_TIMEOUT_SECONDS'] = int(os.getenv('SESSION_INACTIVITY_TIMEOUT_SECONDS', '1800'))

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
register_blueprint_hub(app, accounting_bp)
register_blueprint_hub(app, ai_employee_bp)

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

# --- Enterprise Automatic Static Asset Content Fingerprinting (BUG-159) ---
_STATIC_ASSET_HASH_CACHE = {}

def _get_static_asset_fingerprint(filename: str) -> str:
    """Computes an 8-character SHA-256 content fingerprint for any static file on disk."""
    if not filename:
        return "v1"
    full_path = os.path.join(app.static_folder, filename)
    try:
        mtime = os.path.getmtime(full_path)
        cached = _STATIC_ASSET_HASH_CACHE.get(filename)
        if cached and cached[0] == mtime:
            return cached[1]
        with open(full_path, 'rb') as f:
            digest = hashlib.sha256(f.read()).hexdigest()[:8]
        _STATIC_ASSET_HASH_CACHE[filename] = (mtime, digest)
        return digest
    except Exception:
        return "v1"

@app.url_defaults
def inject_static_asset_fingerprint(endpoint, values):
    """Automatically appends ?f=<sha256_8> to all url_for('static', filename=...) URLs."""
    if endpoint == 'static' and values and 'filename' in values and 'f' not in values:
        values['f'] = _get_static_asset_fingerprint(values['filename'])


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
                if u.get('status') and u.get('status') != 'Active':
                    return None
                role = u.get('role') or ('Executive' if u.get('username') in ['admin', 'hdominguez'] else 'Operator')
                return User(u['id'], u['username'], role, u.get('full_name'), u.get('custom_permissions'), email=u.get('email'))
    except Exception as e:
        print(f"[GUARD] load_user failed: {e}", flush=True)
    finally:
        if conn:
            conn.close()
    return None

@app.before_request
def enforce_session_inactivity_timeout():
    """
    SigmaFidelity™ Enterprise Inactivity Timeout Guard (SOC 2 / ISO 27001).
    Terminates authenticated sessions after 30 minutes of user inactivity.
    Automated health checks and machine pings are validated for timeout but
    STRICTLY EXEMPT from resetting the human activity timer (BUG-117).
    """
    # 1. Skip completely unauthenticated static assets
    if request.path.startswith('/static') or request.endpoint == 'static':
        return

    # Machine polling endpoints that must never reset the inactivity clock
    MACHINE_POLLING_PATHS = {'/health', '/api/v1/health', '/heartbeat', '/api/v1/db-audit'}
    is_machine_ping = request.path in MACHINE_POLLING_PATHS

    if current_user.is_authenticated:
        now = time.time()
        last_active = session.get('last_activity')
        inactivity_limit = app.config.get('SESSION_INACTIVITY_TIMEOUT_SECONDS', 1800)

        # Initialize last_activity if missing; machine pings do not initialize user activity
        if last_active is None:
            if not is_machine_ping:
                session['last_activity'] = now
            return

        if now - last_active > inactivity_limit:
            inactive_mins = round((now - last_active) / 60, 1)
            from core.services.security_logger import log_security_event
            log_security_event(
                event_category='AUTH',
                event_action='SESSION_TIMEOUT',
                severity='INFO',
                user_id=getattr(current_user, 'id', None),
                username=getattr(current_user, 'username', 'Unknown'),
                user_role=getattr(current_user, 'role', 'Unknown'),
                status_code=401,
                details={'inactive_minutes': inactive_mins, 'threshold_seconds': inactivity_limit, 'trigger_path': request.path}
            )

            logout_user()
            session.clear()

            if request.path.startswith('/api/') or is_machine_ping:
                return jsonify({
                    'status': 'error',
                    'reason': 'SESSION_TIMEOUT',
                    'message': f'Your session expired due to {inactive_mins} minutes of inactivity. Please log in again.'
                }), 401

            flash('Your session expired due to inactivity. Please log in again to continue.')
            return redirect(url_for('auth.login', next=request.path, reason='inactivity'))

        # Only human user interactions update the activity timestamp
        if not is_machine_ping:
            session['last_activity'] = now

_orig_save_session = app.session_interface.save_session
def _edge_safe_save_session(app_obj, sess, response):
    if getattr(request, '_is_anonymous_public_cacheable', False) and not sess.modified:
        if 'Vary' in response.headers:
            vary_tokens = [v.strip() for v in response.headers['Vary'].split(',') if v.strip().lower() != 'cookie']
            if vary_tokens:
                response.headers['Vary'] = ', '.join(vary_tokens)
            else:
                del response.headers['Vary']
        return
    return _orig_save_session(app_obj, sess, response)
app.session_interface.save_session = _edge_safe_save_session

@app.after_request
def apply_application_security_headers(response):
    """
    Direct Application Security Headers (SO-COM-001-DIR-05 & HWB-QMS-11.14).
    Enforces HSTS, MIME sniffing protection, clickjacking defense, referrer policy,
    masks backend server headers, and enforces Split Cloudflare Edge Caching.
    """
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()'
    response.headers['Content-Security-Policy'] = "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval'; img-src 'self' https: data: blob:;"
    response.headers['Server'] = 'Cloudflare'
    if request.headers.get('Sec-GPC') == '1' or request.headers.get('DNT') == '1':
        response.headers['X-GPC-Status'] = 'Honored'

    # AI Search Crawler Telemetry (BUG-151: OAI-SearchBot, ChatGPT-User, GPTBot, PerplexityBot, ClaudeBot, Google-Extended, bingbot)
    ua_str = request.headers.get('User-Agent', '')
    if ua_str and not request.path.startswith('/static/'):
        for bot_token in ('OAI-SearchBot', 'ChatGPT-User', 'GPTBot', 'PerplexityBot', 'ClaudeBot', 'Google-Extended', 'Applebot-Extended', 'bingbot'):
            if bot_token.lower() in ua_str.lower():
                try:
                    from core.services.security_logger import log_security_event
                    log_security_event(
                        event_category='AI_CRAWLER_TELEMETRY',
                        event_action='AI_BOT_PAGE_CRAWLED',
                        severity='INFO',
                        status_code=response.status_code,
                        details={'bot': bot_token, 'path': request.path, 'ua': ua_str[:180]}
                    )
                except Exception:
                    pass
                break

    # Static Assets: 7-day immutable edge caching (Cloudflare absorbs 100% of asset requests)
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=604800, immutable'
        if not session.modified:
            request._is_anonymous_public_cacheable = True
        if 'Vary' in response.headers:
            vary_tokens = [v.strip() for v in response.headers['Vary'].split(',') if v.strip().lower() != 'cookie']
            if vary_tokens:
                response.headers['Vary'] = ', '.join(vary_tokens)
            else:
                del response.headers['Vary']
    # Public Marketing Pages: Split Cloudflare Edge Caching for anonymous guests (HWB-QMS-11.14)
    elif (
        request.method in ('GET', 'HEAD')
        and response.status_code == 200
        and not session.modified
        and not session.get('user_id')
        and not session.get('_user_id')
        and not current_user.is_authenticated
        and not request.path.startswith(('/admin', '/api', '/auth', '/sales-desk', '/login', '/logout', '/partner', '/academy', '/manual'))
    ):
        response.headers['Cache-Control'] = 'public, max-age=300, s-maxage=3600, stale-while-revalidate=86400'
        request._is_anonymous_public_cacheable = True
        response.headers.pop('Set-Cookie', None)
        if 'Vary' in response.headers:
            vary_tokens = [v.strip() for v in response.headers['Vary'].split(',') if v.strip().lower() != 'cookie']
            if vary_tokens:
                response.headers['Vary'] = ', '.join(vary_tokens)
            else:
                del response.headers['Vary']
    # Backoffice Desks, APIs, and Auth Routes: Strict zero-cache protection
    elif request.path.startswith(('/admin', '/api', '/auth', '/sales-desk', '/login', '/logout')):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
        response.headers['Pragma'] = 'no-cache'

    # Permanent Enterprise Responsive & Adaptive Table Guardrail (BUG-137):
    # Guarantees that any future HTML page or standalone module added to the website
    # automatically loads sigma_responsive_engine.js even if a template omits the script tag.
    if (
        response.mimetype == 'text/html'
        and not response.direct_passthrough
        and response.status_code == 200
        and not request.path.startswith('/api/')
    ):
        try:
            body_bytes = response.get_data()
            if b'</body>' in body_bytes:
                injected = False
                if b'sigma_responsive_engine.js' not in body_bytes:
                    body_bytes = body_bytes.replace(
                        b'</body>',
                        b'<script src="/static/js/sigma_responsive_engine.js" defer></script>\n</body>',
                        1,
                    )
                    injected = True
                if b'sigma_input_masks.js' not in body_bytes:
                    body_bytes = body_bytes.replace(
                        b'</body>',
                        b'<script src="/static/js/sigma_input_masks.js" defer></script>\n</body>',
                        1,
                    )
                    injected = True
                if (
                    b'id="hwb-cookie-banner"' not in body_bytes
                    and not request.path.startswith(('/admin', '/api', '/sales-desk'))
                ):
                    cookie_banner_snippet = (
                        b'<aside id="hwb-cookie-banner" class="sigma-consent-banner" '
                        b'style="display:none;position:fixed;bottom:0;left:0;width:100%;background:#0f172a;color:#f8fafc;'
                        b'padding:1rem 1.5rem;z-index:99999;box-shadow:0 -4px 20px rgba(0,0,0,0.3);'
                        b'justify-content:space-between;align-items:center;gap:1rem;font-size:0.88rem;'
                        b'border-top:1px solid rgba(255,255,255,0.1);box-sizing:border-box;" '
                        b'role="dialog" aria-label="Cookie and Privacy Consent">'
                        b'<div><strong>Privacy Choices:</strong> We use essential cookies to maintain system security. '
                        b'You can accept optional analytics and session replay, or continue with essential cookies only.</div>'
                        b'<div style="display:flex;align-items:center;gap:0.65rem;flex-shrink:0;">'
                        b'<button type="button" onclick="acceptCookieConsent()" '
                        b'style="padding:0.45rem 0.95rem;border-radius:4px;font-weight:700;font-size:0.8rem;cursor:pointer;border:none;background:#00796b;color:#ffffff;">Accept All</button>'
                        b'<button type="button" onclick="declineCookieConsent()" '
                        b'style="padding:0.45rem 0.95rem;border-radius:4px;font-weight:700;font-size:0.8rem;cursor:pointer;border:none;background:rgba(255,255,255,0.15);color:#f8fafc;">Essential Only</button>'
                        b'<a href="/privacy-policy#opt-out" style="color:#94a3b8;text-decoration:underline;font-size:0.78rem;margin-left:0.35rem;">Do Not Sell My Info</a>'
                        b'</div></aside>'
                        b'<script>'
                        b'if(typeof acceptCookieConsent!=="function"){'
                        b'if(navigator.globalPrivacyControl===true){localStorage.setItem("hwb_telemetry_consent","declined");localStorage.setItem("sigma_cookie_consent","rejected");}'
                        b'window.acceptCookieConsent=function(){localStorage.setItem("hwb_telemetry_consent","granted");var b=document.getElementById("hwb-cookie-banner");if(b)b.style.display="none";};'
                        b'window.declineCookieConsent=function(){localStorage.setItem("hwb_telemetry_consent","declined");var b=document.getElementById("hwb-cookie-banner");if(b)b.style.display="none";};'
                        b'document.addEventListener("DOMContentLoaded",function(){if(navigator.globalPrivacyControl===true){return;}if(!localStorage.getItem("hwb_telemetry_consent")){var b=document.getElementById("hwb-cookie-banner");if(b)b.style.display="flex";}});'
                        b'}'
                        b'</script>\n</body>'
                    )
                    body_bytes = body_bytes.replace(b'</body>', cookie_banner_snippet, 1)
                    injected = True
                if injected:
                    response.set_data(body_bytes)
        except Exception:
            pass

    return response

# --- Boot & Infrastructure Handshake Sequence (HWB-QMS-11.14 Single-Execution Guard) ---
_BOOT_LOCK_FD = None
with app.app_context():
    try:
        print("[BOOT] SigmaFidelity™ High-Fidelity Startup Sequence Initiated.", flush=True)

        # Unified Async Background Startup Thread (Zero-Lock Contention, Instant Gunicorn Port Binding)
        def run_async_infrastructure_boot(db_url, seed_path):
            try:
                time.sleep(1.0)  # Allow preloaded Gunicorn worker fork to complete before opening DB pool sockets
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
                                                        status = CASE
                                                            WHEN "Leads".status IN ('Do Not Call (DNC)', 'Unsubscribed')
                                                                 OR COALESCE("Leads".is_dnc, FALSE) = TRUE
                                                                 OR UPPER(COALESCE("Leads".email_hygiene_status, '')) = 'DO_NOT_EMAIL'
                                                                 OR EXISTS (SELECT 1 FROM "EmailSuppressionList" esl WHERE esl.email_lower = LOWER(TRIM(COALESCE("Leads".email, ''))))
                                                            THEN "Leads".status
                                                            ELSE EXCLUDED.status
                                                        END,
                                                        phone = EXCLUDED.phone,
                                                        email = EXCLUDED.email,
                                                        sqf = EXCLUDED.sqf,
                                                        capacity = EXCLUDED.capacity,
                                                        estimated_annual_value = EXCLUDED.estimated_annual_value,
                                                        is_dnc = CASE
                                                            WHEN COALESCE("Leads".is_dnc, FALSE) = TRUE OR "Leads".status = 'Do Not Call (DNC)'
                                                            THEN TRUE
                                                            ELSE EXCLUDED.is_dnc
                                                        END,
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
                                    
                                    # Seed Users Table (Preserve live password_hash and force_pwd_reset state on conflict)
                                    for u in sdata.get('users', []):
                                        try:
                                            cur.execute('''
                                                INSERT INTO "Users" (id, username, password_hash, full_name, email, role, status, force_pwd_reset, custom_permissions)
                                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                                ON CONFLICT (id) DO UPDATE SET
                                                    username = EXCLUDED.username,
                                                    password_hash = COALESCE(NULLIF("Users".password_hash, ''), EXCLUDED.password_hash),
                                                    full_name = EXCLUDED.full_name,
                                                    email = EXCLUDED.email,
                                                    role = EXCLUDED.role,
                                                    status = COALESCE("Users".status, EXCLUDED.status),
                                                    force_pwd_reset = COALESCE("Users".force_pwd_reset, EXCLUDED.force_pwd_reset),
                                                    custom_permissions = COALESCE("Users".custom_permissions, EXCLUDED.custom_permissions);
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
        try:
            import fcntl
            _BOOT_LOCK_FD = open('/tmp/hwb_enterprise_boot.lock', 'w')
            fcntl.flock(_BOOT_LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _BOOT_LOCK_FD.write(str(os.getpid()))
            _BOOT_LOCK_FD.flush()
            threading.Thread(target=run_async_infrastructure_boot, args=(app.config['DATABASE_URL'], seed_path), daemon=True).start()
            threading.Thread(target=run_autonomous_deal_sync_daemon, args=(app.config['DATABASE_URL'],), daemon=True).start()
        except (BlockingIOError, IOError):
            print(f"[BOOT] Single-execution boot lock held by primary process; worker PID {os.getpid()} skipping duplicate boot threads (0ms).", flush=True)
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
            return redirect(current_user.get_default_landing_url())

        if path.startswith('/api/v1/leads/export') or path.startswith('/api/v1/accounts/export'):
            log_security_violation(current_user.id, current_user.username, role, path, request.method)
            return jsonify({'status': 'error', 'message': 'Exporting data is strictly restricted for Sales personnel.'}), 403

        if path == '/admin/operations':
            active_view = request.args.get('view', 'leads')
            from blueprints.operations import VIEW_AUTHORIZATION_MAP
            req_mod = VIEW_AUTHORIZATION_MAP.get(active_view, active_view)
            if not current_user.has_permission(req_mod, 'view'):
                log_security_violation(current_user.id, current_user.username, role, f"{path}?view={active_view}", request.method)
                flash("Restricted area. Redirected to your primary workspace.")
                return redirect(current_user.get_default_landing_url())
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
            flash("Restricted area. Redirected to your primary workspace.")
            return redirect(current_user.get_default_landing_url())

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

    has_master_qms = is_exec
    if not has_master_qms:
        custom_perms = getattr(current_user, 'custom_permissions', {})
        if isinstance(custom_perms, str):
            try:
                custom_perms = json.loads(custom_perms)
            except Exception:
                custom_perms = {}
        if isinstance(custom_perms, dict):
            qms_perm = custom_perms.get('qms')
            if isinstance(qms_perm, dict):
                has_master_qms = bool(qms_perm.get('master') or qms_perm.get('all') or qms_perm.get('entire'))
            elif isinstance(qms_perm, (list, tuple, set)):
                has_master_qms = any(k in qms_perm for k in ['master', 'all', 'entire'])

    return {
        'has_master_qms': has_master_qms,
        'nav_access': {
            'is_authenticated': True,
            'can_view_command_hub': is_mgmt,
            'is_executive': is_exec,
            'is_manager': is_mgmt,
            'is_sales': is_sales,
            'has_master_qms': has_master_qms,
            'role_name': role,
            'sales_desk_url': url_for('sales_desk') if (is_sales or is_mgmt) else None
        }
    }

@app.context_processor
def inject_corporate_info():
    """Injects verified empirical corporate identity across all templates."""
    return {'corp_info': CORPORATE_INFO}

@app.context_processor
def inject_version_telemetry():
    """Injects authoritative application version, git commit, and deployment environment."""
    return {'app_version_info': get_version_info()}

@app.context_processor
def inject_security_utilities():
    """Injects enterprise bot defense and form security token generator across all templates."""
    return {
        'get_form_security_token': generate_form_security_token
    }

@app.context_processor
def inject_module_registry():
    """Injects authoritative single-word module titles and 4-verb action descriptors."""
    def get_module_meta(view_name):
        return MODULE_REGISTRY.get(view_name, {
            "title": (view_name or "Operations").replace("_", " ").title(),
            "action_phrase": "Manage operations, review records, and maintain standards.",
            "sop_reference": "HWB-QMS-7.6",
            "icon": "fas fa-cube"
        })
    return {
        'MODULE_REGISTRY': MODULE_REGISTRY,
        'get_module_meta': get_module_meta
    }

@app.context_processor
def inject_app_manual_context():
    """Injects contextual active workspace topic, chapter anchor, and deep-link URL for the App Manual."""
    active_view = request.args.get('view', '').lower().strip()
    endpoint = request.endpoint or ''
    path = request.path.lower()

    topic = 'general'
    chapter = 'chapter-1'

    if active_view in ['leads', 'accounts'] or endpoint in ['sales_desk', 'admin_sales_desk'] or 'sales-desk' in path:
        topic = 'leads'
        chapter = 'chapter-2'
    elif active_view in ['construction_bids', 'general_contractors', 'institutional_bids', 'programs'] or endpoint == 'calculator' or 'calculator' in path:
        topic = 'bids'
        chapter = 'chapter-3'
    elif active_view == 'marketing':
        topic = 'outreach'
        chapter = 'chapter-4'
    elif active_view in ['workforce', 'safety', 'monitor', 'dispatch', 'scope'] or 'mobile' in path:
        topic = 'cleaning'
        chapter = 'chapter-5'
    elif active_view in ['it_department', 'it_telemetry'] or endpoint in ['sigma_executive', 'sigmajan_lab', 'admin_master'] or any(p in path for p in ['executive', 'lab', 'master']):
        topic = 'users'
        chapter = 'chapter-6'

    manual_url = f"/manual/app?topic={topic}#{chapter}"

    return {
        'active_manual_topic': topic,
        'active_manual_chapter': chapter,
        'active_manual_url': manual_url
    }

# --- Standardized Error Handlers ---
@app.errorhandler(403)
def forbidden_error(e):
    if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json' or request.is_json:
        return jsonify({
            'status': 'error',
            'error': 'Forbidden',
            'message': 'Access restricted. You do not have permission to view this resource.',
            'status_code': 403
        }), 403
    return render_template('403.html', error_description=getattr(e, 'description', None)), 403

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
