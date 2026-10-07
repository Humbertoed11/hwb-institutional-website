"""
SigmaFidelity™ Public Marketing, Service Directory, and Quote Engine Blueprint
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Lauri Tells (VP of Marketing)
"""

import os
import re
import json
import requests
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, send_from_directory, jsonify
from werkzeug.exceptions import HTTPException
from flask_login import login_required, current_user
from core.services.database import get_db
from core.services.sanitizer import clean_phone, clean_email
from core.services.rate_limiter import rate_limit
from core.services.bot_defense import evaluate_bot_defense
from core.services.task_queue import task_queue
from core.services.notification_service import dispatch_lead_notifications
from core.services.security_logger import log_security_event, extract_client_ip

public_bp = Blueprint('public', __name__)

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

@public_bp.route('/', endpoint='index')
def index():
    return render_template('index.html')

@public_bp.route('/about', endpoint='about')
def about():
    return render_template('about.html')

@public_bp.route('/design-system', endpoint='design_system')
@public_bp.route('/design-systems')
def design_system():
    return render_template('institutional_design_system.html')

@public_bp.route('/services/janitorial', endpoint='services_janitorial')
def services_janitorial():
    return render_template('janitorial.html')

@public_bp.route('/services/commercial', endpoint='services_commercial')
def services_commercial():
    return render_template('commercial.html')

@public_bp.route('/services/industrial', endpoint='services_industrial')
def services_industrial():
    return render_template('industrial.html')

@public_bp.route('/services/construction', endpoint='services_construction')
def services_construction():
    return render_template('construction.html')

@public_bp.route('/compliance', endpoint='compliance')
def compliance():
    return render_template('compliance.html')

@public_bp.route('/ehsq', endpoint='ehsq')
def ehsq():
    return render_template('ehsq.html')

@public_bp.route('/methodology', endpoint='methodology')
def methodology():
    return render_template('methodology.html')

@public_bp.route('/privacy-policy', endpoint='privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@public_bp.route('/accessibility', endpoint='accessibility_statement')
@public_bp.route('/accessibility.html')
def accessibility_statement():
    """Official ADA Title III & WCAG 2.2 AA Accessibility Statement."""
    return render_template('accessibility.html')

@public_bp.route('/contact', endpoint='contact')
@public_bp.route('/contact-us')
def contact():
    """Contact entry point routing to commercial quote intake."""
    return redirect(url_for('public.get_quote'))

@public_bp.route('/terms', endpoint='terms_of_service')
@public_bp.route('/terms-of-service')
def terms_of_service():
    """Official SigmaFidelity™ Terms of Service view (Texas Collin County Jurisdiction & SOC 2 PI1.1)."""
    return render_template('terms.html')

@public_bp.route('/unsubscribe/<tracking_token>', methods=['GET', 'POST'], endpoint='unsubscribe_token')
@public_bp.route('/unsubscribe', methods=['GET', 'POST'], endpoint='unsubscribe_direct')
def unsubscribe(tracking_token=None):
    """
    CAN-SPAM Act (15 U.S.C. § 7701), Texas Anti-Spam (Tex. Bus. & Com. Code § 321),
    and SOC 2 Privacy Criteria P2.1 (Choice & Consent) automated opt-out handler.
    Permanently marks lead as Do Not Call (DNC) / Unsubscribed, cancels pending outbox messages,
    and displays enterprise compliance confirmation.
    """
    conn = None
    audit_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    if request.method == 'POST':
        raw_email = request.form.get('email', '').strip().lower()
        if not raw_email or '@' not in raw_email:
            return render_template('unsubscribe_success.html', unsubscribed=False, error_msg="Please provide a valid corporate email address.")
        
        try:
            conn = get_db(current_app.config['DATABASE_URL'])
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE "Leads"
                    SET is_dnc = TRUE, status = 'Do Not Call (DNC)', updated_at = CURRENT_DATE
                    WHERE LOWER(email) = %s;
                ''', (raw_email,))
                
                cur.execute('''
                    UPDATE "CampaignRecipients"
                    SET status = 'UNSUBSCRIBED', updated_at = CURRENT_TIMESTAMP
                    WHERE LOWER(recipient_email) = %s;
                ''', (raw_email,))
                
                cur.execute('''
                    UPDATE "PendingOutbox"
                    SET status = 'CANCELLED'
                    WHERE LOWER(recipient) = %s AND status = 'PENDING';
                ''', (raw_email,))
            conn.commit()
        except Exception as e:
            if conn:
                try: conn.rollback()
                except Exception: pass
            current_app.logger.error(f"[UNSUBSCRIBE DIRECT ERROR] {e}")
        finally:
            if conn:
                try: conn.close()
                except Exception: pass
                
        return render_template('unsubscribe_success.html', 
                               unsubscribed=True, 
                               email=raw_email, 
                               audit_timestamp=audit_ts, 
                               token_ref="MANUAL_DIRECT_FORM")
                               
    if tracking_token:
        found_email = None
        lead_id = None
        try:
            conn = get_db(current_app.config['DATABASE_URL'])
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT id, lead_id, recipient_email, facility_name
                    FROM "CampaignRecipients"
                    WHERE tracking_token = %s;
                ''', (tracking_token,))
                recip_row = cur.fetchone()
                
                if recip_row:
                    found_email = recip_row['recipient_email'] if isinstance(recip_row, dict) else recip_row[2]
                    lead_id = recip_row['lead_id'] if isinstance(recip_row, dict) else recip_row[1]
                    
                    cur.execute('''
                        UPDATE "CampaignRecipients"
                        SET status = 'UNSUBSCRIBED', updated_at = CURRENT_TIMESTAMP
                        WHERE tracking_token = %s OR LOWER(recipient_email) = LOWER(%s);
                    ''', (tracking_token, found_email))
                else:
                    cur.execute('''
                        SELECT id, recipient, recipient_id
                        FROM "PendingOutbox"
                        WHERE tracking_token = %s;
                    ''', (tracking_token,))
                    outbox_row = cur.fetchone()
                    if outbox_row:
                        found_email = outbox_row['recipient'] if isinstance(outbox_row, dict) else outbox_row[1]
                        lead_id = outbox_row['recipient_id'] if isinstance(outbox_row, dict) else outbox_row[2]
                
                if found_email:
                    cur.execute('''
                        UPDATE "Leads"
                        SET is_dnc = TRUE, 
                            status = 'Unsubscribed', 
                            notes = CASE 
                                WHEN notes IS NULL OR TRIM(notes) = '' THEN 
                                    '[' || TO_CHAR(CURRENT_DATE, 'MM/DD/YYYY') || '] Contact clicked email unsubscribe link. Suppressed from all future marketing.'
                                ELSE 
                                    notes || E'\n[' || TO_CHAR(CURRENT_DATE, 'MM/DD/YYYY') || '] Contact clicked email unsubscribe link. Suppressed from all future marketing.'
                            END,
                            updated_at = CURRENT_DATE
                        WHERE LOWER(email) = LOWER(%s) OR (id = %s AND %s IS NOT NULL);
                    ''', (found_email, lead_id, lead_id))
                    
                    cur.execute('''
                        UPDATE "PendingOutbox"
                        SET status = 'CANCELLED'
                        WHERE (LOWER(recipient) = LOWER(%s) OR tracking_token = %s) AND status = 'PENDING';
                    ''', (found_email, tracking_token))
                    
                    if lead_id:
                        cur.execute('''
                            INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description, timestamp)
                            VALUES (%s, 'Lead', 'Unsubscribed', %s, CURRENT_TIMESTAMP);
                        ''', (lead_id, f"Lead opted out via 1-click unsubscribe token ({tracking_token[:8]}...). Suppressed from all future campaigns."))
                        
            if conn:
                conn.commit()
        except Exception as e:
            if conn:
                try: conn.rollback()
                except Exception: pass
            current_app.logger.error(f"[UNSUBSCRIBE TOKEN ERROR] {e}")
        finally:
            if conn:
                try: conn.close()
                except Exception: pass

        if found_email:
            return render_template('unsubscribe_success.html',
                                   unsubscribed=True,
                                   email=found_email,
                                   audit_timestamp=audit_ts,
                                   token_ref=tracking_token[:16] + "...",
                                   tracking_token=tracking_token)

    return render_template('unsubscribe_success.html', unsubscribed=False, error_msg=None)


@public_bp.route('/api/v1/unsubscribe/reason', methods=['POST'])
def api_unsubscribe_reason():
    """
    Captures post-unsubscribe intelligence survey without server/proxy false positives.
    Records whether facility uses in-house employees, has active vendor contract, or is not interested.
    Supports both tokenized 1-click links and direct manual form submissions.
    """
    data = request.get_json(silent=True) or request.form
    token = (data.get('token') or '').strip()
    email_val = (data.get('email') or '').strip().lower()
    reason = (data.get('reason') or '').strip()

    if not reason or (not token and not email_val):
        return jsonify({'status': 'error', 'message': 'Missing token/email or reason'}), 400

    conn = None
    try:
        conn = get_db(current_app.config['DATABASE_URL'])
        with conn.cursor() as cur:
            lead_id = None
            email = email_val

            if token:
                cur.execute('''
                    SELECT lead_id, recipient_email FROM "CampaignRecipients" WHERE tracking_token = %s
                    UNION
                    SELECT recipient_id, recipient FROM "PendingOutbox" WHERE tracking_token = %s
                    LIMIT 1;
                ''', (token, token))
                row = cur.fetchone()
                if row:
                    lead_id = row['lead_id'] if isinstance(row, dict) else row[0]
                    email = (row['recipient_email'] if isinstance(row, dict) else row[1]) or email_val

            if not lead_id and email:
                cur.execute('SELECT id FROM "Leads" WHERE LOWER(email) = LOWER(%s) LIMIT 1;', (email,))
                lead_row = cur.fetchone()
                if lead_row:
                    lead_id = lead_row['id'] if isinstance(lead_row, dict) else lead_row[0]

            reason_desc = ""
            delivery_model = None

            if reason == 'employees':
                delivery_model = 'IN_HOUSE_STAFF'
                reason_desc = "Uses in-house employees / staff (Corporate operational model)"
            elif reason == 'contract':
                delivery_model = 'OUTSOURCED_CONTRACT'
                reason_desc = "Has active contract with cleaning company (Future requote target)"
            elif reason == 'not_interested':
                reason_desc = "Not interested in commercial cleaning services"
            else:
                reason_desc = f"Other: {reason}"

            if lead_id or email:
                cur.execute('''
                    UPDATE "Leads"
                    SET cleaning_delivery_model = COALESCE(%s, cleaning_delivery_model),
                        notes = CASE 
                            WHEN notes IS NULL OR TRIM(notes) = '' THEN 
                                '[' || TO_CHAR(CURRENT_DATE, 'MM/DD/YYYY') || '] Unsubscribe Feedback: ' || %s
                            ELSE 
                                notes || E'\n[' || TO_CHAR(CURRENT_DATE, 'MM/DD/YYYY') || '] Unsubscribe Feedback: ' || %s
                        END,
                        updated_at = CURRENT_DATE
                    WHERE (id = %s AND %s IS NOT NULL) OR LOWER(email) = LOWER(%s);
                ''', (delivery_model, reason_desc, reason_desc, lead_id, lead_id, email))

                if lead_id:
                    cur.execute('''
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description, timestamp)
                        VALUES (%s, 'Lead', 'Unsubscribe Reason Survey', %s, CURRENT_TIMESTAMP);
                    ''', (lead_id, f"Opt-Out Feedback Recorded: {reason_desc}"))

            conn.commit()
            return jsonify({'status': 'success', 'message': 'Preference recorded successfully.'})
    except Exception as e:
        if conn:
            try: conn.rollback()
            except Exception: pass
        current_app.logger.error(f"[UNSUBSCRIBE REASON ERROR] {e}")
        return jsonify({'status': 'error', 'message': 'Failed to save reason'}), 500
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


@public_bp.route('/capability-statement', endpoint='capability_statement')
@public_bp.route('/capability')
def capability_statement():
    """Official 2026 Single-Sheet Capability Statement view & PDF printout."""
    return render_template('capability_statement.html')

@public_bp.route('/signature', endpoint='signature_vault')
@public_bp.route('/my-signature')
@login_required
def signature_vault():
    """Official 2026 Executive Email Signature portal for Outlook & mobile clients (SOC 2 Protected)."""
    return render_template('executive_signature.html')

@public_bp.route('/manual', endpoint='manual_index')
@login_required
def manual_index():
    """
    Controlled Operating Manual Index (SOC 2 & ISO 9001 Protected).
    Enforces authentication and role-based department visibility.
    """
    user_role = getattr(current_user, 'role', 'Operator')
    user_name = getattr(current_user, 'username', '')
    is_exec = user_role in ['Executive', 'Admin'] or user_name == 'admin'

    # Granular ABAC: Non-executives must have explicit qms view permission
    if not is_exec and hasattr(current_user, 'has_permission') and not current_user.has_permission('qms', 'view'):
        log_security_event(
            event_category='ACCESS_CONTROL',
            event_action='UNAUTHORIZED_MANUAL_ACCESS',
            severity='WARNING',
            user_id=getattr(current_user, 'id', None),
            username=user_name,
            endpoint=request.path,
            status_code=403,
            details={'role': user_role, 'reason': 'qms_view_permission_denied'}
        )
        abort(403)

    try:
        index_path = os.path.join(current_app.root_path, 'qms_index.json')
        if not os.path.exists(index_path):
            index_path = 'qms_index.json'
        with open(index_path, 'r', encoding='utf-8') as f:
            sops = json.load(f)

        sops_by_dept = {}
        today_date = datetime.now().strftime("%m-%d-%Y")
        today_sops = []

        for sop in sops:
            dept = sop['dept']
            tier = sop.get('access_tier', 'STAFF')

            # Role Partitioning: Non-executives cannot view Executive Tier or Accounting docs
            if (dept == 'ACCOUNTING' or tier == 'EXECUTIVE') and not is_exec:
                continue

            if dept not in sops_by_dept:
                sops_by_dept[dept] = []
            sops_by_dept[dept].append(sop)
            if sop.get('date') == today_date:
                today_sops.append(sop)

        for dept in sops_by_dept:
            sops_by_dept[dept].sort(key=lambda x: x.get('title', '').lower())

        return render_template('qms_manual_index.html', sops_by_dept=sops_by_dept, today_sops=today_sops)
    except HTTPException:
        raise
    except Exception as e:
        return f"QMS Index Error: {e}"


@public_bp.route('/manual/<path:filename>', endpoint='view_sop')
@login_required
def view_sop(filename):
    """
    Controlled Document Reader (SOC 2 & ISO 9001 Protected).
    Enforces authentication, single-origin containment, and role-based authorization.
    """
    user_role = getattr(current_user, 'role', 'Operator')
    user_name = getattr(current_user, 'username', '')
    is_exec = user_role in ['Executive', 'Admin'] or user_name == 'admin'

    # Granular ABAC: Non-executives must have explicit qms view permission
    if not is_exec and hasattr(current_user, 'has_permission') and not current_user.has_permission('qms', 'view'):
        log_security_event(
            event_category='ACCESS_CONTROL',
            event_action='UNAUTHORIZED_MANUAL_ACCESS',
            severity='WARNING',
            user_id=getattr(current_user, 'id', None),
            username=user_name,
            endpoint=request.path,
            status_code=403,
            details={'attempted_file': filename, 'role': user_role, 'reason': 'qms_view_permission_denied'}
        )
        abort(403)

    # Security Guardrail: Prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        log_security_event(
            event_category='ACCESS_CONTROL',
            event_action='PATH_TRAVERSAL_ATTEMPT',
            severity='WARNING',
            user_id=getattr(current_user, 'id', None),
            username=user_name,
            endpoint=request.path,
            status_code=400,
            details={'attempted_file': filename}
        )
        abort(400)

    # Check document classification in qms_index.json
    index_path = os.path.join(current_app.root_path, 'qms_index.json')
    if not os.path.exists(index_path):
        index_path = 'qms_index.json'
    
    doc_entry = None
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            sops = json.load(f)
            for s in sops:
                if s.get('file', '').lower() == filename.lower():
                    doc_entry = s
                    break
    except Exception:
        pass

    if doc_entry:
        dept = doc_entry.get('dept', '')
        tier = doc_entry.get('access_tier', 'STAFF')
        if (dept == 'ACCOUNTING' or tier == 'EXECUTIVE') and not is_exec:
            log_security_event(
                event_category='ACCESS_CONTROL',
                event_action='UNAUTHORIZED_MANUAL_ACCESS',
                severity='WARNING',
                user_id=getattr(current_user, 'id', None),
                username=user_name,
                ip_address=extract_client_ip(),
                endpoint=request.path,
                status_code=403,
                details={'attempted_file': filename, 'document_id': doc_entry.get('id'), 'required_tier': 'EXECUTIVE'}
            )
            abort(403)

    try:
        content = None
        # 1. Direct local filesystem read
        local_qms_path = os.path.join(current_app.root_path, 'static', 'qms', filename)
        if os.path.exists(local_qms_path):
            with open(local_qms_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        else:
            # 2. Network microservice fallback
            try:
                response = requests.get(f"http://compliance/qms/{filename}", timeout=2)
                if response.status_code == 200:
                    content = response.text
            except Exception:
                pass

        if content is None:
            return f"QMS Error: Document not found ({filename})", 404

        sops_by_dept = {}
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                sops = json.load(f)
            for sop in sops:
                dept = sop['dept']
                tier = sop.get('access_tier', 'STAFF')
                if (dept == 'ACCOUNTING' or tier == 'EXECUTIVE') and not is_exec:
                    continue
                if dept not in sops_by_dept:
                    sops_by_dept[dept] = []
                sops_by_dept[dept].append(sop)
            for dept in sops_by_dept:
                sops_by_dept[dept].sort(key=lambda x: x.get('title', '').lower())
        except Exception:
            pass

        return render_template('qms_shell.html', content=content, sops_by_dept=sops_by_dept, active_file=filename)
    except Exception as e:
        return f"QMS Connectivity Error: {e}", 500


@public_bp.route('/trust-center', endpoint='trust_center')
def trust_center():
    """
    Public Institutional Trust Center (SOC 2 & ISO 9001 Showcase).
    Exposes verified public credentials, capabilities, and safety ratings
    without exposing internal operational procedures.
    """
    return render_template('trust_center.html')

@public_bp.route('/locations/<city>', endpoint='location_page')
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

@public_bp.route('/get-quote', methods=['GET', 'POST'], endpoint='get_quote')
@rate_limit(limit=15, period_seconds=60, scope="public_quote")
def get_quote():
    """Enterprise client intake form with bot honey-pot filtering and data sanitization."""
    if request.method == 'POST':
        try:
            data = request.form
            form_version = data.get('form_version', 'v1')
            
            if form_version == "v2":
                sqf = 0.0
                need = 2
                facility_type = "Not Specified"
                frequency = "TBD (Handshake)"
                need_label = "Handshake Protocol"
                city = ""
                zipcode = ""
                job_title = ""
                target_start = "Within 30 Days"
                scope_addons = []
            else:
                sqf_raw = str(data.get('sqft', '') or '').strip().replace(',', '')
                sqf = float(sqf_raw) if sqf_raw else 0.0
                need = int(data.get('need', 2))
                facility_type = data.get('facility_type', 'office')
                frequency = data.get('frequency', 'Standard')
                need_labels = { "1": "Slow Traffic", "2": "High Traffic", "3": "24/7 Production" }
                need_label = need_labels.get(data.get('need'), "Standard")
                city = (data.get('city') or '').strip()
                zipcode = (data.get('zipcode') or '').strip()
                job_title = (data.get('job_title') or '').strip()
                target_start = (data.get('target_start') or 'within_30').strip()
                scope_addons = request.form.getlist('scope_addons')
            
            multiplier = 1.0
            if need == 2: multiplier = 1.5
            if need == 3: multiplier = 2.5
            annual_value = (sqf * 0.12) * multiplier * 12 if sqf > 0 else 0.0
            
            company = (data.get('company') or '').strip()
            name = (data.get('name') or '').strip()
            email = (data.get('email') or '').strip()
            phone = (data.get('phone') or '').strip()
            
            # If Mobile Express or company omitted, generate descriptive title
            if not company:
                company = f"{name}'s Commercial Facility" if name else "Commercial Client Facility"
            if not city:
                city = "Pending Walkthrough / Discovery"
            if not frequency or frequency == 'Standard':
                frequency = "Standard Business (Pending Verification)"
            
            # Enterprise Bot Defense (HWB-QMS-11.10): Honeypot + Signed Speed Gate + Lexical Scan + Origin Check
            is_bot, bot_reason = evaluate_bot_defense(request)
            
            data_dict = {
                'name': name,
                'company': company,
                'email': email,
                'phone': phone,
                'facility_type': facility_type,
                'sqft': f"{int(sqf):,}" if sqf > 0 else "Pending Walkthrough Verification",
                'need_label': need_label,
                'city': city,
                'zipcode': zipcode,
                'frequency': frequency
            }

            if is_bot:
                print(f"[BOT_DEFENSE_BLOCKED] Bot submission dropped via Silent Blackhole. Reason: {bot_reason} | IP: {request.remote_addr} | Target: {company} / {email}", flush=True)
                try:
                    from core.services.security_logger import log_security_event
                    log_security_event(
                        event_category='BOT_DEFENSE',
                        event_action='BOT_DROPPED',
                        severity='WARNING',
                        endpoint='/get-quote',
                        http_method='POST',
                        status_code=200,
                        details={'reason': bot_reason, 'target_company': company, 'target_email': email}
                    )
                except Exception:
                    pass
                return render_template('quote_success.html', data=data_dict)

            raw_phone = (data.get('phone') or '').strip()
            clean_p = clean_phone(raw_phone) if raw_phone else ''
            clean_e = clean_email(data.get('email')) or (data.get('email') or '').strip()

            consent_val = data.get('tcpa_consent')
            if not clean_p:
                consent_str = "Not Applicable (Email Only Lead)"
            elif consent_val:
                consent_str = "Granted (Explicit Checkbox)"
            else:
                consent_str = "Not Provided (Phone On File, No SMS)"

            addons_str = ", ".join(scope_addons) if scope_addons else "None Specified"
            full_notes = (
                f"TCPA Consent: {consent_str} | "
                f"Horizon: {target_start} | "
                f"Frequency: {frequency} | "
                f"Scope Addons: {addons_str}"
            )
            
            db_url = current_app.config['DATABASE_URL']
            conn = get_db(db_url)
            try:
                with conn.cursor() as cur:
                    actual_source = 'Website Quote Form (Mobile Express)' if form_version == 'mobile_express' else f'Website Quote Form ({form_version})'
                    cur.execute('''
                        INSERT INTO "Leads" (
                            center_name, decision_maker, email, phone, facility_type, sqf,
                            estimated_annual_value, status, lead_source, traffic_cycle, notes,
                            city, zipcode, job_title
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    ''', (
                        company, name, clean_e, clean_p, facility_type,
                        int(sqf), annual_value, 'New', actual_source,
                        frequency, full_notes, city, zipcode, job_title
                    ))
                    inserted_row = cur.fetchone()
                    lead_id = inserted_row[0] if inserted_row else None
                    data_dict['lead_id'] = lead_id
                    
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
                            <h2 style="font-size: 18px; font-weight: 800; margin-bottom: 20px;">New Commercial Lead Intake</h2>
                            <p><strong>Organization:</strong> {data.get('company')}</p>
                            <p><strong>Contact:</strong> {data.get('name')}{f" ({job_title})" if job_title else ""}</p>
                            <p><strong>Email Address:</strong> {clean_e}</p>
                            <p><strong>Phone Number:</strong> {clean_p or 'Not Provided (Email Only Request)'}</p>
                            <p><strong>Contact Permission:</strong> {consent_str}</p>
                            <p><strong>Location:</strong> {city or 'DFW Metroplex'}, TX {zipcode}</p>
                            <p><strong>Building Details:</strong> {facility_type} ({data_dict['sqft']} SQF) &bull; {frequency}</p>
                            <p><strong>Target Horizon:</strong> {target_start}</p>
                            <p><strong>Scope Additions:</strong> {addons_str}</p>
                            <p><strong>Estimated Annual Valuation:</strong> ${annual_value:,.2f}</p>
                            <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 30px 0;">
                            <p style="font-size: 12px; color: #94a3b8; font-style: italic;">Automatic message from the HWB system.</p>
                        </div>
                    </div>
                    """
                    notification_payload = {
                        'company': data.get('company'),
                        'name': data.get('name'),
                        'job_title': job_title,
                        'phone': clean_p,
                        'email': clean_e,
                        'city': city,
                        'zipcode': zipcode,
                        'facility_type': facility_type,
                        'sqft': data_dict.get('sqft', 'Pending Verification'),
                        'frequency': frequency,
                        'target_start': target_start,
                        'scope_addons': scope_addons,
                        'annual_value': annual_value,
                        'form_version': form_version
                    }
                    
                    cur.execute('''
                        INSERT INTO "PendingOutbox" (recipient, subject, body, status, created_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ''', ('hdominguez@hwbcleaning.com, sales@hwbcleaning.com', f"ACTION REQUIRED: New Lead Ingested ({data.get('company')})", email_body, 'SENT'))
                    
                    cur.execute('''
                        INSERT INTO "SigmaInteractionLog" (user_prompt, agent_explanation, tools_used, status)
                        VALUES (%s, %s, %s, %s)
                    ''', (
                        'Lead Ingestion Webhook',
                        f"Captured {form_version} lead from {data.get('company')}",
                        '["web_quote_form", "task_queue", "telegram", "graph_email"]',
                        'SUCCESS'
                    ))

                conn.commit()
            finally:
                conn.close()

            # Enqueue asynchronous real-time dispatch (Telegram + Graph Email)
            try:
                task_queue.enqueue(
                    dispatch_lead_notifications,
                    notification_payload,
                    name=f"lead_notify_{(data.get('company') or 'unnamed')[:24]}"
                )
            except Exception as queue_err:
                print(f"[PUBLIC_WARN] Async task enqueue error: {queue_err}", flush=True)
                try:
                    dispatch_lead_notifications(notification_payload)
                except Exception as sync_err:
                    print(f"[PUBLIC_ERROR] Sync notification fallback error: {sync_err}", flush=True)

            return render_template('quote_success.html', data=data_dict)
        except Exception as e:
            print(f"Quote Error: {e}")
            flash("Processing error. Please call (214)-586-0257.")
            
    return render_template('quote_form.html')

@public_bp.route('/update-quote-details', methods=['POST'], endpoint='update_quote_details')
@public_bp.route('/update-quote-sqft', methods=['POST'], endpoint='update_quote_sqft')
def update_quote_details():
    """Optional post-submission pricing calibration updater (Option B: Mobile Express Enrichment)."""
    lead_id = request.form.get('lead_id')
    sqft_val = (request.form.get('sqft') or '').strip().replace(',', '')
    city_val = (request.form.get('city') or '').strip()
    freq_val = (request.form.get('frequency') or '').strip()

    if lead_id:
        try:
            db_url = current_app.config['DATABASE_URL']
            conn = get_db(db_url)
            with conn.cursor() as cur:
                updates = []
                params = []
                notes_append = []

                if sqft_val:
                    try:
                        sqf = float(sqft_val)
                        annual_value = (sqf * 0.12) * 1.5 * 12
                        updates.append("sqf = %s")
                        params.append(int(sqf))
                        updates.append("estimated_annual_value = %s")
                        params.append(annual_value)
                        notes_append.append(f"Building Size Added: {int(sqf):,} SF")
                    except ValueError:
                        pass

                if city_val:
                    updates.append("city = %s")
                    params.append(city_val)
                    notes_append.append(f"City Confirmed: {city_val}")

                if freq_val:
                    updates.append("traffic_cycle = %s")
                    params.append(freq_val)
                    notes_append.append(f"Frequency Selected: {freq_val}")

                if notes_append:
                    updates.append("notes = COALESCE(notes, '') || %s")
                    params.append(" | " + " | ".join(notes_append))

                if updates:
                    params.append(int(lead_id))
                    sql = f'UPDATE "Leads" SET {", ".join(updates)} WHERE id = %s'
                    cur.execute(sql, tuple(params))
                    conn.commit()
                    print(f"[PUBLIC_SUCCESS] Quote details enriched for Lead #{lead_id}: {notes_append}", flush=True)

            conn.close()
        except Exception as e:
            print(f"[PUBLIC_WARN] Quote details update error: {e}", flush=True)

    return jsonify({
        'status': 'success',
        'lead_id': lead_id,
        'sqft': sqft_val,
        'city': city_val,
        'frequency': freq_val
    })


@public_bp.route('/robots.txt', endpoint='robots_txt')
def robots_txt():
    host = request.host.lower()
    if 'hwbcleaning.com' not in host:
        return "User-agent: *\nDisallow: /\n", 200, {'Content-Type': 'text/plain'}
    return send_from_directory(current_app.static_folder, 'robots.txt')

@public_bp.after_request
def protect_staging_indexing(response):
    host = request.host.lower()
    if 'hwbcleaning.com' not in host:
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response

@public_bp.route('/sitemap.xml', endpoint='sitemap_xml')
def sitemap_xml():
    return send_from_directory(current_app.static_folder, 'sitemap.xml')

@public_bp.route('/favicon.ico', endpoint='favicon')
def favicon():
    return send_from_directory(current_app.static_folder, 'favicon.ico')

@public_bp.route('/work-with-us', methods=['GET'], endpoint='work_with_us')
def work_with_us():
    """Public portal for cleaning technician applications and subcontractor intake."""
    job_positions = []
    try:
        from core.services.database import get_db
        conn = get_db(current_app.config['DATABASE_URL'])
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "JobPositions" WHERE is_active = TRUE ORDER BY id ASC;')
            job_positions = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        print(f"[WORK-WITH-US] Error loading job positions: {e}", flush=True)
    return render_template('work_with_us.html', job_positions=job_positions)

@public_bp.route('/careers', methods=['GET'], endpoint='careers')
def careers():
    """SEO alias redirect to work-with-us."""
    return redirect(url_for('public.work_with_us'))

@public_bp.route('/onboard/bosanna', methods=['GET'], endpoint='bosanna_onboarding')
@public_bp.route('/portal/bosanna/onboard', methods=['GET'], endpoint='bosanna_onboarding_portal')
def bosanna_onboarding():
    """White-labeled Bosanna LLC workforce compliance and technician onboarding portal (Model C)."""
    return render_template('bosanna_onboarding.html')

@public_bp.route('/sw.js', methods=['GET'], endpoint='service_worker')
def service_worker():
    """Serves PWA service worker with root scope."""
    return send_from_directory(current_app.static_folder, 'sw.js', mimetype='application/javascript')

@public_bp.route('/manifest.json', methods=['GET'], endpoint='pwa_manifest')
def pwa_manifest():
    """Serves PWA web app manifest."""
    return send_from_directory(current_app.static_folder, 'manifest.json', mimetype='application/json')


