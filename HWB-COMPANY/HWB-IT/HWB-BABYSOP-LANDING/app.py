import os
import json
from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Database configuration
DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

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

# HEXGROWTH SUBDIRECTORY ROUTES (Option B Implementation)
@app.route('/hexgrowth')
@app.route('/hud')
def hexgrowth_hud():
    return render_template('hud.html')

@app.route('/manual')
def manual_redirect():
    # Redirect to the main QMS library or a local manual if created
    return render_template('coming_soon.html')

@app.route('/api/v1/grid')
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
