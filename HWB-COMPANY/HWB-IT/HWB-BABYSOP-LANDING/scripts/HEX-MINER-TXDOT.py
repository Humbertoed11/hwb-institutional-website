import os
import psycopg2
from psycopg2.extras import RealDictCursor
import h3
from dotenv import load_dotenv
import math
import json

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

# Tactical Infrastructure Corridors (Plano, TX) for Procedural Fallback
CORRIDOR_75 = (33.0198, -96.7089) 
CORRIDOR_PGBT = (32.9976, -96.7089)

def calculate_proximity_score(lat, lng):
    """Calculate procedural Alpha Score based on proximity to major arteries."""
    dist_75 = math.sqrt((lat - CORRIDOR_75[0])**2 + (lng - CORRIDOR_75[1])**2)
    dist_pgbt = math.sqrt((lat - CORRIDOR_PGBT[0])**2 + (lng - CORRIDOR_PGBT[1])**2)
    min_dist = min(dist_75, dist_pgbt)
    score = 10.0 - (min_dist * 500) 
    return round(max(0.1, min(score, 10.0)), 1)

def normalize_infra_score(aadt):
    """Normalize AADT to 0-10 Alpha Scale. (50,000+ AADT = 10.0)"""
    if not aadt: return 0.0
    score = (aadt / 50000) * 10
    return round(min(score, 10.0), 1)

def run_txdot_scorer():
    print("--- George Bytes: Launching Lobe 2 (TxDOT Scorer) ---")
    
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Determine mode from active session parameters
            use_procedural = True
            cur.execute('SELECT state_data FROM "HEX_SystemState" ORDER BY updated_at DESC LIMIT 1;')
            row = cur.fetchone()
            if row:
                state_data = row['state_data']
                if isinstance(state_data, str):
                    state_data = json.loads(state_data)
                params = state_data.get("parameters", {})
                
                # Check mode options
                mode = params.get("Lobe 2 Mode")
                procedural_switch = params.get("use_procedural_scoring")
                
                if mode == "Real-World" or procedural_switch == "false":
                    use_procedural = False
            
            print(f"[MODE] Scoring Mode: {'Procedural Proximity' if use_procedural else 'Real-World (Staged)'}")

            # 2. Fetch grid cells
            cur.execute('SELECT h3_address FROM "HEX_Grid_Res11"')
            hexes = cur.fetchall()
            
            count = 0
            for row in hexes:
                h_addr = row['h3_address']
                
                if use_procedural:
                    lat, lng = h3.cell_to_latlng(h_addr)
                    infra_score = calculate_proximity_score(lat, lng)
                    traffic_count = int(infra_score * 5000)
                else:
                    # Query staging table populated by Lobe 11
                    cur.execute('SELECT raw_aadt FROM "HEX_TxDOT_Staging" WHERE h3_address = %s;', (h_addr,))
                    stage_row = cur.fetchone()
                    traffic_count = stage_row['raw_aadt'] if stage_row else 0
                    infra_score = normalize_infra_score(traffic_count)

                cur.execute("""
                    INSERT INTO "HEX_Lobe_Infrastructure" (h3_address, traffic_count, alpha_score)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (h3_address) DO UPDATE SET
                    traffic_count = EXCLUDED.traffic_count,
                    alpha_score = EXCLUDED.alpha_score,
                    last_updated = CURRENT_TIMESTAMP;
                """, (h_addr, traffic_count, infra_score))
                
                count += 1
                if count % 20 == 0:
                    conn.commit()

            print(f"SUCCESS: Lobe 2 scoring completed for {count} hexagons.")
            
            # Log action
            explanation = f"George Bytes ran TxDOT scoring in {'Procedural' if use_procedural else 'Real-World'} mode for {count} hexes."
            cur.execute("""
                INSERT INTO "HEX_InteractionCore" (user_prompt, agent_explanation, status)
                VALUES (%s, %s, %s);
            """, ("Lobe 2 Scoring", explanation, "SUCCESS"))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Lobe 2 Scorer failed. {e}")

if __name__ == "__main__":
    run_txdot_scorer()
