import os
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def run_miner(lobe_name="Infrastructure"):
    print(f"--- George Bytes: Initializing Miner Cycle [{lobe_name}] ---")
    
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            # 1. Fetch current hex grid addresses
            cur.execute('SELECT h3_address FROM "HEX_Grid_Res11" LIMIT 10')
            target_hexes = cur.fetchall()
            
            print(f"[FETCH] Target hexes identified: {len(target_hexes)}")
            
            for (h_addr,) in target_hexes:
                # MOCK DATA FETCH (Place holder for actual API logic)
                # In production, this would call TxDOT or FEMA
                mock_traffic = 5000 
                mock_alpha = 7.5
                
                cur.execute("""
                    INSERT INTO "HEX_Lobe_Infrastructure" (h3_address, traffic_count, alpha_score)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (h3_address) DO UPDATE SET
                    traffic_count = EXCLUDED.traffic_count,
                    alpha_score = EXCLUDED.alpha_score,
                    last_updated = CURRENT_TIMESTAMP;
                """, (h_addr, mock_traffic, mock_alpha))
                
            print(f"SUCCESS: Miner cycle complete for {len(target_hexes)} units.")
            
            # Log successful operation to Interaction Core
            cur.execute("""
                INSERT INTO "HEX_InteractionCore" (user_prompt, agent_explanation, status)
                VALUES (%s, %s, %s);
            """, ("Miner Execution", f"George Bytes successfully executed the first {lobe_name} miner cycle.", "SUCCESS"))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Miner cycle failed. {e}")

if __name__ == "__main__":
    run_miner()
