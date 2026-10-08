"""
SigmaFidelity™ CRM Data & REST API Blueprint
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Silas Sync (VP of CRM)
"""

import os
import io
import re
import urllib.parse
import csv
import json
import hashlib
import datetime
from datetime import datetime as dt_cls
import uuid
from flask import Blueprint, request, jsonify, Response, current_app, send_file
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from core.services.database import get_db
from core.services.email_service import transmit_email
from core.services.sanitizer import clean_phone, clean_currency, clean_sqft, clean_zip, clean_email, clean_city
from core.security import (
    encrypt_pii,
    decrypt_pii,
    mask_ssn,
    mask_account,
    log_sensitive_access,
    log_security_violation
)
from core.services.security_logger import log_security_event

crm_api_bp = Blueprint('crm_api', __name__)


def serialize_row(row):
    if not row:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (datetime.date, datetime.datetime)):
            d[k] = v.isoformat()
        elif hasattr(v, '__str__') and 'Decimal' in str(type(v)):
            d[k] = float(v)
    return d


try:
    from core.services.embedding import get_embedding as calculate_query_embedding
except ImportError:
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



def log_and_abort_abac(module: str, action: str):
    """Logs forensic security event to SecurityAuditLogs and returns standard HTTP 403."""
    log_security_event(
        event_category='AUTHORIZATION',
        event_action='UNAUTHORIZED_API_MUTATION_BLOCKED',
        severity='WARNING',
        status_code=403,
        details={
            'module': module,
            'action': action,
            'endpoint': request.path,
            'method': request.method,
            'username': getattr(current_user, 'username', 'anonymous'),
            'role': getattr(current_user, 'role', 'None')
        }
    )
    return jsonify({
        'status': 'error',
        'error': 'Forbidden',
        'message': f'Forbidden: You do not have permission to {action} {module}.'
    }), 403


# --- Accounts REST Endpoints ---

@crm_api_bp.route('/api/v1/accounts/<int:id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@login_required
def api_account_hub(id):
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'GET':
                if not current_user.has_permission('accounts', 'view'):
                    return log_and_abort_abac('accounts', 'view')
                cur.execute('SELECT * FROM "Customers" WHERE customer_id = %s', (id,))
                acc = cur.fetchone()
                cur.execute('SELECT * FROM "Contacts" WHERE account_id = %s', (id,))
                contacts = cur.fetchall()
                cur.execute('SELECT * FROM "GlobalActivities" WHERE parent_id = %s AND parent_type = %s ORDER BY timestamp DESC', (id, "Account"))
                activities = cur.fetchall()

                return jsonify({
                    'account': serialize_row(acc),
                    'contacts': [serialize_row(c) for c in contacts],
                    'activities': [serialize_row(a) for a in activities]
                })

            elif request.method in ['PUT', 'PATCH']:
                if not current_user.has_permission('accounts', 'edit'):
                    return log_and_abort_abac('accounts', 'edit')
                data = request.json or {}
                cur.execute('SELECT * FROM "Customers" WHERE customer_id = %s', (id,))
                current_acc = cur.fetchone()
                if not current_acc:
                    return jsonify({'status': 'error', 'message': 'Account not found'}), 404

                def resolve(key, db_val):
                    val = data.get(key) if key in data else db_val
                    return val if val != "" else None

                def clean_date_val(val):
                    if val is None or str(val).strip() == '':
                        return None
                    return str(val).strip()

                def clean_num(val, default=0.0):
                    if val in (None, ''):
                        return default
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return default

                def clean_int(val, default=0):
                    if val in (None, ''):
                        return default
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        return default

                sqf_val = data.get('sqf') if 'sqf' in data else current_acc['sqf']
                revenue_val = data.get('annual_revenue') if 'annual_revenue' in data else current_acc['annual_revenue']
                sqf_val = clean_sqft(sqf_val) if sqf_val not in ('', None) else 0
                revenue_val = clean_currency(revenue_val) if revenue_val not in ('', None) else 0.0

                cleanable_sqft = clean_int(data.get('cleanable_sqft'), current_acc.get('cleanable_sqft') or 0)
                monthly_billing_rate = clean_num(data.get('monthly_billing_rate'), current_acc.get('monthly_billing_rate') or 0.0)
                overtime_billing_rate = clean_num(data.get('overtime_billing_rate'), current_acc.get('overtime_billing_rate') or 0.0)
                escalation_clause_pct = clean_num(data.get('escalation_clause_pct'), current_acc.get('escalation_clause_pct') or 0.0)

                # Compliance & Dates
                contract_start_date = clean_date_val(data.get('contract_start_date')) if 'contract_start_date' in data else current_acc.get('contract_start_date')
                contract_expiration_date = clean_date_val(data.get('contract_expiration_date')) if 'contract_expiration_date' in data else current_acc.get('contract_expiration_date')
                coi_expiration_date = clean_date_val(data.get('coi_expiration_date')) if 'coi_expiration_date' in data else current_acc.get('coi_expiration_date')

                tax_exempt = bool(data.get('tax_exempt')) if 'tax_exempt' in data else bool(current_acc.get('tax_exempt') or False)
                tax_exempt_number = resolve('tax_exempt_number', current_acc.get('tax_exempt_number'))
                additional_insured_verified = bool(data.get('additional_insured_verified')) if 'additional_insured_verified' in data else bool(current_acc.get('additional_insured_verified', True))
                sb9_fingerprint_required = bool(data.get('sb9_fingerprint_required')) if 'sb9_fingerprint_required' in data else bool(current_acc.get('sb9_fingerprint_required', False))

                coi_liability_limit = resolve('coi_liability_limit', current_acc.get('coi_liability_limit')) or '$1,000,000 / $2,000,000'
                consumables_agreement = resolve('consumables_agreement', current_acc.get('consumables_agreement')) or 'Contractor Provides All Consumables'
                closet_access_instructions = resolve('closet_access_instructions', current_acc.get('closet_access_instructions'))
                service_shift_window = resolve('service_shift_window', current_acc.get('service_shift_window')) or 'Evening Shift (6:00 PM – 11:00 PM)'
                target_quality_level = resolve('target_quality_level', current_acc.get('target_quality_level')) or 'Level 2: Ordinary Tidiness (APPA Standard)'
                umbrella_name = resolve('umbrella_name', current_acc.get('umbrella_name'))
                cleaning_delivery_model = resolve('cleaning_delivery_model', current_acc.get('cleaning_delivery_model')) or 'OUTSOURCED'
                payment_terms = resolve('payment_terms', current_acc.get('payment_terms')) or 'Net 30'
                accounts_payable_email = clean_email(resolve('accounts_payable_email', current_acc.get('accounts_payable_email')))
                accounts_payable_phone = clean_phone(resolve('accounts_payable_phone', current_acc.get('accounts_payable_phone')))

                rep_id_raw = data.get('assigned_rep_id') if 'assigned_rep_id' in data else (data.get('owner_id') if 'owner_id' in data else current_acc.get('assigned_rep_id'))
                if rep_id_raw == '' or rep_id_raw is None or str(rep_id_raw).lower() in ['none', 'null']:
                    rep_id = None
                else:
                    try:
                        rep_id = int(rep_id_raw)
                    except (ValueError, TypeError):
                        rep_id = None

                # Poka-Yoke Automated Safeguard
                new_status = resolve('status', current_acc['status']) or 'Active'
                termination_date = current_acc.get('termination_date')
                termination_reason = resolve('termination_reason', current_acc.get('termination_reason'))

                work_orders_paused = 0
                if new_status in ['Terminated', 'Canceled', 'Operational Hold']:
                    if not termination_date and new_status in ['Terminated', 'Canceled']:
                        termination_date = datetime.date.today()
                    # Auto-pause matching active work orders
                    cur.execute('''
                        UPDATE "WorkOrders"
                        SET status = 'Paused', crew_notes = COALESCE(crew_notes, '') || ' [POKA-YOKE: Account status changed to ' || %s || ']'
                        WHERE customer_id = %s AND status IN ('Active', 'Scheduled', 'In Progress');
                    ''', (new_status, id))
                    work_orders_paused = cur.rowcount
                elif new_status == 'Active':
                    termination_date = None
                    termination_reason = None

                cur.execute('''
                    UPDATE "Customers" SET 
                        company_name = %s, contact_person_name = %s, email = %s, phone = %s, 
                        company_address = %s, city = %s, state = %s, zip = %s, website = %s, 
                        sqf = %s, cleanable_sqft = %s, annual_revenue = %s,
                        monthly_billing_rate = %s, overtime_billing_rate = %s, payment_terms = %s,
                        accounts_payable_email = %s, accounts_payable_phone = %s,
                        tax_exempt = %s, tax_exempt_number = %s,
                        contract_period = %s, contract_start_date = %s, contract_expiration_date = %s, escalation_clause_pct = %s,
                        coi_expiration_date = %s, coi_liability_limit = %s, additional_insured_verified = %s,
                        sb9_fingerprint_required = %s, consumables_agreement = %s, closet_access_instructions = %s,
                        service_shift_window = %s, frequency = %s, traffic_cycle = %s, quote_number = %s,
                        target_quality_level = %s, umbrella_name = %s, cleaning_delivery_model = %s,
                        status = %s, termination_date = %s, termination_reason = %s,
                        billing_address = %s, start_date = %s, assigned_rep_id = %s, notes = %s
                    WHERE customer_id = %s;
                ''', (
                    resolve('company_name', current_acc['company_name']), 
                    resolve('contact_person_name', current_acc['contact_person_name']), 
                    clean_email(resolve('email', current_acc['email'])) or resolve('email', current_acc['email']), 
                    clean_phone(resolve('phone', current_acc['phone'])) or resolve('phone', current_acc['phone']),
                    resolve('company_address', current_acc['company_address']), 
                    clean_city(resolve('city', current_acc['city'])) or resolve('city', current_acc['city']), 
                    resolve('state', current_acc['state']), 
                    clean_zip(resolve('zip', current_acc['zip'])) or resolve('zip', current_acc['zip']), 
                    resolve('website', current_acc['website']), 
                    sqf_val, cleanable_sqft, revenue_val,
                    monthly_billing_rate, overtime_billing_rate, payment_terms,
                    accounts_payable_email, accounts_payable_phone,
                    tax_exempt, tax_exempt_number,
                    resolve('contract_period', current_acc['contract_period']),
                    contract_start_date, contract_expiration_date, escalation_clause_pct,
                    coi_expiration_date, coi_liability_limit, additional_insured_verified,
                    sb9_fingerprint_required, consumables_agreement, closet_access_instructions,
                    service_shift_window, resolve('frequency', current_acc['frequency']),
                    resolve('traffic_cycle', current_acc['traffic_cycle']), resolve('quote_number', current_acc['quote_number']),
                    target_quality_level, umbrella_name, cleaning_delivery_model,
                    new_status, termination_date, termination_reason,
                    resolve('billing_address', current_acc['billing_address']), 
                    resolve('next_action_date', current_acc['start_date']),
                    rep_id, resolve('notes', current_acc['notes']), id
                ))

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
                return jsonify({
                    'status': 'success',
                    'customer_id': id,
                    'account_status': new_status,
                    'work_orders_paused': work_orders_paused,
                    'message': f'Account #{id} ({current_acc["company_name"]}) master dossier updated.'
                })

            elif request.method == 'DELETE':
                if not current_user.has_permission('accounts', 'delete'):
                    return log_and_abort_abac('accounts', 'delete')
                if current_user.role == 'Sales':
                    return jsonify({'status': 'error', 'message': 'Deleting customer accounts is restricted for Sales personnel.'}), 403
                cur.execute('DELETE FROM "Customers" WHERE customer_id = %s', (id,))
                cur.execute('DELETE FROM "Contacts" WHERE account_id = %s', (id,))
                conn.commit()
                return jsonify({'status': 'success'})
    finally:
        conn.close()


@crm_api_bp.route('/api/v1/accounts/batch-action', methods=['POST'])
@login_required
def api_batch_account_action():
    data = request.get_json() or {}
    action = data.get('action')
    account_ids = data.get('account_ids', [])
    params = data.get('params', {})

    if not account_ids:
        return jsonify({'status': 'error', 'message': 'No account IDs provided'}), 400

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if action == 'delete':
                if not current_user.has_permission('accounts', 'delete'):
                    return log_and_abort_abac('accounts', 'delete')
                cur.execute('DELETE FROM "Customers" WHERE customer_id = ANY(%s);', (account_ids,))
                cur.execute('DELETE FROM "Contacts" WHERE account_id = ANY(%s);', (account_ids,))
            elif action == 'update_status':
                if not current_user.has_permission('accounts', 'edit'):
                    return log_and_abort_abac('accounts', 'edit')
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


@crm_api_bp.route('/api/v1/accounts/export-selected', methods=['POST'])
@login_required
def api_export_selected_accounts():
    if not current_user.has_permission('accounts', 'view'):
        return log_and_abort_abac('accounts', 'view')

    account_ids_raw = request.form.get('account_ids', '[]')
    try:
        account_ids = json.loads(account_ids_raw)
    except Exception:
        return "Invalid parameters", 400
        
    if not account_ids:
        return "No accounts selected", 400
        
    conn = get_db(current_app.config['DATABASE_URL'])
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
                
            log_security_event(
                event_category='DATA_LIFECYCLE',
                event_action='BULK_DATA_EXPORT',
                severity='WARNING',
                details={'export_type': 'accounts', 'row_count': len(rows), 'requested_count': len(account_ids)}
            )

            response = Response(output.getvalue(), mimetype='text/csv')
            response.headers['Content-Disposition'] = f'attachment; filename=hwb_accounts_export_{datetime.datetime.now().strftime("%Y%m%d")}.csv'
            return response
    except Exception as e:
        return str(e), 500
    finally:
        conn.close()


@crm_api_bp.route('/api/v1/accounts/<int:id>/contacts', methods=['POST'])
@login_required
def api_account_add_contact(id):
    if not current_user.has_permission('accounts', 'edit'):
        return log_and_abort_abac('accounts', 'edit')
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            data = request.json
            cur.execute('''
                INSERT INTO "Contacts" (account_id, full_name, role, email, phone)
                VALUES (%s, %s, %s, %s, %s)
            ''', (id, data.get('full_name'), data.get('role'), clean_email(data.get('email')) or data.get('email'), clean_phone(data.get('phone')) or data.get('phone')))
            conn.commit()
            return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


# --- Leads REST Endpoints ---

@crm_api_bp.route('/api/v1/leads/<int:id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@login_required
def api_lead_hub(id):
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'GET':
                if not current_user.has_permission('leads', 'view'):
                    return log_and_abort_abac('leads', 'view')
                cur.execute('SELECT * FROM "Leads" WHERE id = %s', (id,))
                lead = cur.fetchone()
                cur.execute('SELECT * FROM "Contacts" WHERE lead_id = %s', (id,))
                contacts = cur.fetchall()
                cur.execute('SELECT * FROM "GlobalActivities" WHERE parent_id = %s AND parent_type = %s ORDER BY timestamp DESC', (id, "Lead"))
                activities = cur.fetchall()
                cur.execute('''
                    SELECT cr.id as recipient_id, cr.campaign_id, mc.name as campaign_name, mc.campaign_code,
                           cr.status as campaign_status, cr.current_step, cr.open_count, cr.opened_at,
                           cr.click_count, cr.clicked_at, cr.recipient_email, mc.sender_persona
                    FROM "CampaignRecipients" cr
                    JOIN "MarketingCampaigns" mc ON cr.campaign_id = mc.id
                    WHERE cr.lead_id = %s
                    ORDER BY cr.id DESC;
                ''', (id,))
                campaigns = cur.fetchall()

                return jsonify({
                    'lead': serialize_row(lead),
                    'contacts': [serialize_row(c) for c in contacts],
                    'activities': [serialize_row(a) for a in activities],
                    'campaigns': [serialize_row(c) for c in campaigns]
                })

            elif request.method in ['PUT', 'PATCH']:
                if not current_user.has_permission('leads', 'edit'):
                    return log_and_abort_abac('leads', 'edit')
                data = request.json or {}
                cur.execute('SELECT * FROM "Leads" WHERE id = %s', (id,))
                current_lead = cur.fetchone()
                if not current_lead:
                    return jsonify({'status': 'error', 'message': 'Lead not found'}), 404

                def resolve(key, db_val):
                    val = data.get(key) if key in data else db_val
                    return val if val != "" else None

                sqf_val = data.get('sqf') if 'sqf' in data else current_lead['sqf']
                revenue_val = data.get('estimated_annual_value') if 'estimated_annual_value' in data else current_lead['estimated_annual_value']
                capacity_val = data.get('capacity') if 'capacity' in data else current_lead['capacity']
                if sqf_val == '' or sqf_val is None:
                    sqf_val = 0
                else:
                    sqf_val = clean_sqft(sqf_val)
                if revenue_val == '' or revenue_val is None:
                    revenue_val = 0.0
                else:
                    revenue_val = clean_currency(revenue_val)
                if capacity_val == '' or capacity_val is None:
                    capacity_val = None
                else:
                    capacity_val = int(capacity_val)

                umbrella_val = resolve('umbrella_name', current_lead['umbrella_name'])
                cleaning_model_val = resolve('cleaning_delivery_model', current_lead['cleaning_delivery_model'])
                acquisition_tier_val = resolve('acquisition_tier', current_lead['acquisition_tier'])
                ownership_type_val = resolve('ownership_type', current_lead['ownership_type'])
                website_val = resolve('website', current_lead.get('website'))
                county_val = resolve('county', current_lead.get('county'))
                enrollment_val = data.get('student_enrollment') if 'student_enrollment' in data else current_lead.get('student_enrollment')
                if enrollment_val == '' or enrollment_val is None:
                    enrollment_val = None
                else:
                    try:
                        enrollment_val = int(enrollment_val)
                    except (ValueError, TypeError):
                        enrollment_val = None
                verification_val = resolve('owner_verification_status', current_lead.get('owner_verification_status'))
                pref_date_val = resolve('preferred_date', current_lead.get('preferred_date'))
                pref_time_val = resolve('preferred_time', current_lead.get('preferred_time'))
                budget_val = resolve('budget_range', current_lead.get('budget_range'))

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
                        website = %s, county = %s, student_enrollment = %s,
                        owner_verification_status = %s, preferred_date = %s, preferred_time = %s,
                        budget_range = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (resolve('company_name', current_lead['center_name']), 
                      resolve('decision_maker', current_lead['decision_maker']), 
                      resolve('job_title', current_lead['job_title']), 
                      clean_email(resolve('email', current_lead['email'])) or resolve('email', current_lead['email']), 
                      clean_phone(resolve('phone', current_lead['phone'])) or resolve('phone', current_lead['phone']), 
                      resolve('address', current_lead['address']), 
                      clean_city(resolve('city', current_lead['city'])) or resolve('city', current_lead['city']), 
                      resolve('state', current_lead['state']), 
                      clean_zip(resolve('zipcode', current_lead['zipcode'])) or resolve('zipcode', current_lead['zipcode']), 
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
                      acquisition_tier_val, ownership_type_val, owner_id_val,
                      website_val, county_val, enrollment_val,
                      verification_val, pref_date_val, pref_time_val,
                      budget_val, id))

                if 'cleaning_delivery_model' in data and (umbrella_val or current_lead['umbrella_name']):
                    eff_umbrella = umbrella_val or current_lead['umbrella_name']
                    cur.execute('''
                        UPDATE "Leads"
                        SET cleaning_delivery_model = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE umbrella_name = %s AND id != %s;
                    ''', (cleaning_model_val, eff_umbrella, id))

                if 'next_action_date' in data or 'notes' in data:
                    activity_type = 'SITE_VISIT' if 'VISIT SCHEDULED' in (data.get('notes') or '') else 'NOTE'
                    description = data.get('notes') or "Strategic lead update."
                    cur.execute('''
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                        VALUES (%s, %s, %s, %s)
                    ''', (id, 'Lead', activity_type, description))

                conn.commit()
                return jsonify({'status': 'success'})

            elif request.method == 'DELETE':
                if not current_user.has_permission('leads', 'delete'):
                    return log_and_abort_abac('leads', 'delete')
                if current_user.role == 'Sales':
                    return jsonify({'status': 'error', 'message': 'Deleting lead records is restricted for Sales personnel.'}), 403
                cur.execute('DELETE FROM "Leads" WHERE id = %s', (id,))
                cur.execute('DELETE FROM "GlobalActivities" WHERE parent_id = %s AND parent_type = %s', (id, "Lead"))
                conn.commit()
                return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@crm_api_bp.route('/api/v1/leads/<int:id>/cadence-save', methods=['POST'])
@login_required
def api_lead_cadence_save(id):
    """Saves live contact corrections, notes, walkthrough dates, and activity outcomes in a single transaction."""
    if not current_user.has_permission('leads', 'edit'):
        return log_and_abort_abac('leads', 'edit')
    data = request.get_json() or {}
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "Leads" WHERE id = %s', (id,))
            current_lead = cur.fetchone()
            if not current_lead:
                return jsonify({'status': 'error', 'message': 'Lead not found'}), 404

            dm = data.get('decision_maker') if 'decision_maker' in data else current_lead['decision_maker']
            title = data.get('job_title') if 'job_title' in data else current_lead['job_title']
            phone_raw = data.get('phone') if 'phone' in data else current_lead['phone']
            phone = clean_phone(phone_raw) or phone_raw
            email_raw = data.get('email') if 'email' in data else current_lead['email']
            email = clean_email(email_raw) or email_raw
            status = data.get('status') if 'status' in data else current_lead['status']
            
            raw_next_date = data.get('next_action_date')
            next_date = raw_next_date if raw_next_date and str(raw_next_date).strip() != '' else current_lead['next_action_date']
            
            # Walkthrough specific fields
            pref_date = data.get('preferred_date') or data.get('walkthrough_date') or current_lead['preferred_date']
            pref_time = data.get('preferred_time') or data.get('walkthrough_time') or current_lead['preferred_time']

            priority = data.get('priority_level') if 'priority_level' in data else current_lead['priority_level']
            note_text = (data.get('note') or '').strip()
            activity_type = data.get('activity_type') or 'Phone Call'

            conductor = (data.get('conductor') or 'Humberto Dominguez').strip()
            rep_email_raw = data.get('rep_email') or ''
            rep_email = clean_email(rep_email_raw) or (rep_email_raw.strip() if '@' in rep_email_raw else '')
            rep_name = (data.get('rep_name') or '').strip()

            cur.execute('''
                UPDATE "Leads" SET 
                    decision_maker = %s,
                    job_title = %s,
                    phone = %s,
                    email = %s,
                    status = %s,
                    next_action_date = %s,
                    preferred_date = %s,
                    preferred_time = %s,
                    priority_level = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (dm, title, phone, email, status, next_date, pref_date, pref_time, priority, id))

            calendar_created = False
            calendar_message = None

            # Schedule on Microsoft Outlook Calendar if requested
            if data.get('sync_calendar') and pref_date:
                try:
                    from core.services.calendar_service import create_calendar_event
                    t_hour, t_min = 10, 0
                    if pref_time:
                        pt = str(pref_time).strip().upper()
                        try:
                            if "AM" in pt or "PM" in pt:
                                parsed_t = dt_cls.strptime(pt, "%I:%M %p").time()
                            else:
                                parsed_t = dt_cls.strptime(pt, "%H:%M").time()
                            t_hour, t_min = parsed_t.hour, parsed_t.minute
                        except Exception:
                            t_hour, t_min = 10, 0
                    
                    try:
                        start_dt = dt_cls.strptime(str(pref_date).strip()[:10], "%Y-%m-%d").replace(hour=t_hour, minute=t_min, second=0)
                        end_dt = start_dt + datetime.timedelta(minutes=45)
                        start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
                        end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

                        center_name = current_lead['center_name'] or 'Commercial Facility'
                        address = current_lead['address'] or ''
                        city = current_lead['city'] or ''
                        state = current_lead['state'] or 'TX'
                        zipcode = current_lead['zipcode'] or ''
                        location_text = f"{address}, {city}, {state} {zipcode}".strip(', ') or "DFW Metroplex"
                        sqf_val = current_lead['sqf'] or 0
                        cap_val = current_lead['capacity'] or 0

                        is_rep_conductor = (conductor != 'Humberto Dominguez')
                        conductor_display = f"{rep_name or 'Local Sales Representative'} (HWB Cleaning Services)" if is_rep_conductor else "Humberto Dominguez (CEO - HWB Cleaning Services)"

                        subject_tag = f" [Conductor: {rep_name or 'Rep'}]" if is_rep_conductor else ""
                        subject = f"Facility Walkthrough & Scope Assessment - {center_name}{subject_tag}"
                        
                        body_html = f"""
                        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; color: #1e293b; line-height: 1.5;">
                            <h2 style="color: #0f172a; margin-bottom: 12px; border-bottom: 2px solid #2563eb; padding-bottom: 6px;">Facility Walkthrough & Proposal Assessment</h2>
                            <p><strong>Facility:</strong> {center_name}</p>
                            <p><strong>Address:</strong> {location_text}</p>
                            <p><strong>Host / Director:</strong> {dm or 'Center Director'} ({title or 'Director'})</p>
                            <p><strong>Direct Phone:</strong> {phone or 'Not listed'}</p>
                            <p><strong>Email:</strong> {email or 'Not listed'}</p>
                            <p><strong>Cleanable SF:</strong> {sqf_val:,} SF | <strong>Capacity:</strong> {cap_val} Children</p>
                            <p><strong>Walkthrough Conductor:</strong> {conductor_display}</p>
                            {f'<p><strong>Booking Sales Representative:</strong> {rep_name} ({rep_email})</p>' if (rep_email and not is_rep_conductor) else ''}
                            {f'<div style="background: #f8fafc; border-left: 3px solid #2563eb; padding: 8px 12px; margin: 12px 0;"><strong>Caller Notes:</strong> {note_text}</div>' if note_text else ''}
                            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 16px 0;">
                            <p style="font-size: 12px; color: #64748b;"><em>Standard 10-15 minute walk: measure cleanable square footage, inspect restrooms, carpeted classrooms, entry glass, and custodial supply closet.</em></p>
                        </div>
                        """

                        additional_atts = []
                        if rep_email and '@' in rep_email:
                            additional_atts.append({
                                "email": rep_email,
                                "name": rep_name or "Sales Representative",
                                "type": "required"
                            })

                        ok, msg, _ = create_calendar_event(
                            subject=subject,
                            start_iso=start_iso,
                            end_iso=end_iso,
                            body_html=body_html,
                            location_text=location_text,
                            attendee_email=email if (email and '@' in email) else None,
                            attendee_name=dm,
                            additional_attendees=additional_atts
                        )
                        calendar_created = ok
                        calendar_message = msg
                    except Exception as cal_parse_err:
                        calendar_message = f"Date parsing error: {cal_parse_err}"
                except Exception as cal_err:
                    calendar_message = f"Calendar integration error: {cal_err}"

            if note_text or activity_type:
                cal_suffix = " (Outlook Calendar Event Confirmed)" if calendar_created else ""
                is_rep_cond = (conductor != 'Humberto Dominguez')
                rep_tag = f" [Conductor: {rep_name or 'Rep'}]" if is_rep_cond else (f" [Rep: {rep_name or rep_email}]" if rep_email else "")
                if activity_type == 'Walkthrough Booked' and pref_date:
                    log_desc = f"🎉 Walkthrough Booked for {pref_date} at {pref_time or '10:00 AM'} with {dm or 'Director'}{rep_tag}. {note_text}{cal_suffix}".strip()
                else:
                    log_desc = f"{note_text}{cal_suffix}" if note_text else f"Call outcome: {activity_type}{cal_suffix}"
                cur.execute('''
                    INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                    VALUES (%s, 'Lead', %s, %s)
                ''', (id, activity_type, log_desc))

            conn.commit()
            return jsonify({
                'status': 'success', 
                'message': 'Lead cadence recorded successfully.',
                'calendar_created': calendar_created,
                'calendar_message': calendar_message,
                'preferred_date': pref_date,
                'preferred_time': pref_time
            })
    except Exception as e:
        if 'conn' in locals() and conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals() and conn: conn.close()


@crm_api_bp.route('/api/v1/leads/batch-action', methods=['POST'])
@login_required
def api_batch_lead_action():
    data = request.get_json() or {}
    action = data.get('action')
    lead_ids = data.get('lead_ids', [])
    recipient_ids = data.get('recipient_ids', [])
    params = data.get('params', {})

    if not lead_ids and not recipient_ids:
        return jsonify({'status': 'error', 'message': 'No lead IDs or recipient IDs provided'}), 400

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if action == 'delete':
                if not current_user.has_permission('leads', 'delete'):
                    return log_and_abort_abac('leads', 'delete')
                cur.execute('DELETE FROM "Leads" WHERE id = ANY(%s);', (lead_ids,))
                cur.execute('DELETE FROM "GlobalActivities" WHERE parent_id = ANY(%s) AND parent_type = %s;', (lead_ids, "Lead"))
            elif action in ['update_status', 'mark_dnc', 'assign_owner', 'dismiss_duplicates', 'auto_merge', 'remove_from_campaign']:
                if not current_user.has_permission('leads', 'edit'):
                    return log_and_abort_abac('leads', 'edit')
                if action == 'update_status':
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
            elif action == 'remove_from_campaign':
                resolved_lead_ids = [int(x) for x in lead_ids if x is not None]
                raw_recip_ids = [int(x) for x in recipient_ids if x is not None]

                target_recips = []
                if resolved_lead_ids:
                    cur.execute('''
                        SELECT id, campaign_id, lead_id
                        FROM "CampaignRecipients"
                        WHERE lead_id = ANY(%s);
                    ''', (resolved_lead_ids,))
                    target_recips.extend(cur.fetchall())

                if raw_recip_ids:
                    cur.execute('''
                        SELECT id, campaign_id, lead_id
                        FROM "CampaignRecipients"
                        WHERE id = ANY(%s);
                    ''', (raw_recip_ids,))
                    for r in cur.fetchall():
                        target_recips.append(r)
                        lid = r[2] if isinstance(r, tuple) else r.get('lead_id')
                        if lid and lid not in resolved_lead_ids:
                            resolved_lead_ids.append(lid)

                recip_ids = list(set([r[0] if isinstance(r, tuple) else r.get('id') for r in target_recips]))
                affected_cids = list(set([r[1] if isinstance(r, tuple) else r.get('campaign_id') for r in target_recips if (r[1] if isinstance(r, tuple) else r.get('campaign_id'))]))

                # 1. Purge or Cancel unsent drafts in PendingOutbox
                if recip_ids:
                    cur.execute('''
                        DELETE FROM "PendingOutbox"
                        WHERE recipient_id = ANY(%s) 
                          AND UPPER(status) IN ('PENDING', 'AWAITING_APPROVAL', 'STAGED', 'QUEUED');
                    ''', (recip_ids,))

                # 2. Delete recipient enrollment records
                if recip_ids:
                    cur.execute('''
                        DELETE FROM "CampaignRecipients"
                        WHERE id = ANY(%s);
                    ''', (recip_ids,))

                # 3. Reset lead status back to 'New' (only if currently 'In Campaign')
                if resolved_lead_ids:
                    cur.execute('''
                        UPDATE "Leads"
                        SET status = 'New', updated_at = CURRENT_TIMESTAMP
                        WHERE id = ANY(%s) AND status = 'In Campaign';
                    ''', (resolved_lead_ids,))

                # 4. Recalculate target and staged tallies for all affected campaigns
                for cid in affected_cids:
                    cur.execute('''
                        UPDATE "MarketingCampaigns"
                        SET total_targets = (SELECT COUNT(*) FROM "CampaignRecipients" WHERE campaign_id = %s),
                            staged_count = (SELECT COUNT(*) FROM "CampaignRecipients" WHERE campaign_id = %s AND status = 'STAGED'),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s;
                    ''', (cid, cid, cid))

                # 5. Insert permanent ISO 9001 audit record in GlobalActivities
                user_label = getattr(current_user, 'full_name', None) or getattr(current_user, 'username', 'Operator')
                for lid in resolved_lead_ids:
                    cur.execute('''
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                        VALUES (%s, 'Lead', 'Marketing Outreach', %s);
                    ''', (lid, f"Removed from marketing sequence by {user_label}. Unsent email drafts canceled."))

                conn.commit()
                count_done = len(resolved_lead_ids) or len(recip_ids)
                return jsonify({
                    'status': 'success',
                    'affected_count': count_done,
                    'message': f"Removed {count_done} lead(s) from campaign sequences."
                })
            else:
                return jsonify({'status': 'error', 'message': f'Unknown action: {action}'}), 400
            
            conn.commit()
            return jsonify({'status': 'success', 'affected_count': len(lead_ids)})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@crm_api_bp.route('/api/v1/leads/export-selected', methods=['POST'])
@login_required
def api_export_selected_leads():
    if not current_user.has_permission('leads', 'view'):
        return log_and_abort_abac('leads', 'view')
    if current_user.role == 'Sales':
        return jsonify({'status': 'error', 'message': 'Exporting lead data is restricted for Sales personnel.'}), 403

    lead_ids_raw = request.form.get('lead_ids', '[]')
    try:
        lead_ids = json.loads(lead_ids_raw)
    except Exception:
        return "Invalid parameters", 400
        
    if not lead_ids:
        return "No leads selected", 400
        
    conn = get_db(current_app.config['DATABASE_URL'])
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
                
            log_security_event(
                event_category='DATA_LIFECYCLE',
                event_action='BULK_DATA_EXPORT',
                severity='WARNING',
                details={'export_type': 'leads', 'row_count': len(rows), 'requested_count': len(lead_ids)}
            )

            response = Response(output.getvalue(), mimetype='text/csv')
            response.headers['Content-Disposition'] = f'attachment; filename=hwb_leads_export_{datetime.datetime.now().strftime("%Y%m%d")}.csv'
            return response
    except Exception as e:
        return str(e), 500
    finally:
        conn.close()


@crm_api_bp.route('/api/v1/leads/<int:id>/promote', methods=['POST'])
@login_required
def api_lead_promote(id):
    if not current_user.has_permission('leads', 'edit'):
        return log_and_abort_abac('leads', 'edit')
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "Leads" WHERE id = %s', (id,))
            lead = cur.fetchone()
            
            if not lead:
                return jsonify({'status': 'error', 'message': 'Lead not found'}), 404

            contact_name = (lead['director'] or lead['decision_maker'] or 'PRIMARY_CONTACT')
            
            rep_id = lead.get('owner_id')
            if not rep_id and current_user.is_authenticated and current_user.role == 'Sales':
                rep_id = current_user.id
            
            try:
                cur.execute('''
                    INSERT INTO "Customers" (company_name, contact_person_name, email, phone, company_address, city, state, zip, sqf, traffic_cycle, annual_revenue, status, assigned_rep_id, umbrella_name, cleaning_delivery_model)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active', %s, %s, %s) RETURNING customer_id
                ''', (lead['center_name'], contact_name, lead['email'], lead['phone'], lead['address'] or 'PENDING_ENTRY', lead['city'], lead['state'], lead['zipcode'], lead['sqf'] or 0, lead['traffic_cycle'], lead['estimated_annual_value'] or 0.0, rep_id, lead.get('umbrella_name'), lead.get('cleaning_delivery_model') or 'Model C Institutional Prime (Bosanna)'))
                
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
        if conn: conn.close()


@crm_api_bp.route('/api/v1/leads/<int:id>/contacts', methods=['POST'])
@login_required
def api_lead_add_contact(id):
    if not current_user.has_permission('leads', 'edit'):
        return log_and_abort_abac('leads', 'edit')
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            data = request.json
            cur.execute('''
                INSERT INTO "Contacts" (lead_id, full_name, role, email, phone)
                VALUES (%s, %s, %s, %s, %s)
            ''', (id, data.get('full_name'), data.get('role'), clean_email(data.get('email')) or data.get('email'), clean_phone(data.get('phone')) or data.get('phone')))
            conn.commit()
            return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


# --- Global Activities Endpoints ---

@crm_api_bp.route('/api/v1/activities/<parent_type>/<int:parent_id>', methods=['GET'])
@login_required
def get_recent_activities(parent_type, parent_id):
    conn = get_db(current_app.config['DATABASE_URL'])
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
        if conn: conn.close()


@crm_api_bp.route('/api/v1/activities/quick-log', methods=['POST'])
@login_required
def api_quick_log_activity():
    data = request.get_json() or {}
    parent_id = data.get('parent_id')
    parent_type = data.get('parent_type', 'Lead')
    note_text = data.get('note', '').strip()
    activity_type = data.get('activity_type', 'Phone Call')

    if not parent_id or not note_text:
        return jsonify({'status': 'error', 'message': 'Missing parent ID or note'}), 400

    target_module = 'leads' if parent_type.lower() == 'lead' else 'accounts'
    if not current_user.has_permission(target_module, 'edit'):
        return log_and_abort_abac(target_module, 'edit')

    conn = get_db(current_app.config['DATABASE_URL'])
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
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/activities', methods=['POST'])
@login_required
def api_activities():
    data = request.json or {}
    p_id, p_type, a_type, desc = data.get('parent_id'), data.get('parent_type'), data.get('activity_type'), data.get('description', '')
    
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, %s, %s, %s)
            ''', (p_id, p_type, a_type, desc))
            conn.commit()
            return jsonify({'status': 'success', 'updates_applied': []})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


# --- Lead Ingestion & Scraper Sync ---

@crm_api_bp.route('/api/v1/trigger-lead-sync')
def trigger_lead_sync_endpoint():
    from psycopg2.extras import execute_values
    seed_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'seed_data.json')
    if not os.path.exists(seed_path):
        return jsonify({'error': 'seed_data.json not found'}), 404
        
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            with open(seed_path, 'r') as sf:
                sdata = json.load(sf)
                leads = sdata.get('leads', [])
                
                values = []
                for l in leads:
                    if l.get('id') == 44518 or 'DFW6' in str(l.get('center_name', '')):
                        continue
                    p_clean = clean_phone(l.get('phone')) or l.get('phone')
                    e_clean = clean_email(l.get('email')) or l.get('email')
                    z_clean = clean_zip(l.get('zipcode')) or l.get('zipcode')
                    c_clean = clean_city(l.get('city')) or l.get('city')
                    values.append((
                        l.get('id'), l.get('center_name'), l.get('lead_source'), l.get('status'), p_clean, e_clean, l.get('address'), c_clean, l.get('state'), z_clean,
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


# --- Knowledge Base Hybrid Search ---

@crm_api_bp.route('/api/v1/kb/search', methods=['GET', 'POST'])
def hybrid_kb_search():
    q = request.args.get('q') or (request.json.get('q') if request.is_json and request.json else '')
    if not q or not q.strip():
        return jsonify({'error': 'Query parameter q is required.'}), 400

    query_str = q.strip()
    embed_vec = calculate_query_embedding(query_str)
    embed_str = f"[{','.join(map(str, embed_vec))}]"
    
    conn = get_db(current_app.config['DATABASE_URL'])
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


@crm_api_bp.route('/api/v1/kb/preflight', methods=['GET', 'POST'])
def api_kb_preflight():
    """
    Automated Pre-Flight Memory Gate & Risk Audit.
    Evaluates incoming directive against SigmaKnowledgeScars to mandate
    preventative rules before execution begins.
    """
    q = request.args.get('q') or (request.json.get('q') if request.is_json and request.json else '')
    if not q or not q.strip():
        return jsonify({'error': 'Query parameter q or directive is required.'}), 400

    query_str = q.strip()
    embed_vec = calculate_query_embedding(query_str)
    embed_str = f"[{','.join(map(str, embed_vec))}]"
    
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            try:
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
            except Exception:
                conn.rollback()
                cur.execute("""
                    SELECT 
                        s.id,
                        s.description,
                        s.category,
                        s.status,
                        s.impact_level,
                        s.root_cause,
                        s.implemented_fix,
                        s.preventative_rule,
                        ts_rank(search_vector, plainto_tsquery('english', %s)) AS rrf_score
                    FROM "SigmaKnowledgeScars" s
                    WHERE search_vector @@ plainto_tsquery('english', %s)
                    ORDER BY rrf_score DESC LIMIT 5;
                """, (query_str, query_str))
                rows = cur.fetchall()
            scars = []
            max_impact = 1
            guardrails = []

            for r in rows:
                impact = r[4] or 1
                if impact > max_impact:
                    max_impact = impact
                rule = (r[7] or "").strip()
                if rule and rule not in guardrails:
                    guardrails.append(rule)

                scars.append({
                    'id': r[0],
                    'description': r[1],
                    'category': r[2],
                    'status': r[3],
                    'impact_level': impact,
                    'root_cause': r[5],
                    'implemented_fix': r[6],
                    'preventative_rule': r[7],
                    'rrf_score': round(float(r[8]), 6)
                })

        risk_map = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
        risk_level = risk_map.get(max_impact, "MEDIUM") if scars else "LOW"

        return jsonify({
            'status': 'GUARDRAILS_MANDATED' if scars else 'AUDIT_CLEARED',
            'directive': query_str,
            'risk_level': risk_level,
            'relevant_scars_count': len(scars),
            'scars': scars,
            'mandatory_guardrails': guardrails
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/neural/sync', methods=['POST'])
@login_required
def api_neural_sync():
    """
    Managed asynchronous neural persistence sync endpoint.
    Runs sigma_sync in the background task worker pool.
    """
    from core.services.task_queue import task_queue
    import subprocess

    def run_sync_worker():
        res = subprocess.run(["python3", "scripts/sigma_sync.py"], capture_output=True, text=True, timeout=180)
        return {
            "returncode": res.returncode,
            "success": res.returncode == 0,
            "summary": "Neural persistence sync completed successfully." if res.returncode == 0 else res.stderr[-300:]
        }

    task_id = task_queue.enqueue(run_sync_worker, name="neural_persistence_sync")
    return jsonify({
        "status": "QUEUED",
        "task_id": task_id,
        "message": "Neural persistence sync enqueued into managed background task queue."
    }), 202


# --- Duplicate Lead Management ---


@crm_api_bp.route('/api/v1/leads/duplicates/compare', methods=['GET'])
@login_required
def api_compare_duplicates():
    group_id = request.args.get('group_id')
    lead_id = request.args.get('lead_id')
    
    conn = get_db(current_app.config['DATABASE_URL'])
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


@crm_api_bp.route('/api/v1/leads/duplicates/merge', methods=['POST'])
@login_required
def api_merge_duplicates():
    data = request.get_json() or {}
    primary_id = data.get('primary_id')
    secondary_id = data.get('secondary_id')
    
    if not primary_id or not secondary_id or primary_id == secondary_id:
        return jsonify({'status': 'error', 'message': 'Valid primary_id and secondary_id required'}), 400
        
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE "GlobalActivities" SET parent_id = %s WHERE parent_id = %s AND parent_type = %s;', (primary_id, secondary_id, 'Lead'))
            
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
            
            cur.execute('DELETE FROM "Leads" WHERE id = %s;', (secondary_id,))
            
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


@crm_api_bp.route('/api/v1/leads/duplicates/dismiss', methods=['POST'])
@login_required
def api_dismiss_duplicates():
    data = request.get_json() or {}
    lead_ids = data.get('lead_ids', [])
    if not lead_ids:
        return jsonify({'status': 'error', 'message': 'No lead IDs provided'}), 400
        
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE "Leads" SET is_duplicate = FALSE, duplicate_group_id = NULL WHERE id = ANY(%s);', (lead_ids,))
            conn.commit()
            return jsonify({'status': 'success', 'affected_count': len(lead_ids)})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


# ==============================================================================
# SigmaFidelity™ Workforce & Subcontractor Intake API
# Standard: HWB-QMS-7.6 On-Demand Labor Architecture & Document Compliance
# ==============================================================================

@crm_api_bp.route('/api/v1/workforce/apply', methods=['POST'])
def api_workforce_apply():
    """Public submission gate for cleaning technician job applicants."""
    data = request.get_json() or request.form.to_dict() or {}
    full_name = (data.get('full_name') or '').strip()
    raw_phone = (data.get('phone') or '').strip()

    if not full_name or not raw_phone:
        return jsonify({'status': 'error', 'message': 'Full name and phone number are required.'}), 400

    phone = clean_phone(raw_phone) or raw_phone
    email = clean_email(data.get('email')) or data.get('email')
    city = clean_city(data.get('city')) or (data.get('city') or '').strip()
    desired_role = data.get('desired_role') or 'Commercial Cleaning Technician'
    desired_shift = data.get('desired_shift') or 'Night'
    experience = data.get('experience_level') or '1-2 Years'
    has_transport = str(data.get('has_transportation', 'true')).lower() in ('true', '1', 'yes')
    authorized_us = str(data.get('authorized_to_work_us', 'true')).lower() in ('true', '1', 'yes')
    language = data.get('preferred_language') or 'English'
    status = data.get('status') or 'New'
    notes = (data.get('notes') or '').strip()
    raw_pos_id = data.get('job_position_id')
    job_position_id = None
    if raw_pos_id:
        try:
            job_position_id = int(raw_pos_id)
        except (ValueError, TypeError):
            job_position_id = None

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if not job_position_id:
                cur.execute('SELECT id FROM "JobPositions" WHERE title ILIKE %s OR position_code = %s LIMIT 1;', (desired_role, desired_role))
                pos_row = cur.fetchone()
                if pos_row:
                    job_position_id = pos_row['id']
                else:
                    role_lower = (desired_role or '').lower()
                    if any(k in role_lower for k in ['account executive', 'enterprise', 'commercial account']):
                        cur.execute('SELECT id FROM "JobPositions" WHERE position_code = %s LIMIT 1;', ('HWB-POS-007',))
                    elif any(k in role_lower for k in ['outside sales', 'outside', 'field sales', 'commercial sales']):
                        cur.execute('SELECT id FROM "JobPositions" WHERE position_code = %s LIMIT 1;', ('HWB-POS-006',))
                    elif any(k in role_lower for k in ['remote', 'inside sales', 'telemarketing', 'appointment setter', 'sales']):
                        cur.execute('SELECT id FROM "JobPositions" WHERE position_code = %s LIMIT 1;', ('HWB-POS-005',))
                    elif 'floor' in role_lower:
                        cur.execute('SELECT id FROM "JobPositions" WHERE position_code = %s LIMIT 1;', ('HWB-POS-002',))
                    elif any(k in role_lower for k in ['lead', 'custodian', 'supervisor']):
                        cur.execute('SELECT id FROM "JobPositions" WHERE position_code = %s LIMIT 1;', ('HWB-POS-003',))
                    elif any(k in role_lower for k in ['cleanroom', 'sanitiz']):
                        cur.execute('SELECT id FROM "JobPositions" WHERE position_code = %s LIMIT 1;', ('HWB-POS-004',))
                    else:
                        cur.execute('SELECT id FROM "JobPositions" WHERE position_code = %s LIMIT 1;', ('HWB-POS-001',))
                    fallback_row = cur.fetchone()
                    if fallback_row:
                        job_position_id = fallback_row['id']

            cur.execute('''
                INSERT INTO "JobApplicants" (
                    full_name, phone, email, city, state, desired_role, desired_shift,
                    experience_level, has_transportation, authorized_to_work_us,
                    preferred_language, status, notes, job_position_id
                ) VALUES (%s, %s, %s, %s, 'TX', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            ''', (full_name, phone, email, city, desired_role, desired_shift, experience, has_transport, authorized_us, language, status, notes, job_position_id))
            new_id = cur.fetchone()[0]

            # Stage official email alert in PendingOutbox
            is_sales = any(k in (desired_role or '').lower() for k in ['sales', 'account executive', 'business development', 'growth', 'appointment setter'])
            applicant_type = "Sales & Revenue Applicant" if is_sales else "Technician Applicant"
            notes_str = f" Notes / Portfolio: {notes}." if notes else ""
            cur.execute('''
                INSERT INTO "PendingOutbox" (recipient, subject, body, status, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ''', (
                'hdominguez@hwbcleaning.com, sales@hwbcleaning.com',
                f"ACTION REQUIRED: New {applicant_type} - {full_name} ({desired_role})",
                f"Candidate {full_name} applied for {desired_role} ({desired_shift} shift) in {city}, TX. Phone: {phone}, Email: {email}, Experience: {experience}.{notes_str}",
                'SENT'
            ))

            cur.execute('''
                INSERT INTO "SigmaInteractionLog" (user_prompt, agent_explanation, tools_used, status)
                VALUES (%s, %s, %s, %s)
            ''', (
                'Workforce Applicant Intake Gate',
                f"Captured job application from {full_name} for {desired_role} (APP-#{new_id})",
                '["web_workforce_form", "task_queue", "telegram", "graph_email"]',
                'SUCCESS'
            ))
            conn.commit()

            # Enqueue asynchronous real-time dispatch (Telegram + Graph Email)
            applicant_payload = {
                'applicant_id': new_id,
                'full_name': full_name,
                'phone': phone,
                'email': email,
                'city': city,
                'desired_role': desired_role,
                'desired_shift': desired_shift,
                'experience_level': experience,
                'has_transportation': has_transport,
                'authorized_to_work_us': authorized_us,
                'preferred_language': language,
                'notes': notes
            }
            try:
                from core.services.task_queue import task_queue
                from core.services.notification_service import dispatch_applicant_notifications
                task_queue.enqueue(
                    dispatch_applicant_notifications,
                    applicant_payload,
                    name=f"applicant_notify_{new_id}"
                )
            except Exception as queue_err:
                current_app.logger.warning(f"[WORKFORCE_WARN] Async task enqueue error: {queue_err}")
                try:
                    from core.services.notification_service import dispatch_applicant_notifications
                    dispatch_applicant_notifications(applicant_payload)
                except Exception as sync_err:
                    current_app.logger.error(f"[WORKFORCE_ERROR] Sync notification fallback error: {sync_err}")

            return jsonify({'status': 'success', 'applicant_id': new_id, 'job_position_id': job_position_id, 'message': 'Application received.'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/workforce/subcontractor', methods=['POST'])
def api_workforce_subcontractor():
    """Public submission gate for 1099 cleaning crew subcontractor registration."""
    data = request.get_json() or request.form.to_dict() or {}
    company_name = (data.get('company_name') or '').strip()
    contact_name = (data.get('contact_name') or '').strip()
    raw_phone = (data.get('phone') or '').strip()

    if not company_name or not contact_name or not raw_phone:
        return jsonify({'status': 'error', 'message': 'Company name, contact name, and phone number are required.'}), 400

    phone = clean_phone(raw_phone) or raw_phone
    email = clean_email(data.get('email')) or data.get('email')
    city = clean_city(data.get('city')) or (data.get('city') or '').strip()
    try:
        crew_size = int(data.get('crew_size', 2))
    except (ValueError, TypeError):
        crew_size = 2
    specialties = data.get('specialties') or 'Post-Construction Cleaning'
    coi_status = data.get('coi_status') or 'Pending'
    hourly_rate = data.get('hourly_rate_range') or '$22 - $28/hr'
    dwc83_signed = str(data.get('dwc83_agreed', 'true')).lower() in ('true', '1', 'yes')
    notes = data.get('notes') or 'Registered via subcontractor portal.'

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO "SubcontractorPartners" (
                    company_name, contact_name, phone, email, city, state,
                    crew_size, specialties, coi_status, hourly_rate_range,
                    dwc83_signed, status, notes
                ) VALUES (%s, %s, %s, %s, %s, 'TX', %s, %s, %s, %s, %s, 'Vetting', %s)
                RETURNING id;
            ''', (company_name, contact_name, phone, email, city, crew_size, specialties, coi_status, hourly_rate, dwc83_signed, notes))
            new_id = cur.fetchone()[0]

            # Stage official email alert in PendingOutbox
            cur.execute('''
                INSERT INTO "PendingOutbox" (recipient, subject, body, status, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ''', (
                'hdominguez@hwbcleaning.com, sales@hwbcleaning.com',
                f"ACTION REQUIRED: New 1099 Subcontractor Crew - {company_name} ({crew_size} Cleaners)",
                f"Subcontractor {company_name} (Contact: {contact_name}) registered in {city}, TX. Phone: {phone}, Email: {email}, Crew Size: {crew_size}, Hourly Rate: {hourly_rate}.",
                'SENT'
            ))

            cur.execute('''
                INSERT INTO "SigmaInteractionLog" (user_prompt, agent_explanation, tools_used, status)
                VALUES (%s, %s, %s, %s)
            ''', (
                'Subcontractor Intake Gate',
                f"Captured 1099 subcontractor registration from {company_name} (SUB-#{new_id})",
                '["web_subcontractor_form", "task_queue", "telegram", "graph_email"]',
                'SUCCESS'
            ))
            conn.commit()

            # Enqueue asynchronous real-time dispatch (Telegram + Graph Email)
            partner_payload = {
                'partner_id': new_id,
                'company_name': company_name,
                'contact_name': contact_name,
                'phone': phone,
                'email': email,
                'city': city,
                'crew_size': crew_size,
                'specialties': specialties,
                'hourly_rate_range': hourly_rate,
                'dwc83_agreed': dwc83_signed,
                'dwc83_signed': dwc83_signed,
                'notes': notes
            }
            try:
                from core.services.task_queue import task_queue
                from core.services.notification_service import dispatch_subcontractor_notifications
                task_queue.enqueue(
                    dispatch_subcontractor_notifications,
                    partner_payload,
                    name=f"subcontractor_notify_{new_id}"
                )
            except Exception as queue_err:
                current_app.logger.warning(f"[WORKFORCE_WARN] Async task enqueue error: {queue_err}")
                try:
                    from core.services.notification_service import dispatch_subcontractor_notifications
                    dispatch_subcontractor_notifications(partner_payload)
                except Exception as sync_err:
                    current_app.logger.error(f"[WORKFORCE_ERROR] Sync notification fallback error: {sync_err}")

            return jsonify({'status': 'success', 'partner_id': new_id, 'message': 'Subcontractor partner registered.'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/workforce/applicants', methods=['GET'])
@login_required
def api_get_applicants():
    """Retrieve applicant records with optional filtering."""
    status_filter = request.args.get('status')
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if status_filter:
                cur.execute('SELECT * FROM "JobApplicants" WHERE status = %s ORDER BY created_at DESC;', (status_filter,))
            else:
                cur.execute('SELECT * FROM "JobApplicants" ORDER BY created_at DESC;')
            rows = [serialize_row(r) for r in cur.fetchall()]
            return jsonify({'status': 'success', 'count': len(rows), 'applicants': rows})
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/workforce/applicants/<int:id>', methods=['PATCH', 'DELETE'])
@login_required
def api_manage_applicant(id):
    """Update status or notes for an applicant."""
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'DELETE':
                cur.execute('DELETE FROM "JobApplicants" WHERE id = %s;', (id,))
                conn.commit()
                return jsonify({'status': 'success', 'deleted_id': id})

            data = request.get_json() or {}
            cur.execute('SELECT * FROM "JobApplicants" WHERE id = %s;', (id,))
            current_app_row = cur.fetchone()
            if not current_app_row:
                return jsonify({'status': 'error', 'message': 'Applicant not found'}), 404

            new_status = data.get('status') if 'status' in data else current_app_row['status']
            new_notes = data.get('notes') if 'notes' in data else current_app_row['notes']
            new_city = clean_city(data.get('city')) if 'city' in data else current_app_row['city']
            new_phone = clean_phone(data.get('phone')) if 'phone' in data else current_app_row['phone']

            cur.execute('''
                UPDATE "JobApplicants"
                SET status = %s, notes = %s, city = %s, phone = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (new_status, new_notes, new_city, new_phone, id))
            conn.commit()
            return jsonify({'status': 'success', 'id': id})
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/workforce/subcontractors', methods=['GET', 'POST'])
@login_required
def api_get_or_create_subcontractors():
    """Retrieve subcontractor records with optional filtering, or onboard a new trade partner."""
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'POST':
                data = request.get_json() or {}
                company_name = (data.get('company_name') or '').strip()
                contact_name = (data.get('contact_name') or '').strip()
                phone = clean_phone(data.get('phone') or '')
                email = (data.get('email') or '').strip()

                if not company_name or not contact_name or not phone:
                    return jsonify({'status': 'error', 'message': 'Company name, contact name, and phone are mandatory.'}), 400

                ein_or_ssn = (data.get('ein_or_ssn') or '').strip()
                city = clean_city(data.get('city') or '')
                state = (data.get('state') or 'TX').strip()
                coverage_counties = (data.get('coverage_counties') or 'Dallas, Tarrant, Collin, Denton').strip()
                crew_size = int(data.get('crew_size') or 2)
                specialties = (data.get('specialties') or 'Commercial Cleaning').strip()
                hourly_rate_range = (data.get('hourly_rate_range') or '$25 - $35/hr').strip()
                coi_status = data.get('coi_status', 'Pending')
                coi_expiration_date = data.get('coi_expiration_date') or None
                w9_status = data.get('w9_status', 'Pending')
                dwc83_signed = bool(data.get('dwc83_signed', False))
                status = data.get('status', 'Active Partner')
                notes = (data.get('notes') or '').strip()

                cur.execute('''
                    INSERT INTO "SubcontractorPartners" (
                        company_name, ein_or_ssn, contact_name, phone, email,
                        city, state, coverage_counties, crew_size, specialties,
                        hourly_rate_range, coi_status, coi_expiration_date,
                        w9_status, dwc83_signed, status, notes
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s
                    ) RETURNING id;
                ''', (
                    company_name, ein_or_ssn, contact_name, phone, email,
                    city, state, coverage_counties, crew_size, specialties,
                    hourly_rate_range, coi_status, coi_expiration_date,
                    w9_status, dwc83_signed, status, notes
                ))
                new_id = cur.fetchone()['id']
                conn.commit()
                return jsonify({
                    'status': 'success',
                    'subcontractor_id': new_id,
                    'message': f"Trade Partner '{company_name}' onboarded successfully."
                }), 201

            # GET method
            status_filter = request.args.get('status')
            if status_filter:
                cur.execute('SELECT * FROM "SubcontractorPartners" WHERE status = %s ORDER BY created_at DESC;', (status_filter,))
            else:
                cur.execute('SELECT * FROM "SubcontractorPartners" ORDER BY created_at DESC;')
            rows = [serialize_row(r) for r in cur.fetchall()]
            from core.services.labor_market_analytics import analyze_subcontractor_rates
            labor_rate_metrics = analyze_subcontractor_rates(rows)
            return jsonify({
                'status': 'success',
                'count': len(rows),
                'subcontractors': rows,
                'labor_rate_metrics': labor_rate_metrics
            })
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/workforce/subcontractors/labor-rate-intelligence', methods=['GET'])
@login_required
def api_subcontractor_labor_rate_intelligence():
    """Enterprise intelligence endpoint returning live 1099 subcontractor wage analytics."""
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "SubcontractorPartners" ORDER BY created_at DESC;')
            rows = [serialize_row(r) for r in cur.fetchall()]
            from core.services.labor_market_analytics import analyze_subcontractor_rates
            metrics = analyze_subcontractor_rates(rows)
            return jsonify({'status': 'success', 'metrics': metrics})
    finally:
        if conn: conn.close()



@crm_api_bp.route('/api/v1/workforce/subcontractors/<int:id>', methods=['GET', 'PATCH', 'DELETE'])
@login_required
def api_manage_subcontractor(id):
    """View, update, or remove a subcontractor record."""
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'GET':
                cur.execute('SELECT * FROM "SubcontractorPartners" WHERE id = %s;', (id,))
                sub = cur.fetchone()
                if not sub:
                    return jsonify({'status': 'error', 'message': 'Subcontractor not found'}), 404
                return jsonify({'status': 'success', 'subcontractor': serialize_row(sub)})

            elif request.method == 'DELETE':
                cur.execute('DELETE FROM "SubcontractorPartners" WHERE id = %s;', (id,))
                conn.commit()
                return jsonify({'status': 'success', 'deleted_id': id})

            elif request.method == 'PATCH':
                data = request.get_json() or {}
                cur.execute('SELECT * FROM "SubcontractorPartners" WHERE id = %s;', (id,))
                current_sub = cur.fetchone()
                if not current_sub:
                    return jsonify({'status': 'error', 'message': 'Subcontractor not found'}), 404

                company_name = data.get('company_name', current_sub['company_name'])
                contact_name = data.get('contact_name', current_sub['contact_name'])
                phone = clean_phone(data.get('phone', current_sub['phone']))
                email = data.get('email', current_sub['email'])
                ein_or_ssn = data.get('ein_or_ssn', current_sub['ein_or_ssn'])
                city = clean_city(data.get('city', current_sub['city']))
                state = data.get('state', current_sub['state'])
                coverage_counties = data.get('coverage_counties', current_sub['coverage_counties'])
                crew_size = int(data.get('crew_size', current_sub['crew_size'] or 2))
                specialties = data.get('specialties', current_sub['specialties'])
                hourly_rate_range = data.get('hourly_rate_range', current_sub['hourly_rate_range'])
                coi_status = data.get('coi_status', current_sub['coi_status'])
                coi_expiration_date = data.get('coi_expiration_date') if 'coi_expiration_date' in data else current_sub['coi_expiration_date']
                w9_status = data.get('w9_status', current_sub['w9_status'])
                dwc83_signed = bool(data.get('dwc83_signed', current_sub['dwc83_signed']))
                status = data.get('status', current_sub['status'])
                notes = data.get('notes', current_sub['notes'])
                rating = float(data.get('rating', current_sub['rating'] or 5.0))

                cur.execute('''
                    UPDATE "SubcontractorPartners" SET
                        company_name = %s, contact_name = %s, phone = %s, email = %s,
                        ein_or_ssn = %s, city = %s, state = %s, coverage_counties = %s,
                        crew_size = %s, specialties = %s, hourly_rate_range = %s,
                        coi_status = %s, coi_expiration_date = %s, w9_status = %s,
                        dwc83_signed = %s, status = %s, notes = %s, rating = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                ''', (
                    company_name, contact_name, phone, email,
                    ein_or_ssn, city, state, coverage_counties,
                    crew_size, specialties, hourly_rate_range,
                    coi_status, coi_expiration_date, w9_status,
                    dwc83_signed, status, notes, rating, id
                ))
                conn.commit()
                return jsonify({'status': 'success', 'id': id, 'message': 'Subcontractor profile updated successfully.'})
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/workforce/subcontractors/<int:id>/documents', methods=['POST'])
@login_required
def api_upload_subcontractor_document(id):
    """Securely uploads and deposits COI or W-9 into the HR Vault for a subcontractor."""
    if 'document' not in request.files:
        return jsonify({'status': 'error', 'message': 'No document file provided.'}), 400

    file = request.files['document']
    doc_type = (request.form.get('document_type') or 'COI').strip()
    coi_expiration = request.form.get('expiration_date') or None

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'Empty file selected.'}), 400

    filename = secure_filename(file.filename)
    safe_name = f"sub_{id}_{doc_type.replace(' ', '_')}_{int(dt_cls.now().timestamp())}_{filename}"
    file_path = os.path.join(HR_VAULT_DIR, safe_name)
    file.save(file_path)

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if 'w-9' in doc_type.lower():
                cur.execute('''
                    UPDATE "SubcontractorPartners" 
                    SET w9_file_url = %s, w9_status = 'Verified', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                ''', (safe_name, id))
            elif 'dwc' in doc_type.lower():
                cur.execute('''
                    UPDATE "SubcontractorPartners" 
                    SET dwc83_signed = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                ''', (id,))
            else:  # COI
                exp_clause = ", coi_expiration_date = %s" if coi_expiration else ""
                params = [safe_name]
                if coi_expiration:
                    params.append(coi_expiration)
                params.append(id)
                cur.execute(f'''
                    UPDATE "SubcontractorPartners" 
                    SET coi_file_url = %s, coi_status = 'Verified'{exp_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                ''', tuple(params))

            conn.commit()
            return jsonify({
                'status': 'success',
                'file_name': filename,
                'document_type': doc_type,
                'message': f"{doc_type} securely deposited into Vault."
            }), 201
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/workforce/subcontractors/<int:id>/download/<doc_type>', methods=['GET'])
@login_required
def api_download_subcontractor_document(id, doc_type):
    """Securely downloads a subcontractor compliance document from the HR Vault."""
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT company_name, coi_file_url, w9_file_url FROM "SubcontractorPartners" WHERE id = %s;', (id,))
            sub = cur.fetchone()
            if not sub:
                return jsonify({'status': 'error', 'message': 'Subcontractor not found'}), 404

            file_key = sub['w9_file_url'] if doc_type.lower() == 'w9' else sub['coi_file_url']
            if not file_key:
                return jsonify({'status': 'error', 'message': f'No {doc_type.upper()} file deposited.'}), 404

            file_path = os.path.join(HR_VAULT_DIR, file_key)
            if not os.path.exists(file_path):
                return jsonify({'status': 'error', 'message': 'Document file not found on disk'}), 404

            return send_file(file_path, as_attachment=True, download_name=f"{sub['company_name'].replace(' ', '_')}_{doc_type.upper()}.pdf")
    finally:
        if conn: conn.close()


# =========================================================================
# SigmaFidelity™ Human Resources & Payroll Management Engine
# Standard: HWB-QMS-7.6 / ISO 9001:2015 Clause 7.2 (Competence)
# =========================================================================

HR_VAULT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vault', 'hr_documents'))
os.makedirs(HR_VAULT_DIR, exist_ok=True)


@crm_api_bp.route('/api/v1/hr/onboard', methods=['POST'])
@login_required
def api_hr_onboard_candidate():
    """
    Onboards a candidate into the Employees ledger.
    Can be linked to an existing JobApplicant or created fresh.
    Auto-generates employee_number (HWB-EMP-####).
    """
    data = request.get_json() or {}
    applicant_id = data.get('applicant_id')
    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()
    phone = clean_phone(data.get('phone') or '')
    email = (data.get('email') or '').strip()
    
    if not first_name or not last_name or not phone:
        return jsonify({'status': 'error', 'message': 'First name, last name, and phone are mandatory.'}), 400

    role = (data.get('primary_role') or 'Commercial Cleaning Technician').strip()
    employment_type = data.get('employment_type', 'W-2 Full-Time')
    employment_status = data.get('employment_status', 'Active')
    hire_date = data.get('hire_date') or dt_cls.now().strftime('%Y-%m-%d')
    pay_rate = float(data.get('pay_rate_hourly') or 16.00)
    overtime_rate = float(data.get('overtime_rate_hourly') or (pay_rate * 1.5))
    pay_frequency = data.get('pay_frequency', 'Bi-Weekly')
    primary_language = data.get('primary_language', 'Spanish')
    city = clean_city(data.get('city') or '')
    state = (data.get('state') or 'TX').strip()
    emergency_name = (data.get('emergency_contact_name') or '').strip()
    emergency_phone = clean_phone(data.get('emergency_contact_phone') or '')
    assigned_customer_id = data.get('assigned_customer_id') or None
    weekly_hours = float(data.get('weekly_hours_allocated') or 40.00)
    notes = (data.get('notes') or '').strip()
    raw_pos_id = data.get('job_position_id')
    job_position_id = None
    if raw_pos_id:
        try:
            job_position_id = int(raw_pos_id)
        except (ValueError, TypeError):
            job_position_id = None

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if not job_position_id:
                cur.execute('SELECT id, title FROM "JobPositions" WHERE title ILIKE %s OR position_code = %s LIMIT 1;', (role, role))
                pos_row = cur.fetchone()
                if pos_row:
                    job_position_id = pos_row['id']

            cur.execute('SELECT MAX(id) as max_id FROM "Employees";')
            max_row = cur.fetchone()
            next_id = (max_row['max_id'] or 0) + 1001
            emp_number = f"HWB-EMP-{next_id}"

            cur.execute('''
                INSERT INTO "Employees" (
                    employee_number, applicant_id, first_name, last_name, phone, email,
                    hire_date, employment_status, employment_type, primary_role,
                    pay_rate_hourly, overtime_rate_hourly, pay_frequency, primary_language,
                    emergency_contact_name, emergency_contact_phone, address_city, address_state,
                    assigned_customer_id, weekly_hours_allocated, notes,
                    job_position_id, job_description_acknowledged_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, NOW()
                ) RETURNING id, employee_number;
            ''', (
                emp_number, applicant_id, first_name, last_name, phone, email,
                hire_date, employment_status, employment_type, role,
                pay_rate, overtime_rate, pay_frequency, primary_language,
                emergency_name, emergency_phone, city, state,
                assigned_customer_id, weekly_hours, notes,
                job_position_id
            ))
            new_emp = cur.fetchone()

            if applicant_id:
                cur.execute('''
                    UPDATE "JobApplicants" 
                    SET status = 'Hired', notes = COALESCE(notes, '') || E'\n[ONBOARDED] Hired as ' || %s || E' (' || %s || E')'
                    WHERE id = %s;
                ''', (role, emp_number, applicant_id))

            conn.commit()
            return jsonify({
                'status': 'success',
                'employee_id': new_emp['id'],
                'employee_number': new_emp['employee_number'],
                'message': f"Employee {first_name} {last_name} ({new_emp['employee_number']}) onboarded successfully."
            }), 201
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/hr/employees', methods=['GET'])
@login_required
def api_get_employees():
    """Retrieve all employees with optional role, status, or search filters."""
    status_filter = request.args.get('status')
    role_filter = request.args.get('role')
    search_q = (request.args.get('q') or '').strip().lower()

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            query = '''
                SELECT e.*, c.company_name as assigned_facility_name,
                       jp.position_code as job_position_code, jp.title as job_position_title,
                       jp.hourly_min as job_position_hourly_min, jp.hourly_max as job_position_hourly_max,
                       (SELECT COUNT(*) FROM "EmployeeDocuments" d WHERE d.employee_id = e.id) as document_count
                FROM "Employees" e
                LEFT JOIN "Customers" c ON e.assigned_customer_id = c.customer_id
                LEFT JOIN "JobPositions" jp ON e.job_position_id = jp.id
                WHERE 1=1
            '''
            params = []
            if status_filter:
                query += ' AND e.employment_status = %s'
                params.append(status_filter)
            if role_filter:
                query += ' AND e.primary_role = %s'
                params.append(role_filter)
            if search_q:
                query += ' AND (LOWER(e.first_name) LIKE %s OR LOWER(e.last_name) LIKE %s OR LOWER(e.employee_number) LIKE %s OR LOWER(e.phone) LIKE %s)'
                like_term = f"%{search_q}%"
                params.extend([like_term, like_term, like_term, like_term])

            query += ' ORDER BY e.created_at DESC;'
            cur.execute(query, tuple(params))
            raw_rows = cur.fetchall()
            rows = []
            for r in raw_rows:
                s_row = serialize_row(r)
                # Security Sanitize: Zero plaintext leaks
                s_row.pop('ssn_encrypted', None)
                s_row.pop('direct_deposit_account_encrypted', None)
                s_row['has_ssn'] = bool(r.get('ssn_last_four'))
                s_row['ssn_masked'] = mask_ssn(last_four=r.get('ssn_last_four')) if r.get('ssn_last_four') else ''
                s_row['ssn_last_four'] = r.get('ssn_last_four') or ''
                if r.get('direct_deposit_account_last_four'):
                    s_row['direct_deposit_account_masked'] = mask_account(last_four=r.get('direct_deposit_account_last_four'))
                elif r.get('direct_deposit_account'):
                    s_row['direct_deposit_account_masked'] = mask_account(raw_acc=r.get('direct_deposit_account'))
                else:
                    s_row['direct_deposit_account_masked'] = ''
                s_row['direct_deposit_account'] = s_row['direct_deposit_account_masked']
                rows.append(s_row)
            return jsonify({'status': 'success', 'count': len(rows), 'employees': rows})
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/hr/employees/<int:id>', methods=['GET', 'PATCH', 'DELETE'])
@login_required
def api_manage_employee(id):
    """View, update, or terminate an employee record."""
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'GET':
                cur.execute('''
                    SELECT e.*, c.company_name as assigned_facility_name,
                           jp.position_code as job_position_code, jp.title as job_position_title,
                           jp.department as job_position_department, jp.reports_to as job_position_reports_to,
                           jp.summary as job_position_summary, jp.key_responsibilities as job_position_responsibilities,
                           jp.required_competencies as job_position_competencies, jp.required_experience as job_position_experience,
                           jp.required_certifications as job_position_certifications, jp.physical_demands as job_position_physical_demands,
                           jp.work_environment as job_position_work_environment, jp.hourly_min as job_position_hourly_min,
                           jp.hourly_max as job_position_hourly_max, jp.sop_template_id as job_position_sop_id
                    FROM "Employees" e
                    LEFT JOIN "Customers" c ON e.assigned_customer_id = c.customer_id
                    LEFT JOIN "JobPositions" jp ON e.job_position_id = jp.id
                    WHERE e.id = %s;
                ''', (id,))
                emp = cur.fetchone()
                if not emp:
                    return jsonify({'status': 'error', 'message': 'Employee not found'}), 404
                
                cur.execute('SELECT * FROM "EmployeeDocuments" WHERE employee_id = %s ORDER BY created_at DESC;', (id,))
                docs = [serialize_row(d) for d in cur.fetchall()]

                emp_data = serialize_row(emp)
                emp_data['documents'] = docs
                # PII Vault Serialization (SOC 2 / ISO 27001)
                emp_data.pop('ssn_encrypted', None)
                emp_data.pop('direct_deposit_account_encrypted', None)
                emp_data['has_ssn'] = bool(emp.get('ssn_last_four'))
                emp_data['ssn_last_four'] = emp.get('ssn_last_four') or ''
                emp_data['ssn_masked'] = mask_ssn(last_four=emp.get('ssn_last_four')) if emp.get('ssn_last_four') else ''
                if emp.get('direct_deposit_account_last_four'):
                    emp_data['direct_deposit_account_masked'] = mask_account(last_four=emp.get('direct_deposit_account_last_four'))
                elif emp.get('direct_deposit_account'):
                    emp_data['direct_deposit_account_masked'] = mask_account(raw_acc=emp.get('direct_deposit_account'))
                else:
                    emp_data['direct_deposit_account_masked'] = ''
                emp_data['direct_deposit_account'] = emp_data['direct_deposit_account_masked']
                return jsonify({'status': 'success', 'employee': emp_data})

            elif request.method == 'DELETE':
                cur.execute('''
                    UPDATE "Employees" 
                    SET employment_status = 'Terminated', termination_date = CURRENT_DATE, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                ''', (id,))
                conn.commit()
                return jsonify({'status': 'success', 'message': f'Employee #{id} marked Terminated.'})

            elif request.method == 'PATCH':
                data = request.get_json() or {}
                cur.execute('SELECT * FROM "Employees" WHERE id = %s;', (id,))
                emp = cur.fetchone()
                if not emp:
                    return jsonify({'status': 'error', 'message': 'Employee not found'}), 404

                first_name = data.get('first_name', emp['first_name'])
                last_name = data.get('last_name', emp['last_name'])
                phone = clean_phone(data.get('phone', emp['phone']))
                email = data.get('email', emp['email'])
                primary_role = data.get('primary_role', emp['primary_role'])
                employment_status = data.get('employment_status', emp['employment_status'])
                employment_type = data.get('employment_type', emp['employment_type'])
                pay_rate = float(data.get('pay_rate_hourly', emp['pay_rate_hourly']))
                overtime_rate = float(data.get('overtime_rate_hourly', emp['overtime_rate_hourly']))
                primary_language = data.get('primary_language', emp['primary_language'])
                weekly_hours = float(data.get('weekly_hours_allocated', emp['weekly_hours_allocated']))
                emergency_name = data.get('emergency_contact_name', emp['emergency_contact_name'])
                emergency_phone = clean_phone(data.get('emergency_contact_phone', emp['emergency_contact_phone']))
                city = clean_city(data.get('address_city', emp['address_city']))
                street = data.get('address_street', emp.get('address_street'))
                zip_code = clean_zip(data.get('address_zip', emp.get('address_zip')))
                pay_frequency = data.get('pay_frequency', emp.get('pay_frequency') or 'Bi-Weekly')
                notes = data.get('notes', emp['notes'])

                # Assigned facility handle null/empty
                if 'assigned_customer_id' in data:
                    raw_cust = data.get('assigned_customer_id')
                    assigned_customer_id = int(raw_cust) if raw_cust not in (None, '', 0, '0') else None
                else:
                    assigned_customer_id = emp.get('assigned_customer_id')

                # Helper date/string cleaners
                def clean_date_field(val):
                    if val is None or str(val).strip() == '':
                        return None
                    return str(val).strip()

                def clean_str_field(val):
                    if val is None:
                        return None
                    s = str(val).strip()
                    return s if s else None

                # Lifecycle, W-4, and Compliance Fields
                w4_filing_status = clean_str_field(data.get('w4_filing_status')) or emp.get('w4_filing_status') or 'Single'
                w4_step2_multiple_jobs = bool(data.get('w4_step2_multiple_jobs', emp.get('w4_step2_multiple_jobs') or False))
                try:
                    w4_step3_dependents = float(data.get('w4_step3_dependents', emp.get('w4_step3_dependents') or 0.0) or 0.0)
                except (ValueError, TypeError):
                    w4_step3_dependents = 0.0
                try:
                    w4_step4c_extra_withholding = float(data.get('w4_step4c_extra_withholding', emp.get('w4_step4c_extra_withholding') or 0.0) or 0.0)
                except (ValueError, TypeError):
                    w4_step4c_extra_withholding = 0.0

                pto_start_date = clean_date_field(data['pto_start_date']) if 'pto_start_date' in data else emp.get('pto_start_date')
                pto_end_date = clean_date_field(data['pto_end_date']) if 'pto_end_date' in data else emp.get('pto_end_date')
                termination_reason = clean_str_field(data['termination_reason']) if 'termination_reason' in data else emp.get('termination_reason')

                if 'eligible_for_rehire' in data:
                    eligible_for_rehire = bool(data['eligible_for_rehire'])
                else:
                    eligible_for_rehire = True if emp.get('eligible_for_rehire') is None else bool(emp.get('eligible_for_rehire'))

                state_id_number = clean_str_field(data['state_id_number']) if 'state_id_number' in data else emp.get('state_id_number')
                state_id_expiration = clean_date_field(data['state_id_expiration']) if 'state_id_expiration' in data else emp.get('state_id_expiration')
                dps_clearance_date = clean_date_field(data['dps_clearance_date']) if 'dps_clearance_date' in data else emp.get('dps_clearance_date')
                i9_verification_date = clean_date_field(data['i9_verification_date']) if 'i9_verification_date' in data else emp.get('i9_verification_date')
                direct_deposit_bank = clean_str_field(data['direct_deposit_bank']) if 'direct_deposit_bank' in data else emp.get('direct_deposit_bank')
                direct_deposit_routing = clean_str_field(data['direct_deposit_routing']) if 'direct_deposit_routing' in data else emp.get('direct_deposit_routing')

                # PII Vault Handling: Social Security Number / ITIN
                raw_ssn = None
                if 'social_security_number' in data:
                    raw_ssn = clean_str_field(data.get('social_security_number'))
                elif 'ssn' in data:
                    raw_ssn = clean_str_field(data.get('ssn'))

                if raw_ssn is not None:
                    # Check if user entered an unmasked SSN
                    if raw_ssn and not raw_ssn.startswith('***') and not raw_ssn.startswith('•••'):
                        digits = re.sub(r'\D', '', raw_ssn)
                        if len(digits) == 9:
                            formatted_ssn = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
                            ssn_encrypted = encrypt_pii(formatted_ssn)
                            ssn_last_four = digits[-4:]
                        elif len(digits) >= 4:
                            ssn_encrypted = encrypt_pii(raw_ssn)
                            ssn_last_four = digits[-4:]
                        else:
                            ssn_encrypted = None
                            ssn_last_four = None
                    elif raw_ssn == '':
                        ssn_encrypted = None
                        ssn_last_four = None
                    else:
                        ssn_encrypted = emp.get('ssn_encrypted')
                        ssn_last_four = emp.get('ssn_last_four')
                else:
                    ssn_encrypted = emp.get('ssn_encrypted')
                    ssn_last_four = emp.get('ssn_last_four')

                # PII Vault Handling: Direct Deposit Account
                if 'direct_deposit_account' in data:
                    raw_dda = clean_str_field(data.get('direct_deposit_account'))
                    if raw_dda and not raw_dda.startswith('••••') and not raw_dda.startswith('****'):
                        dda_clean = re.sub(r'\s', '', raw_dda)
                        direct_deposit_account_encrypted = encrypt_pii(dda_clean)
                        direct_deposit_account_last_four = dda_clean[-4:] if len(dda_clean) >= 4 else dda_clean
                        direct_deposit_account = mask_account(raw_acc=dda_clean)
                    elif raw_dda == '':
                        direct_deposit_account_encrypted = None
                        direct_deposit_account_last_four = None
                        direct_deposit_account = None
                    else:
                        direct_deposit_account_encrypted = emp.get('direct_deposit_account_encrypted')
                        direct_deposit_account_last_four = emp.get('direct_deposit_account_last_four')
                        direct_deposit_account = emp.get('direct_deposit_account')
                else:
                    direct_deposit_account_encrypted = emp.get('direct_deposit_account_encrypted')
                    direct_deposit_account_last_four = emp.get('direct_deposit_account_last_four')
                    direct_deposit_account = emp.get('direct_deposit_account')

                # Automated Security Lockout Protocol (Poka-Yoke)
                badge_status = data.get('badge_status', emp.get('badge_status') or 'Active')
                termination_date = emp.get('termination_date')

                if employment_status in ['Terminated', 'Fired']:
                    badge_status = 'Revoked'
                    if not termination_date:
                        termination_date = datetime.date.today()
                    # Revoke candidate in JobApplicants table if linked
                    if emp.get('applicant_id'):
                        cur.execute('''
                            UPDATE "JobApplicants" 
                            SET status = 'Terminated', updated_at = CURRENT_TIMESTAMP 
                            WHERE id = %s;
                        ''', (emp['applicant_id'],))
                elif employment_status in ['On Leave', 'Suspended']:
                    badge_status = 'Suspended'
                elif employment_status == 'Active':
                    badge_status = 'Active'

                raw_job_pos_id = data.get('job_position_id')
                if raw_job_pos_id is not None:
                    try:
                        job_position_id = int(raw_job_pos_id) if raw_job_pos_id else None
                    except (ValueError, TypeError):
                        job_position_id = emp.get('job_position_id')
                else:
                    job_position_id = emp.get('job_position_id')

                if data.get('job_description_acknowledged'):
                    job_description_acknowledged_at = dt_cls.now()
                else:
                    job_description_acknowledged_at = emp.get('job_description_acknowledged_at')

                cur.execute('''
                    UPDATE "Employees" SET
                        first_name = %s, last_name = %s, phone = %s, email = %s,
                        primary_role = %s, employment_status = %s, employment_type = %s,
                        pay_rate_hourly = %s, overtime_rate_hourly = %s, primary_language = %s,
                        assigned_customer_id = %s, weekly_hours_allocated = %s,
                        emergency_contact_name = %s, emergency_contact_phone = %s,
                        address_street = %s, address_city = %s, address_zip = %s,
                        pay_frequency = %s, notes = %s,
                        w4_filing_status = %s, w4_step2_multiple_jobs = %s,
                        w4_step3_dependents = %s, w4_step4c_extra_withholding = %s,
                        pto_start_date = %s, pto_end_date = %s,
                        termination_reason = %s, eligible_for_rehire = %s,
                        badge_status = %s, termination_date = %s,
                        state_id_number = %s, state_id_expiration = %s,
                        dps_clearance_date = %s, i9_verification_date = %s,
                        direct_deposit_bank = %s, direct_deposit_routing = %s,
                        direct_deposit_account = %s,
                        ssn_encrypted = %s, ssn_last_four = %s,
                        direct_deposit_account_encrypted = %s, direct_deposit_account_last_four = %s,
                        job_position_id = %s, job_description_acknowledged_at = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                ''', (
                    first_name, last_name, phone, email,
                    primary_role, employment_status, employment_type,
                    pay_rate, overtime_rate, primary_language,
                    assigned_customer_id, weekly_hours,
                    emergency_name, emergency_phone,
                    street, city, zip_code,
                    pay_frequency, notes,
                    w4_filing_status, w4_step2_multiple_jobs,
                    w4_step3_dependents, w4_step4c_extra_withholding,
                    pto_start_date, pto_end_date,
                    termination_reason, eligible_for_rehire,
                    badge_status, termination_date,
                    state_id_number, state_id_expiration,
                    dps_clearance_date, i9_verification_date,
                    direct_deposit_bank, direct_deposit_routing,
                    direct_deposit_account,
                    ssn_encrypted, ssn_last_four,
                    direct_deposit_account_encrypted, direct_deposit_account_last_four,
                    job_position_id, job_description_acknowledged_at,
                    id
                ))
                conn.commit()
                return jsonify({
                    'status': 'success',
                    'id': id,
                    'badge_status': badge_status,
                    'has_ssn': bool(ssn_last_four),
                    'ssn_masked': mask_ssn(last_four=ssn_last_four) if ssn_last_four else '',
                    'direct_deposit_account_masked': mask_account(last_four=direct_deposit_account_last_four) if direct_deposit_account_last_four else '',
                    'message': f'Employee #{id} ({first_name} {last_name}) updated successfully.'
                })
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/hr/employees/<int:id>/reveal-ssn', methods=['POST'])
@login_required
def api_reveal_employee_ssn(id):
    """
    Enterprise PII Reveal Protocol (SOC 2 / ISO 27001):
    Allows authorized administrators to decrypt and view an employee's Social Security Number
    with mandatory audit logging to GlobalActivities and automatic 30-second client-side remasking.
    """
    if current_user.role not in ['Executive', 'Admin', 'Operations']:
        log_security_violation(current_user.id, current_user.username, current_user.role, request.path, request.method)
        return jsonify({'status': 'error', 'message': 'Unauthorized to view sensitive identification data.'}), 403

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, first_name, last_name, ssn_encrypted, ssn_last_four FROM "Employees" WHERE id = %s;', (id,))
            emp = cur.fetchone()
            if not emp:
                return jsonify({'status': 'error', 'message': 'Employee not found'}), 404

            ssn_encrypted = emp.get('ssn_encrypted')
            if not ssn_encrypted:
                return jsonify({'status': 'error', 'message': 'No Social Security Number on file for this employee.'}), 404

            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            log_sensitive_access(
                user_id=current_user.id,
                username=current_user.username,
                employee_id=id,
                field_name='Social Security Number',
                ip_address=client_ip
            )

            decrypted_ssn = decrypt_pii(ssn_encrypted)
            if not decrypted_ssn:
                return jsonify({'status': 'error', 'message': 'Cryptographic decryption failed.'}), 500

            return jsonify({
                'status': 'success',
                'ssn': decrypted_ssn,
                'ssn_last_four': emp.get('ssn_last_four'),
                'remask_seconds': 30,
                'message': 'Decrypted SSN revealed. View will automatically lock and re-mask in 30 seconds.'
            })
    finally:
        if conn:
            conn.close()


@crm_api_bp.route('/api/v1/hr/employees/<int:id>/documents', methods=['POST'])
@login_required
def api_upload_employee_document(id):
    """Securely uploads and attaches a compliance document to an employee record."""
    if 'document' not in request.files:
        return jsonify({'status': 'error', 'message': 'No document file provided.'}), 400
    
    file = request.files['document']
    doc_type = (request.form.get('document_type') or 'Form I-9').strip()
    notes = (request.form.get('notes') or '').strip()
    expiration_date = request.form.get('expiration_date') or None

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'Empty file selected.'}), 400

    filename = secure_filename(file.filename)
    safe_name = f"emp_{id}_{int(dt_cls.now().timestamp())}_{filename}"
    file_path = os.path.join(HR_VAULT_DIR, safe_name)
    file.save(file_path)
    file_size = os.path.getsize(file_path)
    mime_type = file.mimetype or 'application/octet-stream'

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO "EmployeeDocuments" (
                    employee_id, document_type, file_name, file_path, file_size,
                    mime_type, verification_status, expiration_date, verified_by, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            ''', (
                id, doc_type, filename, safe_name, file_size,
                mime_type, 'Verified', expiration_date, 'Humberto Dominguez', notes
            ))
            doc_id = cur.fetchone()['id']
            conn.commit()
            return jsonify({
                'status': 'success',
                'document_id': doc_id,
                'file_name': filename,
                'message': f"{doc_type} securely deposited into Vault."
            }), 201
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/hr/documents/<int:doc_id>/download', methods=['GET'])
@login_required
def api_download_employee_document(doc_id):
    """Secure authorized download/view of an employee document from the Vault."""
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "EmployeeDocuments" WHERE id = %s;', (doc_id,))
            doc = cur.fetchone()
            if not doc:
                return jsonify({'status': 'error', 'message': 'Document not found'}), 404
            
            full_path = os.path.join(HR_VAULT_DIR, doc['file_path'])
            if not os.path.exists(full_path):
                return jsonify({'status': 'error', 'message': 'File missing from Vault storage'}), 404
            
            return send_file(full_path, mimetype=doc['mime_type'], as_attachment=False, download_name=doc['file_name'])
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/hr/payroll', methods=['GET'])
@login_required
def api_get_payroll_summary():
    """Generates the current payroll summary across all active personnel."""
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT e.id, e.employee_number, e.first_name, e.last_name, e.primary_role,
                       e.employment_type, e.pay_rate_hourly, e.weekly_hours_allocated,
                       c.company_name as assigned_facility_name
                FROM "Employees" e
                LEFT JOIN "Customers" c ON e.assigned_customer_id = c.customer_id
                WHERE e.employment_status = 'Active'
                ORDER BY e.last_name ASC;
            ''')
            employees = cur.fetchall()
            
            payroll_items = []
            total_weekly_hours = 0.0
            total_biweekly_gross = 0.0

            for emp in employees:
                hours = float(emp['weekly_hours_allocated'] or 0.0)
                rate = float(emp['pay_rate_hourly'] or 0.0)
                biweekly_hours = hours * 2.0
                biweekly_gross = biweekly_hours * rate

                total_weekly_hours += hours
                total_biweekly_gross += biweekly_gross

                payroll_items.append({
                    'id': emp['id'],
                    'employee_number': emp['employee_number'],
                    'name': f"{emp['first_name']} {emp['last_name']}",
                    'role': emp['primary_role'],
                    'facility': emp['assigned_facility_name'] or 'Floater / Unassigned',
                    'weekly_hours': round(hours, 2),
                    'hourly_rate': round(rate, 2),
                    'biweekly_hours': round(biweekly_hours, 2),
                    'biweekly_gross': round(biweekly_gross, 2)
                })

            return jsonify({
                'status': 'success',
                'count': len(payroll_items),
                'total_weekly_hours': round(total_weekly_hours, 2),
                'total_biweekly_gross': round(total_biweekly_gross, 2),
                'payroll': payroll_items
            })
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/hr/payroll/export', methods=['GET'])
@login_required
def api_export_payroll_csv():
    """Exports payroll summary as a CSV file formatted for QuickBooks / Gusto / ADP."""
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT e.employee_number, e.first_name, e.last_name, e.phone, e.email,
                       e.primary_role, e.employment_type, e.pay_rate_hourly, e.weekly_hours_allocated,
                       c.company_name as assigned_facility_name
                FROM "Employees" e
                LEFT JOIN "Customers" c ON e.assigned_customer_id = c.customer_id
                WHERE e.employment_status = 'Active'
                ORDER BY e.last_name ASC;
            ''')
            rows = cur.fetchall()

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                'Employee ID', 'First Name', 'Last Name', 'Role', 'Employment Type',
                'Hourly Rate ($)', 'Weekly Hours', 'Bi-Weekly Hours', 'Gross Pay ($)',
                'Assigned Facility', 'Phone', 'Email'
            ])

            for r in rows:
                hours = float(r['weekly_hours_allocated'] or 0.0)
                rate = float(r['pay_rate_hourly'] or 0.0)
                biweekly_hours = hours * 2.0
                gross_pay = biweekly_hours * rate
                writer.writerow([
                    r['employee_number'], r['first_name'], r['last_name'], r['primary_role'],
                    r['employment_type'], f"{rate:.2f}", f"{hours:.2f}", f"{biweekly_hours:.2f}",
                    f"{gross_pay:.2f}", r['assigned_facility_name'] or 'Floater', r['phone'], r['email'] or ''
                ])

            output.seek(0)
            log_security_event(
                event_category='DATA_LIFECYCLE',
                event_action='BULK_DATA_EXPORT',
                severity='WARNING',
                details={'export_type': 'payroll', 'row_count': len(rows)}
            )
            timestamp = dt_cls.now().strftime('%Y%m%d')
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-disposition": f"attachment; filename=HWB_Payroll_Export_{timestamp}.csv"}
            )
    finally:
        if conn: conn.close()

# -------------------------------------------------------------------------
# SigmaFidelity™ Job Positions & Digital Job Descriptions (HWB-FORM-7.2-001)
# -------------------------------------------------------------------------

@crm_api_bp.route('/api/v1/hr/job-positions', methods=['GET'])
def api_get_job_positions():
    """
    Returns active job positions and specifications.
    Publicly accessible for the careers portal (/work-with-us) and backoffice hiring workflows.
    """
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, position_code, title, department, reports_to, summary,
                       key_responsibilities, required_competencies, required_experience,
                       required_certifications, physical_demands, work_environment,
                       hourly_min, hourly_max, standard_weekly_hours, is_active,
                       sop_template_id, created_at, updated_at
                FROM "JobPositions"
                WHERE is_active = TRUE
                ORDER BY id ASC;
            ''')
            rows = cur.fetchall()
            return jsonify({
                'status': 'success',
                'count': len(rows),
                'positions': [serialize_row(r) for r in rows]
            })
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/hr/job-positions/<int:id>', methods=['GET'])
def api_get_job_position_detail(id):
    """
    Returns full digital job description specifications conforming to HWB-FORM-7.2-001.
    """
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "JobPositions" WHERE id = %s;', (id,))
            pos = cur.fetchone()
            if not pos:
                return jsonify({'status': 'error', 'message': 'Job position not found'}), 404
            return jsonify({
                'status': 'success',
                'position': serialize_row(pos)
            })
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/hr/employees/<int:id>/acknowledge-job-description', methods=['POST'])
@login_required
def api_acknowledge_job_description(id):
    """
    Records official employee / supervisor acknowledgement of HWB-FORM-7.2-001 Job Description.
    Satisfies ISO 9001:2015 Clause 7.2 (Competence) and HWB-QMS-7.2 standards.
    """
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE "Employees"
                SET job_description_acknowledged_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, employee_number, first_name, last_name, job_position_id, job_description_acknowledged_at;
            ''', (id,))
            emp = cur.fetchone()
            if not emp:
                return jsonify({'status': 'error', 'message': 'Employee not found'}), 404

            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, 'Employee', 'Compliance', %s);
            ''', (id, f"Job Description (HWB-FORM-7.2-001) acknowledged by {current_user.username} for {emp['first_name']} {emp['last_name']} ({emp['employee_number']})."))

            conn.commit()
            return jsonify({
                'status': 'success',
                'message': 'Job Description acknowledged successfully.',
                'employee': serialize_row(emp)
            })
    finally:
        if conn: conn.close()


# -------------------------------------------------------------------------
# SigmaFidelity™ Work Order Dispatch & Execution Engine (HWB-QMS-11.2)
# -------------------------------------------------------------------------

@crm_api_bp.route('/api/v1/dispatch/work-orders', methods=['GET'])
@login_required
def api_get_dispatch_work_orders():
    """Returns all work orders with facility, service, technician, and shift metadata."""
    status_filter = request.args.get('status')
    customer_id = request.args.get('customer_id')
    date_filter = request.args.get('date')
    technician_id = request.args.get('technician_id')
    search_q = (request.args.get('q') or '').strip().lower()

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            query = '''
                SELECT w.*, 
                       c.company_name, 
                       c.company_address as facility_address,
                       c.city as facility_city,
                       COALESCE(s.service_requested, w.service_type, 'Routine Nightly Custodial') as service_name,
                       e.first_name as tech_first_name,
                       e.last_name as tech_last_name,
                       e.employee_number as tech_employee_number,
                       e.phone as tech_phone,
                       e.dps_clearance_date as tech_dps_clearance,
                       e.badge_status as tech_badge_status
                FROM "WorkOrders" w
                JOIN "Customers" c ON w.customer_id = c.customer_id
                LEFT JOIN "Services" s ON w.service_id = s.service_id
                LEFT JOIN "Employees" e ON COALESCE(w.assigned_technician_id, w.crew_lead_id) = e.id
                WHERE 1=1
            '''
            params = []
            if status_filter:
                query += ' AND UPPER(w.status) = UPPER(%s)'
                params.append(status_filter)
            if customer_id:
                query += ' AND w.customer_id = %s'
                params.append(int(customer_id))
            if date_filter:
                query += ' AND w.scheduled_date = %s'
                params.append(date_filter)
            if technician_id:
                query += ' AND COALESCE(w.assigned_technician_id, w.crew_lead_id) = %s'
                params.append(int(technician_id))
            if search_q:
                query += ''' AND (
                    LOWER(c.company_name) LIKE %s OR 
                    LOWER(COALESCE(w.service_type, '')) LIKE %s OR 
                    LOWER(COALESCE(e.first_name, '')) LIKE %s OR 
                    LOWER(COALESCE(e.last_name, '')) LIKE %s OR
                    LOWER(COALESCE(w.dock_ingress_instructions, '')) LIKE %s
                )'''
                l_term = f"%{search_q}%"
                params.extend([l_term, l_term, l_term, l_term, l_term])

            query += ' ORDER BY w.scheduled_date DESC, w.work_order_id DESC;'
            cur.execute(query, tuple(params))
            rows = [serialize_row(r) for r in cur.fetchall()]
            return jsonify({'status': 'success', 'count': len(rows), 'work_orders': rows})
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/dispatch/work-orders', methods=['POST'])
@login_required
def api_create_dispatch_work_order():
    """Creates a new shift dispatch and assigns a technician."""
    data = request.get_json() or {}
    customer_id = data.get('customer_id')
    if not customer_id:
        return jsonify({'status': 'error', 'message': 'Customer ID is required.'}), 400

    service_id = data.get('service_id') or None
    if service_id in ('', '0', 0):
        service_id = None
    else:
        try:
            service_id = int(service_id)
        except (ValueError, TypeError):
            service_id = None

    scheduled_date = data.get('scheduled_date') or dt_cls.now().strftime('%Y-%m-%d')
    scheduled_time = data.get('scheduled_time') or '18:00'
    shift_window = data.get('shift_window') or 'Evening Shift (6:00 PM – 11:00 PM)'
    service_type = data.get('service_type') or 'Routine Nightly Custodial'
    
    assigned_tech_id = data.get('assigned_technician_id') or None
    if assigned_tech_id in ('', '0', 0):
        assigned_tech_id = None
    else:
        try:
            assigned_tech_id = int(assigned_tech_id)
        except (ValueError, TypeError):
            assigned_tech_id = None

    status = data.get('status') or 'Scheduled'
    client_notes = (data.get('client_notes') or '').strip()
    crew_notes = (data.get('crew_notes') or '').strip()
    dock_ingress = (data.get('dock_ingress_instructions') or '').strip()
    security_code = (data.get('security_access_code') or '').strip()

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO "WorkOrders" (
                    customer_id, service_id, scheduled_date, scheduled_time,
                    shift_window, service_type, assigned_technician_id, crew_lead_id,
                    status, client_notes, crew_notes, dock_ingress_instructions,
                    security_access_code
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s
                ) RETURNING work_order_id;
            ''', (
                int(customer_id), service_id, scheduled_date, scheduled_time,
                shift_window, service_type, assigned_tech_id, assigned_tech_id,
                status, client_notes, crew_notes, dock_ingress,
                security_code
            ))
            new_id = cur.fetchone()['work_order_id']

            # Log audit activity
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, 'WorkOrder', 'Shift Dispatch Created', %s);
            ''', (new_id, f"Work Order #{new_id} scheduled for {scheduled_date} ({shift_window})."))

            conn.commit()
            return jsonify({
                'status': 'success',
                'work_order_id': new_id,
                'message': f"Work Order #{new_id} successfully created and dispatched."
            }), 201
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/dispatch/work-orders/<int:order_id>', methods=['GET', 'PATCH', 'DELETE'])
@login_required
def api_manage_dispatch_work_order(order_id: int):
    """Retrieves, updates, or cancels a specific dispatch work order."""
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'GET':
                cur.execute('''
                    SELECT w.*, 
                           c.company_name, 
                           c.company_address as facility_address,
                           c.city as facility_city,
                           COALESCE(s.service_requested, w.service_type, 'Routine Nightly Custodial') as service_name,
                           e.first_name as tech_first_name,
                           e.last_name as tech_last_name,
                           e.employee_number as tech_employee_number,
                           e.phone as tech_phone,
                           e.dps_clearance_date as tech_dps_clearance,
                           e.badge_status as tech_badge_status
                    FROM "WorkOrders" w
                    JOIN "Customers" c ON w.customer_id = c.customer_id
                    LEFT JOIN "Services" s ON w.service_id = s.service_id
                    LEFT JOIN "Employees" e ON COALESCE(w.assigned_technician_id, w.crew_lead_id) = e.id
                    WHERE w.work_order_id = %s;
                ''', (order_id,))
                order = cur.fetchone()
                if not order:
                    return jsonify({'status': 'error', 'message': 'Work order not found.'}), 404
                return jsonify({'status': 'success', 'work_order': serialize_row(order)})

            elif request.method == 'DELETE':
                cur.execute('UPDATE "WorkOrders" SET status = \'Canceled\' WHERE work_order_id = %s;', (order_id,))
                conn.commit()
                return jsonify({'status': 'success', 'message': f"Work order #{order_id} marked as Canceled."})

            elif request.method == 'PATCH':
                data = request.get_json() or {}
                cur.execute('SELECT * FROM "WorkOrders" WHERE work_order_id = %s;', (order_id,))
                existing = cur.fetchone()
                if not existing:
                    return jsonify({'status': 'error', 'message': 'Work order not found.'}), 404

                fields_to_update = []
                params = []

                if 'assigned_technician_id' in data:
                    tech_id = data['assigned_technician_id']
                    val = int(tech_id) if tech_id not in (None, '', 0, '0') else None
                    fields_to_update.extend(['assigned_technician_id = %s', 'crew_lead_id = %s'])
                    params.extend([val, val])

                if 'status' in data:
                    new_st = data['status'].strip()
                    fields_to_update.append('status = %s')
                    params.append(new_st)
                    # Automatic timestamping
                    if new_st == 'In Progress' and not existing.get('actual_start_time'):
                        fields_to_update.append('actual_start_time = %s')
                        params.append(dt_cls.now().isoformat())
                    elif new_st == 'COMPLETED' and not existing.get('actual_end_time'):
                        fields_to_update.append('actual_end_time = %s')
                        params.append(dt_cls.now().isoformat())

                if 'scheduled_date' in data:
                    fields_to_update.append('scheduled_date = %s')
                    params.append(data['scheduled_date'])

                if 'scheduled_time' in data:
                    fields_to_update.append('scheduled_time = %s')
                    params.append(data['scheduled_time'])

                if 'shift_window' in data:
                    fields_to_update.append('shift_window = %s')
                    params.append(data['shift_window'])

                if 'service_type' in data:
                    fields_to_update.append('service_type = %s')
                    params.append(data['service_type'])

                if 'dock_ingress_instructions' in data:
                    fields_to_update.append('dock_ingress_instructions = %s')
                    params.append(data['dock_ingress_instructions'])

                if 'security_access_code' in data:
                    fields_to_update.append('security_access_code = %s')
                    params.append(data['security_access_code'])

                if 'client_notes' in data:
                    fields_to_update.append('client_notes = %s')
                    params.append(data['client_notes'])

                if 'crew_notes' in data:
                    fields_to_update.append('crew_notes = %s')
                    params.append(data['crew_notes'])

                if 'actual_start_time' in data:
                    fields_to_update.append('actual_start_time = %s')
                    params.append(data['actual_start_time'])

                if 'actual_end_time' in data:
                    fields_to_update.append('actual_end_time = %s')
                    params.append(data['actual_end_time'])

                if 'quality_score' in data:
                    val = float(data['quality_score']) if data['quality_score'] is not None else None
                    fields_to_update.append('quality_score = %s')
                    params.append(val)

                if 'completion_signature' in data:
                    fields_to_update.append('completion_signature = %s')
                    params.append(data['completion_signature'])

                if 'supervisor_signoff' in data:
                    fields_to_update.append('supervisor_signoff = %s')
                    params.append(data['supervisor_signoff'])

                if not fields_to_update:
                    return jsonify({'status': 'noop', 'message': 'No changes provided.'})

                query = f'UPDATE "WorkOrders" SET {", ".join(fields_to_update)} WHERE work_order_id = %s;'
                params.append(order_id)
                cur.execute(query, tuple(params))

                cur.execute('''
                    INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                    VALUES (%s, 'WorkOrder', 'Work Order Updated', %s);
                ''', (order_id, f"Work Order #{order_id} modified via Dispatch Console."))

                conn.commit()
                return jsonify({'status': 'success', 'message': f"Work Order #{order_id} updated successfully."})
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/dispatch/work-orders/<int:order_id>/assign', methods=['POST'])
@login_required
def api_quick_assign_technician(order_id: int):
    """Assigns an employee directly to a work order and reports DPS FACT compliance status."""
    data = request.get_json() or {}
    raw_tech_id = data.get('technician_id')
    tech_id = int(raw_tech_id) if raw_tech_id not in (None, '', 0, '0') else None

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "WorkOrders" WHERE work_order_id = %s;', (order_id,))
            order = cur.fetchone()
            if not order:
                return jsonify({'status': 'error', 'message': 'Work order not found.'}), 404

            tech_info = None
            if tech_id:
                cur.execute('SELECT id, first_name, last_name, employee_number, dps_clearance_date, badge_status FROM "Employees" WHERE id = %s;', (tech_id,))
                tech_info = cur.fetchone()
                if not tech_info:
                    return jsonify({'status': 'error', 'message': f"Employee ID #{tech_id} does not exist."}), 404

            cur.execute('''
                UPDATE "WorkOrders"
                SET assigned_technician_id = %s, crew_lead_id = %s
                WHERE work_order_id = %s;
            ''', (tech_id, tech_id, order_id))

            assignee_desc = f"{tech_info['first_name']} {tech_info['last_name']} ({tech_info['employee_number']})" if tech_info else "Unassigned"
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, 'WorkOrder', 'Technician Assigned', %s);
            ''', (order_id, f"Assigned technician to Work Order #{order_id}: {assignee_desc}."))

            conn.commit()
            return jsonify({
                'status': 'success',
                'work_order_id': order_id,
                'technician_id': tech_id,
                'technician_name': f"{tech_info['first_name']} {tech_info['last_name']}" if tech_info else None,
                'dps_cleared': bool(tech_info and tech_info['dps_clearance_date']),
                'message': f"Successfully assigned {assignee_desc} to Work Order #{order_id}."
            })
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/dispatch/work-orders/<int:order_id>/transition', methods=['POST'])
@login_required
def api_transition_work_order(order_id: int):
    """Transitions work order execution status and records automated timestamps."""
    data = request.get_json() or {}
    new_status = (data.get('status') or '').strip()
    valid_statuses = ['Scheduled', 'In Progress', 'Paused', 'COMPLETED', 'Canceled']
    
    # Case-insensitive match
    matched_status = next((s for s in valid_statuses if s.lower() == new_status.lower()), None)
    if not matched_status:
        return jsonify({'status': 'error', 'message': f"Invalid status '{new_status}'. Must be one of {valid_statuses}."}), 400

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "WorkOrders" WHERE work_order_id = %s;', (order_id,))
            order = cur.fetchone()
            if not order:
                return jsonify({'status': 'error', 'message': 'Work order not found.'}), 404

            now_iso = dt_cls.now().isoformat()
            if matched_status == 'In Progress' and not order.get('actual_start_time'):
                cur.execute('''
                    UPDATE "WorkOrders"
                    SET status = %s, actual_start_time = %s
                    WHERE work_order_id = %s;
                ''', (matched_status, now_iso, order_id))
            elif matched_status == 'COMPLETED':
                cur.execute('''
                    UPDATE "WorkOrders"
                    SET status = %s, actual_end_time = COALESCE(actual_end_time, %s)
                    WHERE work_order_id = %s;
                ''', (matched_status, now_iso, order_id))
            else:
                cur.execute('''
                    UPDATE "WorkOrders"
                    SET status = %s
                    WHERE work_order_id = %s;
                ''', (matched_status, order_id))

            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, 'WorkOrder', 'Status Transition', %s);
            ''', (order_id, f"Work Order #{order_id} transitioned to '{matched_status}'."))

            conn.commit()
            return jsonify({
                'status': 'success',
                'work_order_id': order_id,
                'status_applied': matched_status,
                'message': f"Work Order #{order_id} transitioned to '{matched_status}'."
            })
    finally:
        if conn: conn.close()


# ==============================================================================
# SIGMAFIDELITY™ MARKETING CAMPAIGNS & OUTBOX ENGINE (HWB-QMS-8.0 / HWB-SAL-2026-001)
# ==============================================================================

def format_marketing_letterhead(body_html: str, tracking_token: str = None) -> str:
    """
    Wraps content inside official HWB-COM-001 Letterhead Standard (v2.1.0)
    with corporate branding, booking button, and tracking pixel.
    """
    tracking_pixel_html = ""
    if tracking_token:
        tracking_pixel_html = f'<img src="https://www.hwbcleaning.com/api/v1/marketing/track/open/{tracking_token}.gif" alt="" width="1" height="1" style="display:none;width:1px;height:1px;border:0;" />'
    
    current_year = datetime.datetime.now().year
    unsub_url = f"https://www.hwbcleaning.com/unsubscribe/{tracking_token}" if tracking_token else "https://www.hwbcleaning.com/unsubscribe"
    return f"""<div class="hwb-letterhead" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 32px 36px; border: 1px solid #e2e8f0; border-radius: 8px; max-width: 760px; margin: 0 auto; background: #ffffff; color: #1e293b; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
    <!-- 🏛️ MASTHEAD -->
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2.5px solid #0f172a; padding-bottom: 16px; margin-bottom: 22px;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <img src="https://www.hwbcleaning.com/static/logo_standard.png" alt="HWB Cleaning Services LLC" height="46" style="display: block; object-fit: contain;">
            <div>
                <div style="font-weight: 800; font-size: 15px; color: #0f172a; letter-spacing: -0.01em;">HWB CLEANING SERVICES LLC</div>
                <div style="font-weight: 700; font-size: 10.5px; color: #2563eb; letter-spacing: 0.05em; text-transform: uppercase;">Institutional Division • SigmaFidelity™</div>
            </div>
        </div>
        <div style="text-align: right; font-size: 11px; color: #475569; line-height: 1.45;">
            <strong style="color: #0f172a;">Corporate Headquarters:</strong><br>
            3342 FM 1827 Ste 8d, McKinney, TX 75071<br>
            Office: (214) 586-0257 | Mobile: (972) 800-7808<br>
            <a href="https://www.hwbcleaning.com" style="color: #2563eb; text-decoration: none; font-weight: 600;">www.hwbcleaning.com</a>
        </div>
    </div>

    <!-- 📄 BODY CONTENT -->
    <div style="padding: 10px 0 24px 0; min-height: 280px; line-height: 1.7; color: #1e293b; font-size: 14.5px;">
        {body_html}
    </div>

    <!-- 📜 FOOTER BLOCK (CAN-SPAM Act, Texas Anti-Spam & SOC 2 Privacy P2.1 Compliant) -->
    <div style="border-top: 1px solid #e2e8f0; padding-top: 16px; margin-top: 20px; text-align: center; font-size: 11px; color: #64748b; line-height: 1.6;">
        <strong style="color: #0f172a; letter-spacing: 0.05em;">FIDELITY. SAFETY. RESPECT.</strong><br>
        HWB Cleaning Services LLC • 3342 FM 1827 Ste 8d, McKinney, TX 75071 • Phone: (214) 586-0257<br>
        Texas Charter #802920409 • CAGE (SAM) #082830635 • Commercial EMR: .43 • ISO 9001:2015 Registered<br>
        <div style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed #cbd5e1; font-size: 10.5px; color: #94a3b8;">
            You are receiving this commercial communication as an operational facility contact in Texas.<br>
            To stop receiving future marketing messages, you may <a href="{unsub_url}" style="color: #2563eb; text-decoration: underline; font-weight: 600;">Unsubscribe Instantly</a> or email <a href="mailto:info@hwbcleaning.com?subject=Unsubscribe" style="color: #2563eb; text-decoration: underline;">info@hwbcleaning.com</a>.<br>
            <span style="font-size: 9.5px; color: #94a3b8; display: inline-block; margin-top: 4px;">Notice: This communication contains standard commercial delivery confirmation beacons. We respect your digital privacy.</span>
        </div>
    </div>
    {tracking_pixel_html}
</div>"""


def replace_email_tokens(template: str, recipient: dict, tracking_token: str = None) -> str:
    """
    Replaces dynamic tokens with recipient values.
    Ensures first-name only and conversational facility phrasing per CEO directive.
    """
    if not template:
        return ""
    
    booking_dest = os.getenv('HWB_CEO_BOOKING_URL') or "https://bookings.cloud.microsoft/book/FacilityWalkthroughquote@NETORGFT3163094.onmicrosoft.com/"
    if tracking_token:
        encoded_dest = urllib.parse.quote_plus(booking_dest)
        booking_link = f"https://www.hwbcleaning.com/api/v1/marketing/track/click/{tracking_token}?dest={encoded_dest}"
        unsub_link = f"https://www.hwbcleaning.com/unsubscribe/{tracking_token}"
    else:
        booking_link = booking_dest
        unsub_link = "https://www.hwbcleaning.com/unsubscribe"

    raw_name = recipient.get('recipient_name') or recipient.get('director') or ""
    parts = raw_name.strip().split()
    if parts:
        first = parts[0]
        if first.lower().replace('.', '') in ['mr', 'ms', 'mrs', 'dr'] and len(parts) > 1:
            first = parts[1]
        first_name = first
    else:
        first_name = "there"

    city = recipient.get('city') or "North Texas"
    county = recipient.get('county') or "Texas"
    cap = recipient.get('capacity')
    capacity_str = f"{cap} enrolled students" if cap else "your student body"
    sqf = recipient.get('sqf')
    sqf_str = f"{sqf:,} SF" if sqf else ""

    content = template
    replacements = {
        "{first_name}": first_name,
        "{director_first_name}": first_name,
        "{director_name}": first_name,
        "{recipient_name}": first_name,
        "{facility_name}": "your facility",
        "{center_name}": "your facility",
        "{facility}": "your facility",
        "{city}": city,
        "{county}": county,
        "{capacity}": capacity_str,
        "{sqf}": sqf_str,
        "{booking_link}": booking_link,
        "{unsubscribe_link}": unsub_link,
        "[BOOKING_LINK]": booking_link,
        "[UNSUBSCRIBE_LINK]": unsub_link,
        "{sender_name}": "Humberto Dominguez",
        "{sender_title}": "Owner & Operator"
    }
    for token, val in replacements.items():
        content = content.replace(token, str(val))
    return content


@crm_api_bp.route('/api/v1/marketing/leads/preview-count', methods=['GET'])
@login_required
def api_marketing_leads_preview_count():
    """
    Returns live count of verified commercial leads matching target filter criteria.
    """
    sector = (request.args.get('sector') or 'all').strip().lower()
    geo = (request.args.get('geo') or 'north_texas').strip()
    min_capacity = request.args.get('min_capacity', type=int) or 0
    min_sqf = request.args.get('min_sqf', type=int) or 0

    where_clauses = [
        "email IS NOT NULL",
        "POSITION('@' IN email) > 0",
        "COALESCE(is_dnc, FALSE) = FALSE",
        "COALESCE(is_converted, FALSE) = FALSE"
    ]
    params = []

    if sector in ['child care', 'childcare', 'daycare']:
        where_clauses.append("(industry ILIKE %s OR facility_type ILIKE %s)")
        params.extend(['%child%', '%child%'])
    elif sector in ['commercial', 'office', 'corporate']:
        where_clauses.append("(industry ILIKE %s OR facility_type ILIKE %s)")
        params.extend(['%commercial%', '%commercial%'])

    if geo == 'north_texas':
        where_clauses.append("county IN ('Collin', 'Dallas', 'Denton', 'Tarrant')")
    elif geo and geo != 'all_texas' and geo != 'all':
        where_clauses.append("county ILIKE %s")
        params.append(f"%{geo}%")

    if min_capacity > 0:
        where_clauses.append("capacity >= %s")
        params.append(min_capacity)

    if min_sqf > 0:
        where_clauses.append("sqf >= %s")
        params.append(min_sqf)

    where_sql = "WHERE " + " AND ".join(where_clauses)

    db_url = current_app.config.get('DATABASE_URL')
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute(f'''
                SELECT COUNT(*), COALESCE(SUM(estimated_annual_value), 0)
                FROM "Leads"
                {where_sql}
            ''', tuple(params))
            row = cur.fetchone()
            count = row[0] if row else 0
            est_value = float(row[1]) if row and row[1] else 0.0

            cur.execute(f'''
                SELECT center_name, director, city, county, capacity, sqf, email
                FROM "Leads"
                {where_sql}
                ORDER BY capacity DESC NULLS LAST, id ASC
                LIMIT 5
            ''', tuple(params))
            samples = [dict(r) for r in cur.fetchall()]

            return jsonify({
                'status': 'success',
                'count': count,
                'estimated_annual_value': est_value,
                'samples': samples
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/marketing/campaign/create', methods=['POST'])
@login_required
def api_marketing_campaign_create():
    """
    Creates a new marketing campaign and optionally stages matching leads.
    """
    data = request.get_json() or request.form
    name = (data.get('name') or '').strip()
    campaign_code = (data.get('campaign_code') or '').strip().upper()
    target_sector = (data.get('target_sector') or 'Licensed Childcare').strip()
    target_geo = (data.get('target_geo') or 'North Texas Core').strip()
    cadence_type = (data.get('cadence_type') or '1-Step Intro with Calendar Link').strip()
    sender_persona = (data.get('sender_persona') or 'Humberto Dominguez (Owner & Operator)').strip()
    daily_throttle = int(data.get('daily_throttle_limit') or 50)
    subject_tmpl = (data.get('email_subject_template') or '').strip()
    if not subject_tmpl:
        subject_tmpl = "Commercial Cleaning Proposal & Facility Walkthrough | HWB Cleaning Services"
    body_tmpl = (data.get('email_body_template') or '').strip()
    stage_leads = data.get('stage_leads', True)
    stage_limit = int(data.get('stage_limit') or 100)
    min_capacity = int(data.get('min_capacity') or 0)

    if not name:
        return jsonify({'status': 'error', 'message': 'Campaign Name is required.'}), 400
    if not campaign_code:
        campaign_code = f"CMP-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    db_url = current_app.config.get('DATABASE_URL')
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO "MarketingCampaigns" (
                    campaign_code, name, target_sector, target_geo, cadence_type,
                    sender_persona, status, daily_throttle_limit,
                    email_subject_template, email_body_template, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, 'Active', %s, %s, %s, %s)
                RETURNING id;
            ''', (
                campaign_code, name, target_sector, target_geo, cadence_type,
                sender_persona, daily_throttle, subject_tmpl, body_tmpl,
                f"{current_user.username if hasattr(current_user, 'username') else 'Executive'}"
            ))
            campaign_id = cur.fetchone()[0]

            staged_count = 0
            if stage_leads:
                where_clauses = [
                    "email IS NOT NULL",
                    "POSITION('@' IN email) > 0",
                    "COALESCE(is_dnc, FALSE) = FALSE",
                    "COALESCE(is_converted, FALSE) = FALSE",
                    "(state IS NULL OR UPPER(state) NOT IN ('CA', 'WA'))",
                    "LOWER(email) NOT LIKE '%.ca'",
                    "LOWER(email) NOT LIKE '%.ca.gov'"
                ]
                params = []
                if 'child' in target_sector.lower() or 'daycare' in target_sector.lower():
                    where_clauses.append("(industry ILIKE %s OR facility_type ILIKE %s)")
                    params.extend(['%child%', '%child%'])
                elif 'commercial' in target_sector.lower() or 'office' in target_sector.lower():
                    where_clauses.append("(industry ILIKE %s OR facility_type ILIKE %s)")
                    params.extend(['%commercial%', '%commercial%'])

                if 'statewide' in target_geo.lower() or 'texas' in target_geo.lower():
                    pass # all Texas
                elif 'north' in target_geo.lower():
                    where_clauses.append("county IN ('Collin', 'Dallas', 'Denton', 'Tarrant')")

                if min_capacity > 0:
                    where_clauses.append("capacity >= %s")
                    params.append(min_capacity)

                where_sql = "WHERE " + " AND ".join(where_clauses)
                params.append(stage_limit)

                cur.execute(f'''
                    SELECT id, center_name, director, email, city, county, capacity, sqf
                    FROM "Leads"
                    {where_sql}
                    ORDER BY capacity DESC NULLS LAST, id ASC
                    LIMIT %s;
                ''', tuple(params))
                matched_leads = cur.fetchall()

                for lead in matched_leads:
                    lid, center, director, email, city, county, cap, sqf = lead
                    token = uuid.uuid4().hex
                    director_name = director.strip() if director and director.strip() else "Facility Director"
                    cur.execute('''
                        INSERT INTO "CampaignRecipients" (
                            campaign_id, lead_id, recipient_email, recipient_name,
                            facility_name, city, county, capacity, sqf,
                            current_step, status, tracking_token
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 'STAGED', %s);
                    ''', (campaign_id, lid, email.strip(), director_name, center, city, county, cap or 0, sqf or 0, token))
                    staged_count += 1

                    if lid:
                        cur.execute('''
                            INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                            VALUES (%s, 'Lead', 'Marketing Outreach', %s);
                        ''', (lid, f"Enrolled in marketing campaign: '{name}' ({campaign_code}) - Status: STAGED"))

                        # Option 2 Smart Status Automation: Advance 'New' leads to 'In Campaign' while protecting active sales stages
                        cur.execute('''
                            UPDATE "Leads"
                            SET status = 'In Campaign', updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s AND (status ILIKE 'new' OR status IS NULL)
                            RETURNING id;
                        ''', (lid,))
                        if cur.fetchone():
                            cur.execute('''
                                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                                VALUES (%s, 'Lead', 'Status Change', %s);
                            ''', (lid, f"Status advanced from 'New' to 'In Campaign' via '{name}' ({campaign_code})"))

                cur.execute('''
                    UPDATE "MarketingCampaigns"
                    SET total_targets = (SELECT COUNT(*) FROM "CampaignRecipients" WHERE campaign_id = %s),
                        staged_count = (SELECT COUNT(*) FROM "CampaignRecipients" WHERE campaign_id = %s AND status = 'STAGED')
                    WHERE id = %s;
                ''', (campaign_id, campaign_id, campaign_id))

            conn.commit()
            return jsonify({
                'status': 'success',
                'campaign_id': campaign_id,
                'campaign_code': campaign_code,
                'staged_count': staged_count,
                'message': f"Campaign {campaign_code} created with {staged_count} staged targets."
            })
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/marketing/campaign/<int:campaign_id>/toggle-status', methods=['POST'])
@login_required
def api_marketing_campaign_toggle_status(campaign_id):
    """
    Toggles marketing campaign status between Active and Paused.
    """
    db_url = current_app.config.get('DATABASE_URL')
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute('SELECT id, campaign_code, status FROM "MarketingCampaigns" WHERE id = %s', (campaign_id,))
            campaign = cur.fetchone()
            if not campaign:
                return jsonify({'status': 'error', 'message': 'Campaign not found.'}), 404

            cur_status = campaign.get('status') or 'Active'
            new_status = 'Paused' if cur_status.strip().lower() == 'active' else 'Active'

            cur.execute('''
                UPDATE "MarketingCampaigns"
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (new_status, campaign_id))
            conn.commit()

            return jsonify({
                'status': 'success',
                'new_status': new_status,
                'message': f"Campaign {campaign.get('campaign_code')} is now {new_status}."
            })
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/marketing/campaign/<int:campaign_id>/template', methods=['GET'])
@login_required
def api_marketing_get_campaign_template(campaign_id):
    """
    Retrieves campaign copy templates, sender persona, and authenticated user email.
    """
    db_url = current_app.config.get('DATABASE_URL')
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, campaign_code, name, target_sector, target_geo, cadence_type,
                       sender_persona, status, email_subject_template, email_body_template
                FROM "MarketingCampaigns"
                WHERE id = %s;
            ''', (campaign_id,))
            campaign = cur.fetchone()
            if not campaign:
                return jsonify({'status': 'error', 'message': 'Campaign not found.'}), 404

            user_email = getattr(current_user, 'email', None)
            if not user_email and hasattr(current_user, 'id'):
                cur.execute('SELECT email FROM "Users" WHERE id = %s', (current_user.id,))
                urow = cur.fetchone()
                if urow and urow['email']:
                    user_email = urow['email']

            return jsonify({
                'status': 'success',
                'campaign': serialize_row(campaign),
                'current_user_email': user_email or 'info@hwbcleaning.com'
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/marketing/campaign/<int:campaign_id>/save-template', methods=['POST'])
@login_required
def api_marketing_save_campaign_template(campaign_id):
    """
    Saves campaign subject and body copy, with optional mass-recalibration of queued drafts.
    """
    data = request.get_json() or request.form
    subject_tmpl = (data.get('email_subject_template') or '').strip()
    body_tmpl = (data.get('email_body_template') or '').strip()
    recalibrate_outbox = bool(data.get('recalibrate_outbox', False))

    if not subject_tmpl or not body_tmpl:
        return jsonify({'status': 'error', 'message': 'Both Subject Line and Body copy are required.'}), 400

    db_url = current_app.config.get('DATABASE_URL')
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute('SELECT id, campaign_code, name FROM "MarketingCampaigns" WHERE id = %s', (campaign_id,))
            campaign = cur.fetchone()
            if not campaign:
                return jsonify({'status': 'error', 'message': 'Campaign not found.'}), 404

            cur.execute('''
                UPDATE "MarketingCampaigns"
                SET email_subject_template = %s, email_body_template = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (subject_tmpl, body_tmpl, campaign_id))

            recalibrated_count = 0
            if recalibrate_outbox:
                cur.execute('''
                    SELECT po.id, po.recipient_id, po.tracking_token,
                           cr.recipient_email, cr.recipient_name, cr.facility_name, cr.city, cr.county, cr.capacity, cr.sqf,
                           l.director, l.center_name
                    FROM "PendingOutbox" po
                    LEFT JOIN "CampaignRecipients" cr ON po.recipient_id = cr.id OR po.tracking_token = cr.tracking_token
                    LEFT JOIN "Leads" l ON cr.lead_id = l.id
                    WHERE po.campaign_id = %s AND UPPER(po.status) = 'PENDING';
                ''', (campaign_id,))
                pending_drafts = cur.fetchall()

                for draft in pending_drafts:
                    recip_dict = {
                        'recipient_name': draft.get('recipient_name') or draft.get('director') or '',
                        'recipient_email': draft.get('recipient_email') or '',
                        'facility_name': draft.get('facility_name') or draft.get('center_name') or 'your facility',
                        'city': draft.get('city') or 'Texas',
                        'county': draft.get('county') or 'Texas',
                        'capacity': draft.get('capacity'),
                        'sqf': draft.get('sqf')
                    }
                    tok = draft.get('tracking_token')
                    new_subj = replace_email_tokens(subject_tmpl, recip_dict, tok)
                    new_body_rendered = replace_email_tokens(body_tmpl, recip_dict, tok)
                    new_letterhead = format_marketing_letterhead(new_body_rendered, tok)

                    cur.execute('''
                        UPDATE "PendingOutbox"
                        SET subject = %s, body = %s
                        WHERE id = %s;
                    ''', (new_subj, new_letterhead, draft['id']))
                    recalibrated_count += 1

                if recalibrated_count > 0:
                    cur.execute('''
                        INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                        VALUES (%s, 'Campaign', 'Copy Recalibration', %s);
                    ''', (campaign_id, f"Campaign '{campaign['campaign_code']}' copy updated and mass-applied across {recalibrated_count} queued outbox drafts."))

            conn.commit()
            msg = f"Campaign {campaign.get('campaign_code')} master copy saved."
            if recalibrate_outbox:
                msg += f" Successfully recalibrated {recalibrated_count} queued outbox drafts."

            return jsonify({
                'status': 'success',
                'campaign_id': campaign_id,
                'recalibrated_count': recalibrated_count,
                'message': msg
            })
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/marketing/campaign/<int:campaign_id>/test-send', methods=['POST'])
@login_required
def api_marketing_test_send_proof(campaign_id):
    """
    Sends an immediate live test proof via Microsoft Graph API to whoever is logged in (or specified).
    """
    data = request.get_json() or request.form
    target_email = (data.get('recipient_email') or '').strip()
    subject_tmpl = (data.get('email_subject_template') or '').strip()
    body_tmpl = (data.get('email_body_template') or '').strip()

    if not target_email:
        target_email = getattr(current_user, 'email', None)

    if not target_email:
        db_url = current_app.config.get('DATABASE_URL')
        try:
            with get_db(db_url).cursor() as cur:
                cur.execute('SELECT email FROM "Users" WHERE id = %s', (current_user.id,))
                urow = cur.fetchone()
                if urow and urow['email']:
                    target_email = urow['email']
        except Exception:
            pass

    if not target_email:
        target_email = 'hdominguez@hwbcleaning.com'

    if not subject_tmpl or not body_tmpl:
        return jsonify({'status': 'error', 'message': 'Subject and Body copy required to send test proof.'}), 400

    test_token = f"TEST-{uuid.uuid4().hex[:8]}"
    sample_recip = {
        'recipient_name': getattr(current_user, 'full_name', 'Operations Director'),
        'recipient_email': target_email,
        'facility_name': 'Commercial Facility (Proof Sample)',
        'city': 'McKinney',
        'county': 'Collin',
        'capacity': 150,
        'sqf': 14500
    }

    rendered_subject = f"[TEST PROOF] " + replace_email_tokens(subject_tmpl, sample_recip, test_token)
    rendered_body = replace_email_tokens(body_tmpl, sample_recip, test_token)
    full_letterhead = format_marketing_letterhead(rendered_body, test_token)

    ok, reason = transmit_email(target_email, rendered_subject, full_letterhead)
    if ok:
        return jsonify({
            'status': 'success',
            'recipient': target_email,
            'message': f"Test proof successfully delivered to {target_email} via Microsoft Graph API."
        })
    else:
        return jsonify({
            'status': 'error',
            'recipient': target_email,
            'message': f"Test send failed: {reason}"
        }), 502


@crm_api_bp.route('/api/v1/marketing/campaign/<int:campaign_id>/generate-drafts', methods=['POST'])
@login_required
def api_marketing_generate_drafts(campaign_id):
    """
    Generates personalized HWB-COM-001 drafts into PendingOutbox for staged recipients.
    """
    db_url = current_app.config.get('DATABASE_URL')
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "MarketingCampaigns" WHERE id = %s', (campaign_id,))
            campaign = cur.fetchone()
            if not campaign:
                return jsonify({'status': 'error', 'message': 'Campaign not found.'}), 404

            subject_tmpl = campaign.get('email_subject_template') or "Commercial Cleaning Proposal & Facility Walkthrough | HWB Cleaning Services"
            body_tmpl = campaign.get('email_body_template') or """<p>Hi {first_name},</p>

<p>You probably already have a regular cleaning crew or an active contract in place—and if you are happy with their service, that is wonderful.</p>

<p>Still, you and I know that running a successful facility and protecting your bottom line takes a team effort. HWB Cleaning Services is my company, and here are three things I will put together for you at zero cost:</p>

<ol style="margin: 0.5rem 0 1rem 1.25rem; padding: 0; line-height: 1.6;">
    <li><strong>A Walkthrough Plan</strong> with your total cleanable square footage and room layout.</li>
    <li><strong>An Objective Cleanliness Score</strong> so you know exactly where your facility currently stands.</li>
    <li><strong>A Locked-In Contract</strong> with an exact flat monthly dollar figure you can keep in your back pocket whenever you need to replace or requote your current contract.</li>
</ol>

<p style="font-size: 0.88rem; color: #64748b; background: #f8fafc; border: 1px solid #e2e8f0; padding: 10px 14px; border-radius: 6px;">
    If you don't want to continue with my sales pitch, please feel free to <a href="{unsubscribe_link}" style="color: #2563eb; text-decoration: underline; font-weight: 600;">click here to unsubscribe</a> and you will receive no further emails from me.
</p>

<p>But if having a solid backup plan will save your school headaches, protect your budget, and keep your staff from burning out, here is what our service covers:</p>

<ul style="margin: 0.5rem 0 1rem 1.25rem; padding: 0; line-height: 1.6;">
    <li><strong>Teachers Don't Stay Late:</strong> We handle all the heavy vacuuming and scrubbing after 6:30 PM so your teachers don't have to stay late after a full day with the kids.</li>
    <li><strong>Classroom Rugs &amp; HEPA Filtration:</strong> Backpack vacuums with quiet HEPA filters that trap dust and dirt instead of blowing it around, plus fresh mopping on all hard floors.</li>
    <li><strong>Restrooms &amp; Low Sinks:</strong> Nightly deep scrubbing of toddler toilets, sinks, faucets, and door handles.</li>
    <li><strong>Diaper Pails to Dumpster:</strong> All diaper bins emptied directly to the outside dumpster so your facility opens fresh and clean every morning.</li>
    <li><strong>Morning Restock:</strong> Soap, paper towels, and toilet paper restocked every night so teachers are fully ready for the 6:30 AM drop-off.</li>
    <li><strong>Floor Care Included (No Surprise Bills):</strong> Stripping, waxing, and carpet cleaning twice a year included right in your regular monthly rate, with no extra fees.</li>
</ul>

<p>If you're open to it, I can swing by for just 5 minutes this week to take a quick look at your layout and get these three items ready for you.</p>

<p>Would you have 5 minutes this Tuesday morning or Thursday afternoon? Or feel free to pick a time directly on my calendar here:<br />
<a href="{booking_link}" style="display: inline-block; background: #2563eb; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: 700; margin-top: 10px;">Select a 5-Minute Time on Humberto's Calendar</a></p>

<p>Thank you for everything you and your team do for our local kids every day.</p>

<p>Sincerely,<br />
<strong>Humberto Dominguez</strong><br />
Owner &amp; Operator | HWB Cleaning Services LLC<br />
(972) 800-7808 | hdominguez@hwbcleaning.com</p>"""

            limit = 50
            if request.is_json and request.json:
                limit = request.json.get('limit', 50)
            
            cur.execute('''
                SELECT * FROM "CampaignRecipients"
                WHERE campaign_id = %s AND outbox_id IS NULL AND status = 'STAGED'
                ORDER BY capacity DESC NULLS LAST, id ASC
                LIMIT %s;
            ''', (campaign_id, limit))
            recipients = cur.fetchall()

            drafts_created = 0
            for recip in recipients:
                recip_email = (recip.get('recipient_email') or '').strip().lower()
                if not recip_email or '@' not in recip_email:
                    continue

                # Geofence Exclusion Shield: Block cold emails to CA (§ 17529.5), WA (RCW 19.190), and Canada (CASL)
                if recip_email.endswith('.ca') or recip_email.endswith('.ca.gov'):
                    cur.execute("UPDATE \"CampaignRecipients\" SET status = 'GEOFENCE_BLOCKED', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (recip['id'],))
                    continue

                lid = recip.get('lead_id')
                if lid:
                    cur.execute('SELECT state FROM "Leads" WHERE id = %s', (lid,))
                    lrow = cur.fetchone()
                    lstate = (lrow.get('state') or 'TX').strip().upper() if lrow else 'TX'
                    if lstate in ('CA', 'WA'):
                        cur.execute("UPDATE \"CampaignRecipients\" SET status = 'GEOFENCE_BLOCKED', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (recip['id'],))
                        continue

                token = recip.get('tracking_token') or uuid.uuid4().hex
                if not recip.get('tracking_token'):
                    cur.execute('UPDATE "CampaignRecipients" SET tracking_token = %s WHERE id = %s', (token, recip['id']))

                rendered_subject = replace_email_tokens(subject_tmpl, recip, token)
                rendered_body = replace_email_tokens(body_tmpl, recip, token)
                full_html = format_marketing_letterhead(rendered_body, token)

                cur.execute('''
                    INSERT INTO "PendingOutbox" (
                        recipient, subject, body, created_at, status, tracking_token, campaign_id, recipient_id
                    ) VALUES (%s, %s, %s, CURRENT_DATE, 'PENDING', %s, %s, %s)
                    RETURNING id;
                ''', (recip['recipient_email'], rendered_subject, full_html, token, campaign_id, recip['id']))
                outbox_id = cur.fetchone()[0]

                cur.execute('''
                    UPDATE "CampaignRecipients"
                    SET outbox_id = %s, status = 'AWAITING_APPROVAL', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                ''', (outbox_id, recip['id']))
                drafts_created += 1

            cur.execute('''
                UPDATE "MarketingCampaigns"
                SET staged_count = (SELECT COUNT(*) FROM "CampaignRecipients" WHERE campaign_id = %s AND status = 'STAGED'),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (campaign_id, campaign_id))

            conn.commit()
            return jsonify({
                'status': 'success',
                'drafts_created': drafts_created,
                'message': f"Generated {drafts_created} personalized drafts in PendingOutbox ready for CEO review."
            })
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/marketing/outbox/<int:email_id>', methods=['GET'])
@login_required
def api_marketing_get_outbox(email_id):
    """
    Returns full email draft content and recipient metadata for inspection and editing.
    """
    db_url = current_app.config.get('DATABASE_URL')
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute('''
                SELECT po.*, cr.facility_name, cr.recipient_name, cr.city, cr.county, cr.capacity, cr.sqf, cr.open_count, cr.opened_at
                FROM "PendingOutbox" po
                LEFT JOIN "CampaignRecipients" cr ON po.recipient_id = cr.id OR po.tracking_token = cr.tracking_token
                WHERE po.id = %s;
            ''', (email_id,))
            msg = cur.fetchone()
            if not msg:
                return jsonify({'status': 'error', 'message': 'Outbox message not found.'}), 404
            return jsonify({
                'status': 'success',
                'email': serialize_row(msg)
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/marketing/outbox/<int:email_id>/update', methods=['POST', 'PUT'])
@login_required
def api_marketing_update_outbox(email_id):
    """
    Allows the CEO to edit the subject line or email body before releasing.
    """
    data = request.get_json() or request.form
    new_subject = data.get('subject')
    new_body = data.get('body') if data.get('body') is not None else data.get('body_text')

    if not new_subject and not new_body:
        return jsonify({'status': 'error', 'message': 'Subject or Body required for update.'}), 400

    db_url = current_app.config.get('DATABASE_URL')
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "PendingOutbox" WHERE id = %s', (email_id,))
            existing = cur.fetchone()
            if not existing:
                return jsonify({'status': 'error', 'message': 'Email not found.'}), 404

            updated_subject = new_subject if new_subject is not None else existing['subject']
            updated_body = new_body if new_body is not None else existing['body']

            cur.execute('''
                UPDATE "PendingOutbox"
                SET subject = %s, body = %s
                WHERE id = %s;
            ''', (updated_subject, updated_body, email_id))
            conn.commit()

            return jsonify({
                'status': 'success',
                'message': f"Email #{email_id} successfully updated."
            })
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/marketing/outbox/batch-action', methods=['POST'])
@login_required
def api_marketing_outbox_batch():
    """
    Batch release or reject queued emails via Microsoft Graph API.
    """
    data = request.get_json() or request.form
    action = data.get('action') # 'approve' or 'reject'
    email_ids = data.get('email_ids', [])
    limit = int(data.get('limit') or 10)

    db_url = current_app.config.get('DATABASE_URL')
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            if not email_ids:
                cur.execute('''
                    SELECT id, recipient, subject, body, tracking_token
                    FROM "PendingOutbox"
                    WHERE UPPER(status) = 'PENDING'
                    ORDER BY id ASC
                    LIMIT %s;
                ''', (limit,))
                pending_msgs = cur.fetchall()
            else:
                cur.execute('''
                    SELECT id, recipient, subject, body, tracking_token
                    FROM "PendingOutbox"
                    WHERE id = ANY(%s) AND UPPER(status) = 'PENDING';
                ''', (email_ids,))
                pending_msgs = cur.fetchall()

            success_count, error_count = 0, 0
            for msg in pending_msgs:
                eid = msg['id']
                if action == 'approve':
                    ok, reason = transmit_email(msg['recipient'], msg['subject'], msg['body'])
                    if ok:
                        cur.execute("UPDATE \"PendingOutbox\" SET status = 'SENT' WHERE id = %s", (eid,))
                        cur.execute('''
                            UPDATE "CampaignRecipients"
                            SET status = 'SENT', sent_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                            WHERE outbox_id = %s OR tracking_token = %s
                            RETURNING lead_id, facility_name;
                        ''', (eid, msg.get('tracking_token')))
                        ret_recip = cur.fetchone()
                        if ret_recip and ret_recip['lead_id']:
                            cur.execute('''
                                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                                VALUES (%s, 'Lead', 'Email Sent', %s);
                            ''', (ret_recip['lead_id'], f"Marketing outreach email sent to {msg['recipient']}: '{msg['subject']}'"))
                        success_count += 1
                    else:
                        error_count += 1
                elif action == 'reject':
                    cur.execute("UPDATE \"PendingOutbox\" SET status = 'REJECTED' WHERE id = %s", (eid,))
                    cur.execute('''
                        UPDATE "CampaignRecipients"
                        SET status = 'REJECTED', updated_at = CURRENT_TIMESTAMP
                        WHERE outbox_id = %s OR tracking_token = %s;
                    ''', (eid, msg.get('tracking_token')))
                    success_count += 1

            conn.commit()
            return jsonify({
                'status': 'success',
                'action': action,
                'processed': len(pending_msgs),
                'successful': success_count,
                'errors': error_count,
                'message': f"Batch {action} completed: {success_count} messages processed successfully."
            })
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


# --- User Custom Calling Scripts REST API (HWB-SAL-2026-SCRIPTS) ---

@crm_api_bp.route('/api/v1/user/scripts', methods=['GET'], endpoint='api_get_user_scripts')
@login_required
def api_get_user_scripts():
    """Retrieves all personal and team-shared calling scripts for the authenticated user."""
    conn = None
    try:
        conn = get_db(current_app.config['DATABASE_URL'])
        with conn.cursor() as cur:
            cur.execute('''
                SELECT 
                    s.id, 
                    s.user_id, 
                    s.tab_label, 
                    s.scenario_type, 
                    s.script_text, 
                    s.operator_tip, 
                    s.is_default, 
                    s.is_shared,
                    s.created_at,
                    s.updated_at,
                    u.full_name as author_name,
                    u.username as author_username,
                    (s.user_id = %s) as is_mine
                FROM user_scripts s
                LEFT JOIN "Users" u ON s.user_id = u.id
                WHERE s.user_id = %s OR s.is_shared = TRUE
                ORDER BY s.is_default DESC, (s.user_id = %s) DESC, s.updated_at DESC;
            ''', (current_user.id, current_user.id, current_user.id))
            rows = cur.fetchall()
            scripts = []
            for r in rows:
                scripts.append({
                    'id': r['id'],
                    'user_id': r['user_id'],
                    'tab_label': r['tab_label'],
                    'scenario_type': r['scenario_type'] or 'Custom Pitch',
                    'script_text': r['script_text'],
                    'operator_tip': r['operator_tip'] or '',
                    'is_default': bool(r['is_default']),
                    'is_shared': bool(r['is_shared']),
                    'is_mine': bool(r['is_mine']),
                    'author_name': r['author_name'] or r['author_username'] or 'Team Member',
                    'created_at': r['created_at'].isoformat() if r['created_at'] else None,
                    'updated_at': r['updated_at'].isoformat() if r['updated_at'] else None
                })
            return jsonify({'status': 'success', 'scripts': scripts, 'count': len(scripts)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/user/scripts', methods=['POST'], endpoint='api_create_user_script')
@login_required
def api_create_user_script():
    """Creates a new personal calling script for the authenticated user."""
    data = request.get_json() or {}
    tab_label = (data.get('tab_label') or '').strip()
    script_text = (data.get('script_text') or '').strip()
    scenario_type = (data.get('scenario_type') or 'Custom Pitch').strip()
    operator_tip = (data.get('operator_tip') or '').strip()
    is_default = bool(data.get('is_default', False))
    is_shared = bool(data.get('is_shared', False))

    if not tab_label:
        return jsonify({'status': 'error', 'message': 'Tab button name is required.'}), 400
    if not script_text:
        return jsonify({'status': 'error', 'message': 'Script content text is required.'}), 400

    conn = None
    try:
        conn = get_db(current_app.config['DATABASE_URL'])
        with conn.cursor() as cur:
            if is_default:
                cur.execute('UPDATE user_scripts SET is_default = FALSE WHERE user_id = %s;', (current_user.id,))

            cur.execute('''
                INSERT INTO user_scripts (user_id, tab_label, scenario_type, script_text, operator_tip, is_default, is_shared)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at, updated_at;
            ''', (current_user.id, tab_label, scenario_type, script_text, operator_tip, is_default, is_shared))
            res = cur.fetchone()
            conn.commit()

            return jsonify({
                'status': 'success',
                'message': 'Custom script saved to profile successfully.',
                'script': {
                    'id': res['id'],
                    'user_id': current_user.id,
                    'tab_label': tab_label,
                    'scenario_type': scenario_type,
                    'script_text': script_text,
                    'operator_tip': operator_tip,
                    'is_default': is_default,
                    'is_shared': is_shared,
                    'is_mine': True,
                    'author_name': getattr(current_user, 'full_name', None) or current_user.username
                }
            }), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/user/scripts/<int:script_id>', methods=['PUT'], endpoint='api_update_user_script')
@login_required
def api_update_user_script(script_id):
    """Updates an existing personal script."""
    data = request.get_json() or {}
    tab_label = (data.get('tab_label') or '').strip()
    script_text = (data.get('script_text') or '').strip()
    scenario_type = (data.get('scenario_type') or 'Custom Pitch').strip()
    operator_tip = (data.get('operator_tip') or '').strip()
    is_default = bool(data.get('is_default', False))
    is_shared = bool(data.get('is_shared', False))

    if not tab_label or not script_text:
        return jsonify({'status': 'error', 'message': 'Tab name and script text are required.'}), 400

    conn = None
    try:
        conn = get_db(current_app.config['DATABASE_URL'])
        with conn.cursor() as cur:
            # Check ownership or executive role
            cur.execute('SELECT user_id FROM user_scripts WHERE id = %s;', (script_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'status': 'error', 'message': 'Script not found.'}), 404
            
            if row['user_id'] != current_user.id and current_user.role not in ['Executive', 'Admin']:
                return jsonify({'status': 'error', 'message': 'Unauthorized to edit this script.'}), 403

            if is_default:
                cur.execute('UPDATE user_scripts SET is_default = FALSE WHERE user_id = %s;', (current_user.id,))

            cur.execute('''
                UPDATE user_scripts
                SET tab_label = %s, scenario_type = %s, script_text = %s, operator_tip = %s,
                    is_default = %s, is_shared = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (tab_label, scenario_type, script_text, operator_tip, is_default, is_shared, script_id))
            conn.commit()

            return jsonify({
                'status': 'success',
                'message': 'Custom script updated successfully.'
            })
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/user/scripts/<int:script_id>', methods=['DELETE'], endpoint='api_delete_user_script')
@login_required
def api_delete_user_script(script_id):
    """Deletes a custom script from the user's profile."""
    conn = None
    try:
        conn = get_db(current_app.config['DATABASE_URL'])
        with conn.cursor() as cur:
            cur.execute('SELECT user_id FROM user_scripts WHERE id = %s;', (script_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'status': 'error', 'message': 'Script not found.'}), 404
            
            if row['user_id'] != current_user.id and current_user.role not in ['Executive', 'Admin']:
                return jsonify({'status': 'error', 'message': 'Unauthorized to delete this script.'}), 403

            cur.execute('DELETE FROM user_scripts WHERE id = %s;', (script_id,))
            conn.commit()

            return jsonify({'status': 'success', 'message': 'Custom script removed from profile.'})
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn: conn.close()


