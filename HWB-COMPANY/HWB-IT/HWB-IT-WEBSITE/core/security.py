"""
SigmaFidelity™ Enterprise RBAC Security Gateway
Standard: HWB-QMS-7.6 Zero-Hotfix Standard / SOC 2 / ISO 27001
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

from functools import wraps
from flask import request, redirect, url_for, flash, abort, current_app
from flask_login import current_user
from core.services.database import get_db


def log_security_violation(user_id, username, role, path, method):
    """Institutional Security Telemetry (SOC 2 / ISO 27001): Logs access breaches to GlobalActivities."""
    conn = None
    try:
        db_url = current_app.config['DATABASE_URL']
        conn = get_db(db_url)
        with conn.cursor() as cur:
            desc = f"Role '{role}' ({username}) blocked from accessing {method} {path}"
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, "User", "SECURITY_VIOLATION", desc))
            conn.commit()
    except Exception as e:
        print(f"[SECURITY_LOG_ERROR] Could not log violation: {e}", flush=True)
    finally:
        if conn:
            conn.close()


def roles_required(*roles):
    """Declarative Role-Based Access Control Decorator (Enterprise Standard)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login', next=request.url))
            if current_user.role not in roles:
                print(f"[SECURITY_AUDIT] Unauthorized access attempt by {current_user.username} ({current_user.role}) to {request.path}", flush=True)
                log_security_violation(current_user.id, current_user.username, current_user.role, request.path, request.method)
                if current_user.role == 'Sales':
                    flash("Access restricted. Outside Sales personnel are routed to the Field Sales Desk.")
                    return redirect(url_for('sales_desk'))
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
