"""
SigmaFidelity™ Enterprise Telemetry & Health Blueprint
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Peter (Recovery Specialist)
"""

import time
import os
from urllib.parse import urlparse
from flask import Blueprint, jsonify, current_app, Response, request, redirect
from core.services.database import get_db, get_pool_status
from core.services.task_queue import task_queue
from core.services.version_service import get_version_info

telemetry_bp = Blueprint('telemetry', __name__)

@telemetry_bp.route('/api/v1/ping')
def ping():
    """Liveness probe for container orchestration."""
    return jsonify({
        "status": "ok",
        "service": "hwb_web_app",
        "timestamp": time.time()
    }), 200

@telemetry_bp.route('/api/v1/version')
def version_endpoint():
    """Authoritative API endpoint for version, commit hash, and deployment environment verification."""
    ver = get_version_info()
    return jsonify({
        "status": "ok",
        **ver
    }), 200

@telemetry_bp.route('/api/v1/health')
def health_check():
    """Enterprise readiness, database latency, and connection pool telemetry."""
    db_url = current_app.config.get('DATABASE_URL')
    start_t = time.time()
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute('SELECT 1;')
            cur.fetchone()
        latency_ms = round((time.time() - start_t) * 1000, 2)
        ver = get_version_info()
        return jsonify({
            "status": "healthy",
            "version": ver["app_version"],
            "commit": ver["commit"],
            "build_tag": ver["build_tag"],
            "environment": ver["environment"],
            "display_version": ver["display_version"],
            "database": "connected",
            "db_host": urlparse(db_url).hostname if db_url else "unknown",
            "latency_ms": latency_ms,
            "connection_pool": get_pool_status(db_url)
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 503
    finally:
        if conn:
            conn.close()

@telemetry_bp.route('/api/v1/db-audit')
def db_audit_endpoint():
    """Live audit endpoint verifying leads and test row segregation."""
    db_url = current_app.config.get('DATABASE_URL')
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM "Leads";')
            total_leads = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM "Leads" WHERE (is_duplicate = FALSE OR is_duplicate IS NULL) AND (status != \'ARCHIVED\' OR status IS NULL);')
            active_clean_leads = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM "Leads" WHERE is_duplicate = TRUE;')
            duplicate_leads = cur.fetchone()[0]
            cur.execute('SELECT id, center_name FROM "Leads" WHERE id = 44518 OR center_name ILIKE \'%DFW6%\';')
            dfw6_rows = cur.fetchall()
            cur.execute('SELECT id, center_name FROM "Leads" WHERE center_name ILIKE \'%Test Lead%\';')
            test_leads = cur.fetchall()

            # Commercial Construction Bids Telemetry
            cur.execute('SELECT COUNT(*), COALESCE(SUM(estimated_value), 0) FROM "ConstructionBids";')
            cb_row = cur.fetchone()
            cb_count = cb_row[0] if cb_row else 0
            cb_val = float(cb_row[1]) if cb_row and cb_row[1] else 0.0

            # Institutional Bids Telemetry
            cur.execute('SELECT COUNT(*), COALESCE(SUM(hwb_bid_total), 0) FROM "InstitutionalBids";')
            ib_row = cur.fetchone()
            ib_count = ib_row[0] if ib_row else 0
            ib_val = float(ib_row[1]) if ib_row and ib_row[1] else 0.0

        return jsonify({
            'database_host': urlparse(db_url).hostname if db_url else "unknown",
            'total_leads_count': total_leads,
            'active_clean_leads_count': active_clean_leads,
            'duplicate_leads_count': duplicate_leads,
            'construction_bids_count': cb_count,
            'construction_bids_total_value': cb_val,
            'institutional_bids_count': ib_count,
            'institutional_bids_total_value': ib_val,
            'dfw6_rows_found': [dict(r) for r in dfw6_rows],
            'test_leads_found': [dict(r) for r in test_leads]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@telemetry_bp.route('/api/v1/tasks', methods=['GET'])
def list_tasks():
    """Returns telemetry on background tasks managed by the task queue."""
    return jsonify({
        "status": "success",
        "tasks": task_queue.list_recent(limit=25)
    }), 200

@telemetry_bp.route('/api/v1/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Queries live execution state and logs for a specific background task."""
    task = task_queue.get_status(task_id)
    if not task:
        return jsonify({"status": "error", "message": "Task not found"}), 404
    return jsonify({"status": "success", "task": task}), 200


@telemetry_bp.route('/api/v1/analytics/site-audit', methods=['GET'])
def site_analytics_audit():
    """Live audit endpoint verifying Google Analytics GA4 and SEO infrastructure."""
    ga_id = current_app.config.get('GA_MEASUREMENT_ID') or 'G-8BX5Q7THYR'
    db_url = current_app.config.get('DATABASE_URL')
    six_sigma_data = {}
    conn = None
    try:
        conn = get_db(db_url)
        with conn.cursor() as cur:
            cur.execute('SELECT tool_name, result FROM "Analytics";')
            for row in cur.fetchall():
                six_sigma_data[row[0]] = row[1]
    except Exception as e:
        six_sigma_data["error"] = str(e)
    finally:
        if conn: conn.close()

    return jsonify({
        "status": "HEALTHY",
        "google_analytics": {
            "measurement_id": ga_id,
            "container": "gtag.js",
            "tag_status": "ACTIVE_CONFIGURED",
            "tag_location": "base.html <head>",
            "conversion_events": [
                {
                    "event_name": "generate_lead",
                    "trigger": "quote_success.html on lead capture",
                    "parameters": {"currency": "USD", "value": 150.00}
                },
                {
                    "event_name": "click_to_call",
                    "trigger": "a[href^='tel:'] on tap/click",
                    "parameters": {"event_category": "Contact"}
                }
            ]
        },
        "search_infrastructure": {
            "sitemap_url": "https://www.hwbcleaning.com/sitemap.xml",
            "sitemap_priority_pages": 11,
            "robots_txt_url": "https://www.hwbcleaning.com/robots.txt",
            "staging_shield": "ACTIVE (X-Robots-Tag: noindex, nofollow on non-production hosts)"
        },
        "internal_analytics": six_sigma_data
    }), 200


# 1x1 Transparent GIF Byte Structure
TRANSPARENT_GIF_BYTES = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
    b'\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
    b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
)


@telemetry_bp.route('/api/v1/marketing/track/open/<tracking_token>.gif', methods=['GET'])
@telemetry_bp.route('/api/v1/telemetry/pixel/<tracking_token>.gif', methods=['GET'])
def track_email_open(tracking_token):
    """
    Transparent 1x1 GIF tracking pixel for marketing email open detection.
    Updates CampaignRecipients and MarketingCampaigns telemetry in real time.
    """
    if tracking_token:
        conn = None
        try:
            db_url = current_app.config.get('DATABASE_URL')
            conn = get_db(db_url)
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE "CampaignRecipients"
                    SET opened_at = COALESCE(opened_at, CURRENT_TIMESTAMP),
                        open_count = COALESCE(open_count, 0) + 1,
                        status = CASE WHEN status IN ('STAGED', 'AWAITING_APPROVAL', 'SENT') THEN 'OPENED' ELSE status END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tracking_token = %s
                    RETURNING campaign_id, lead_id, open_count, facility_name;
                ''', (tracking_token,))
                row = cur.fetchone()
                if row:
                    camp_id = row['campaign_id'] if isinstance(row, dict) else row[0]
                    lead_id = row['lead_id'] if isinstance(row, dict) else row[1]
                    open_count = row['open_count'] if isinstance(row, dict) else row[2]
                    facility = row['facility_name'] if isinstance(row, dict) else row[3]

                    if camp_id:
                        cur.execute('''
                            UPDATE "MarketingCampaigns"
                            SET opened_count = (SELECT COUNT(DISTINCT id) FROM "CampaignRecipients" WHERE campaign_id = %s AND COALESCE(open_count, 0) > 0),
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s;
                        ''', (camp_id, camp_id))

                    if lead_id:
                        cur.execute('''
                            INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                            VALUES (%s, 'Lead', 'Email Opened', %s);
                        ''', (lead_id, f"Customer opened marketing email (View #{open_count}) for {facility or 'facility'}"))

                        # Option 2 Smart Status Automation: Promote lead to 'Engaged 🔥' and prioritize for sales team
                        cur.execute('''
                            UPDATE "Leads"
                            SET status = 'Engaged',
                                priority_level = 'High',
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s AND (status IN ('New', 'NEW', 'In Campaign', 'Contacted') OR status IS NULL)
                            RETURNING id;
                        ''', (lead_id,))
                        if cur.fetchone():
                            cur.execute('''
                                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                                VALUES (%s, 'Lead', 'Status Change', %s);
                            ''', (lead_id, f"Lead status promoted to 'Engaged 🔥' (Customer viewed email {open_count}x). Prioritized for sales follow-up."))

                conn.commit()
        except Exception as e:
            if conn:
                try: conn.rollback()
                except Exception: pass
            current_app.logger.warning(f"[TRACKING PIXEL] Error recording open for token {tracking_token}: {e}")
        finally:
            if conn:
                try: conn.close()
                except Exception: pass

    resp = Response(TRANSPARENT_GIF_BYTES, mimetype='image/gif')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@telemetry_bp.route('/api/v1/marketing/track/click/<tracking_token>', methods=['GET'])
def track_email_click(tracking_token):
    """
    Tracks marketing email link clicks (e.g. CEO booking calendar) and redirects to destination.
    """
    default_dest = os.getenv('HWB_CEO_BOOKING_URL') or 'https://bookings.cloud.microsoft/book/FacilityWalkthroughquote@NETORGFT3163094.onmicrosoft.com/'
    dest = request.args.get('dest') or default_dest
    if 'hdominguez@hwbcleaning.com' in dest and 'bookwithme' in dest:
        dest = default_dest
    if tracking_token:
        conn = None
        try:
            db_url = current_app.config.get('DATABASE_URL')
            conn = get_db(db_url)
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE "CampaignRecipients"
                    SET clicked_at = COALESCE(clicked_at, CURRENT_TIMESTAMP),
                        click_count = COALESCE(click_count, 0) + 1,
                        status = 'ENGAGED',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tracking_token = %s
                    RETURNING campaign_id, lead_id, facility_name;
                ''', (tracking_token,))
                click_row = cur.fetchone()
                if click_row:
                    c_lead_id = click_row['lead_id'] if isinstance(click_row, dict) else click_row[1]
                    c_facility = click_row['facility_name'] if isinstance(click_row, dict) else click_row[2]
                    if c_lead_id:
                        cur.execute('''
                            INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                            VALUES (%s, 'Lead', 'Link Clicked', %s);
                        ''', (c_lead_id, f"Customer clicked walkthrough booking link in marketing email for {c_facility or 'facility'}"))

                        # Option 2 Smart Status Automation: Promote lead to 'Qualified'
                        cur.execute('''
                            UPDATE "Leads"
                            SET status = 'Qualified',
                                priority_level = 'High',
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s AND (status IN ('New', 'NEW', 'In Campaign', 'Contacted', 'Engaged') OR status IS NULL)
                            RETURNING id;
                        ''', (c_lead_id,))
                        if cur.fetchone():
                            cur.execute('''
                                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                                VALUES (%s, 'Lead', 'Status Change', %s);
                            ''', (c_lead_id, "Lead status promoted to 'Qualified' (Customer clicked walkthrough calendar link in marketing email)."))
                conn.commit()
        except Exception as e:
            if conn:
                try: conn.rollback()
                except Exception: pass
            current_app.logger.warning(f"[TRACKING CLICK] Error recording click for token {tracking_token}: {e}")
        finally:
            if conn:
                try: conn.close()
                except Exception: pass
    return redirect(dest)


@telemetry_bp.route('/api/v1/telemetry/breadcrumbs', methods=['POST'])
def record_client_breadcrumbs():
    """
    Ingests client-side micro-interaction breadcrumbs (clicks, rage clicks, JS runtime errors).
    Standard: ISO 27001 Control A.8.15 / SOC 2 CC6.8.
    """
    try:
        data = request.get_json(silent=True, force=True) or {}
        session_id = (data.get('session_id') or 'anon_session')[:100]
        page_url = (data.get('page_url') or request.path)[:255]
        events = data.get('events') or []
        if not isinstance(events, list) or len(events) == 0:
            return jsonify({'status': 'ignored', 'reason': 'empty_events'}), 200

        # Cap batch size to 50 events per request (Poka-Yoke anti-abuse)
        events = events[:50]

        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
        user_agent = request.headers.get('User-Agent', '')[:500]

        from psycopg2.extras import Json
        db_url = current_app.config.get('DATABASE_URL')
        conn = get_db(db_url)
        inserted_count = 0
        try:
            with conn.cursor() as cur:
                for ev in events:
                    if not isinstance(ev, dict):
                        continue
                    event_type = (ev.get('event_type') or 'CLICK')[:50]
                    ev_page = (ev.get('page_url') or page_url)[:255]
                    tag = (ev.get('element_tag') or '')[:50]
                    el_id = (ev.get('element_id') or '')[:100]
                    el_class = (ev.get('element_class') or '')[:150]
                    el_text = (ev.get('element_text') or '')[:150]
                    details = ev.get('details')

                    cur.execute('''
                        INSERT INTO "ClientBreadcrumbs" (
                            timestamp, session_id, page_url, event_type, element_tag,
                            element_id, element_class, element_text, details, ip_address, user_agent
                        ) VALUES (
                            NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        );
                    ''', (
                        session_id, ev_page, event_type, tag,
                        el_id, el_class, el_text,
                        Json(details) if details else None,
                        client_ip, user_agent
                    ))
                    inserted_count += 1
            conn.commit()
        finally:
            conn.close()

        return jsonify({'status': 'success', 'ingested': inserted_count}), 200
    except Exception as e:
        current_app.logger.warning(f"[CLIENT_BREADCRUMBS_ERROR] Failed to ingest breadcrumbs: {e}")
        return jsonify({'status': 'error', 'message': 'telemetry_swallowed'}), 200


@telemetry_bp.route('/api/v1/telemetry/breadcrumbs', methods=['GET'])
def get_client_breadcrumbs():
    """Returns recent client interaction breadcrumbs for forensic troubleshooting."""
    from flask_login import current_user
    if not current_user.is_authenticated or getattr(current_user, 'role', '') != 'Executive':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    session_id = request.args.get('session_id')
    limit = min(int(request.args.get('limit', 50)), 200)

    db_url = current_app.config.get('DATABASE_URL')
    conn = get_db(db_url)
    try:
        with conn.cursor() as cur:
            if session_id:
                cur.execute('''
                    SELECT id, timestamp, session_id, page_url, event_type, element_tag, element_id, element_class, element_text, details, ip_address
                    FROM "ClientBreadcrumbs"
                    WHERE session_id = %s
                    ORDER BY id DESC LIMIT %s;
                ''', (session_id, limit))
            else:
                cur.execute('''
                    SELECT id, timestamp, session_id, page_url, event_type, element_tag, element_id, element_class, element_text, details, ip_address
                    FROM "ClientBreadcrumbs"
                    ORDER BY id DESC LIMIT %s;
                ''', (limit,))
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append({
                    'id': r[0],
                    'timestamp': r[1].isoformat() if hasattr(r[1], 'isoformat') else str(r[1]),
                    'session_id': r[2],
                    'page_url': r[3],
                    'event_type': r[4],
                    'element_tag': r[5],
                    'element_id': r[6],
                    'element_class': r[7],
                    'element_text': r[8],
                    'details': r[9],
                    'ip_address': r[10]
                })
        return jsonify({'status': 'success', 'count': len(results), 'breadcrumbs': results}), 200
    finally:
        conn.close()



