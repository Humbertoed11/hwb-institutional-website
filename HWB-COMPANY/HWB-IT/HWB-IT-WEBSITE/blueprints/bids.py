"""
SigmaFidelity™ Construction Bids & Estimating Blueprint
Standard: HWB-QMS-7.7 Commercial Construction Takeoff & Estimating Engine SOP
Custodians: George (Systems Architect) & Natalie Navy (CDO)
"""

import os
import subprocess
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app
from flask_login import login_required
from core.services.database import get_db
from core.services.sanitizer import clean_phone, clean_email
from core.security import roles_required
from core.services.task_queue import task_queue

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

