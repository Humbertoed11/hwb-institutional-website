"""
SigmaFidelity™ Construction Bids & Estimating Blueprint
Standard: HWB-QMS-7.7 Commercial Construction Takeoff & Estimating Engine SOP
Custodians: George (Systems Architect) & Natalie Navy (CDO)
"""

import os
import subprocess
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app, abort, send_from_directory
from flask_login import login_required
from core.services.database import get_db
from core.services.sanitizer import clean_phone, clean_email
from core.security import roles_required
from core.services.task_queue import task_queue
from core.services.estimator import (
    calculate_commercial_gc_bid,
    calculate_institutional_bid,
    calculate_municipal_cluster_bid,
    calculate_federal_sca_bid,
    get_sca_wage_determination
)
from core.services.gc_vetting_engine import GCVettingEngine
from core.services.security_logger import log_security_event

bids_bp = Blueprint('bids', __name__)

@bids_bp.route('/prequal', endpoint='prequal')
def prequal():
    """Institutional Subcontractor Prequalification Portal."""
    return render_template('prequal.html')

@bids_bp.route('/csi', endpoint='csi_map')
def csi_map():
    """Construction Specifications Institute (CSI) MasterFormat Map."""
    return render_template('HWB-WEB Csi.html')

@bids_bp.route('/tma/estimator', endpoint='tma_estimator')
def tma_estimator():
    """Telegram Mini App endpoint for interactive scope & takeoff configuration."""
    return render_template('tma_estimator.html')

@bids_bp.route('/admin/construction-bids', endpoint='admin_construction_bids')
@login_required
@roles_required('Executive', 'Admin', 'Manager', 'Estimator')
def admin_construction_bids():
    return redirect(url_for('admin_operations', view='construction_bids'))

@bids_bp.route('/api/v1/construction-bids/create', methods=['POST'])
@login_required
def api_bid_create():
    """API Endpoint to create a new commercial construction bid record."""
    data = request.get_json() or {}
    gc_name = data.get('gc_name', '').strip()
    project_name = data.get('project_name', '').strip()
    if not gc_name or not project_name:
        return jsonify({'status': 'error', 'message': 'GC Name and Project Name are required'}), 400

    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
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
                data.get('estimator_name'), 
                clean_phone(data.get('estimator_phone')) or data.get('estimator_phone'), 
                clean_email(data.get('estimator_email')) or data.get('estimator_email'),
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
        if conn: conn.close()

def _run_gc_bids_sync():
    res = subprocess.run(['python', 'scripts/gc_bids_sync.py'], capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        raise RuntimeError(f"Sync failed with exit code {res.returncode}: {res.stderr}")
    return res.stdout

@bids_bp.route('/api/v1/construction-bids/sync', methods=['POST', 'GET'])
@login_required
def api_sync_construction_bids():
    """Enqueues background synchronization for GC planroom bids via managed task queue."""
    task_id = task_queue.enqueue(_run_gc_bids_sync, name="GC Planroom Bids Sync", max_retries=2)
    return jsonify({
        'status': 'success',
        'task_id': task_id,
        'message': 'GC planroom sync enqueued in background task queue.'
    })

@bids_bp.route('/api/v1/construction-bids/<int:bid_id>/status', methods=['POST'])
@login_required
def api_update_bid_status(bid_id):
    data = request.get_json() or {}
    new_status = data.get('status')
    notes = data.get('notes', '').strip()
    if not new_status:
        return jsonify({'status': 'error', 'message': 'Missing status'}), 400
    conn = get_db(current_app.config['DATABASE_URL'])
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
        if 'conn' in locals() and conn: conn.close()

@bids_bp.route('/api/v1/construction-bids/<int:bid_id>/activity', methods=['POST'])
@login_required
def api_bid_log_activity(bid_id):
    data = request.get_json() or {}
    note = data.get('note', '').strip()
    activity_type = data.get('activity_type', 'Phone Call')
    if not note:
        return jsonify({'status': 'error', 'message': 'Missing note content'}), 400
    conn = get_db(current_app.config['DATABASE_URL'])
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
        if 'conn' in locals() and conn: conn.close()

@bids_bp.route('/api/v1/construction-bids/<int:bid_id>/edit', methods=['POST'])
@login_required
def api_bid_edit(bid_id):
    data = request.get_json() or {}
    cleanable_sqft = data.get('cleanable_sqft')
    estimated_value = data.get('estimated_value')
    scope_phase = data.get('scope_phase')
    special_requirements = data.get('special_requirements')
    estimator_name = data.get('estimator_name')
    estimator_phone = clean_phone(data.get('estimator_phone')) or data.get('estimator_phone')
    estimator_email = clean_email(data.get('estimator_email')) or data.get('estimator_email')
    notes = data.get('notes')

    conn = get_db(current_app.config['DATABASE_URL'])
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
        if 'conn' in locals() and conn: conn.close()

# --- GC Vetting & Profile Completer Engine (Option 1 Standard) ---

@bids_bp.route('/api/v1/gc-vetting/<int:bid_id>/enrich', methods=['POST'])
@login_required
@roles_required('Executive', 'Admin', 'Manager', 'Estimator')
def api_enrich_single_bid(bid_id):
    """Executes on-demand autonomous profile enrichment and 4-point vetting for a bid."""
    db_url = current_app.config['DATABASE_URL']
    res = GCVettingEngine.enrich_single_bid(bid_id, db_url)
    status_code = 200 if res.get('status') == 'success' else 500
    return jsonify(res), status_code

@bids_bp.route('/api/v1/gc-vetting/enrich-all', methods=['POST'])
@login_required
@roles_required('Executive', 'Admin', 'Manager')
def api_enrich_all_bids():
    """Executes batch autonomous profile completion across all commercial construction bids."""
    db_url = current_app.config['DATABASE_URL']
    summary = GCVettingEngine.enrich_all_bids(db_url)
    return jsonify(summary)

@bids_bp.route('/api/v1/general-contractors', methods=['GET'])
@login_required
def api_list_general_contractors():
    """Fetches master directory of vetted general contractors."""
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, company_name, legal_name, headquarters_address, city, state, zipcode,
                       corporate_phone, website, entity_type, sos_status, certifications,
                       lead_estimator_name, lead_estimator_title, lead_estimator_email, lead_estimator_phone,
                       payment_terms, billing_format, retainage_pct, pay_rating, operating_radius_miles,
                       primary_market, vetting_score, vetting_tier, vetting_notes, is_verified
                FROM "GeneralContractors"
                ORDER BY vetting_score DESC, company_name ASC;
            ''')
            rows = cur.fetchall()
            return jsonify({'status': 'success', 'count': len(rows), 'general_contractors': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals() and conn: conn.close()

# --- Institutional & Public Solicitations API (HWB-QMS-11.6) ---

@bids_bp.route('/admin/institutional-bids', endpoint='admin_institutional_bids')
@login_required
@roles_required('Executive', 'Admin', 'Manager', 'Estimator')
def admin_institutional_bids():
    """Redirect to unified operations institutional_bids view."""
    return redirect(url_for('admin_operations', view='institutional_bids'))

@bids_bp.route('/api/v1/institutional-bids/create', methods=['POST'])
@login_required
def api_inst_bid_create():
    """API Endpoint to create a new institutional/public solicitation record."""
    data = request.get_json() or {}
    solicitation_number = data.get('solicitation_number', '').strip()
    title = data.get('title', '').strip()
    agency_name = data.get('agency_name', '').strip()
    if not solicitation_number or not title or not agency_name:
        return jsonify({'status': 'error', 'message': 'Solicitation #, Title, and Agency are required'}), 400

    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO "InstitutionalBids" (
                    solicitation_number, title, agency_name, sector, portal_name, portal_doc_id,
                    procurement_officer, officer_email, officer_phone, contract_term_months,
                    cleanable_sqft, facilities_count, published_budget, hwb_bid_total,
                    monthly_base_rate, annual_base_rate, hourly_porter_rate,
                    status, compliance_status, rfp_url, notes
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s
                ) RETURNING id
            ''', (
                solicitation_number, title, agency_name,
                data.get('sector', 'Public Authority'),
                data.get('portal_name', ''),
                data.get('portal_doc_id', ''),
                data.get('procurement_officer', ''),
                clean_email(data.get('officer_email')) or data.get('officer_email', ''),
                clean_phone(data.get('officer_phone')) or data.get('officer_phone', ''),
                int(data.get('contract_term_months', 24) or 24),
                float(data.get('cleanable_sqft', 0) or 0),
                int(data.get('facilities_count', 1) or 1),
                float(data.get('published_budget', 0) or 0),
                float(data.get('hwb_bid_total', 0) or 0),
                float(data.get('monthly_base_rate', 0) or 0),
                float(data.get('annual_base_rate', 0) or 0),
                float(data.get('hourly_porter_rate', 0) or 0),
                data.get('status', 'Active Solicitation'),
                data.get('compliance_status', 'Pending Review'),
                data.get('rfp_url', ''),
                data.get('notes', '')
            ))
            new_id = cur.fetchone()[0]
            conn.commit()
            return jsonify({'status': 'success', 'message': 'Institutional solicitation created.', 'id': new_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals() and conn: conn.close()

@bids_bp.route('/api/v1/institutional-bids/<int:bid_id>/status', methods=['POST'])
@login_required
def api_inst_bid_status(bid_id):
    """Update institutional bid pipeline or compliance status."""
    data = request.get_json() or {}
    new_status = data.get('status')
    compliance_status = data.get('compliance_status')
    if not new_status and not compliance_status:
        return jsonify({'status': 'error', 'message': 'Status parameter required'}), 400

    conn = get_db(current_app.config['DATABASE_URL'])
    try:
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE "InstitutionalBids"
                SET status = COALESCE(%s, status),
                    compliance_status = COALESCE(%s, compliance_status),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (new_status, compliance_status, bid_id))
            conn.commit()
            return jsonify({'status': 'success', 'message': 'Institutional status updated.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals() and conn: conn.close()


# ==============================================================================
# UNIFIED ESTIMATING & DIGITAL BID ROOM ENDPOINTS (SigmaEstimator™ Evolution)
# ==============================================================================

@bids_bp.route('/api/v1/bids/estimate', methods=['POST'])
@login_required
def api_bid_estimate():
    """
    Unified 3-Tier Estimating API:
    - tier: 'commercial' | 'institutional' | 'federal_sca'
    """
    data = request.get_json() or {}
    tier = data.get('tier', 'commercial').lower().strip()
    db_url = current_app.config.get('DATABASE_URL')

    try:
        if tier in ['commercial', 'gc', 'construction']:
            res = calculate_commercial_gc_bid(
                cleanable_sqft=float(data.get('cleanable_sqft', 0)),
                scope_phase=data.get('scope_phase', 'Rough, Final & Touch-Up Clean'),
                num_floors=int(data.get('num_floors', 1)),
                has_high_glass=bool(data.get('has_high_glass', False)),
                lift_rental=float(data.get('lift_rental', 0)),
                target_margin=float(data.get('target_margin', 0.20)),
                negotiation_buffer=float(data.get('negotiation_buffer', 0.04)),
                walkaway_margin=float(data.get('walkaway_margin', 0.16)),
                urban_logistics=bool(data.get('urban_logistics', False)),
                retainage_float=bool(data.get('retainage_float', False)),
                offsite_trash_hauling=bool(data.get('offsite_trash_hauling', False))
            )
        elif tier in ['institutional', 'municipal', 'tips', 'cluster', 'municipal_cluster']:
            num_facilities = int(data.get('num_facilities', 1) or 1)
            if num_facilities > 1 or tier in ['cluster', 'municipal_cluster']:
                res = calculate_municipal_cluster_bid(
                    num_facilities=num_facilities,
                    cleanable_sqft_per_facility=float(data.get('cleanable_sqft_per_facility', data.get('cleanable_sqft', 10000.0) or 10000.0)),
                    days_per_week=int(data.get('days_per_week', 5) or 5),
                    custodians_per_facility=float(data.get('custodians_per_facility', 1.0) or 1.0),
                    hours_per_day_per_custodian=float(data.get('hours_per_day', 4.0) or 4.0),
                    hourly_wage=float(data.get('base_hourly_rate', data.get('hourly_wage', 18.00)) or 18.00),
                    contract_term_months=int(data.get('term_months', 36) or 36),
                    supply_per_facility_monthly=float(data.get('supply_monthly', 150.0) or 150.0),
                    equipment_per_facility_monthly=float(data.get('equipment_monthly', 100.0) or 100.0),
                    target_margin=float(data.get('target_margin', 0.18) or 0.18),
                    negotiation_buffer=float(data.get('negotiation_buffer', 0.03) or 0.03),
                    walkaway_margin=float(data.get('walkaway_margin', 0.14) or 0.14),
                    is_mwbe_subcontract=bool(data.get('is_mwbe_subcontract', True))
                )
            else:
                res = calculate_institutional_bid(
                    cleanable_sqft=float(data.get('cleanable_sqft', 0)),
                    mandated_weekly_hours=float(data.get('weekly_hours', 40.0)),
                    term_months=int(data.get('term_months', 24)),
                    day_porters=int(data.get('day_porters', 1)),
                    night_custodians=int(data.get('night_custodians', 2)),
                    base_hourly_rate=float(data.get('base_hourly_rate', 16.00)),
                    sup_hourly_rate=float(data.get('sup_hourly_rate', 18.50)),
                    supply_monthly=float(data.get('supply_monthly', 500.0)),
                    equipment_monthly=float(data.get('equipment_monthly', 350.0)),
                    target_margin=float(data.get('target_margin', 0.18)),
                    negotiation_buffer=float(data.get('negotiation_buffer', 0.03)),
                    walkaway_margin=float(data.get('walkaway_margin', 0.14))
                )
        elif tier in ['federal', 'sca', 'federal_sca']:
            res = calculate_federal_sca_bid(
                county=data.get('county', 'Collin'),
                cleanable_sqft=float(data.get('cleanable_sqft', 25000.0)),
                weekly_labor_hours=float(data.get('weekly_hours', 40.0)),
                occupation=data.get('occupation', 'Janitor / Custodian'),
                use_eo13706=bool(data.get('use_eo13706', True)),
                vacation_weeks=int(data.get('vacation_weeks', 2)),
                paid_holidays=int(data.get('paid_holidays', 11)),
                supplies_monthly=float(data.get('supplies_monthly', 300.0)),
                equipment_monthly=float(data.get('equipment_monthly', 200.0)),
                target_margin=float(data.get('target_margin', 0.15)),
                db_url=db_url
            )
        else:
            return jsonify({'status': 'error', 'message': f"Unsupported estimating tier: '{tier}'"}), 400

        return jsonify({'status': 'success', 'data': res})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bids_bp.route('/api/v1/bids/sca/wage-determination', methods=['GET'])
@login_required
def api_sca_wage_determination():
    """Lookup binding DOL Wage Determination for a specific Texas county and occupation."""
    county = request.args.get('county', 'Collin')
    occupation = request.args.get('occupation', 'Janitor / Custodian')
    db_url = current_app.config.get('DATABASE_URL')
    wd_info = get_sca_wage_determination(county=county, occupation=occupation, db_url=db_url)
    return jsonify({'status': 'success', 'data': wd_info})


@bids_bp.route('/api/v1/bids/<int:bid_id>/documents', methods=['GET', 'POST'])
@login_required
def api_bid_documents(bid_id):
    """Digital Bid Room: Attach or list planroom documents, specs, drawings, and submittals."""
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            if request.method == 'POST':
                data = request.get_json() or {}
                doc_name = data.get('document_name', '').strip()
                file_path = data.get('file_path', '').strip()
                doc_type = data.get('document_type', 'Spec')
                bid_type = data.get('bid_type', 'ConstructionBid')
                notes = data.get('notes', '')

                if not doc_name or not file_path:
                    return jsonify({'status': 'error', 'message': 'document_name and file_path are required.'}), 400

                cur.execute('''
                    INSERT INTO "BidDocuments" (
                        bid_type, construction_bid_id, institutional_bid_id,
                        document_name, document_type, file_path, file_size, notes
                    ) VALUES (
                        %s,
                        CASE WHEN %s = 'ConstructionBid' THEN %s ELSE NULL END,
                        CASE WHEN %s = 'InstitutionalBid' THEN %s ELSE NULL END,
                        %s, %s, %s, %s, %s
                    ) RETURNING id;
                ''', (
                    bid_type, bid_type, bid_id, bid_type, bid_id,
                    doc_name, doc_type, file_path, int(data.get('file_size', 0)), notes
                ))
                new_id = cur.fetchone()[0]
                conn.commit()
                return jsonify({'status': 'success', 'document_id': new_id, 'message': 'Document attached to bid room.'}), 201
            else:
                cur.execute('''
                    SELECT id, document_name, document_type, file_path, file_size, notes, created_at
                    FROM "BidDocuments"
                    WHERE construction_bid_id = %s OR institutional_bid_id = %s
                    ORDER BY created_at DESC;
                ''', (bid_id, bid_id))
                docs = [
                    {
                        'id': r[0], 'document_name': r[1], 'document_type': r[2],
                        'file_path': r[3], 'file_size': r[4], 'notes': r[5],
                        'created_at': r[6].isoformat() if r[6] else None
                    }
                    for r in cur.fetchall()
                ]
                return jsonify({'status': 'success', 'documents': docs})
    except Exception as e:
        if 'conn' in locals() and conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals() and conn: conn.close()


@bids_bp.route('/api/v1/bids/<int:bid_id>/addenda', methods=['GET', 'POST'])
@login_required
def api_bid_addenda(bid_id):
    """Addenda Sentinel: Track amendments, changes in scope, and auto-update due dates."""
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            if request.method == 'POST':
                data = request.get_json() or {}
                addendum_num = data.get('addendum_number', '').strip()
                summary = data.get('summary_of_changes', '').strip()
                revised_due_date = data.get('revised_bid_due_date')
                scope_impact = data.get('scope_impact', 'No Scope Change')
                bid_type = data.get('bid_type', 'ConstructionBid')

                if not addendum_num or not summary:
                    return jsonify({'status': 'error', 'message': 'addendum_number and summary_of_changes are required.'}), 400

                cur.execute('''
                    INSERT INTO "BidAddenda" (
                        bid_type, construction_bid_id, institutional_bid_id,
                        addendum_number, revised_bid_due_date, summary_of_changes, scope_impact
                    ) VALUES (
                        %s,
                        CASE WHEN %s = 'ConstructionBid' THEN %s ELSE NULL END,
                        CASE WHEN %s = 'InstitutionalBid' THEN %s ELSE NULL END,
                        %s, NULLIF(%s, '')::timestamptz, %s, %s
                    ) RETURNING id;
                ''', (
                    bid_type, bid_type, bid_id, bid_type, bid_id,
                    addendum_num, revised_due_date, summary, scope_impact
                ))
                new_id = cur.fetchone()[0]

                # Auto-update parent bid due date if revised
                if revised_due_date:
                    if bid_type == 'ConstructionBid':
                        cur.execute('''
                            UPDATE "ConstructionBids"
                            SET bid_due_date = %s::timestamptz, updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s;
                        ''', (revised_due_date, bid_id))
                    elif bid_type == 'InstitutionalBid':
                        cur.execute('''
                            UPDATE "InstitutionalBids"
                            SET bid_due_date = %s::timestamptz, updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s;
                        ''', (revised_due_date, bid_id))

                cur.execute('''
                    INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                    VALUES (%s, %s, 'Addendum Logged', %s);
                ''', (bid_id, bid_type, f"Addendum {addendum_num} recorded: {summary[:100]}"))

                conn.commit()
                return jsonify({
                    'status': 'success',
                    'addendum_id': new_id,
                    'message': f"Addendum {addendum_num} recorded successfully."
                }), 201
            else:
                cur.execute('''
                    SELECT id, addendum_number, revised_bid_due_date, summary_of_changes,
                           scope_impact, is_acknowledged, created_at
                    FROM "BidAddenda"
                    WHERE construction_bid_id = %s OR institutional_bid_id = %s
                    ORDER BY created_at DESC;
                ''', (bid_id, bid_id))
                addenda = [
                    {
                        'id': r[0], 'addendum_number': r[1],
                        'revised_bid_due_date': r[2].isoformat() if r[2] else None,
                        'summary_of_changes': r[3], 'scope_impact': r[4],
                        'is_acknowledged': r[5],
                        'created_at': r[6].isoformat() if r[6] else None
                    }
                    for r in cur.fetchall()
                ]
                return jsonify({'status': 'success', 'addenda': addenda})
    except Exception as e:
        if 'conn' in locals() and conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals() and conn: conn.close()


@bids_bp.route('/api/v1/bids/<int:bid_id>/rfis', methods=['GET', 'POST'])
@login_required
def api_bid_rfis(bid_id):
    """RFI Tracker: Record formal questions submitted to General Contractors and public agencies."""
    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            if request.method == 'POST':
                data = request.get_json() or {}
                rfi_num = data.get('rfi_number', '').strip()
                subject = data.get('subject', '').strip()
                question = data.get('question', '').strip()
                answer = data.get('answer', '')
                status = data.get('status', 'Submitted')
                bid_type = data.get('bid_type', 'ConstructionBid')

                if not rfi_num or not subject or not question:
                    return jsonify({'status': 'error', 'message': 'rfi_number, subject, and question are required.'}), 400

                cur.execute('''
                    INSERT INTO "BidRFIs" (
                        bid_type, construction_bid_id, institutional_bid_id,
                        rfi_number, subject, question, answer, status
                    ) VALUES (
                        %s,
                        CASE WHEN %s = 'ConstructionBid' THEN %s ELSE NULL END,
                        CASE WHEN %s = 'InstitutionalBid' THEN %s ELSE NULL END,
                        %s, %s, %s, NULLIF(%s, ''), %s
                    ) RETURNING id;
                ''', (
                    bid_type, bid_type, bid_id, bid_type, bid_id,
                    rfi_num, subject, question, answer, status
                ))
                new_id = cur.fetchone()[0]

                cur.execute('''
                    INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                    VALUES (%s, %s, 'RFI Submitted', %s);
                ''', (bid_id, bid_type, f"RFI {rfi_num} ({subject}): {question[:100]}"))

                conn.commit()
                return jsonify({'status': 'success', 'rfi_id': new_id, 'message': f"RFI {rfi_num} recorded."}), 201
            else:
                cur.execute('''
                    SELECT id, rfi_number, subject, question, answer, status, date_submitted, date_answered
                    FROM "BidRFIs"
                    WHERE construction_bid_id = %s OR institutional_bid_id = %s
                    ORDER BY date_submitted DESC;
                ''', (bid_id, bid_id))
                rfis = [
                    {
                        'id': r[0], 'rfi_number': r[1], 'subject': r[2],
                        'question': r[3], 'answer': r[4], 'status': r[5],
                        'date_submitted': r[6].isoformat() if r[6] else None,
                        'date_answered': r[7].isoformat() if r[7] else None
                    }
                    for r in cur.fetchall()
                ]
                return jsonify({'status': 'success', 'rfis': rfis})
    except Exception as e:
        if 'conn' in locals() and conn: conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals() and conn: conn.close()


@bids_bp.route('/api/v1/bids/download-file', methods=['GET'])
@login_required
def api_bid_download_file():
    """Securely streams quote files, bid sheets, dossiers, or plans from HWB-QUOTES."""
    file_path = request.args.get('path', '').strip()
    if not file_path:
        abort(400, "Missing path parameter")

    clean_path = file_path
    for pfx in ['/home/humbertoed/gemini_projects/', '/app/', '/home/humbertoed/gemini_projects', '/app']:
        if clean_path.startswith(pfx):
            clean_path = clean_path[len(pfx):]
            break
    clean_path = clean_path.lstrip('/')
    base_app_dir = current_app.root_path  # /app in Docker container
    target_abs = os.path.normpath(os.path.join(base_app_dir, clean_path))

    allowed_base = os.path.normpath(os.path.join(base_app_dir, 'HWB-COMPANY'))
    alt_allowed_base = os.path.normpath(os.path.join(base_app_dir, '../../../HWB-COMPANY'))

    target_is_valid = False
    if target_abs.startswith(allowed_base) and os.path.exists(target_abs):
        target_is_valid = True
    else:
        alt_target = os.path.normpath(os.path.join(base_app_dir, '../../..', clean_path))
        if alt_target.startswith(alt_allowed_base) and os.path.exists(alt_target):
            target_abs = alt_target
            target_is_valid = True

    if not target_is_valid or os.path.isdir(target_abs):
        abort(404, "File not found or access restricted")

    directory = os.path.dirname(target_abs)
    filename = os.path.basename(target_abs)
    return send_from_directory(directory, filename, as_attachment=('download' in request.args))


@bids_bp.route('/api/v1/bids/<int:bid_id>/commit-estimate', methods=['POST'])
@login_required
@roles_required('Executive', 'Admin')
def api_bid_commit_estimate(bid_id):
    """Commits recalculated takeoff values, square footage, and pricing to ConstructionBids."""
    payload = request.get_json() or {}
    cleanable_sqft = float(payload.get('cleanable_sqft', 0))
    estimated_value = float(payload.get('estimated_value', 0))
    scope_phase = payload.get('scope_phase', '').strip()
    status = payload.get('status', 'Takeoff Completed')
    notes = payload.get('notes', '')

    db_url = current_app.config['DATABASE_URL']
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE "ConstructionBids"
                SET cleanable_sqft = %s,
                    estimated_value = %s,
                    scope_phase = COALESCE(NULLIF(%s, ''), scope_phase),
                    status = %s,
                    notes = COALESCE(NULLIF(%s, ''), notes),
                    updated_at = NOW()
                WHERE id = %s;
            ''', (cleanable_sqft, estimated_value, scope_phase, status, notes, bid_id))
            conn.commit()
        
        log_security_event(
            event_category='FINANCIAL_INTEGRITY',
            event_action='TAKEOFF_COMMITTED',
            severity='INFO',
            details={
                'bid_id': bid_id,
                'cleanable_sqft': cleanable_sqft,
                'estimated_value': estimated_value,
                'scope_phase': scope_phase,
                'status': status
            }
        )
        return jsonify({'status': 'success', 'message': f'Bid #{bid_id} updated successfully.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()



