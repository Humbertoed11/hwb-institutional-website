import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import h3
from dotenv import load_dotenv
import time

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")
TXDOT_API_URL = "https://services1.arcgis.com/8vCH76S0Y9O6S9Yx/arcgis/rest/services/TxDOT_AADT_Counts/FeatureServer/0/query"

def get_txdot_data(lat, lng, radius_m=500):
    """Query TxDOT ArcGIS REST API for AADT data near a point."""
    params = {
        'where': '1=1',
        'geometry': f'{lng},{lat}',
        'geometryType': 'esriGeometryPoint',
        'inSR': '4326',
        'spatialRel': 'esriSpatialRelIntersects',
        'distance': radius_m,
        'units': 'esriSRUnit_Meter',
        'outFields': 'LATEST_AADT_QTY,AADT_YEAR,DIST_NM,CNTY_NM',
        'returnGeometry': 'false',
        'f': 'json'
    }
    try:
        # User-agent header to avoid firewalls blocking raw python requests
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(TXDOT_API_URL, params=params, headers=headers, timeout=10)
        data = response.json()
        features = data.get('features', [])
        if not features:
            return 0
        
        # Get the highest AADT in the vicinity
        max_aadt = max([f['attributes'].get('LATEST_AADT_QTY', 0) for f in features])
        return max_aadt
    except Exception as e:
        print(f"[ERROR] API Request failed for coordinates ({lat}, {lng}): {e}")
        return 0

def run_lobe11_harvester():
    print("--- George Bytes: Inception Lobe 11 (Scout Brain) TxDOT Harvester ---")
    
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Fetch hexagons that need oxygenation
            cur.execute('SELECT h3_address FROM "HEX_Grid_Res11"')
            hexes = cur.fetchall()
            print(f"[PROCESS] Harvesting data for {len(hexes)} hexagons...")

            count = 0
            for row in hexes:
                h_addr = row['h3_address']
                lat, lng = h3.cell_to_latlng(h_addr)
                
                # Fetch real traffic AADT
                aadt = get_txdot_data(lat, lng, radius_m=300)
                
                # Ingest to staging table
                cur.execute("""
                    INSERT INTO "HEX_TxDOT_Staging" (h3_address, raw_aadt, last_scouted)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (h3_address) DO UPDATE SET
                    raw_aadt = EXCLUDED.raw_aadt,
                    last_scouted = CURRENT_TIMESTAMP;
                """, (h_addr, aadt))
                
                count += 1
                if count % 20 == 0:
                    print(f"[STATUS] Harvested {count}/{len(hexes)} units...")
                    conn.commit()
                
                # Respectful rate limiting
                time.sleep(0.05)

            print(f"SUCCESS: Lobe 11 Harvest Complete. {count} raw units stored in HEX_TxDOT_Staging.")
            
            # Log action to telemetry
            cur.execute("""
                INSERT INTO "HEX_Telemetry" (action_name, status, technical_data)
                VALUES (%s, %s, %s);
            """, ("L11_TxDOT_Harvest", "SUCCESS", '{"units_harvested": ' + str(count) + '}'))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Scout Brain TxDOT Harvester failed. {e}")

if __name__ == "__main__":
    run_lobe11_harvester()
