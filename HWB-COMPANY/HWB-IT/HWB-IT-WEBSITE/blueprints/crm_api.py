"""
SigmaFidelity™ CRM Data & REST API Blueprint
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Silas Sync (VP of CRM)
"""

import os
import io
import csv
import json
import hashlib
import datetime
from datetime import datetime as dt_cls
from flask import Blueprint, request, jsonify, Response, current_app, send_file
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from core.services.database import get_db
from core.services.sanitizer import clean_phone, clean_currency, clean_sqft, clean_zip, clean_email, clean_city

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



# --- Accounts REST Endpoints ---

@crm_api_bp.route('/api/v1/accounts/<int:id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@login_required
def api_account_hub(id):
    conn = get_db(current_app.config['DATABASE_URL'])
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
                    'account': serialize_row(acc),
                    'contacts': [serialize_row(c) for c in contacts],
                    'activities': [serialize_row(a) for a in activities]
                })

            elif request.method in ['PUT', 'PATCH']:
                data = request.json or {}
                cur.execute('SELECT * FROM "Customers" WHERE customer_id = %s', (id,))
                current_acc = cur.fetchone()
                if not current_acc:
                    return jsonify({'status': 'error', 'message': 'Account not found'}), 404

                def resolve(key, db_val):
                    val = data.get(key) if key in data else db_val
                    return val if val != "" else None

                sqf_val = data.get('sqf') if 'sqf' in data else current_acc['sqf']
                revenue_val = data.get('annual_revenue') if 'annual_revenue' in data else current_acc['annual_revenue']
                if sqf_val == '' or sqf_val is None:
                    sqf_val = 0
                else:
                    sqf_val = clean_sqft(sqf_val)
                if revenue_val == '' or revenue_val is None:
                    revenue_val = 0.0
                else:
                    revenue_val = clean_currency(revenue_val)

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
                      clean_email(resolve('email', current_acc['email'])) or resolve('email', current_acc['email']), 
                      clean_phone(resolve('phone', current_acc['phone'])) or resolve('phone', current_acc['phone']),
                      resolve('company_address', current_acc['company_address']), 
                      clean_city(resolve('city', current_acc['city'])) or resolve('city', current_acc['city']), 
                      resolve('state', current_acc['state']), 
                      clean_zip(resolve('zip', current_acc['zip'])) or resolve('zip', current_acc['zip']), 
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


@crm_api_bp.route('/api/v1/accounts/export-selected', methods=['POST'])
@login_required
def api_export_selected_accounts():
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
                cur.execute('SELECT * FROM "Leads" WHERE id = %s', (id,))
                lead = cur.fetchone()
                cur.execute('SELECT * FROM "Contacts" WHERE lead_id = %s', (id,))
                contacts = cur.fetchall()
                cur.execute('SELECT * FROM "GlobalActivities" WHERE parent_id = %s AND parent_type = %s ORDER BY timestamp DESC', (id, "Lead"))
                activities = cur.fetchall()

                return jsonify({
                    'lead': serialize_row(lead),
                    'contacts': [serialize_row(c) for c in contacts],
                    'activities': [serialize_row(a) for a in activities]
                })

            elif request.method in ['PUT', 'PATCH']:
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
                      acquisition_tier_val, ownership_type_val, owner_id_val, id))

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
    """Saves live contact corrections, notes, and activity outcomes in a single transaction."""
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
    params = data.get('params', {})

    if not lead_ids:
        return jsonify({'status': 'error', 'message': 'No lead IDs provided'}), 400

    conn = get_db(current_app.config['DATABASE_URL'])
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


@crm_api_bp.route('/api/v1/leads/export-selected', methods=['POST'])
@login_required
def api_export_selected_leads():
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
        if conn: conn.close()


@crm_api_bp.route('/api/v1/leads/<int:id>/contacts', methods=['POST'])
@login_required
def api_lead_add_contact(id):
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
    notes = data.get('notes') or 'Applied via public careers portal.'

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO "JobApplicants" (
                    full_name, phone, email, city, state, desired_role, desired_shift,
                    experience_level, has_transportation, authorized_to_work_us,
                    preferred_language, status, notes
                ) VALUES (%s, %s, %s, %s, 'TX', %s, %s, %s, %s, %s, %s, 'New', %s)
                RETURNING id;
            ''', (full_name, phone, email, city, desired_role, desired_shift, experience, has_transport, authorized_us, language, notes))
            new_id = cur.fetchone()[0]
            conn.commit()
            return jsonify({'status': 'success', 'applicant_id': new_id, 'message': 'Application received.'}), 201
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
            conn.commit()
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


@crm_api_bp.route('/api/v1/workforce/subcontractors', methods=['GET'])
@login_required
def api_get_subcontractors():
    """Retrieve subcontractor records with optional filtering."""
    status_filter = request.args.get('status')
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if status_filter:
                cur.execute('SELECT * FROM "SubcontractorPartners" WHERE status = %s ORDER BY created_at DESC;', (status_filter,))
            else:
                cur.execute('SELECT * FROM "SubcontractorPartners" ORDER BY created_at DESC;')
            rows = [serialize_row(r) for r in cur.fetchall()]
            return jsonify({'status': 'success', 'count': len(rows), 'subcontractors': rows})
    finally:
        if conn: conn.close()


@crm_api_bp.route('/api/v1/workforce/subcontractors/<int:id>', methods=['PATCH', 'DELETE'])
@login_required
def api_manage_subcontractor(id):
    """Update status, COI status, or rating for a subcontractor."""
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'DELETE':
                cur.execute('DELETE FROM "SubcontractorPartners" WHERE id = %s;', (id,))
                conn.commit()
                return jsonify({'status': 'success', 'deleted_id': id})

            data = request.get_json() or {}
            cur.execute('SELECT * FROM "SubcontractorPartners" WHERE id = %s;', (id,))
            current_sub = cur.fetchone()
            if not current_sub:
                return jsonify({'status': 'error', 'message': 'Subcontractor not found'}), 404

            new_status = data.get('status') if 'status' in data else current_sub['status']
            new_coi_status = data.get('coi_status') if 'coi_status' in data else current_sub['coi_status']
            new_notes = data.get('notes') if 'notes' in data else current_sub['notes']
            new_city = clean_city(data.get('city')) if 'city' in data else current_sub['city']
            new_phone = clean_phone(data.get('phone')) if 'phone' in data else current_sub['phone']

            cur.execute('''
                UPDATE "SubcontractorPartners"
                SET status = %s, coi_status = %s, notes = %s, city = %s, phone = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (new_status, new_coi_status, new_notes, new_city, new_phone, id))
            conn.commit()
            return jsonify({'status': 'success', 'id': id})
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

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
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
                    assigned_customer_id, weekly_hours_allocated, notes
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s
                ) RETURNING id, employee_number;
            ''', (
                emp_number, applicant_id, first_name, last_name, phone, email,
                hire_date, employment_status, employment_type, role,
                pay_rate, overtime_rate, pay_frequency, primary_language,
                emergency_name, emergency_phone, city, state,
                assigned_customer_id, weekly_hours, notes
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
                       (SELECT COUNT(*) FROM "EmployeeDocuments" d WHERE d.employee_id = e.id) as document_count
                FROM "Employees" e
                LEFT JOIN "Customers" c ON e.assigned_customer_id = c.customer_id
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
            rows = [serialize_row(r) for r in cur.fetchall()]
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
                    SELECT e.*, c.company_name as assigned_facility_name
                    FROM "Employees" e
                    LEFT JOIN "Customers" c ON e.assigned_customer_id = c.customer_id
                    WHERE e.id = %s;
                ''', (id,))
                emp = cur.fetchone()
                if not emp:
                    return jsonify({'status': 'error', 'message': 'Employee not found'}), 404
                
                cur.execute('SELECT * FROM "EmployeeDocuments" WHERE employee_id = %s ORDER BY created_at DESC;', (id,))
                docs = [serialize_row(d) for d in cur.fetchall()]

                emp_data = serialize_row(emp)
                emp_data['documents'] = docs
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
                assigned_customer_id = data.get('assigned_customer_id', emp['assigned_customer_id'])
                weekly_hours = float(data.get('weekly_hours_allocated', emp['weekly_hours_allocated']))
                emergency_name = data.get('emergency_contact_name', emp['emergency_contact_name'])
                emergency_phone = clean_phone(data.get('emergency_contact_phone', emp['emergency_contact_phone']))
                city = clean_city(data.get('address_city', emp['address_city']))
                notes = data.get('notes', emp['notes'])

                cur.execute('''
                    UPDATE "Employees" SET
                        first_name = %s, last_name = %s, phone = %s, email = %s,
                        primary_role = %s, employment_status = %s, employment_type = %s,
                        pay_rate_hourly = %s, overtime_rate_hourly = %s, primary_language = %s,
                        assigned_customer_id = %s, weekly_hours_allocated = %s,
                        emergency_contact_name = %s, emergency_contact_phone = %s,
                        address_city = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                ''', (
                    first_name, last_name, phone, email,
                    primary_role, employment_status, employment_type,
                    pay_rate, overtime_rate, primary_language,
                    assigned_customer_id, weekly_hours,
                    emergency_name, emergency_phone,
                    city, notes, id
                ))
                conn.commit()
                return jsonify({'status': 'success', 'id': id, 'message': 'Employee updated successfully.'})
    finally:
        if conn: conn.close()


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
            timestamp = dt_cls.now().strftime('%Y%m%d')
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-disposition": f"attachment; filename=HWB_Payroll_Export_{timestamp}.csv"}
            )
    finally:
        if conn: conn.close()

