from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sigma-fidelity-secret-2026'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DATABASE = 'database/sigma_leads.db'
CLIENT_DATABASE = 'database/clients.db'
CRM_DATABASE = '../HWB-IT-CRM/database/crm.db'

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection(DATABASE)
    user_data = conn.execute('SELECT * FROM Users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user_data:
        return User(user_data['id'], user_data['username'])
    return None

def init_db():
    if not os.path.exists('database'):
        os.makedirs('database')
    conn = sqlite3.connect(DATABASE)
    conn.execute('CREATE TABLE IF NOT EXISTS Users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL);')
    admin = conn.execute('SELECT * FROM Users WHERE username = "admin"').fetchone()
    if not admin:
        hashed_pw = generate_password_hash('HWB-Admin-2026!')
        conn.execute('INSERT INTO Users (username, password_hash) VALUES (?, ?)', ('admin', hashed_pw))
    
    conn.execute('CREATE TABLE IF NOT EXISTS Leads (id INTEGER PRIMARY KEY AUTOINCREMENT, process_id TEXT DEFAULT "MKT-001", job_title TEXT, center_name TEXT, email TEXT, wage REAL, cleaning_hours REAL, calculated_waste REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);')
    conn.execute('CREATE TABLE IF NOT EXISTS Chemicals (id INTEGER PRIMARY KEY AUTOINCREMENT, process_id TEXT DEFAULT "SAFE-001", name TEXT NOT NULL, product_id TEXT, hazard_level TEXT, intended_use TEXT, sds_link TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);')
    conn.execute('CREATE TABLE IF NOT EXISTS Milestones (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, name TEXT NOT NULL, status TEXT DEFAULT "pending", description TEXT);')
    conn.execute('CREATE TABLE IF NOT EXISTS COPQ (id INTEGER PRIMARY KEY AUTOINCREMENT, defect_type TEXT NOT NULL, impact TEXT, status TEXT DEFAULT "OPEN");')
    conn.execute('CREATE TABLE IF NOT EXISTS KPIVs (id INTEGER PRIMARY KEY AUTOINCREMENT, metric_name TEXT NOT NULL, value TEXT, target TEXT);')
    conn.execute('CREATE TABLE IF NOT EXISTS Analytics (id INTEGER PRIMARY KEY AUTOINCREMENT, tool_name TEXT NOT NULL, result TEXT NOT NULL);')
    conn.execute('CREATE TABLE IF NOT EXISTS ActivityLog (id INTEGER PRIMARY KEY AUTOINCREMENT, date DATE DEFAULT CURRENT_DATE, activity_name TEXT NOT NULL, hours REAL NOT NULL, category TEXT DEFAULT "Value-Add");')
    conn.execute('CREATE TABLE IF NOT EXISTS Incidents (id INTEGER PRIMARY KEY AUTOINCREMENT, date DATE DEFAULT CURRENT_DATE, description TEXT NOT NULL, category TEXT NOT NULL, severity TEXT DEFAULT "Low");')
    conn.execute('CREATE TABLE IF NOT EXISTS Uptime (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, status INTEGER);')
    conn.execute('CREATE TABLE IF NOT EXISTS ClientActivities (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, activity_type TEXT NOT NULL, description TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);')
    conn.commit()
    conn.close()

init_db()

def get_db_connection(db_path=DATABASE):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_crm_db_connection():
    conn = sqlite3.connect(CRM_DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Authentication ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection(DATABASE)
        user_data = conn.execute('SELECT * FROM Users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'], user_data['username'])
            login_user(user)
            return redirect(url_for('sigma_executive'))
        flash('Invalid Credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/security-notice')
def security_notice():
    return render_template('security_notice.html')

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('security_notice'))

# --- Backoffice Protected Routes ---
@app.route('/admin/executive', methods=['GET', 'POST'], endpoint='sigma_executive')
@login_required
def sigma_executive():
    conn = get_db_connection(DATABASE)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_milestone':
            conn.execute('INSERT INTO Milestones (category, name, status, description) VALUES (?, ?, ?, ?)', (request.form['category'], request.form['name'], request.form['status'], request.form['description']))
        elif action == 'add_defect':
            conn.execute('INSERT INTO COPQ (defect_type, impact, status) VALUES (?, ?, ?)', (request.form['defect_type'], request.form['impact'], request.form['status']))
        elif action == 'update_kpiv':
            conn.execute('INSERT INTO KPIVs (metric_name, value, target) VALUES (?, ?, ?)', (request.form['metric_name'], request.form['value'], request.form['target']))
        conn.commit()
        return redirect(url_for('sigma_executive', _anchor='tools'))
    leads_count = conn.execute('SELECT COUNT(*) FROM Leads').fetchone()[0]
    total_waste = conn.execute('SELECT SUM(calculated_waste) FROM Leads').fetchone()[0] or 0
    recent_leads = conn.execute('SELECT * FROM Leads ORDER BY timestamp DESC LIMIT 5').fetchall()
    analytics_rows = conn.execute('SELECT * FROM Analytics').fetchall()
    analytics = {row['tool_name']: row['result'] for row in analytics_rows}
    uptime_data = conn.execute('SELECT status FROM Uptime ORDER BY timestamp DESC LIMIT 1').fetchone()
    latest_status = uptime_data['status'] if uptime_data else 1
    uptime_stats = { 'status': "ACTIVE" if latest_status == 1 else "INACTIVE" }
    milestones = conn.execute('SELECT * FROM Milestones').fetchall()
    defects = conn.execute('SELECT * FROM COPQ').fetchall()
    kpivs = conn.execute('SELECT * FROM KPIVs').fetchall()
    conn.close()
    return render_template('HWB-WEB Sigma Executive.html', leads_count=leads_count, total_waste=f"${total_waste:,.2f}", recent_leads=recent_leads, analytics=analytics, uptime=uptime_stats, milestones=milestones, defects=defects, kpivs=kpivs)

@app.route('/admin/crm', endpoint='crm_dashboard')
@login_required
def crm_dashboard():
    conn_clients = get_db_connection(CLIENT_DATABASE)
    conn_sigma = get_db_connection(DATABASE)
    try:
        clients = conn_clients.execute('SELECT * FROM Customers ORDER BY company_name ASC').fetchall()
    except:
        clients = []
    leads = conn_sigma.execute('SELECT * FROM Leads ORDER BY timestamp DESC').fetchall()
    activities = conn_sigma.execute('SELECT * FROM ClientActivities ORDER BY timestamp DESC').fetchall()
    conn_clients.close()
    conn_sigma.close()
    return render_template('backoffice_crm.html', clients=clients, activities=activities, leads=leads)

@app.route('/admin/crm/convert/<int:lead_id>')
@login_required
def convert_to_client(lead_id):
    try:
        conn_sigma = get_db_connection(DATABASE)
        lead = conn_sigma.execute('SELECT * FROM Leads WHERE id = ?', (lead_id,)).fetchone()
        if lead:
            conn_clients = get_db_connection(CLIENT_DATABASE)
            conn_clients.execute('INSERT INTO Customers (company_name, email, company_address) VALUES (?, ?, ?)', (lead['center_name'], lead['email'], 'Address Pending Audit'))
            conn_clients.commit()
            conn_clients.close()
            conn_sigma.execute('INSERT INTO ClientActivities (client_id, activity_type, description) VALUES (?, "Conversion", "Lead converted to client via Zero-Fog automation.")', (lead_id, ))
            conn_sigma.commit()
            flash(f"Successfully converted {lead['center_name']} to Client.")
        conn_sigma.close()
    except Exception as e:
        with open("conversion_error.log", "a") as f:
            f.write(f"Error converting lead {lead_id}: {str(e)}\n")
        flash(f"Error: {str(e)}")
    return redirect(url_for('crm_dashboard'))

@app.route('/admin/crm/activity/add', methods=['POST'])
@login_required
def add_activity():
    client_id = request.form['client_id']
    activity_type = request.form['activity_type']
    description = request.form['description']
    conn = get_db_connection(DATABASE)
    conn.execute('INSERT INTO ClientActivities (client_id, activity_type, description) VALUES (?, ?, ?)', (client_id, activity_type, description))
    conn.commit()
    conn.close()
    return redirect(url_for('crm_dashboard'))

@app.route('/admin/crm/activity/delete/<int:id>')
@login_required
def delete_activity(id):
    conn = get_db_connection(DATABASE)
    conn.execute('DELETE FROM ClientActivities WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('crm_dashboard'))

@app.route('/admin/master', endpoint='admin_master')
@login_required
def admin_master():
    conn_sigma = get_db_connection(DATABASE)
    conn_clients = get_db_connection(CLIENT_DATABASE)
    leads = conn_sigma.execute('SELECT * FROM Leads ORDER BY timestamp DESC').fetchall()
    chemicals = conn_sigma.execute('SELECT * FROM Chemicals ORDER BY name ASC').fetchall()
    incidents = conn_sigma.execute('SELECT * FROM Incidents ORDER BY date DESC').fetchall()
    try:
        customers = conn_clients.execute('SELECT * FROM Customers ORDER BY company_name ASC').fetchall()
        services = conn_clients.execute('SELECT * FROM Services').fetchall()
    except:
        customers, services = [], []
    conn_sigma.close()
    conn_clients.close()
    return render_template('HWB-WEB Admin Master.html', leads=leads, chemicals=chemicals, incidents=incidents, customers=customers, services=services)

@app.route('/admin/concept-lab', endpoint='concept_lab')
@login_required
def concept_lab(): return render_template('concept_lab.html')

# --- Public Routes ---
@app.route('/')
def index(): return render_template('HWB-WEB Index.html')

@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    if request.method == 'POST':
        job_title, center_name, email = request.form['job_title'], request.form['center_name'], request.form['email']
        wage, hours = float(request.form['wage']), float(request.form['cleaning_hours'])
        waste = (wage * hours * 52) * 0.15
        conn = get_db_connection(DATABASE)
        conn.execute('INSERT INTO Leads (job_title, center_name, email, wage, cleaning_hours, calculated_waste) VALUES (?, ?, ?, ?, ?, ?)', (job_title, center_name, email, wage, hours, waste))
        conn.commit(); conn.close()
        return render_template('HWB-WEB Results.html', waste=f"${waste:,.2f}", hours=hours, job_title=job_title)
    return render_template('HWB-WEB Calculator.html')

@app.route('/about')
def about(): return render_template('HWB-WEB About.html')

@app.route('/services')
def services(): return render_template('HWB-WEB Services.html')

@app.route('/services/construction')
def services_construction(): return render_template('HWB-WEB Construction.html')

@app.route('/services/warehouse')
def services_warehouse(): return render_template('HWB-WEB Warehouse.html')

@app.route('/services/office')
def services_office(): return render_template('HWB-WEB Office.html')

@app.route('/resources')
def resources(): return render_template('HWB-WEB Resources.html')

@app.route('/babysop')
def babysop(): return render_template('HWB-BABYSOP Index.html')

@app.route('/compliance')
def compliance():
    conn = get_db_connection(DATABASE)
    chemicals = conn.execute('SELECT * FROM Chemicals ORDER BY name ASC').fetchall()
    conn.close()
    return render_template('HWB-WEB Compliance.html', chemicals=chemicals)

@app.route('/ehsq')
def ehsq():
    conn = get_db_connection(DATABASE)
    incidents = conn.execute('SELECT * FROM Incidents ORDER BY date DESC').fetchall()
    chemicals = conn.execute('SELECT COUNT(*) FROM Chemicals').fetchone()[0]
    conn.close()
    return render_template('HWB-WEB Ehsq.html', incidents=incidents, chemical_count=chemicals)

@app.route('/concept')
def concept(): return render_template('concept_cdata.html')

@app.route('/privacy-policy')
def privacy_policy(): return render_template('privacy_policy.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
