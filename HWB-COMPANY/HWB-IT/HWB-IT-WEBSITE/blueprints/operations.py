"""
SigmaFidelity™ Operations, Backoffice & Executive Management Blueprint
Standard: HWB-QMS-7.6 Enterprise Architecture Standards
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
import json
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, session, current_app
from flask_login import login_required, current_user, login_user
from werkzeug.security import generate_password_hash

from core.models.user import User
from core.constants import FACILITY_TYPES, LEAD_SOURCES, PRIORITY_LEVELS
from core.security import roles_required
from core.services.database import get_db
from core.services.search import parse_advanced_search
from core.services.sanitizer import clean_phone, clean_currency, clean_sqft, clean_zip, clean_email, clean_city
from core.services.email_service import transmit_email

operations_bp = Blueprint('operations', __name__)


# --- Admin Operations Unified Hub ---

@operations_bp.route('/admin/operations', endpoint='admin_operations')
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
    applicants, subcontractors = [], []
    applicants_count, subcontractors_count = 0, 0
    
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

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            # 1. FETCH ACCOUNTS
            cur.execute('SELECT SUM(annual_revenue) FROM "Customers"')
            portfolio_total_row = cur.fetchone()
            portfolio_total = portfolio_total_row[0] if portfolio_total_row and portfolio_total_row[0] is not None else 0

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

            include_archived = request.args.get('include_archived') == 'true'
            if not include_archived and active_view == 'leads':
                lead_where_clauses.append("is_commercial = TRUE")

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

            cur.execute(f'SELECT COUNT(*) FROM "Leads" l {lead_where_str}', tuple(lead_params))
            leads_count = cur.fetchone()[0]

            cur.execute('SELECT COUNT(*) FROM "Leads" WHERE is_duplicate = TRUE;')
            dup_count_row = cur.fetchone()
            dup_count = dup_count_row[0] if dup_count_row else 0

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

            # 4. CONSTRUCTION BIDS PIPELINE
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

            # 5. ACTIVE SYSTEM USERS
            cur.execute('SELECT id, username, full_name, role FROM "Users" WHERE status = \'Active\' ORDER BY id ASC')
            system_users = cur.fetchall()

            # 6. WORKFORCE & SUBCONTRACTORS
            applicant_where_clauses = []
            applicant_params = []
            if search_q and active_view == 'workforce':
                applicant_where_clauses.append("(full_name ILIKE %s OR city ILIKE %s OR phone ILIKE %s OR desired_role ILIKE %s)")
                param_val = f"%{search_q}%"
                applicant_params.extend([param_val, param_val, param_val, param_val])
            app_where_str = ("WHERE " + " AND ".join(applicant_where_clauses)) if applicant_where_clauses else ""
            cur.execute(f'SELECT * FROM "JobApplicants" {app_where_str} ORDER BY created_at DESC', tuple(applicant_params))
            applicants = cur.fetchall()
            applicants_count = len(applicants)

            sub_where_clauses = []
            sub_params = []
            if search_q and active_view == 'workforce':
                sub_where_clauses.append("(company_name ILIKE %s OR contact_name ILIKE %s OR city ILIKE %s OR specialties ILIKE %s)")
                param_val = f"%{search_q}%"
                sub_params.extend([param_val, param_val, param_val, param_val])
            sub_where_str = ("WHERE " + " AND ".join(sub_where_clauses)) if sub_where_clauses else ""
            cur.execute(f'SELECT * FROM "SubcontractorPartners" {sub_where_str} ORDER BY created_at DESC', tuple(sub_params))
            subcontractors = cur.fetchall()
            subcontractors_count = len(subcontractors)
    finally:
        if "conn" in locals() and conn: conn.close()

    if request.args.get('format') == 'json' or (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.accept_mimetypes.best == 'application/json'):
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
                'applicants': [serialize_row(a) for a in applicants] if applicants else [],
                'subcontractors': [serialize_row(s) for s in subcontractors] if subcontractors else [],
                'system_users': [serialize_row(u) for u in system_users] if system_users else [],
                'facility_types': FACILITY_TYPES,
                'lead_sources': LEAD_SOURCES,
                'priority_levels': PRIORITY_LEVELS,
                'counts': {'leads': leads_count or 0, 'accounts': len(clients) if clients else 0, 'bids': len(construction_bids) if construction_bids else 0, 'applicants': applicants_count, 'subcontractors': subcontractors_count},
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
                         applicants=applicants, applicants_count=applicants_count,
                         subcontractors=subcontractors, subcontractors_count=subcontractors_count,
                         library=json.dumps(lib), activities=activities, system_users=system_users,
                         facility_types=FACILITY_TYPES, lead_sources=LEAD_SOURCES, priority_levels=PRIORITY_LEVELS)


# --- Field Sales Desk ---

@operations_bp.route('/admin/sales-desk', endpoint='sales_desk')
@login_required
@roles_required('Sales', 'Executive', 'Admin', 'Manager')
def sales_desk():
    """Field Sales Desk for Outside Sales Representatives (HWB-SAL-2026-001)."""
    search_q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            user_id = current_user.id
            is_sales_rep = (current_user.role == 'Sales')
            
            cur.execute('SELECT COUNT(*) FROM "Leads" WHERE owner_id = %s AND is_converted = FALSE', (user_id,))
            user_assigned_count = cur.fetchone()[0]
            
            where_clauses = ['is_converted = FALSE']
            params = []
            
            if is_sales_rep and user_assigned_count > 0:
                where_clauses.append('owner_id = %s')
                params.append(user_id)
            elif is_sales_rep:
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


# --- Lead & Account Editing / Creation ---

@operations_bp.route('/admin/edit-lead/<int:id>', methods=['GET', 'POST'], endpoint='crm_edit_lead')
@login_required
def edit_lead(id):
    conn = get_db(current_app.config['DATABASE_URL'])
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
                    data.get('company_name'), data.get('decision_maker'), data.get('job_title'), 
                    clean_email(data.get('email')) or data.get('email'), 
                    clean_phone(data.get('phone')) or data.get('phone'),
                    data.get('address'), clean_city(data.get('city')) or data.get('city'), data.get('state'), clean_zip(data.get('zipcode')), data.get('industry'), sqf,
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
        if "conn" in locals() and conn: conn.close()


@operations_bp.route('/admin/add-lead', methods=['POST'], endpoint='add_manual_lead')
@login_required
def add_manual_lead():
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            data = request.form
            sqf = float(clean_sqft(data.get('sqf', '0')))
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
                clean_email(data.get('email')) or data.get('email'), 
                clean_phone(data.get('phone')) or data.get('phone'), data.get('address'),
                clean_city(data.get('city')) or data.get('city'), data.get('state'), clean_zip(data.get('zipcode')), data.get('industry'),
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
        if "conn" in locals() and conn: conn.close()
    return redirect(url_for('admin_operations', view='leads'))


@operations_bp.route('/admin/add-account', methods=['POST'], endpoint='add_account')
@login_required
def add_account():
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            data = request.form

            sqf = clean_sqft(data.get('sqf'))
            revenue = clean_currency(data.get('annual_revenue'))

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
            ''', (data.get('company_name'), data.get('contact_person_name'), 
                  clean_email(data.get('email')) or data.get('email'), 
                  clean_phone(data.get('phone')) or data.get('phone'), 
                  data.get('company_address'), clean_city(data.get('city')) or data.get('city'), data.get('state'), clean_zip(data.get('zip')), 
                  data.get('website'), sqf, revenue, 
                  data.get('traffic_cycle'), data.get('quote_number'),
                  data.get('frequency'), data.get('notes'), assigned_rep_id))
            customer_id = cur.fetchone()[0]

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
        if "conn" in locals() and conn: conn.close()
    return redirect(url_for('admin_operations', view='accounts'))


# --- Admin Master & Executive Hubs ---

@operations_bp.route('/admin/master', methods=['GET', 'POST'], endpoint='admin_master')
@login_required
@roles_required('Executive', 'Admin', 'Manager')
def admin_master():
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            if request.method == 'POST':
                action = request.form.get('action')
                if action == 'add_chemical':
                    cur.execute(
                        'INSERT INTO "Chemicals" (name, product_id, hazard_level, sds_link, intended_use) VALUES (%s, %s, %s, %s, %s)',
                        (request.form.get('name'), request.form.get('product_id'), request.form.get('hazard_level'), request.form.get('sds_link'), request.form.get('intended_use'))
                    )
                    conn.commit()
                    flash("Chemical Record Added.")
                return redirect(url_for('admin_master'))

            cur.execute('SELECT w.*, c.company_name, s.service_requested FROM "WorkOrders" w JOIN "Customers" c ON w.customer_id = c.customer_id JOIN "Services" s ON w.service_id = s.service_id ORDER BY w.scheduled_date DESC LIMIT 20')
            work_orders = cur.fetchall()
            cur.execute('SELECT * FROM "Chemicals" ORDER BY name ASC')
            chemicals = cur.fetchall()
            cur.execute('SELECT * FROM "Customers" ORDER BY company_name ASC')
            customers = cur.fetchall()
            cur.execute('SELECT * FROM "Warchest" ORDER BY name ASC')
            warchest = cur.fetchall()
    finally:
        if "conn" in locals() and conn: conn.close()
        
    return render_template('HWB-WEB Admin Master.html', work_orders=work_orders, chemicals=chemicals, customers=customers, warchest=warchest)


@operations_bp.route('/admin/executive', methods=['GET', 'POST'], endpoint='sigma_executive')
@login_required
@roles_required('Executive', 'Admin')
def sigma_executive():
    conn = get_db(current_app.config['DATABASE_URL'])
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
                        for module in ['leads', 'accounts', 'sales_desk', 'bids', 'workforce', 'monitor', 'qms', 'social', 'outbox', 'users', 'tools']:
                            custom_perms[module] = {
                                'view': True if request.form.get(f'perm_{module}_view') == 'true' else False,
                                'edit': True if request.form.get(f'perm_{module}_edit') == 'true' else False,
                                'delete': True if request.form.get(f'perm_{module}_delete') == 'true' else False,
                            }
                        perms_json = json.dumps(custom_perms)
                        
                        cur.execute('INSERT INTO "Users" (username, password_hash, full_name, email, role, status, force_pwd_reset, custom_permissions) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                                     (request.form.get('new_username'), phash, request.form.get('full_name'), clean_email(request.form.get('user_email')) or request.form.get('user_email'), role, status, force_pwd, perms_json))
                        flash("User account created successfully.")
                    elif action == 'edit_user':
                        uid = request.form.get('user_id')
                        fname = request.form.get('full_name')
                        uemail = clean_email(request.form.get('user_email')) or request.form.get('user_email')
                        urole = request.form.get('user_role', 'Operator')
                        ustatus = request.form.get('status', 'Active')
                        force_pwd = True if request.form.get('force_pwd_reset') == 'true' else False
                        new_pass = request.form.get('new_password')
                        
                        custom_perms = {}
                        for module in ['leads', 'accounts', 'sales_desk', 'bids', 'workforce', 'monitor', 'qms', 'social', 'outbox', 'users', 'tools']:
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
                        for module in ['leads', 'accounts', 'sales_desk', 'bids', 'workforce', 'monitor', 'qms', 'social', 'outbox', 'users', 'tools']:
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
        if "conn" in locals() and conn: conn.close()
        
    return render_template('HWB-WEB Sigma Executive.html', 
                         leads_count=leads_count, recent_leads=recent_leads,
                         total_waste=total_waste, uptime=uptime, analytics=analytics,
                         kpivs=kpivs, users=users, role_permissions=role_permissions,
                         system_errors=system_errors, linkedin_authorized=linkedin_authorized,
                         pending_social=pending_social, pending_emails=pending_emails)


# --- Supporting Tools & Debug Helpers ---

@operations_bp.route('/calculator', endpoint='calculator')
def calculator():
    return redirect(url_for('get_quote'))


@operations_bp.route('/admin/scope-builder', methods=['POST'], endpoint='scope_builder')
@login_required
def scope_builder():
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            s_id, s_json = request.form.get('service_id'), request.form.get('scope_json')
            cur.execute('UPDATE "Services" SET scope_of_work = %s WHERE service_id = %s', (s_json, s_id))
            conn.commit()
            flash("CleanSync™ Operational: Scope updated.")
    except Exception as e:
        flash(f"Sync Error: {e}")
    finally:
        if "conn" in locals() and conn: conn.close()
    return redirect(url_for('admin_operations', view='scope'))


@operations_bp.route('/admin/lab', endpoint='sigmajan_lab')
@login_required
@roles_required('Executive', 'Admin')
def sigmajan_lab():
    return render_template('sigmajan_lab_home.html')


@operations_bp.route('/admin/linkedin-auth')
@login_required
def linkedin_auth():
    flash("LinkedIn Authorization Module is currently in R&D.")
    return redirect(url_for('sigma_executive'))


@operations_bp.route('/debug-login')
def debug_login():
    login_user(User(1, 'admin', 'Admin'))
    return redirect(url_for('admin_operations'))


@operations_bp.route('/debug-leads-count')
def debug_leads_count():
    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM "Leads";')
            total = cur.fetchone()[0]
        return jsonify({"total": total}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()
