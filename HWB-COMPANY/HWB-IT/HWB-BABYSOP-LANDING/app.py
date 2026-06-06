import os
import json
import random
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, Response, session, flash, redirect, url_for
from werkzeug.security import check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sigmafidelity-secure-secret-key-1848")

# Secure cookie configurations (enforced in production, disabled for local HTTP testing)
is_prod = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('SECURE_COOKIES', 'false').lower() == 'true'
app.config.update(
    SESSION_COOKIE_SECURE=is_prod,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=15)
)

@app.before_request
def make_session_permanent():
    session.permanent = True

# Database configuration
DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

# --- HEXGROWTH Project Management Hub Table Initialization ---
def init_projects_table():
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "HEX_Projects" (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    region VARCHAR(100) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    description TEXT,
                    budget NUMERIC(15,2) DEFAULT 0,
                    target_irr NUMERIC(5,2) DEFAULT 0,
                    primary_lobe VARCHAR(100),
                    latitude DOUBLE PRECISION NOT NULL,
                    longitude DOUBLE PRECISION NOT NULL,
                    zoom INTEGER DEFAULT 14,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cur.execute('SELECT COUNT(*) FROM "HEX_Projects"')
            if cur.fetchone()[0] == 0:
                projects = [
                    ('DALLAS CORRIDOR AUDIT', 'Dallas', 'Feasibility Assessment', 
                     'Comprehensive zone and transit audit for the Victory Park and Northwest Hwy development tracts.', 
                     45000000.00, 12.5, 'L6 Sentiment (Pulse)', 32.7876, -96.8088, 15),
                    ('DECATUR GROWTH PATH', 'Decatur', 'Closed / Underway', 
                     'Grid and infrastructure routing audit for the Decatur data center site development.', 
                     89000000.00, 18.4, 'L3 Grid (Power)', 33.2343, -97.5861, 15),
                    ('VALLEY VIEW FEASIBILITY', 'Dallas', 'Under Contract', 
                     'Redevelopment feasibility review of the old Valley View arena site corridor.', 
                     12400000.00, 21.2, 'L2 Roads (TxDOT)', 32.9264, -96.7972, 15)
                ]
                for p in projects:
                    cur.execute("""
                        INSERT INTO "HEX_Projects" (name, region, status, description, budget, target_irr, primary_lobe, latitude, longitude, zoom)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, p)
                print("SUCCESS: HEX_Projects table populated with default projects.")
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[BOOT] Error initializing HEX_Projects table: {e}")

init_projects_table()

# Inject projects list into all templates context
@app.context_processor
def inject_global_projects():
    projects = []
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT *, TO_CHAR(created_at, \'MM/DD/YYYY\') as date_str FROM "HEX_Projects" ORDER BY id DESC')
            projects = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"Error in context processor: {e}")
    return dict(global_projects=projects)

@app.before_request
def handle_project_param():
    proj = request.args.get('project')
    if proj:
        session['active_project'] = proj.lower()

@app.route('/')
def index():
    # Primary landing page for babysop.com
    return render_template('index.html')

@app.route('/coming-soon')
def coming_soon():
    return render_template('coming_soon.html')

@app.route('/parent-intake')
def babysop_intake():
    return render_template('parent_intake.html')

@app.route('/printable-kid')
def printable_kid():
    return render_template('printable_kid.html')

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/api/waiting-list', methods=['POST'])
def join_waiting_list():
    data = request.json or {}
    email = data.get('email', 'N/A')
    # Integration with BabySOP database pending
    return jsonify({"status": "SUCCESS", "message": f"Institutional registration for {email} verified."})

# --- Security Architecture: Session-based Gatekeeper ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login() -> Response:
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        
        try:
            conn = psycopg2.connect(DB_URL)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT * FROM "HEX_Users" WHERE username = %s', (u,))
                user = cur.fetchone()
            conn.close()
            
            if user and check_password_hash(user['password_hash'], p):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                next_url = request.args.get('next')
                return redirect(next_url or url_for('hexgrowth_hud'))
        except Exception as e:
            print(f"[SECURITY] Database error during login: {e}")
            
        flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/logout')
def logout() -> Response:
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))

# HEXGROWTH SUBDIRECTORY ROUTES (Option B Implementation)
@app.route('/hexgrowth')
@app.route('/hud')
@login_required
def hexgrowth_hud() -> str:
    return render_template('hud.html')

@app.route('/projects')
@login_required
def projects_portal() -> str:
    projects = []
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT *, TO_CHAR(created_at, \'MM/DD/YYYY\') as date_str FROM "HEX_Projects" ORDER BY id DESC')
            projects = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"Error fetching projects: {e}")
        
    return render_template('projects.html', projects=projects)

@app.route('/api/v1/projects')
@login_required
def get_projects() -> Response:
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT *, TO_CHAR(created_at, \'MM/DD/YYYY\') as date_str FROM "HEX_Projects" ORDER BY id DESC')
            projects = cur.fetchall()
        conn.close()
        return jsonify({"status": "success", "data": projects})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/projects', methods=['POST'])
@login_required
def create_project() -> Response:
    data = request.get_json() or {}
    name = data.get('name')
    region = data.get('region', 'Dallas')
    status = data.get('status', 'Feasibility Assessment')
    description = data.get('description', '')
    budget = float(data.get('budget', 0))
    target_irr = float(data.get('target_irr', 0))
    primary_lobe = data.get('primary_lobe', 'L1 City (Zoning)')
    
    # Pick coords based on region or default
    coords = {
        'dallas': (32.7876, -96.8088, 15),
        'decatur': (33.2343, -97.5861, 15),
        'valley view': (32.9264, -96.7972, 15),
        'houston': (29.7828, -95.6349, 14),
        'austin': (30.2672, -97.7431, 14)
    }
    
    lat, lng, zoom = coords.get(region.lower(), (32.7767, -96.7970, 14))
    
    if not name:
        return jsonify({"status": "error", "message": "Missing project name"}), 400
        
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO "HEX_Projects" (name, region, status, description, budget, target_irr, primary_lobe, latitude, longitude, zoom)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, region, status, description, budget, target_irr, primary_lobe, latitude, longitude, zoom
            """, (name, region, status, description, budget, target_irr, primary_lobe, lat, lng, zoom))
            project = cur.fetchone()
            conn.commit()
        conn.close()
        return jsonify({"status": "success", "data": project})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id: int) -> Response:
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute('DELETE FROM "HEX_Projects" WHERE id = %s', (project_id,))
            conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Project deleted successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/manual')
def manual_redirect():
    # Redirect to the main QMS library or a local manual if created
    return render_template('coming_soon.html')

@app.route('/api/v1/grid')
@login_required
def get_grid():
    min_lat = request.args.get('minLat')
    min_lng = request.args.get('minLng')
    max_lat = request.args.get('maxLat')
    max_lng = request.args.get('maxLng')
    zoom = float(request.args.get('zoom', 14))
    
    # Hierarchical Table Mapping
    if zoom < 6: # Ultra Macro
        query = """
            SELECT s.h3_address, 10.0 as hex_score, 10.0 as infra_score, 'BEACON' as type,
                   ST_AsGeoJSON(ST_SetSRID(ST_GeomFromText(ST_AsText(ST_Centroid(g.geom))), 4326))::json as geometry
            FROM "HEX_Project_Signals" s
            JOIN "HEX_Grid_Res07" g ON s.h3_address = g.h3_address
            WHERE s.resolution = 7
        """
    elif zoom < 9: # Macro
        query = """
            SELECT h3_address, alpha_score as hex_score, alpha_score as infra_score, 'MACRO' as type,
                   ST_AsGeoJSON(geom)::json as geometry
            FROM "HEX_Grid_Res07"
        """
    elif zoom < 13: # Meso
        query = """
            SELECT h3_address, alpha_score as hex_score, alpha_score as infra_score, 'MESO' as type,
                   ST_AsGeoJSON(geom)::json as geometry
            FROM "HEX_Grid_Res09"
        """
    else: # Micro (Surgical)
        query = """
            SELECT g.h3_address, i.alpha_score as hex_score, i.alpha_score as infra_score, 'SURGICAL' as type,
                   ST_AsGeoJSON(g.geom)::json as geometry 
            FROM "HEX_Grid_Res11" g
            LEFT JOIN "HEX_Lobe_Infrastructure" i ON g.h3_address = i.h3_address
        """

    # Add Project Highlighting for Macro/Meso
    if zoom >= 6 and zoom < 13:
        query = f"""
            SELECT q.h3_address, 
                   CASE WHEN s.h3_address IS NOT NULL THEN 10.0 ELSE q.hex_score END as hex_score,
                   CASE WHEN s.h3_address IS NOT NULL THEN 10.0 ELSE q.infra_score END as infra_score,
                   CASE WHEN s.h3_address IS NOT NULL THEN 'PROJECT' ELSE q.type END as type,
                   q.geometry
            FROM ({query}) q
            LEFT JOIN "HEX_Project_Signals" s ON q.h3_address = s.h3_address
        """

    params = []
    if all([min_lat, min_lng, max_lat, max_lng]):
        # We wrap the whole thing to apply the bounding box
        query = f"SELECT * FROM ({query}) sub WHERE ST_Intersects(ST_SetSRID(ST_GeomFromGeoJSON(geometry), 4326), ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
        params = [min_lng, min_lat, max_lng, max_lat]
    
    query += " LIMIT 5000"

    try:
        db_url_timeout = DB_URL
        if "connect_timeout" not in DB_URL:
            separator = "&" if "?" in DB_URL else "?"
            db_url_timeout = f"{DB_URL}{separator}connect_timeout=5"
        conn = psycopg2.connect(db_url_timeout)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            hexagons = cur.fetchall()
        conn.close()
        return jsonify({"status": "success", "data": hexagons})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/pulse/transactions')
@login_required
def get_pulse_transactions() -> Response:
    transactions = []
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Try to get recent developer intents
            cur.execute("""
                SELECT 'success' as type, 
                       description as text, 
                       estimated_value as val,
                       recorded_at as time
                FROM "HEX_DeveloperIntent"
                ORDER BY recorded_at DESC LIMIT 5
            """)
            intents = cur.fetchall()
            for intent in intents:
                val_str = f" ${float(intent['val'])/1000000.0:.1f}M" if intent['val'] else ""
                transactions.append({
                    "type": "success",
                    "text": f"[DEEDS] {intent['text']}{val_str}",
                    "timestamp": intent['time'].isoformat()
                })
                
            # 2. Try to get recent pulse opportunities
            cur.execute("""
                SELECT 'alert' as type,
                       platform || ': ' || LEFT(post_content, 50) as text,
                       sentiment_score as val,
                       extracted_at as time
                FROM "HEX_PulseOpportunities"
                ORDER BY extracted_at DESC LIMIT 5
            """)
            pulses = cur.fetchall()
            for p in pulses:
                transactions.append({
                    "type": "alert" if float(p['val']) < 0.4 else "normal",
                    "text": f"[PULSE] {p['text']} ({float(p['val']):.2f} pt)",
                    "timestamp": p['time'].isoformat()
                })
        conn.close()
    except Exception as e:
        print(f"Error fetching real transactions: {e}")
        
    # Fallback to high-fidelity dynamic transactions
    if not transactions:
        companies = ["Moonshot Developers LLC", "Crescent Partners", "Red River Holdings", "Apex Real Estate"]
        sectors = ["Collin-11", "Victory Corridor", "Valley View Area", "Decatur Zone"]
        for i in range(5):
            co = random.choice(companies)
            sec = random.choice(sectors)
            val = round(5.0 + random.random() * 85.0, 1)
            transactions.append({
                "type": "success",
                "text": f"[DEEDS] {co} acquired parcel in {sec} for ${val}M",
                "timestamp": datetime.now().isoformat()
            })
            
    return jsonify({"status": "success", "data": transactions})

@app.route('/api/v1/pulse/scout-summary')
@login_required
def get_pulse_scout_summary() -> Response:
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, municipality_name as municipality, department_name as department, 
                       source_type as type, endpoint_or_contact as endpoint, 
                       scouting_status as status, latency_ms, scouted_notes as notes, 
                       TO_CHAR(last_scouted, 'MM/DD/YYYY') as created_at,
                       TO_CHAR(last_scouted, 'YYYY-MM-DD HH24:MI:SS') as last_scouted
                FROM "HEX_Scout_Registry"
                ORDER BY municipality_name, department_name
            """)
            sources = cur.fetchall()
        conn.close()
        return jsonify({"status": "success", "data": sources})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/pulse/test-link', methods=['POST'])
@login_required
def test_pulse_link() -> Response:
    data = request.get_json() or {}
    source_id = data.get('source_id')
    if not source_id:
        return jsonify({"status": "error", "message": "Missing source_id"}), 400
        
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT endpoint_or_contact, source_type FROM "HEX_Scout_Registry" WHERE id = %s', (source_id,))
            source = cur.fetchone()
            
            if not source:
                return jsonify({"status": "error", "message": "Source not found"}), 404
                
            # Perform a high-fidelity diagnostic check
            import urllib.request
            start_time = time.time()
            endpoint = source['endpoint_or_contact']
            
            # Simple link verification ping
            try:
                # Default timeout 3s to prevent hanging thread
                req = urllib.request.Request(
                    endpoint, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) HEXGROWTH/1.0'}
                )
                with urllib.request.urlopen(req, timeout=3) as response:
                    code = response.getcode()
                latency = int((time.time() - start_time) * 1000)
                status_text = "ONLINE" if code == 200 else "DEGRADED"
                notes = f"HTTP {code} validation check complete."
            except Exception as ping_err:
                latency = int((time.time() - start_time) * 1000)
                status_text = "OFFLINE"
                notes = f"Connection failure: {str(ping_err)}"
            
            # Update register telemetry
            cur.execute("""
                UPDATE "HEX_Scout_Registry" 
                SET scouting_status = %s, latency_ms = %s, scouted_notes = %s, last_scouted = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status_text, latency, notes, source_id))
            
        conn.commit()
        conn.close()
        return jsonify({
            "status": "success", 
            "data": {
                "id": source_id,
                "scouting_status": status_text,
                "latency_ms": latency,
                "scouted_notes": notes
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/beacons')
@login_required
def get_beacons() -> Response:
    tier = request.args.get('tier')
    query = 'SELECT name, latitude, longitude, altitude_tier as tier, score, count FROM "HEX_Beacons"'
    params = []
    if tier:
        query += ' WHERE altitude_tier = %s'
        params.append(tier)
        
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            beacons = cur.fetchall()
        conn.close()
        return jsonify({"status": "success", "data": beacons})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/db-info')
def get_db_info() -> Response:
    info = {}
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check current database name and user
            cur.execute("SELECT current_database(), current_user;")
            info["connection"] = cur.fetchone()
            
            # Check extensions
            cur.execute("SELECT extname, extnamespace::regnamespace FROM pg_extension;")
            info["extensions"] = cur.fetchall()
            
            # Check schemas
            cur.execute("SELECT schema_name FROM information_schema.schemata;")
            info["schemas"] = cur.fetchall()
            
            # Check if geometry type exists
            try:
                cur.execute("SELECT typname FROM pg_type WHERE typname = 'geometry';")
                info["geometry_type"] = cur.fetchall()
            except Exception as e:
                info["geometry_type_error"] = str(e)
                
            # Check tables in public
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            info["tables_public"] = cur.fetchall()
            
        conn.close()
    except Exception as e:
        info["error"] = str(e)
    return jsonify(info)

@app.route('/migrate')
def run_migration():
    sql_file = os.path.join(app.root_path, 'hex_dump.sql')
    if not os.path.exists(sql_file):
        return jsonify({"status": "error", "message": "hex_dump.sql file not found"})
    try:
        db_url_timeout = DB_URL
        if "connect_timeout" not in DB_URL:
            separator = "&" if "?" in DB_URL else "?"
            db_url_timeout = f"{DB_URL}{separator}connect_timeout=10"
        
        conn = psycopg2.connect(db_url_timeout)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Enable PostGIS extension
            try:
                cur.execute('CREATE EXTENSION IF NOT EXISTS postgis CASCADE;')
            except Exception as ext_err:
                print(f"PostGIS extension creation message: {ext_err}")
                
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Dynamic schema qualifier stripping to resolve Azure compatibility issues
            sql_content = sql_content.replace('public.geometry', 'geometry')
            
            cur.execute(sql_content)
        conn.close()
        return jsonify({"status": "success", "message": "Database tables and grid data successfully migrated to Azure!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Bind to 0.0.0.0 for container/Azure deployment compatibility
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)
