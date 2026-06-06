import h3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def lay_grid(lat, lng, radius_km=1, city="Plano"):
    print(f"--- George Bytes: Laying Layer 0 Grid for {city} ---")
    
    # Get all hexagons at resolution 11 within radius
    hexagons = h3.grid_disk(h3.latlng_to_cell(lat, lng, 11), int(radius_km / 0.05)) # Rough radius conversion
    
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            count = 0
            for h_addr in hexagons:
                # Get coordinates for the hexagon
                boundary = h3.cell_to_boundary(h_addr)
                # Convert to WKT Polygon
                wkt_poly = f"POLYGON(({','.join([f'{p[1]} {p[0]}' for p in boundary])}, {boundary[0][1]} {boundary[0][0]}))"
                
                cur.execute("""
                    INSERT INTO "HEX_Grid_Res11" (h3_address, geom, city_name)
                    VALUES (%s, ST_GeomFromText(%s, 4326), %s)
                    ON CONFLICT (h3_address) DO NOTHING;
                """, (h_addr, wkt_poly, city))
                count += cur.rowcount
            
            print(f"SUCCESS: Laid {count} new hexagons into the grid.")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Grid laying failed. {e}")

if __name__ == "__main__":
    # Test: Lay a small grid in Plano, TX
    lay_grid(33.0198, -96.6989, radius_km=0.5, city="Plano")
