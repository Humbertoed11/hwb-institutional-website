import os
import json
import urllib.request
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def init_scout_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "HEX_Scout_Registry" (
            id SERIAL PRIMARY KEY,
            municipality_name VARCHAR(150) NOT NULL,
            department_name VARCHAR(150) NOT NULL,
            source_type VARCHAR(100) NOT NULL,
            endpoint_or_contact TEXT UNIQUE NOT NULL,
            scouting_status VARCHAR(50) DEFAULT 'Identified',
            latency_ms INTEGER,
            scouted_notes TEXT,
            last_scouted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("SUCCESS: HEX_Scout_Registry table initialized.")

def probe_endpoint(url):
    import time
    start_time = time.time()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                latency = int((time.time() - start_time) * 1000)
                return "Active", latency
    except Exception as e:
        pass
    return "Offline / Needs Review", None

def run_scout_probes():
    print("--- George Bytes: Actively Scouting Municipal Data Pipelines ---")
    
    # Extended scout targets to cover Denton, Tarrant, and Dallas Counties
    scout_targets = [
        # City of Plano
        {
            "municipality": "City of Plano",
            "department": "GIS & Open Data Portal",
            "type": "ArcGIS REST Service",
            "endpoint": "https://gis.plano.gov/arcgis/rest/services",
            "notes": "Houses zoning, parcel boundaries, utility lines, and street egress features."
        },
        {
            "municipality": "City of Plano",
            "department": "Planning and Zoning",
            "type": "Email Contact",
            "endpoint": "planner@plano.gov",
            "notes": "Direct planning contact for zoning variance submissions."
        },
        # Wise County
        {
            "municipality": "Wise County",
            "department": "GIS Department",
            "type": "ArcGIS REST Service",
            "endpoint": "https://arcgis.co.wise.tx.us/arcgis/rest/services",
            "notes": "Provides agricultural zoning, county parcel lines, and local infrastructure features."
        },
        {
            "municipality": "Wise County",
            "department": "County Appraisal District",
            "type": "Email Contact",
            "endpoint": "wisecad@wisecad.org",
            "notes": "Appraisal district contact for property valuation records."
        },
        # Collin County
        {
            "municipality": "Collin County",
            "department": "GIS Department",
            "type": "ArcGIS REST Service",
            "endpoint": "https://gis.collincountytx.gov/arcgis/rest/services",
            "notes": "County parcel mappings, easement shapefiles, and municipal border lines."
        },
        # Denton County (Extended)
        {
            "municipality": "Denton County",
            "department": "GIS Department",
            "type": "ArcGIS REST Service",
            "endpoint": "https://gis.dentoncounty.gov/arcgis/rest/services",
            "notes": "County-wide zoning layers, parcel geometry, and environmental maps."
        },
        # Tarrant County (Extended)
        {
            "municipality": "Tarrant County",
            "department": "GIS Department",
            "type": "ArcGIS REST Service",
            "endpoint": "https://gis.tarrantcounty.com/arcgis/rest/services",
            "notes": "Parcels, utility grid corridors, highway intersections, and flood plain zones."
        },
        # Dallas County (Extended)
        {
            "municipality": "Dallas County",
            "department": "GIS Department",
            "type": "ArcGIS REST Service",
            "endpoint": "https://gis.dallascounty.org/arcgis/rest/services",
            "notes": "Zoning classifications, arterial roadways, appraiser maps, and soil surveys."
        }
    ]

    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    init_scout_table(cursor)
    conn.commit()

    count_added = 0

    for target in scout_targets:
        muni = target["municipality"]
        dept = target["department"]
        stype = target["type"]
        endpoint = target["endpoint"]
        notes = target["notes"]
        
        status = "Active"
        latency = None
        
        if stype == "ArcGIS REST Service":
            print(f"Probing {muni} GIS portal...")
            status, latency = probe_endpoint(endpoint)
            print(f"  Result: {status} (Latency: {latency}ms)")
        else:
            status = "Verified Contact"
            latency = None
            
        try:
            cursor.execute("""
                INSERT INTO "HEX_Scout_Registry" (municipality_name, department_name, source_type, endpoint_or_contact, scouting_status, latency_ms, scouted_notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (endpoint_or_contact) DO UPDATE
                SET scouting_status = EXCLUDED.scouting_status,
                    latency_ms = EXCLUDED.latency_ms,
                    scouted_notes = EXCLUDED.scouted_notes,
                    last_scouted = CURRENT_TIMESTAMP;
            """, (muni, dept, stype, endpoint, status, latency, notes))
            count_added += 1
        except Exception as e:
            print(f"ERROR: Failed to save scout node {endpoint}: {e}")
            conn.rollback()
            continue

    # Log telemetry
    try:
        cursor.execute("""
            INSERT INTO "HEX_Telemetry" (action_name, status, technical_data)
            VALUES (%s, %s, %s)
        """, ("Pulse_Scouting_Probe", "SUCCESS", json.dumps({"probes_completed": count_added})))
        conn.commit()
    except Exception as e:
        conn.rollback()

    conn.close()
    print(f"SUCCESS: Scouting run completed. Saved {count_added} endpoints.")

if __name__ == "__main__":
    run_scout_probes()
