import os
import psycopg2

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def setup_beacons_table():
    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        # Recreate Beacons Table with description
        cur.execute("DROP TABLE IF EXISTS \"HEX_Beacons\" CASCADE;")
        cur.execute("""
            CREATE TABLE "HEX_Beacons" (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL,
                altitude_tier VARCHAR(20) NOT NULL,
                score DOUBLE PRECISION NOT NULL DEFAULT 8.0,
                count INTEGER NOT NULL DEFAULT 1,
                description TEXT
            );
        """)
        
        # Populate Beacons
        beacons = [
            # Sky Tier (Metro Beacons)
            ("DFW Metroplex Hub", 32.77, -96.79, "sky", 8.8, 122193, "City Lobe: Principal metropolitan convergence center. Zoning variance approval rate 92%. High traffic volume."),
            ("Wise County Hub", 33.23, -97.58, "sky", 7.9, 12, "Finance Lobe: Wise County aggregate industrial node. Moderate land costs, rapid development timeline."),
            ("Wichita Falls Green Energy Hub", 33.9137, -98.4934, "sky", 8.4, 250, "Power Lobe: Major wind and solar transmission node. ERCOT connection gateway. Low congestion risk."),
            ("Vernon Industrial Extraction Node", 34.1545, -99.2651, "sky", 8.1, 180, "Extraction Lobe: Primary compression and chemical extraction corridor. Direct pipeline easement."),
            ("Bowie Logistics & Fiber Spur", 33.5594, -97.8481, "sky", 8.3, 140, "Pulse Lobe: US-287 logistics cross-docking center. Redundant fiber spur and high capacity freight route."),
            
            # Clouds Tier (Corridor Pillars)
            ("Northwest Hwy Corridor", 32.8637, -96.6963, "clouds", 8.9, 45, "TxDOT Lobe: Commercial Retail Corridor. Freight access optimized, direct ingress/egress from US-287 Spur."),
            ("Valley View District", 32.9264, -96.7972, "clouds", 8.8, 62, "City Lobe: Reinvestment Zone / TIF Zone. High density multi-use zoning variance active. Strong Preston Hollow NIMBY risk."),
            ("Decatur Growth Path", 33.2343, -97.5861, "clouds", 7.9, 12, "City Lobe: Wise County ETJ commercial expansion zone. Wise Electric Cooperative dual feed. Outside 100-year flood zone."),
            
            # Micro Markers (Clouds Tier) near Wichita Falls, Vernon TX, and Bowie TX along US-287 highway
            ("Wichita Falls Wind Farm Spur", 33.9300, -98.4800, "clouds", 8.5, 80, "Power Lobe: 150MW capacity wind spur. Transmission lag under 12ms. Interconnect queue approval scheduled Q4 2026. Phase 1 grid hardiness certified."),
            ("Vernon Gas Compressor Facility", 34.1700, -99.2500, "clouds", 8.2, 95, "Extraction Lobe: 2.4Bcf/d direct pipeline tap. Helium easement secured. 480V three-phase utility feed active. No environmental contaminants logged."),
            ("Bowie Fiber Vault Junction", 33.5450, -97.8300, "clouds", 8.4, 110, "Pulse Lobe: Dual long-haul carrier fiber splice vault (Zayo/Crown). Redundant dark fiber access. TX-287 logistics corridor ingress/egress variance approved.")
        ]
        
        for name, lat, lng, tier, score, cnt, desc in beacons:
            cur.execute("""
                INSERT INTO "HEX_Beacons" (name, latitude, longitude, altitude_tier, score, count, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (name, lat, lng, tier, score, cnt, desc))
            
        conn.commit()
    conn.close()
    print("SUCCESS: HEX_Beacons table recreated and populated in PostgreSQL.")

if __name__ == '__main__':
    setup_beacons_table()
