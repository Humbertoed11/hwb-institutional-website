"""
SigmaFidelity™ Public Marketing, Service Directory, and Quote Engine Blueprint
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Lauri Tells (VP of Marketing)
"""

import os
import re
import json
import urllib.parse
import requests
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, send_from_directory, jsonify
from werkzeug.exceptions import HTTPException
from flask_login import login_required, current_user
from core.services.database import get_db
from core.services.sanitizer import clean_phone, clean_email, clean_city, extract_phone_digits
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
    },
    'irving': {
        'name': 'Irving',
        'title': 'Commercial Cleaning & Janitorial Services in Irving & Las Colinas | HWB Cleaning',
        'h1': 'Commercial Cleaning & Janitorial Services in Irving & Las Colinas',
        'meta_desc': 'ISO 9001:2026 & OSHA-compliant commercial cleaning, corporate janitorial, and post-construction cleanup in Irving and Las Colinas, TX. Get a quote today.',
        'desc': 'Delivering clinical-grade nightly janitorial, day porter staffing, and specialty floor care for corporate headquarters, medical plazas, and logistics hubs across Irving, Las Colinas, and DFW Airport corridors.'
    },
    'richardson': {
        'name': 'Richardson',
        'title': 'Commercial Cleaning & Janitorial Services in Richardson | HWB Cleaning',
        'h1': 'Commercial Cleaning & Janitorial Services in Richardson',
        'meta_desc': 'ISO 9001:2026 commercial cleaning, data center sanitation, and office janitorial services in Richardson and the Telecom Corridor, TX. Request a quote.',
        'desc': 'Supporting technology campuses, defense contractors, and Class-A office buildings across Richardson, the Telecom Corridor, and CityLine with vetted, badged cleaning technicians.'
    },
    'allen': {
        'name': 'Allen',
        'title': 'Commercial Cleaning & Janitorial Services in Allen | HWB Cleaning',
        'h1': 'Commercial Cleaning & Janitorial Services in Allen',
        'meta_desc': 'Reliable commercial office cleaning, educational facility sanitization, and floor care in Allen, TX along US-75 & SH-121. Request a custom quote today.',
        'desc': 'Providing dependable nightly office cleaning, daycare and school sanitization, and post-construction final cleans throughout Allen, Watters Creek, and the US-75 commercial corridor.'
    },
    'arlington': {
        'name': 'Arlington',
        'title': 'Commercial & Industrial Cleaning Services in Arlington | HWB Cleaning',
        'h1': 'Commercial & Industrial Cleaning Services in Arlington',
        'meta_desc': 'Heavy-duty industrial warehouse scrubbing, commercial janitorial, and post-construction cleanup in Arlington, TX. OSHA-trained crews. Request a quote.',
        'desc': 'Engineered for high-volume manufacturing plants, distribution centers, medical offices, and commercial venues across Arlington and the Mid-Cities industrial corridor.'
    },
    'addison': {
        'name': 'Addison',
        'title': 'Commercial Office Cleaning & Janitorial Services in Addison | HWB Cleaning',
        'h1': 'Commercial Office Cleaning & Janitorial Services in Addison',
        'meta_desc': 'Executive office cleaning, commercial floor care, and day porter services in Addison and the Dallas North Tollway corridor, TX. Request a free quote.',
        'desc': 'Maintaining pristine executive suites, financial institutions, and multi-tenant commercial buildings throughout Addison, Quorum Drive, and the Dallas North Tollway corridor.'
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
                    INSERT INTO "EmailSuppressionList" (email_lower, reason, source)
                    VALUES (%s, 'UNSUBSCRIBED', 'PUBLIC_UNSUBSCRIBE_FORM')
                    ON CONFLICT (email_lower) DO NOTHING;
                ''', (raw_email,))

                cur.execute('''
                    UPDATE "Leads"
                    SET is_dnc = TRUE, status = 'Do Not Call (DNC)', campaign_ready = FALSE, email_hygiene_status = 'DO_NOT_EMAIL', updated_at = CURRENT_DATE
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
                        INSERT INTO "EmailSuppressionList" (email_lower, reason, source, lead_id)
                        VALUES (LOWER(TRIM(%s)), 'UNSUBSCRIBED', 'ONE_CLICK_TOKEN', %s)
                        ON CONFLICT (email_lower) DO NOTHING;
                    ''', (found_email, lead_id))

                    cur.execute('''
                        UPDATE "Leads"
                        SET is_dnc = TRUE, 
                            status = 'Unsubscribed',
                            campaign_ready = FALSE,
                            email_hygiene_status = 'DO_NOT_EMAIL',
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

APPLICATION_MANUAL_FILE = 'hwb-qms-7.5_backoffice_and_crm_management_sop.html'

def user_has_master_qms_clearance(user) -> bool:
    """
    Evaluates whether the user is authorized to view the full ISO 9001 QMS master catalog.
    By default, standard staff/operators are strictly restricted to the Application Manual.
    Master QMS access requires Executive/Admin role or explicit 'qms:master'/'qms:all' permission.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    user_role = getattr(user, 'role', '')
    user_name = getattr(user, 'username', '')
    if user_role in ['Executive', 'Admin'] or user_name == 'admin':
        return True
    
    if hasattr(user, 'has_permission') and user.has_permission('qms', 'view'):
        return True
    
    custom_perms = getattr(user, 'custom_permissions', {})
    if isinstance(custom_perms, str):
        try:
            custom_perms = json.loads(custom_perms)
        except Exception:
            custom_perms = {}
            
    if isinstance(custom_perms, dict):
        qms_perm = custom_perms.get('qms')
        if isinstance(qms_perm, dict):
            return bool(qms_perm.get('master') or qms_perm.get('all') or qms_perm.get('entire') or qms_perm.get('view'))
        if isinstance(qms_perm, (list, tuple, set)):
            return any(k in qms_perm for k in ['master', 'all', 'entire', 'view'])
            
    return False


WORKSPACE_CHAPTER_MAP = {
    # Chapter 1: Login & Getting Started
    'login': ('chapter-1', 'Getting Started & Login', 'general'),
    'session': ('chapter-1', 'Session Security & Getting Started', 'general'),
    'general': ('chapter-1', 'Getting Started & General Help', 'general'),
    'home': ('chapter-1', 'Getting Started & Login', 'general'),

    # Chapter 2: Leads & CRM
    'leads': ('chapter-2', 'Commercial Leads & CRM', 'leads'),
    'lead': ('chapter-2', 'Commercial Leads & CRM', 'leads'),
    'accounts': ('chapter-2', 'Client Accounts & CRM', 'leads'),
    'clients': ('chapter-2', 'Client Accounts & CRM', 'leads'),
    'sales_desk': ('chapter-2', 'Calling Desk & CRM', 'leads'),
    'sales-desk': ('chapter-2', 'Calling Desk & CRM', 'leads'),
    'crm': ('chapter-2', 'Commercial Leads & CRM', 'leads'),

    # Chapter 3: Bidding & Price Estimating
    'construction_bids': ('chapter-3', 'Commercial Construction Bids', 'bids'),
    'general_contractors': ('chapter-3', 'General Contractors Directory', 'bids'),
    'institutional_bids': ('chapter-3', 'Institutional Bidding & Cooperatives', 'bids'),
    'programs': ('chapter-3', 'Certifications & Programs', 'bids'),
    'bids': ('chapter-3', 'Bidding & Price Estimating', 'bids'),
    'calculator': ('chapter-3', 'Estimating Calculator', 'bids'),
    'capability_statement': ('chapter-3', 'Commercial Capability Statement', 'bids'),
    'capability-statement': ('chapter-3', 'Commercial Capability Statement', 'bids'),
    'takeoff': ('chapter-3', 'Commercial Takeoffs', 'bids'),

    # Chapter 4: Customer Outreach & Calendar Walkthroughs
    'marketing': ('chapter-4', 'Marketing & Email Outreach', 'outreach'),
    'outbox': ('chapter-4', 'Customer Outreach & Pending Outbox', 'outreach'),
    'campaigns': ('chapter-4', 'Marketing Campaigns', 'outreach'),
    'walkthroughs': ('chapter-4', 'Walkthroughs & Bookings', 'outreach'),
    'bookings': ('chapter-4', 'Calendar Bookings', 'outreach'),
    'email': ('chapter-4', 'Customer Outreach & Emailing', 'outreach'),

    # Chapter 5: Cleaning Staff, Schedules & Safety
    'workforce': ('chapter-5', 'Workforce & Field Operations', 'cleaning'),
    'safety': ('chapter-5', 'Jobsite Safety & EHSQ', 'cleaning'),
    'monitor': ('chapter-5', 'Live Shift Dispatch & Monitoring', 'cleaning'),
    'dispatch': ('chapter-5', 'Live Shift Dispatch & Monitoring', 'cleaning'),
    'scope': ('chapter-5', 'Scopes of Work Matrix', 'cleaning'),
    'mobile': ('chapter-5', 'Technician Mobile App & Field Work', 'cleaning'),
    'cleaning': ('chapter-5', 'Cleaning Steps & Field Standards', 'cleaning'),
    'technician': ('chapter-5', 'Technician Mobile App & Field Work', 'cleaning'),

    # Chapter 6: User Accounts & System Administration
    'users': ('chapter-6', 'User Accounts & Administration', 'users'),
    'user': ('chapter-6', 'User Accounts & Administration', 'users'),
    'settings': ('chapter-6', 'System Administration & Settings', 'users'),
    'executive': ('chapter-6', 'Executive Command & Administration', 'users'),
    'it_department': ('chapter-6', 'Systems Hub & IT Administration', 'users'),
    'it_telemetry': ('chapter-6', 'Systems Telemetry & Architecture', 'users'),
    'lab': ('chapter-6', 'Systems Sandbox & Lab', 'users'),
    'sigmajan_lab': ('chapter-6', 'Systems Sandbox & Lab', 'users'),
    'admin_master': ('chapter-6', 'Master Administration', 'users'),
}


@public_bp.route('/manual/app', endpoint='application_manual')
@public_bp.route('/manual/application', endpoint='application_manual_alias')
@login_required
def application_manual():
    """
    Direct endpoint for the Application Manual.
    Authorized for all active employees to access their backoffice software operating instructions.
    Detects the user's active workspace and deep-links directly to the relevant chapter.
    """
    user_role = getattr(current_user, 'role', 'Operator')
    user_name = getattr(current_user, 'username', '')
    is_exec = user_role in ['Executive', 'Admin'] or user_name == 'admin'
    has_master_qms = user_has_master_qms_clearance(current_user)

    target_chapter = None
    target_chapter_title = None
    canonical_topic = None

    # 1. Direct query parameter inspection
    topic_param = (
        request.args.get('topic') or 
        request.args.get('view') or 
        request.args.get('from_view') or 
        request.args.get('chapter')
    )
    if topic_param:
        key = topic_param.strip().lower()
        if key in WORKSPACE_CHAPTER_MAP:
            target_chapter, target_chapter_title, canonical_topic = WORKSPACE_CHAPTER_MAP[key]
        elif key.startswith('chapter-'):
            target_chapter = key
            for v in WORKSPACE_CHAPTER_MAP.values():
                if v[0] == key:
                    target_chapter_title = v[1]
                    canonical_topic = v[2]
                    break

    # 2. Referrer detection fallback if no query param provided
    if not target_chapter and request.referrer:
        try:
            parsed = urllib.parse.urlparse(request.referrer)
            q_params = urllib.parse.parse_qs(parsed.query)
            view_val = q_params.get('view', [None])[0]
            if view_val and view_val.strip().lower() in WORKSPACE_CHAPTER_MAP:
                target_chapter, target_chapter_title, canonical_topic = WORKSPACE_CHAPTER_MAP[view_val.strip().lower()]
            else:
                path = parsed.path.lower()
                for k, v in WORKSPACE_CHAPTER_MAP.items():
                    if f"/{k}" in path:
                        target_chapter, target_chapter_title, canonical_topic = v
                        break
            
            # If detected from referrer, redirect with explicit anchor so the browser scrolls smoothly
            if target_chapter:
                return redirect(url_for('public.application_manual', topic=canonical_topic, _anchor=target_chapter))
        except Exception:
            pass

    sops_by_dept = {}
    if has_master_qms:
        try:
            index_path = os.path.join(current_app.root_path, 'qms_index.json')
            if os.path.exists(index_path):
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

    return render_template(
        'application_manual.html',
        has_master_qms=has_master_qms,
        is_exec=is_exec,
        is_app_manual=True,
        active_file='application_manual',
        sops_by_dept=sops_by_dept,
        target_chapter=target_chapter,
        target_chapter_title=target_chapter_title,
        canonical_topic=canonical_topic
    )


@public_bp.route('/manual', endpoint='manual_index')
@login_required
def manual_index():
    """
    Controlled Operating Manual Index (SOC 2 & ISO 9001 Protected).
    By default, employees without master QMS security level only see the Application Manual.
    Users with master QMS clearance see the entire company catalog.
    """
    user_role = getattr(current_user, 'role', 'Operator')
    user_name = getattr(current_user, 'username', '')
    is_exec = user_role in ['Executive', 'Admin'] or user_name == 'admin'
    has_master_qms = user_has_master_qms_clearance(current_user)

    # Basic QMS access: non-executives must have explicit qms view permission
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
            sop_file = sop.get('file', '')

            # Default Employee Restriction:
            # If user does not have master QMS clearance, only the Application Manual is visible.
            if not has_master_qms:
                if sop_file.lower() != APPLICATION_MANUAL_FILE.lower():
                    continue

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

        return render_template(
            'qms_manual_index.html',
            sops_by_dept=sops_by_dept,
            today_sops=today_sops,
            has_master_qms=has_master_qms,
            app_manual_file=APPLICATION_MANUAL_FILE
        )
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
    Standard employees are strictly authorized for the Application Manual.
    Master QMS documents require elevated clearance.
    """
    user_role = getattr(current_user, 'role', 'Operator')
    user_name = getattr(current_user, 'username', '')
    is_exec = user_role in ['Executive', 'Admin'] or user_name == 'admin'
    has_master_qms = user_has_master_qms_clearance(current_user)

    is_app_manual = filename.lower() == APPLICATION_MANUAL_FILE.lower()

    # Default Employee Isolation: Non-executives without elevated master QMS clearance
    # are strictly restricted to the Application Manual.
    if not has_master_qms and not is_app_manual:
        log_security_event(
            event_category='ACCESS_CONTROL',
            event_action='UNAUTHORIZED_MANUAL_ACCESS',
            severity='WARNING',
            user_id=getattr(current_user, 'id', None),
            username=user_name,
            endpoint=request.path,
            status_code=403,
            details={'attempted_file': filename, 'role': user_role, 'reason': 'master_qms_security_level_required'}
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
                sop_file = sop.get('file', '')

                # Default Employee Restriction for sidebar
                if not has_master_qms:
                    if sop_file.lower() != APPLICATION_MANUAL_FILE.lower():
                        continue

                if (dept == 'ACCOUNTING' or tier == 'EXECUTIVE') and not is_exec:
                    continue
                if dept not in sops_by_dept:
                    sops_by_dept[dept] = []
                sops_by_dept[dept].append(sop)
            for dept in sops_by_dept:
                sops_by_dept[dept].sort(key=lambda x: x.get('title', '').lower())
        except Exception:
            pass

        return render_template(
            'qms_shell.html',
            content=content,
            sops_by_dept=sops_by_dept,
            active_file=filename,
            has_master_qms=has_master_qms,
            app_manual_file=APPLICATION_MANUAL_FILE
        )
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
            is_repeat_lead = False
            try:
                with conn.cursor() as cur:
                    actual_source = 'Website Quote Form (Mobile Express)' if form_version == 'mobile_express' else f'Website Quote Form ({form_version})'
                    phone_digits = extract_phone_digits(clean_p)
                    existing_lead = None

                    if phone_digits and len(phone_digits) == 10:
                        cur.execute('''
                            SELECT id, sqf, estimated_annual_value, notes
                            FROM "Leads"
                            WHERE COALESCE(is_duplicate, FALSE) = FALSE
                              AND RIGHT(REGEXP_REPLACE(COALESCE(phone, ''), '[^0-9]', '', 'g'), 10) = %s
                            ORDER BY id ASC LIMIT 1;
                        ''', (phone_digits,))
                        existing_lead = cur.fetchone()

                    if not existing_lead and clean_e:
                        cur.execute('''
                            SELECT id, sqf, estimated_annual_value, notes
                            FROM "Leads"
                            WHERE COALESCE(is_duplicate, FALSE) = FALSE
                              AND LOWER(TRIM(COALESCE(email, ''))) = LOWER(%s)
                            ORDER BY id ASC LIMIT 1;
                        ''', (clean_e,))
                        existing_lead = cur.fetchone()

                    if not existing_lead and company and city and city != 'Pending Walkthrough / Discovery':
                        cur.execute('''
                            SELECT id, sqf, estimated_annual_value, notes
                            FROM "Leads"
                            WHERE COALESCE(is_duplicate, FALSE) = FALSE
                              AND LOWER(TRIM(COALESCE(center_name, ''))) = LOWER(TRIM(%s))
                              AND LOWER(TRIM(COALESCE(city, ''))) = LOWER(TRIM(%s))
                            ORDER BY id ASC LIMIT 1;
                        ''', (company, city))
                        existing_lead = cur.fetchone()

                    if existing_lead:
                        is_repeat_lead = True
                        lead_id = existing_lead[0]
                        prev_sqf = int(existing_lead[1] or 0)
                        prev_val = float(existing_lead[2] or 0.0)
                        prev_notes = existing_lead[3] or ''
                        merged_sqf = int(sqf) if int(sqf) > 0 else prev_sqf
                        merged_val = float(annual_value) if float(annual_value) > 0 else prev_val
                        stamp = datetime.now().strftime('%Y-%m-%d')
                        merged_notes = f"{prev_notes}\n[REPEAT REQUEST {stamp}]: {full_notes}".strip()

                        cur.execute('''
                            UPDATE "Leads"
                            SET center_name = COALESCE(NULLIF(%s, ''), center_name),
                                decision_maker = COALESCE(NULLIF(%s, ''), decision_maker),
                                email = COALESCE(NULLIF(%s, ''), email),
                                phone = COALESCE(NULLIF(%s, ''), phone),
                                facility_type = COALESCE(NULLIF(%s, ''), facility_type),
                                sqf = %s,
                                estimated_annual_value = %s,
                                traffic_cycle = COALESCE(NULLIF(%s, ''), traffic_cycle),
                                notes = %s,
                                city = CASE WHEN %s != 'Pending Walkthrough / Discovery' AND %s != '' THEN %s ELSE city END,
                                zipcode = COALESCE(NULLIF(%s, ''), zipcode),
                                job_title = COALESCE(NULLIF(%s, ''), job_title),
                                priority_level = 'High'
                            WHERE id = %s;
                        ''', (
                            company, name, clean_e, clean_p, facility_type,
                            merged_sqf, merged_val, frequency, merged_notes,
                            city, city, city, zipcode, job_title, lead_id
                        ))
                    else:
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

                    ref_code = f"LEAD-#{int(lead_id or 0):05d}"
                    data_dict['lead_id'] = lead_id
                    data_dict['already_registered'] = is_repeat_lead
                    data_dict['reference_code'] = ref_code
                    
                    request_type = "Quick Registration" if form_version == "v2" else "Full Cleaning Plan"
                    email_body = f"""
                    <div style="font-family: 'Inter', sans-serif; padding: 40px; border: 1px solid #e2e8f0; border-radius: 8px; max-width: 600px;">
                        <div style="display: flex; justify-content: space-between; border-bottom: 3px solid #2563eb; padding-bottom: 20px; margin-bottom: 30px;">
                            <div>
                                <div style="font-weight: 900; font-size: 18px; color: #2563eb;">HWB NOTIFICATION</div>
                                <div style="font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 5px;">Request Type: {request_type} ({ref_code})</div>
                            </div>
                        </div>
                        <div style="line-height: 1.8; color: #1e293b; font-size: 14px;">
                            <h2 style="font-size: 18px; font-weight: 800; margin-bottom: 20px;">{'Updated Commercial Lead Request' if is_repeat_lead else 'New Commercial Lead Intake'}</h2>
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
                        'lead_id': lead_id,
                        'reference_code': ref_code,
                        'is_repeat': is_repeat_lead,
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
                    
                    if not is_repeat_lead:
                        cur.execute('''
                            INSERT INTO "PendingOutbox" (recipient, subject, body, status, created_at)
                            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ''', ('hdominguez@hwbcleaning.com, sales@hwbcleaning.com', f"ACTION REQUIRED: New Lead Ingested ({data.get('company')})", email_body, 'SENT'))
                    
                    cur.execute('''
                        INSERT INTO "SigmaInteractionLog" (user_prompt, agent_explanation, tools_used, status)
                        VALUES (%s, %s, %s, %s)
                    ''', (
                        'Lead Ingestion Webhook',
                        f"{'Updated existing' if is_repeat_lead else 'Captured'} {form_version} lead from {data.get('company')} ({ref_code})",
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


def _is_onboarding_token_expired(partner_row: dict) -> bool:
    """Checks whether the 30-day rolling TTL on onboarding_token_expires_at has elapsed."""
    from datetime import datetime as dt_cls, timezone
    exp_val = partner_row.get('onboarding_token_expires_at')
    if not exp_val:
        return False
    if isinstance(exp_val, str):
        try:
            exp_val = dt_cls.fromisoformat(exp_val.replace('Z', '+00:00'))
        except Exception:
            return False
    now_ref = dt_cls.now(timezone.utc) if getattr(exp_val, 'tzinfo', None) else dt_cls.now()
    return exp_val < now_ref


@public_bp.route('/onboard/subcontractor/<token>', methods=['GET'], endpoint='subcontractor_onboarding')
def subcontractor_onboarding(token: str):
    """Pre-filled 1099 Subcontractor Partner Self-Service Onboarding Portal (HWB-QMS-7.6 / BUG-139)."""
    from core.services.database import get_db
    from database.schema_engine import ensure_subcontractor_onboarding_schema
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        ensure_subcontractor_onboarding_schema(conn)
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "SubcontractorPartners" WHERE onboarding_token = %s LIMIT 1;', (token,))
            row = cur.fetchone()
            if not row:
                return render_template('404.html'), 404
            partner = dict(row)
            ref_code = f"SUB-#{int(partner['id']):04d}"
            submitted = bool(request.args.get('submitted'))
            token_expired = _is_onboarding_token_expired(partner)
            return render_template(
                'subcontractor_onboarding.html',
                partner=partner,
                ref_code=ref_code,
                submitted=submitted,
                token_expired=token_expired,
            )
    finally:
        if conn:
            conn.close()


@public_bp.route('/onboard/subcontractor/<token>/renew-link', methods=['POST'], endpoint='subcontractor_onboarding_renew')
def subcontractor_onboarding_renew(token: str):
    """Extends an expired onboarding magic link by 30 days and emails a fresh link to the partner."""
    from core.services.database import get_db
    from database.schema_engine import ensure_subcontractor_onboarding_schema
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        ensure_subcontractor_onboarding_schema(conn)
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "SubcontractorPartners" WHERE onboarding_token = %s LIMIT 1;', (token,))
            row = cur.fetchone()
            if not row:
                return jsonify({'status': 'error', 'message': 'Invalid onboarding link.'}), 404
            partner = dict(row)
            sub_id = partner['id']
            cur.execute(
                '''
                UPDATE "SubcontractorPartners"
                SET onboarding_token_expires_at = CURRENT_TIMESTAMP + INTERVAL '30 days',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
                ''',
                (sub_id,),
            )
            conn.commit()
            onboarding_url = f"{request.host_url.rstrip('/')}/onboard/subcontractor/{token}"
            if partner.get('email'):
                try:
                    from core.services.notification_service import send_subcontractor_onboarding_invite_email
                    send_subcontractor_onboarding_invite_email({
                        'partner_id': sub_id,
                        'company_name': partner.get('company_name'),
                        'contact_name': partner.get('contact_name'),
                        'email': partner.get('email'),
                        'onboarding_url': onboarding_url,
                        'review_mode': '30-Day Link Renewal',
                    })
                except Exception:
                    pass
            return jsonify({
                'status': 'success',
                'onboarding_url': onboarding_url,
                'message': 'Your onboarding link has been renewed for 30 days.',
            })
    finally:
        if conn:
            conn.close()


@public_bp.route('/onboard/subcontractor/<token>/extract-document', methods=['POST'], endpoint='subcontractor_onboarding_extract')
def subcontractor_onboarding_extract(token: str):
    """
    Uploads and auto-extracts IRS Form W-9 or ACORD 25 COI fields in real time
    for the pre-filled 1099 onboarding portal, protected by per-IP/token rate limiting
    and AES-256 Fernet full-TIN encryption.
    """
    import json
    from datetime import datetime as dt_cls
    from werkzeug.utils import secure_filename
    from core.services.database import get_db
    from core.services.security_logger import extract_client_ip
    from database.schema_engine import ensure_subcontractor_onboarding_schema
    from core.services.subcontractor_doc_extractor import (
        extract_subcontractor_document_metadata,
        check_extraction_rate_limit,
        encrypt_and_mask_subcontractor_tin,
        deposit_subcontractor_document_vault,
    )

    client_ip = extract_client_ip()
    allowed, remaining_quota = check_extraction_rate_limit(f"{token}:{client_ip}", limit=15, window_seconds=600)
    if not allowed:
        return jsonify({
            'status': 'error',
            'code': 'RATE_LIMIT_EXCEEDED',
            'message': 'Too many document extraction requests. Please wait a few minutes and try again.',
        }), 429

    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No document file uploaded.'}), 400
    f_obj = request.files['file']
    if not f_obj or not f_obj.filename:
        return jsonify({'status': 'error', 'message': 'Empty file selected.'}), 400

    doc_type = (request.form.get('doc_type') or 'w9').strip().lower()
    raw_bytes = f_obj.read()
    if not raw_bytes:
        return jsonify({'status': 'error', 'message': 'Uploaded file is empty.'}), 400

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        ensure_subcontractor_onboarding_schema(conn)
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "SubcontractorPartners" WHERE onboarding_token = %s LIMIT 1;', (token,))
            row = cur.fetchone()
            if not row:
                return jsonify({'status': 'error', 'message': 'Invalid onboarding link.'}), 404
            partner = dict(row)
            if _is_onboarding_token_expired(partner):
                return jsonify({
                    'status': 'error',
                    'code': 'TOKEN_EXPIRED',
                    'message': 'This onboarding link has expired after 30 days. Click Renew Link to continue.',
                }), 410
            sub_id = partner['id']

            vault_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vault', 'hr_documents'))
            os.makedirs(vault_dir, exist_ok=True)
            clean_fn = secure_filename(f_obj.filename)
            tag = 'W9' if 'w9' in doc_type else 'COI'
            safe_name = f"sub_{sub_id}_{tag}_{int(dt_cls.now().timestamp())}_{clean_fn}"
            vault_receipt = deposit_subcontractor_document_vault(
                conn=conn,
                subcontractor_id=sub_id,
                doc_type='w9' if tag == 'W9' else 'coi',
                file_key=safe_name,
                original_filename=clean_fn,
                raw_bytes=raw_bytes,
                mime_type=f_obj.mimetype or 'application/pdf',
                uploaded_by='subcontractor_portal_extract',
                uploaded_ip=client_ip,
                vault_dir=vault_dir,
            )

            extracted = extract_subcontractor_document_metadata(
                raw_bytes, clean_fn, doc_type=doc_type, partner_row=partner
            )

            if tag == 'W9':
                raw_tin = extracted.get('ein_or_ssn') or ''
                masked_tin, last4, encrypted_tin = encrypt_and_mask_subcontractor_tin(raw_tin)
                cur.execute(
                    '''
                    UPDATE "SubcontractorPartners"
                    SET w9_file_url = %s,
                        w9_status = 'File Uploaded (Review)',
                        legal_entity_name = COALESCE(NULLIF(%s, ''), legal_entity_name),
                        tax_classification = COALESCE(NULLIF(%s, ''), tax_classification),
                        street_address = COALESCE(NULLIF(%s, ''), street_address),
                        city = COALESCE(NULLIF(%s, ''), city),
                        state = COALESCE(NULLIF(%s, ''), state),
                        zip_code = COALESCE(NULLIF(%s, ''), zip_code),
                        ein_or_ssn = COALESCE(NULLIF(%s, ''), ein_or_ssn),
                        w9_ein_last4 = COALESCE(NULLIF(%s, ''), w9_ein_last4),
                        w9_tin_encrypted = COALESCE(%s, w9_tin_encrypted),
                        w9_extracted_json = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                    ''',
                    (
                        safe_name,
                        extracted.get('legal_entity_name') or '',
                        extracted.get('tax_classification') or '',
                        extracted.get('street_address') or '',
                        extracted.get('city') or '',
                        extracted.get('state') or '',
                        extracted.get('zip_code') or '',
                        masked_tin or raw_tin,
                        last4,
                        encrypted_tin,
                        json.dumps({**extracted, 'ein_or_ssn': masked_tin or raw_tin}),
                        sub_id,
                    ),
                )
            else:
                exp_val = extracted.get('coi_expiration_date') or None
                cur.execute(
                    '''
                    UPDATE "SubcontractorPartners"
                    SET coi_file_url = %s,
                        coi_status = 'File Uploaded (Review)',
                        coi_carrier = COALESCE(NULLIF(%s, ''), coi_carrier),
                        coi_policy_number = COALESCE(NULLIF(%s, ''), coi_policy_number),
                        coi_coverage_amount = COALESCE(NULLIF(%s, ''), coi_coverage_amount),
                        coi_expiration_date = COALESCE(%s::date, coi_expiration_date),
                        coi_extracted_json = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                    ''',
                    (
                        safe_name,
                        extracted.get('coi_carrier') or '',
                        extracted.get('coi_policy_number') or '',
                        extracted.get('coi_coverage_amount') or '',
                        exp_val if exp_val else None,
                        json.dumps(extracted),
                        sub_id,
                    ),
                )
            conn.commit()
            return jsonify({
                'status': 'success',
                'doc_type': tag,
                'file_name': safe_name,
                'extracted': extracted,
                'vault_receipt': vault_receipt,
                'rate_limit_remaining': remaining_quota,
            })
    except Exception as err:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(err)}), 500
    finally:
        if conn:
            conn.close()


@public_bp.route('/onboard/subcontractor/<token>/submit', methods=['POST'], endpoint='subcontractor_onboarding_submit')
def subcontractor_onboarding_submit(token: str):
    """
    Finalizes the pre-filled 1099 Subcontractor Onboarding submission:
    1. Saves verified/extracted W-9 business address, encrypted 9-digit Tax ID, and classification.
    2. Handles COI upload or holds status at 'Pending COI' per executive policy.
    3. Generates both locked PDF and HTML tamper-evident signed Master Subcontractor Agreement (MSA)
       + Texas DWC-83 certificates with SHA-256 cryptographic signature hash.
    4. Dispatches executive & partner notifications.
    """
    import json
    from datetime import datetime as dt_cls
    from werkzeug.utils import secure_filename
    from core.services.database import get_db
    from core.services.sanitizer import clean_phone, clean_email, clean_city
    from core.services.security_logger import extract_client_ip
    from database.schema_engine import ensure_subcontractor_onboarding_schema
    from core.services.subcontractor_doc_extractor import (
        extract_subcontractor_document_metadata,
        generate_signed_msa_dwc83_certificate_html,
        generate_signed_msa_dwc83_certificate_pdf,
        compute_msa_signature_hash,
        encrypt_and_mask_subcontractor_tin,
        deposit_subcontractor_document_vault,
    )

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        ensure_subcontractor_onboarding_schema(conn)
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "SubcontractorPartners" WHERE onboarding_token = %s LIMIT 1;', (token,))
            row = cur.fetchone()
            if not row:
                return jsonify({'status': 'error', 'message': 'Invalid onboarding link.'}), 404
            partner = dict(row)
            if _is_onboarding_token_expired(partner):
                return jsonify({
                    'status': 'error',
                    'code': 'TOKEN_EXPIRED',
                    'message': 'This onboarding link has expired after 30 days. Please renew your link to submit.',
                }), 410
            sub_id = partner['id']

            vault_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vault', 'hr_documents'))
            os.makedirs(vault_dir, exist_ok=True)

            w9_file_url = partner.get('w9_file_url')
            coi_file_url = partner.get('coi_file_url')
            w9_ext_data = {}
            coi_ext_data = {}

            # Handle direct file attachments if not already uploaded via AJAX
            if 'w9_file' in request.files and request.files['w9_file'].filename:
                wf = request.files['w9_file']
                w_bytes = wf.read()
                if w_bytes:
                    clean_wfn = secure_filename(wf.filename)
                    w9_file_url = f"sub_{sub_id}_W9_{int(dt_cls.now().timestamp())}_{clean_wfn}"
                    deposit_subcontractor_document_vault(
                        conn=conn,
                        subcontractor_id=sub_id,
                        doc_type='w9',
                        file_key=w9_file_url,
                        original_filename=clean_wfn,
                        raw_bytes=w_bytes,
                        mime_type=wf.mimetype or 'application/pdf',
                        uploaded_by='subcontractor_portal_submit',
                        uploaded_ip=extract_client_ip(),
                        vault_dir=vault_dir,
                    )
                    w9_ext_data = extract_subcontractor_document_metadata(
                        w_bytes, clean_wfn, doc_type='w9', partner_row=partner
                    )

            if 'coi_file' in request.files and request.files['coi_file'].filename:
                cf = request.files['coi_file']
                c_bytes = cf.read()
                if c_bytes:
                    clean_cfn = secure_filename(cf.filename)
                    coi_file_url = f"sub_{sub_id}_COI_{int(dt_cls.now().timestamp())}_{clean_cfn}"
                    deposit_subcontractor_document_vault(
                        conn=conn,
                        subcontractor_id=sub_id,
                        doc_type='coi',
                        file_key=coi_file_url,
                        original_filename=clean_cfn,
                        raw_bytes=c_bytes,
                        mime_type=cf.mimetype or 'application/pdf',
                        uploaded_by='subcontractor_portal_submit',
                        uploaded_ip=extract_client_ip(),
                        vault_dir=vault_dir,
                    )
                    coi_ext_data = extract_subcontractor_document_metadata(
                        c_bytes, clean_cfn, doc_type='coi', partner_row=partner
                    )

            if not w9_file_url:
                return jsonify({
                    'status': 'error',
                    'message': 'Please upload your signed IRS Form W-9 in Step 1 before submitting.'
                }), 400

            company_name = (request.form.get('company_name') or w9_ext_data.get('company_name') or partner.get('company_name') or '').strip()
            legal_entity_name = (request.form.get('legal_entity_name') or w9_ext_data.get('legal_entity_name') or partner.get('legal_entity_name') or partner.get('contact_name') or '').strip()
            tax_classification = (request.form.get('tax_classification') or w9_ext_data.get('tax_classification') or partner.get('tax_classification') or 'LLC').strip()
            raw_ein_input = (request.form.get('ein_or_ssn') or w9_ext_data.get('ein_or_ssn') or partner.get('ein_or_ssn') or '').strip()
            masked_tin, last4_tin, encrypted_tin = encrypt_and_mask_subcontractor_tin(raw_ein_input)
            ein_or_ssn = masked_tin or raw_ein_input
            street_address = (request.form.get('street_address') or w9_ext_data.get('street_address') or partner.get('street_address') or '').strip()
            city = clean_city(request.form.get('city') or w9_ext_data.get('city') or partner.get('city') or '')
            state = (request.form.get('state') or w9_ext_data.get('state') or partner.get('state') or 'TX').strip().upper()
            zip_code = (request.form.get('zip_code') or w9_ext_data.get('zip_code') or partner.get('zip_code') or '').strip()
            contact_name = (request.form.get('contact_name') or partner.get('contact_name') or '').strip()
            phone = clean_phone(request.form.get('phone') or partner.get('phone') or '')
            email = clean_email(request.form.get('email') or partner.get('email') or '')
            try:
                crew_size = int(request.form.get('crew_size') or partner.get('crew_size') or 2)
            except (ValueError, TypeError):
                crew_size = 2

            coi_carrier = (request.form.get('coi_carrier') or coi_ext_data.get('coi_carrier') or partner.get('coi_carrier') or '').strip()
            coi_policy_number = (request.form.get('coi_policy_number') or coi_ext_data.get('coi_policy_number') or partner.get('coi_policy_number') or '').strip()
            coi_expiration_date = (request.form.get('coi_expiration_date') or coi_ext_data.get('coi_expiration_date') or None)
            if coi_expiration_date == '':
                coi_expiration_date = None

            msa_signer_name = (request.form.get('msa_signer_name') or contact_name).strip()
            msa_signer_title = (request.form.get('msa_signer_title') or 'Owner / Authorized Principal').strip()
            msa_agreed = str(request.form.get('msa_agreed', 'true')).lower() in ('true', '1', 'yes', 'on')
            dwc83_agreed = str(request.form.get('dwc83_agreed', 'true')).lower() in ('true', '1', 'yes', 'on')

            if not ein_or_ssn or not street_address or not msa_signer_name:
                return jsonify({
                    'status': 'error',
                    'message': 'Federal Tax ID (EIN/SSN), Street Address, and Electronic Signature Name are required.'
                }), 400
            if not msa_agreed or not dwc83_agreed:
                return jsonify({
                    'status': 'error',
                    'message': 'You must agree to both the Master Subcontractor Agreement and the Texas DWC Form-83 affirmation.'
                }), 400

            signer_ip = extract_client_ip()
            now_dt = dt_cls.now()
            ts_int = int(now_dt.timestamp())
            signed_at_display = now_dt.strftime('%m/%d/%Y %I:%M %p CST')

            # Generate signed MSA & TX DWC-83 Compliance Certificate (Both Locked PDF and HTML Mirror)
            cert_context = dict(partner)
            cert_context.update({
                'company_name': company_name,
                'legal_entity_name': legal_entity_name,
                'tax_classification': tax_classification,
                'ein_or_ssn': ein_or_ssn,
                'street_address': street_address,
                'city': city,
                'state': state,
                'zip_code': zip_code,
                'phone': phone,
                'email': email,
            })
            sig_hash = compute_msa_signature_hash(
                cert_context, msa_signer_name, msa_signer_title, signer_ip, signed_at_display
            )
            cert_html = generate_signed_msa_dwc83_certificate_html(
                cert_context, msa_signer_name, msa_signer_title, signer_ip, signed_at_display, signature_hash=sig_hash
            )
            cert_pdf_bytes = generate_signed_msa_dwc83_certificate_pdf(
                cert_context, msa_signer_name, msa_signer_title, signer_ip, signed_at_display, signature_hash=sig_hash
            )
            msa_html_filename = f"sub_{sub_id}_MSA_DWC83_Signed_{ts_int}.html"
            msa_pdf_filename = f"sub_{sub_id}_MSA_DWC83_Signed_{ts_int}.pdf"
            with open(os.path.join(vault_dir, msa_html_filename), 'w', encoding='utf-8') as cf_out:
                cf_out.write(cert_html)
            deposit_subcontractor_document_vault(
                conn=conn,
                subcontractor_id=sub_id,
                doc_type='msa',
                file_key=msa_pdf_filename,
                original_filename=msa_pdf_filename,
                raw_bytes=cert_pdf_bytes,
                mime_type='application/pdf',
                uploaded_by=msa_signer_name or 'subcontractor_portal_submit',
                uploaded_ip=signer_ip,
                vault_dir=vault_dir,
            )
            deposit_subcontractor_document_vault(
                conn=conn,
                subcontractor_id=sub_id,
                doc_type='dwc83',
                file_key=msa_pdf_filename,
                original_filename=msa_pdf_filename,
                raw_bytes=cert_pdf_bytes,
                mime_type='application/pdf',
                uploaded_by=msa_signer_name or 'subcontractor_portal_submit',
                uploaded_ip=signer_ip,
                vault_dir=vault_dir,
            )

            # Determine COI & Onboarding Status per CEO Directive A2
            has_coi_file = bool(coi_file_url)
            if has_coi_file:
                new_coi_status = 'File Uploaded (Review)'
                new_onboarding_status = 'Docs Under Review'
                new_partner_status = 'Docs Submitted'
                completion_msg = (
                    f"Your Form W-9, Certificate of Insurance (COI), and signed Master Subcontractor Agreement "
                    f"&amp; Texas DWC-83 PDF have been saved under <strong>SUB-#{int(sub_id):04d}</strong>. "
                    f"Our operations team has been notified for final partner activation."
                )
            else:
                new_coi_status = 'Pending'
                new_onboarding_status = 'Pending COI'
                new_partner_status = 'Pending COI'
                completion_msg = (
                    f"Your Form W-9, extracted address/Tax ID, and signed Master Subcontractor Agreement "
                    f"&amp; Texas DWC-83 PDF have been saved under <strong>SUB-#{int(sub_id):04d}</strong>! "
                    f"Because your Certificate of Insurance (COI) was not uploaded yet, your profile is held at "
                    f"<strong>Pending COI</strong>. You can revisit this same link anytime to upload your COI."
                )

            cur.execute(
                '''
                UPDATE "SubcontractorPartners"
                SET company_name = %s,
                    legal_entity_name = %s,
                    tax_classification = %s,
                    ein_or_ssn = %s,
                    w9_ein_last4 = COALESCE(NULLIF(%s, ''), w9_ein_last4),
                    w9_tin_encrypted = COALESCE(%s, w9_tin_encrypted),
                    street_address = %s,
                    city = %s,
                    state = %s,
                    zip_code = %s,
                    contact_name = %s,
                    phone = %s,
                    email = %s,
                    crew_size = %s,
                    w9_file_url = %s,
                    w9_status = 'Verified',
                    coi_file_url = %s,
                    coi_status = %s,
                    coi_carrier = COALESCE(NULLIF(%s, ''), coi_carrier),
                    coi_policy_number = COALESCE(NULLIF(%s, ''), coi_policy_number),
                    coi_expiration_date = COALESCE(%s::date, coi_expiration_date),
                    dwc83_signed = TRUE,
                    dwc83_file_url = %s,
                    msa_signed = TRUE,
                    msa_signer_name = %s,
                    msa_signer_title = %s,
                    msa_signed_at = CURRENT_TIMESTAMP,
                    msa_signer_ip = %s,
                    msa_signature_hash = %s,
                    msa_file_url = %s,
                    onboarding_status = %s,
                    onboarding_completed_at = CURRENT_TIMESTAMP,
                    status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
                ''',
                (
                    company_name,
                    legal_entity_name,
                    tax_classification,
                    ein_or_ssn,
                    last4_tin,
                    encrypted_tin,
                    street_address,
                    city,
                    state,
                    zip_code,
                    contact_name,
                    phone,
                    email,
                    crew_size,
                    w9_file_url,
                    coi_file_url,
                    new_coi_status,
                    coi_carrier,
                    coi_policy_number,
                    coi_expiration_date,
                    msa_pdf_filename,
                    msa_signer_name,
                    msa_signer_title,
                    signer_ip,
                    sig_hash,
                    msa_pdf_filename,
                    new_onboarding_status,
                    new_partner_status,
                    sub_id,
                ),
            )

            cur.execute(
                '''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description, timestamp)
                VALUES (%s, 'Subcontractor', '1099 Onboarding Submitted', %s, CURRENT_TIMESTAMP);
                ''',
                (
                    sub_id,
                    f"1099 Partner {company_name} (SUB-#{int(sub_id):04d}) submitted W-9 ({tax_classification}), address ({street_address}, {city}, {state} {zip_code}), and e-signed MSA + TX DWC-83 PDF by {msa_signer_name} (SHA-256: {sig_hash[:12]}...). Stage: {new_onboarding_status}.",
                ),
            )
            conn.commit()

            notify_payload = {
                'partner_id': sub_id,
                'company_name': company_name,
                'contact_name': contact_name,
                'email': email,
                'phone': phone,
                'street_address': street_address,
                'city': city,
                'state': state,
                'zip_code': zip_code,
                'tax_classification': tax_classification,
                'coi_status': new_coi_status,
                'onboarding_status': new_onboarding_status,
                'msa_signer_name': msa_signer_name,
            }
            try:
                from core.services.notification_service import send_subcontractor_onboarding_completed_notifications
                send_subcontractor_onboarding_completed_notifications(notify_payload)
            except Exception as notify_err:
                current_app.logger.warning(f"[ONBOARDING_NOTIFY_WARN] {notify_err}")

            return jsonify({
                'status': 'success',
                'partner_id': sub_id,
                'reference_code': f"SUB-#{int(sub_id):04d}",
                'onboarding_status': new_onboarding_status,
                'coi_status': new_coi_status,
                'msa_certificate_file': msa_pdf_filename,
                'msa_signature_hash': sig_hash,
                'message': completion_msg,
            })
    except Exception as err:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(err)}), 500
    finally:
        if conn:
            conn.close()


# ==============================================================================
# W-2 EMPLOYEE SELF-SERVICE ONBOARDING PORTAL & AUTO-EXTRACTION (HWB-QMS-7.6)
# ==============================================================================

@public_bp.route('/onboard/employee/<token>', methods=['GET'])
def employee_onboarding_portal(token: str):
    """
    Renders the pre-filled 4-Stage Self-Service W-2 Employee Onboarding Portal
    (/onboard/employee/<token>) with Form W-4, Form I-9, State ID, Direct Deposit
    auto-extraction, and ISO 9001 Clause 7.2 Job Description e-signature.
    """
    from database.schema_engine import ensure_employee_onboarding_schema
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        ensure_employee_onboarding_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT e.*,
                       jp.position_code AS job_position_code,
                       jp.title AS job_position_title,
                       jp.summary AS job_position_summary,
                       jp.key_responsibilities AS job_position_responsibilities
                FROM "Employees" e
                LEFT JOIN "JobPositions" jp ON e.job_position_id = jp.id
                WHERE e.onboarding_token = %s
                LIMIT 1;
                ''',
                (token.strip(),),
            )
            emp = cur.fetchone()
            if not emp:
                return render_template('404.html'), 404

            cur.execute(
                '''
                SELECT id, document_type, file_name, version_number, sha256_checksum, created_at
                FROM "EmployeeDocuments"
                WHERE employee_id = %s AND is_current = TRUE
                ORDER BY created_at DESC;
                ''',
                (emp['id'],),
            )
            current_docs = cur.fetchall()

        return render_template(
            'employee_onboarding_portal.html',
            employee=emp,
            current_docs=current_docs,
            token=token.strip(),
        )
    finally:
        if conn:
            conn.close()


@public_bp.route('/api/v1/employees/onboard/<token>/upload-doc', methods=['POST'])
def api_employee_portal_upload_doc(token: str):
    """
    Self-service W-2 portal document upload & auto-extraction endpoint.
    Accepts Form W-4, Driver License / State ID, Direct Deposit Void Check, or Form I-9,
    extracts structured fields, auto-populates Employees, and stores encrypted BYTEA in EmployeeDocuments.
    """
    from database.schema_engine import ensure_employee_onboarding_schema
    from core.services.employee_doc_extractor import (
        apply_extracted_fields_to_employee,
        deposit_employee_document_vault,
        extract_employee_document_auto,
    )

    if 'document' not in request.files:
        return jsonify({'status': 'error', 'message': 'No document file provided.'}), 400

    f_obj = request.files['document']
    if not f_obj or not f_obj.filename:
        return jsonify({'status': 'error', 'message': 'Empty file selected.'}), 400

    doc_type = (request.form.get('document_type') or 'Form W-4').strip()
    raw_bytes = f_obj.read()
    if not raw_bytes:
        return jsonify({'status': 'error', 'message': 'Uploaded file is empty.'}), 400

    clean_fn = secure_filename(f_obj.filename)
    mime_type = f_obj.mimetype or 'application/pdf'
    signer_ip = extract_client_ip()

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        ensure_employee_onboarding_schema(conn)
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "Employees" WHERE onboarding_token = %s LIMIT 1;', (token.strip(),))
            emp = cur.fetchone()
            if not emp:
                return jsonify({'status': 'error', 'message': 'Invalid or expired onboarding token.'}), 404

            emp_id = emp['id']
            extracted = extract_employee_document_auto(doc_type, raw_bytes, clean_fn, mime_type)
            updated_fields = apply_extracted_fields_to_employee(conn, emp_id, doc_type, extracted)
            vault_receipt = deposit_employee_document_vault(
                conn=conn,
                employee_id=emp_id,
                doc_type=doc_type,
                raw_bytes=raw_bytes,
                original_filename=clean_fn,
                mime_type=mime_type,
                expiration_date=extracted.get('state_id_expiration') or None,
                verified_by='Self-Service Auto-Extractor',
                notes=f"Self-service upload ({ ', '.join(updated_fields) })" if updated_fields else 'Self-service upload',
                uploaded_by='employee_onboarding_portal',
                uploaded_ip=signer_ip,
                extracted_metadata=extracted,
            )

            safe_extracted = {
                k: v for k, v in extracted.items()
                if k not in ('ssn_raw', 'direct_deposit_account_raw')
            }
            return jsonify({
                'status': 'success',
                'document_id': vault_receipt['document_id'],
                'document_type': doc_type,
                'version_number': vault_receipt['version_number'],
                'sha256_checksum': vault_receipt['sha256_checksum'],
                'extracted_fields': safe_extracted,
                'auto_populated_fields': updated_fields,
                'message': f"{doc_type} encrypted in Vault (v{vault_receipt['version_number']})."
            })
    finally:
        if conn:
            conn.close()


@public_bp.route('/api/v1/employees/onboard/<token>/complete', methods=['POST'])
def api_employee_portal_complete(token: str):
    """
    Finalizes the W-2 Employee Self-Service Onboarding Packet:
    1. Saves verified address, emergency contact, W-4 withholding, State ID, I-9, and Direct Deposit.
    2. Encrypts SSN and Direct Deposit Account with AES-256 Fernet if provided.
    3. Generates locked ReportLab PDF for ISO 9001 Clause 7.2 Job Description & W-2 Packet
       with SHA-256 cryptographic signature certificate and stores it in EmployeeDocuments.
    """
    import hashlib
    from core.security import encrypt_pii, mask_account
    from database.schema_engine import ensure_employee_onboarding_schema
    from core.services.employee_doc_extractor import (
        deposit_employee_document_vault,
        generate_signed_w2_onboarding_pdf,
    )

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    signer_ip = extract_client_ip()

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        ensure_employee_onboarding_schema(conn)
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "Employees" WHERE onboarding_token = %s LIMIT 1;', (token.strip(),))
            emp = cur.fetchone()
            if not emp:
                return jsonify({'status': 'error', 'message': 'Invalid onboarding link.'}), 404

            emp_id = emp['id']
            first_name = (data.get('first_name') or emp.get('first_name') or '').strip()
            last_name = (data.get('last_name') or emp.get('last_name') or '').strip()
            phone = clean_phone(data.get('phone') or emp.get('phone') or '')
            email = clean_email(data.get('email') or emp.get('email') or '')
            address_street = (data.get('address_street') or emp.get('address_street') or '').strip()
            address_city = clean_city(data.get('address_city') or emp.get('address_city') or '')
            address_state = (data.get('address_state') or emp.get('address_state') or 'TX').strip().upper()
            address_zip = (data.get('address_zip') or emp.get('address_zip') or '').strip()
            emergency_name = (data.get('emergency_contact_name') or emp.get('emergency_contact_name') or '').strip()
            emergency_phone = clean_phone(data.get('emergency_contact_phone') or emp.get('emergency_contact_phone') or '')

            w4_filing_status = (data.get('w4_filing_status') or emp.get('w4_filing_status') or 'Single').strip()
            w4_step2 = str(data.get('w4_step2_multiple_jobs', emp.get('w4_step2_multiple_jobs') or False)).lower() in ('true', '1', 'yes', 'on')
            try:
                w4_step3 = float(data.get('w4_step3_dependents', emp.get('w4_step3_dependents') or 0) or 0)
            except (ValueError, TypeError):
                w4_step3 = 0.0
            try:
                w4_step4c = float(data.get('w4_step4c_extra_withholding', emp.get('w4_step4c_extra_withholding') or 0) or 0)
            except (ValueError, TypeError):
                w4_step4c = 0.0

            state_id_number = (data.get('state_id_number') or emp.get('state_id_number') or '').strip()
            state_id_exp = (data.get('state_id_expiration') or emp.get('state_id_expiration') or None)
            if state_id_exp == '':
                state_id_exp = None
            i9_citizenship = (data.get('i9_citizenship_status') or emp.get('i9_citizenship_status') or 'US Citizen').strip()

            dd_bank = (data.get('direct_deposit_bank') or emp.get('direct_deposit_bank') or '').strip()
            dd_routing = (data.get('direct_deposit_routing') or emp.get('direct_deposit_routing') or '').strip()

            ssn_encrypted = emp.get('ssn_encrypted')
            ssn_last_four = emp.get('ssn_last_four')
            raw_ssn = (data.get('ssn') or '').strip()
            if raw_ssn and not raw_ssn.startswith('*'):
                digits = re.sub(r'\D', '', raw_ssn)
                if len(digits) == 9:
                    ssn_encrypted = encrypt_pii(f"{digits[:3]}-{digits[3:5]}-{digits[5:]}")
                    ssn_last_four = digits[-4:]

            dd_acc_encrypted = emp.get('direct_deposit_account_encrypted')
            dd_acc_last_four = emp.get('direct_deposit_account_last_four')
            dd_acc_masked = emp.get('direct_deposit_account')
            raw_dda = (data.get('direct_deposit_account') or '').strip()
            if raw_dda and not raw_dda.startswith('•') and not raw_dda.startswith('*'):
                clean_dda = re.sub(r'\s', '', raw_dda)
                if len(clean_dda) >= 4:
                    dd_acc_encrypted = encrypt_pii(clean_dda)
                    dd_acc_last_four = clean_dda[-4:]
                    dd_acc_masked = mask_account(raw_acc=clean_dda)

            signer_name = (data.get('signer_name') or f"{first_name} {last_name}").strip()
            if not signer_name:
                return jsonify({'status': 'error', 'message': 'Electronic signature name is required.'}), 400

            job_pos = None
            if emp.get('job_position_id'):
                cur.execute('SELECT * FROM "JobPositions" WHERE id = %s;', (emp['job_position_id'],))
                job_pos = cur.fetchone()

            now_iso = dt_cls.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            sig_seed = f"{emp_id}:{emp.get('employee_number')}:{signer_name}:{now_iso}:{signer_ip}"
            sig_hash = hashlib.sha256(sig_seed.encode('utf-8')).hexdigest()

            updated_emp_ctx = dict(emp)
            updated_emp_ctx.update({
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'email': email,
                'address_street': address_street,
                'address_city': address_city,
                'address_state': address_state,
                'address_zip': address_zip,
                'w4_filing_status': w4_filing_status,
                'w4_step3_dependents': w4_step3,
                'w4_step4c_extra_withholding': w4_step4c,
                'ssn_last_four': ssn_last_four,
                'state_id_number': state_id_number,
                'state_id_expiration': state_id_exp,
                'direct_deposit_bank': dd_bank,
                'direct_deposit_account_last_four': dd_acc_last_four,
            })

            pdf_bytes = generate_signed_w2_onboarding_pdf(
                employee_record=updated_emp_ctx,
                signer_name=signer_name,
                signer_ip=signer_ip,
                signed_at_iso=now_iso,
                signature_hash=sig_hash,
                job_position=dict(job_pos) if job_pos else None,
            )

            emp_num = emp.get('employee_number') or f"HWB-EMP-{emp_id}"
            vault_receipt = deposit_employee_document_vault(
                conn=conn,
                employee_id=emp_id,
                doc_type='ISO 9001 Job Description & W-2 Packet',
                raw_bytes=pdf_bytes,
                original_filename=f"{emp_num}_W2_Onboarding_Packet_Signed.pdf",
                mime_type='application/pdf',
                verified_by='Self-Service E-Signature Engine',
                notes=f"Signed by {signer_name} | SHA-256: {sig_hash[:16]}...",
                uploaded_by=signer_name,
                uploaded_ip=signer_ip,
            )

            cur.execute(
                '''
                UPDATE "Employees"
                SET first_name = %s,
                    last_name = %s,
                    phone = %s,
                    email = %s,
                    address_street = %s,
                    address_city = %s,
                    address_state = %s,
                    address_zip = %s,
                    emergency_contact_name = %s,
                    emergency_contact_phone = %s,
                    w4_filing_status = %s,
                    w4_step2_multiple_jobs = %s,
                    w4_step3_dependents = %s,
                    w4_step4c_extra_withholding = %s,
                    state_id_number = %s,
                    state_id_expiration = COALESCE(%s::date, state_id_expiration),
                    i9_citizenship_status = %s,
                    i9_verification_date = COALESCE(i9_verification_date, CURRENT_DATE),
                    direct_deposit_bank = %s,
                    direct_deposit_routing = %s,
                    direct_deposit_account = %s,
                    direct_deposit_account_encrypted = %s,
                    direct_deposit_account_last_four = %s,
                    ssn_encrypted = %s,
                    ssn_last_four = %s,
                    job_description_acknowledged_at = CURRENT_TIMESTAMP,
                    onboarding_packet_signed = TRUE,
                    onboarding_signer_name = %s,
                    onboarding_signed_at = CURRENT_TIMESTAMP,
                    onboarding_signer_ip = %s,
                    onboarding_signature_hash = %s,
                    onboarding_packet_file_url = %s,
                    onboarding_status = 'Active',
                    onboarding_completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
                ''',
                (
                    first_name, last_name, phone, email,
                    address_street, address_city, address_state, address_zip,
                    emergency_name, emergency_phone,
                    w4_filing_status, w4_step2, w4_step3, w4_step4c,
                    state_id_number, state_id_exp, i9_citizenship,
                    dd_bank, dd_routing, dd_acc_masked, dd_acc_encrypted, dd_acc_last_four,
                    ssn_encrypted, ssn_last_four,
                    signer_name, signer_ip, sig_hash, vault_receipt['file_key'],
                    emp_id,
                ),
            )

            cur.execute(
                '''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description, timestamp)
                VALUES (%s, 'Employee', 'W-2 Onboarding Completed', %s, CURRENT_TIMESTAMP);
                ''',
                (
                    emp_id,
                    f"W-2 Employee {first_name} {last_name} ({emp_num}) completed self-service onboarding & signed ISO 9001 Job Description PDF (SHA-256: {sig_hash[:12]}...).",
                ),
            )
            conn.commit()

            return jsonify({
                'status': 'success',
                'employee_id': emp_id,
                'employee_number': emp_num,
                'document_id': vault_receipt['document_id'],
                'signature_hash': sig_hash,
                'message': f"Welcome aboard, {first_name}! Your W-2 onboarding packet and signed Job Description have been securely encrypted under {emp_num}."
            })
    except Exception as err:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(err)}), 500
    finally:
        if conn:
            conn.close()


@public_bp.route('/sw.js', methods=['GET'], endpoint='service_worker')
def service_worker():
    """Serves PWA service worker with root scope."""
    return send_from_directory(current_app.static_folder, 'sw.js', mimetype='application/javascript')

@public_bp.route('/manifest.json', methods=['GET'], endpoint='pwa_manifest')
def pwa_manifest():
    """Serves PWA web app manifest."""
    return send_from_directory(current_app.static_folder, 'manifest.json', mimetype='application/json')


