import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def setup_cognitive_bridge():
    print("--- George Bytes: Initiating Cognitive Bridge Table Creation ---")
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # Create HEX_CognitiveBridge table
        cursor.execute("""
            DROP TABLE IF EXISTS "HEX_CognitiveBridge" CASCADE;
            CREATE TABLE "HEX_CognitiveBridge" (
                id SERIAL PRIMARY KEY,
                parameter_name VARCHAR(150) UNIQUE NOT NULL,
                parameter_value NUMERIC(15, 4) NOT NULL,
                source_lobe VARCHAR(100) NOT NULL,
                description TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("SUCCESS: Table 'HEX_CognitiveBridge' created.")
        
        # Seed parameters representing active economic and operational forces
        seed_parameters = [
            ("interest_rate", 0.0550, "L7 Finance Brain", "Federal funds and commercial borrowing rate baseline."),
            ("cap_rate_baseline", 0.0725, "L7 Finance Brain", "Average capitalization rate for commercial real estate in target counties."),
            ("permit_latency_days", 120.0, "L1 City Brain", "Average municipal planning approval delay."),
            ("egress_speed_mph", 45.0, "L2 TxDOT Brain", "Average vehicle transit speed near prime corridors."),
            ("sentiment_index", 0.6500, "L6 Pulse Brain", "Community sentiment score regarding high-density construction."),
            ("construction_cost_index", 1.1500, "L7 Finance Brain", "Materials and labor cost premium indicator.")
        ]
        
        for name, value, source, desc in seed_parameters:
            cursor.execute("""
                INSERT INTO "HEX_CognitiveBridge" (parameter_name, parameter_value, source_lobe, description)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (parameter_name) DO UPDATE SET
                    parameter_value = EXCLUDED.parameter_value,
                    source_lobe = EXCLUDED.source_lobe,
                    description = EXCLUDED.description,
                    last_updated = CURRENT_TIMESTAMP;
            """, (name, value, source, desc))
            
        conn.commit()
        conn.close()
        print(f"SUCCESS: Seeded {len(seed_parameters)} parameters into 'HEX_CognitiveBridge'.")
    except Exception as e:
        print(f"FAILURE: Failed to set up Cognitive Bridge database. {e}")

if __name__ == '__main__':
    setup_cognitive_bridge()
