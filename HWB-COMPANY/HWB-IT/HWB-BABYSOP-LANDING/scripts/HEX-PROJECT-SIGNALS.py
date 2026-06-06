import os
import psycopg2
import h3
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def generate_signals():
    print("--- George Bytes: Generating Hierarchical Project Signals ---")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            # 1. Create Signal Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "HEX_Project_Signals" (
                    h3_address text PRIMARY KEY,
                    project_name text,
                    resolution integer,
                    is_beacon boolean DEFAULT true
                );
            """)

            # 2. Get active projects (Res 11)
            cur.execute('SELECT DISTINCT project_name, h3_address FROM "HEX_Lobe_Projects"')
            projects = cur.fetchall()

            for name, addr in projects:
                # Generate Res 9 and Res 7 signals
                p09 = h3.cell_to_parent(addr, 9)
                p07 = h3.cell_to_parent(addr, 7)
                p05 = h3.cell_to_parent(addr, 5) # For "32,000 feet"
                
                for p_addr, res in [(p09, 9), (p07, 7), (p05, 5)]:
                    cur.execute("""
                        INSERT INTO "HEX_Project_Signals" (h3_address, project_name, resolution)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (h3_address) DO NOTHING;
                    """, (p_addr, name, res))
            
            print(f"SUCCESS: Hierarchical Signals Manifested for {len(projects)} units.")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Signal generation failed. {e}")

if __name__ == "__main__":
    generate_signals()
