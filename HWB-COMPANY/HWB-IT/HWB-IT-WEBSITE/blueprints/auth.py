"""
SigmaFidelity™ Authentication & Session Security Blueprint
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from core.models.user import User
from core.services.database import get_db
from core.services.rate_limiter import rate_limit

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
@rate_limit(limit=10, period_seconds=60, scope="auth_login")
def login():
    """Enterprise authentication endpoint with role-based routing and rate limit protection."""
    if request.method == 'POST':
        u = (request.form.get('username') or '').strip()
        p = (request.form.get('password') or '').strip()
        db_url = current_app.config['DATABASE_URL']
        conn = get_db(db_url)
        user = None
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM "Users" WHERE LOWER(username) = LOWER(%s)', (u,))
                user = cur.fetchone()
        finally:
            conn.close()
        
        if user and check_password_hash(user['password_hash'], p):
            session.permanent = True
            login_user(User(user['id'], user['username'], user['role'], user.get('full_name')))
            if user['role'] == 'Sales':
                return redirect(url_for('admin_operations', view='leads'))
            return redirect(url_for('admin_operations'))
        flash('Invalid credentials.')
    return render_template('login.html')

@auth_bp.route('/logout', endpoint='logout')
@login_required
def logout():
    """Terminates session and purges auth cookies."""
    logout_user()
    session.clear()
    return redirect(url_for('index'))

@auth_bp.route('/heartbeat', endpoint='heartbeat')
@login_required
def heartbeat():
    """Keeps the active user session alive."""
    session.modified = True
    return jsonify({"status": "healthy", "user": current_user.username}), 200
