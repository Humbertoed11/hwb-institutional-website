import os
import psycopg2
import h3
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

# MEDICINE MOUND COORDINATES (Approximate center of 60-acre plot)
MEDICINE_MOUND = (34.1878, -99.5945)

def run_simulation():
    print(f"--- George Bytes: Simulating Vernon Data Center Filing ---")
    
    # 1. Lay Grid at Res 11
    # 60 acres is roughly 0.25 sq km. A disk of radius 1km covers this easily.
    center_hex = h3.latlng_to_cell(MEDICINE_MOUND[0], MEDICINE_MOUND[1], 11)
    grid = h3.grid_disk(center_hex, 10) # 10 hexes radius to ensure coverage
    
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            print(f"[PROCESS] Laying surgical grid for Vernon Sector...")
            for h_addr in grid:
                boundary = h3.cell_to_boundary(h_addr)
                wkt = f"POLYGON(({','.join([f'{p[1]} {p[0]}' for p in boundary])}, {boundary[0][1]} {boundary[0][0]}))"
                cur.execute("""
                    INSERT INTO "HEX_Grid_Res11" (h3_address, geom, city_name)
                    VALUES (%s, ST_GeomFromText(%s, 4326), %s)
                    ON CONFLICT (h3_address) DO NOTHING;
                """, (h_addr, wkt, "Vernon"))

            # 2. Define the 60-acre plot (Approx 60 hexagons at Res 11)
            # 1 Res 11 hex is ~0.002 sq km (~0.5 acres). 60 acres = ~120 hexes.
            plot_hexes = h3.grid_disk(center_hex, 6)
            
            print(f"[PROCESS] Injecting Zone Change: AG -> INDUSTRIAL (DATA CENTER)")
            for h_addr in plot_hexes:
                # High Alpha boost for Data Center potential (Energy proximity)
                cur.execute("""
                    INSERT INTO "HEX_Lobe_Projects" (h3_address, project_name, status, alpha_boost, acreage)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (h3_address) DO UPDATE SET status = EXCLUDED.status, alpha_boost = EXCLUDED.alpha_boost;
                """, (h_addr, "MEDICINE-MOUND-DC-01", "FILING-ACTIVE", 4.5, 60.0))

            # 3. Consolidate into Alpha Spine
            # Normally this would be a trigger, but we simulate it here
            cur.execute("""
                INSERT INTO "HEX_Lobe_Infrastructure" (h3_address, alpha_score)
                SELECT h3_address, 8.5 FROM "HEX_Lobe_Projects" WHERE project_name = 'MEDICINE-MOUND-DC-01'
                ON CONFLICT (h3_address) DO UPDATE SET alpha_score = 8.5;
            """)
            
            print(f"SUCCESS: Data Center Simulation Active. 60-acre plot oxygenated.")
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Simulation failed. {e}")

if __name__ == "__main__":
    run_simulation()
