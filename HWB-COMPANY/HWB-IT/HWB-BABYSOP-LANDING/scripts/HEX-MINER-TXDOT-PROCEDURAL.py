import os
import psycopg2
from psycopg2.extras import RealDictCursor
import h3
from dotenv import load_dotenv
import math

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

# Tactical Infrastructure Corridors (Plano, TX)
# 1. US-75 Corridor (Central Expressway)
CORRIDOR_75 = (33.0198, -96.7089) 
# 2. PGBT Corridor (President George Bush Turnpike)
CORRIDOR_PGBT = (32.9976, -96.7089)

def calculate_proximity_score(lat, lng):
    """
    Calculate procedural Alpha Score based on proximity to major arteries.
    High Alpha = Near Highways (Commercial Opportunity)
    """
    # Distance to US-75
    dist_75 = math.sqrt((lat - CORRIDOR_75[0])**2 + (lng - CORRIDOR_75[1])**2)
    # Distance to PGBT
    dist_pgbt = math.sqrt((lat - CORRIDOR_PGBT[0])**2 + (lng - CORRIDOR_PGBT[1])**2)
    
    min_dist = min(dist_75, dist_pgbt)
    
    # Scale: 0.0 (Far) to 10.0 (Very Close)
    # 0.01 degree is roughly 1km
    score = 10.0 - (min_dist * 500) 
    return round(max(0.1, min(score, 10.0)), 1)

def run_procedural_miner():
    print("--- George Bytes: Executing Procedural Lobe 2 Oxygenation ---")
    
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT h3_address FROM "HEX_Grid_Res11"')
            hexes = cur.fetchall()
            
            count = 0
            for row in hexes:
                h_addr = row['h3_address']
                lat, lng = h3.cell_to_latlng(h_addr)
                
                infra_score = calculate_proximity_score(lat, lng)
                # Weighted traffic count based on score
                traffic_count = int(infra_score * 5000)
                
                cur.execute("""
                    INSERT INTO "HEX_Lobe_Infrastructure" (h3_address, traffic_count, alpha_score)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (h3_address) DO UPDATE SET
                    traffic_count = EXCLUDED.traffic_count,
                    alpha_score = EXCLUDED.alpha_score,
                    last_updated = CURRENT_TIMESTAMP;
                """, (h_addr, traffic_count, infra_score))
                
                count += 1
            
            print(f"SUCCESS: Procedural Oxygenation Complete. {count} units updated.")
            
            # Update Interaction Core
            cur.execute("""
                INSERT INTO "HEX_InteractionCore" (user_prompt, agent_explanation, status)
                VALUES (%s, %s, %s);
            """, ("Procedural Oxygenation", f"George Bytes executed procedural Alpha Scoring for {count} hexagons.", "SUCCESS"))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Procedural Miner failed. {e}")

if __name__ == "__main__":
    run_procedural_miner()
