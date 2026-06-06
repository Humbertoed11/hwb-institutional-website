import os
import psycopg2
import h3
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def dilate_spine():
    print("--- George Bytes: Initiating Hierarchical Spine Dilation ---")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            # 1. Create Hierarchical Tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "HEX_Grid_Res09" (
                    h3_address text PRIMARY KEY,
                    geom geometry(Polygon, 4326),
                    alpha_score numeric(3,1) DEFAULT 5.0
                );
                CREATE TABLE IF NOT EXISTS "HEX_Grid_Res07" (
                    h3_address text PRIMARY KEY,
                    geom geometry(Polygon, 4326),
                    alpha_score numeric(3,1) DEFAULT 5.0
                );
            """)
            
            # 2. Extract Res 11 data to aggregate
            cur.execute('SELECT h3_address, alpha_score FROM "HEX_Lobe_Infrastructure"')
            res11_data = cur.fetchall()
            print(f"[PROCESS] Inhaling {len(res11_data)} Res11 units...")

            res09_agg = {}
            res07_agg = {}

            for addr, score in res11_data:
                # Parent Res 9
                p09 = h3.cell_to_parent(addr, 9)
                if p09 not in res09_agg: res09_agg[p09] = []
                res09_agg[p09].append(float(score))
                
                # Parent Res 7
                p07 = h3.cell_to_parent(addr, 7)
                if p07 not in res07_agg: res07_agg[p07] = []
                res07_agg[p07].append(float(score))

            # 3. Ingest Res 09
            for p_addr, scores in res09_agg.items():
                avg_score = sum(scores) / len(scores)
                boundary = h3.cell_to_boundary(p_addr)
                wkt = f"POLYGON(({','.join([f'{p[1]} {p[0]}' for p in boundary])}, {boundary[0][1]} {boundary[0][0]}))"
                cur.execute("""
                    INSERT INTO "HEX_Grid_Res09" (h3_address, geom, alpha_score)
                    VALUES (%s, ST_GeomFromText(%s, 4326), %s)
                    ON CONFLICT (h3_address) DO UPDATE SET alpha_score = EXCLUDED.alpha_score;
                """, (p_addr, wkt, avg_score))

            # 4. Ingest Res 07
            for p_addr, scores in res07_agg.items():
                avg_score = sum(scores) / len(scores)
                boundary = h3.cell_to_boundary(p_addr)
                wkt = f"POLYGON(({','.join([f'{p[1]} {p[0]}' for p in boundary])}, {boundary[0][1]} {boundary[0][0]}))"
                cur.execute("""
                    INSERT INTO "HEX_Grid_Res07" (h3_address, geom, alpha_score)
                    VALUES (%s, ST_GeomFromText(%s, 4326), %s)
                    ON CONFLICT (h3_address) DO UPDATE SET alpha_score = EXCLUDED.alpha_score;
                """, (p_addr, wkt, avg_score))
            
            print(f"SUCCESS: Spine Dilated. Res09: {len(res09_agg)} | Res07: {len(res07_agg)}")
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Dilation failed. {e}")

if __name__ == "__main__":
    dilate_spine()
