import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def simulate_expansion():
    print("--- George Bytes: Simulating TxDOT US-75 Lane Expansion ---")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            # Create the simulation zone (US-75 Corridor in Plano)
            # US-75 is roughly along Longitude -96.7089
            
            # Logic: If a hex is within 200m of the highway center, apply "Construction Friction"
            # This lowers Alpha score temporarily but flags it as "Future Tier 1"
            
            # 1. Update Infrastructure Lobe (Res 11)
            cur.execute("""
                UPDATE "HEX_Lobe_Infrastructure"
                SET alpha_score = alpha_score * 0.5,
                    traffic_count = traffic_count + 20000
                WHERE ST_DWithin(
                    (SELECT geom FROM "HEX_Grid_Res11" WHERE h3_address = "HEX_Lobe_Infrastructure".h3_address),
                    ST_GeomFromText('LINESTRING(-96.7089 33.05, -96.7089 32.95)', 4326)::geography,
                    300
                );
            """)
            print(f"[SIM] Construction friction applied to {cur.rowcount} surgical units.")

            # 2. Log to Knowledge Scars
            cur.execute("""
                INSERT INTO "HEX_KnowledgeScars" (description, category, impact_level)
                VALUES (%s, %s, %s);
            """, ("SIMULATION: TxDOT US-75 Lane Expansion Plan detected. Expected construction window: 2027-2029.", "INFRASTRUCTURE", "HIGH"))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Simulation failed. {e}")

if __name__ == "__main__":
    simulate_expansion()
