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
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, send_from_directory
from core.services.database import get_db
from core.services.sanitizer import clean_phone, clean_email
from core.services.rate_limiter import rate_limit
from core.services.task_queue import task_queue
from core.services.notification_service import dispatch_lead_notifications

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

@public_bp.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@public_bp.route('/manual', endpoint='manual_index')
def manual_index():
    try:
        with open('qms_index.json', 'r') as f:
            sops = json.load(f)
        sops_by_dept = {}
        today_date = datetime.now().strftime("%m-%d-%Y")
        today_sops = []
        for sop in sops:
            dept = sop['dept']
            if dept not in sops_by_dept:
                sops_by_dept[dept] = []
            sops_by_dept[dept].append(sop)
            if sop.get('date') == today_date:
                today_sops.append(sop)
        for dept in sops_by_dept:
            sops_by_dept[dept].sort(key=lambda x: x.get('title', '').lower())
        return render_template('qms_manual_index.html', sops_by_dept=sops_by_dept, today_sops=today_sops)
    except Exception as e:
        return f"QMS Index Error: {e}"

@public_bp.route('/manual/<path:filename>', endpoint='view_sop')
def view_sop(filename):
    try:
        response = requests.get(f"http://compliance/qms/{filename}", timeout=5)
        sops_by_dept = {}
        try:
            with open('qms_index.json', 'r') as f:
                sops = json.load(f)
            for sop in sops:
                dept = sop['dept']
                if dept not in sops_by_dept:
                    sops_by_dept[dept] = []
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
            else:
                sqf = float(data.get('sqft', 0))
                need = int(data.get('need', 2))
                facility_type = data.get('facility_type', 'Other')
                frequency = data.get('frequency', 'Standard')
                need_labels = { "1": "Slow Traffic", "2": "High Traffic", "3": "24/7 Production" }
                need_label = need_labels.get(data.get('need'), "Standard")
            
            multiplier = 1.0
            if need == 2: multiplier = 1.5
            if need == 3: multiplier = 2.5
            annual_value = (sqf * 0.12) * multiplier * 12
            
            company = data.get('company', '')
            name = data.get('name', '')
            email = data.get('email', '')
            phone = data.get('phone', '')
            
            is_spam = False
            for text in [company, name]:
                if not text:
                    continue
                if any(x in text for x in ["http://", "https://", "graph.org", ".org/", ".net/", ".com/"]):
                    is_spam = True
                    break
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
                print(f"[SPAM DETECTED] Honey-pot triggered for lead: {company} / {email}")
                return render_template('quote_success.html', data=data_dict)

            consent_val = data.get('tcpa_consent')
            consent_notes = "TCPA Consent: Granted (Explicit checkbox checked during quote submission)." if consent_val else "TCPA Consent: Not Provided."
            
            db_url = current_app.config['DATABASE_URL']
            conn = get_db(db_url)
            try:
                with conn.cursor() as cur:
                    clean_p = clean_phone(data.get('phone')) or data.get('phone')
                    clean_e = clean_email(data.get('email')) or data.get('email')
                    cur.execute('''
                        INSERT INTO "Leads" (center_name, decision_maker, email, phone, facility_type, sqf, estimated_annual_value, status, lead_source, traffic_cycle, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (data.get('company'), data.get('name'), clean_e, clean_p, facility_type, sqf, annual_value, 'New', f'Website Quote Form ({form_version})', frequency, consent_notes))
                    
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
                    notification_payload = {
                        'company': data.get('company'),
                        'name': data.get('name'),
                        'phone': clean_p,
                        'email': clean_e,
                        'facility_type': facility_type,
                        'sqft': data_dict.get('sqft', 'Pending Verification'),
                        'frequency': frequency,
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

