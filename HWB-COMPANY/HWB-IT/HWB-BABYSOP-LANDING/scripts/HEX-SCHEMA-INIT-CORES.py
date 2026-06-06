import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def init_cores():
    print("--- George Bytes: Initializing Core Brain Schemas ---")
    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        # Check if vector extension is available
        has_vector = False
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()
            has_vector = True
            print("SUCCESS: Vector extension is enabled.")
        except Exception as e:
            conn.rollback()
            print("INFO: Vector extension is not available. Falling back to numeric array for embeddings.")

        embedding_type = "vector(1536)" if has_vector else "DOUBLE PRECISION[]"

        # 1. Neural Core
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "HEX_KB_Library" (
                id SERIAL PRIMARY KEY,
                doc_id VARCHAR(50) UNIQUE NOT NULL,
                title VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                content TEXT,
                url_slug VARCHAR(255),
                embedding {embedding_type},
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS "HEX_SystemState" (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(100) UNIQUE NOT NULL,
                state_data JSONB NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS "HEX_Telemetry" (
                id SERIAL PRIMARY KEY,
                action_name VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL,
                technical_data JSONB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Revenue Core (Real Estate Parcels, Deals, Comps)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "HEX_Leads" (
                id SERIAL PRIMARY KEY,
                parcel_id VARCHAR(100) UNIQUE NOT NULL,
                owner_name VARCHAR(255),
                owner_contact VARCHAR(255),
                status VARCHAR(50) DEFAULT 'New',
                lead_source VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS "HEX_Accounts" (
                id SERIAL PRIMARY KEY,
                account_name VARCHAR(255) UNIQUE NOT NULL,
                partner_type VARCHAR(100),
                contact_email VARCHAR(255),
                status VARCHAR(50) DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS "HEX_MarketValue" (
                id SERIAL PRIMARY KEY,
                parcel_id VARCHAR(100) NOT NULL,
                estimated_value NUMERIC(15, 2),
                asking_price NUMERIC(15, 2),
                underwritten_value NUMERIC(15, 2),
                compositions JSONB,
                assessed_date DATE,
                FOREIGN KEY (parcel_id) REFERENCES "HEX_Leads"(parcel_id) ON DELETE CASCADE
            );
        """)

        # 3. Operations Core (Due Diligence tasks, SOP steps, Quality check results)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "HEX_WorkOrders" (
                id SERIAL PRIMARY KEY,
                parcel_id VARCHAR(100) NOT NULL,
                task_name VARCHAR(255) NOT NULL,
                assigned_to VARCHAR(100),
                status VARCHAR(50) DEFAULT 'Pending',
                due_date DATE,
                completed_at TIMESTAMP,
                FOREIGN KEY (parcel_id) REFERENCES "HEX_Leads"(parcel_id) ON DELETE CASCADE
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS "HEX_StandardProcedures" (
                id SERIAL PRIMARY KEY,
                sop_id VARCHAR(50) UNIQUE NOT NULL,
                title VARCHAR(255) NOT NULL,
                steps JSONB NOT NULL,
                department VARCHAR(100),
                last_revised TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS "HEX_QualityAudits" (
                id SERIAL PRIMARY KEY,
                audit_id VARCHAR(50) UNIQUE NOT NULL,
                parcel_id VARCHAR(100) NOT NULL,
                score NUMERIC(5, 2),
                findings JSONB,
                audited_by VARCHAR(100),
                audited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parcel_id) REFERENCES "HEX_Leads"(parcel_id) ON DELETE CASCADE
            );
        """)

        # 4. Governance Core (Boundary regulations, Service health tracking)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "HEX_Incidents" (
                id SERIAL PRIMARY KEY,
                incident_type VARCHAR(100) NOT NULL,
                parcel_id VARCHAR(100),
                description TEXT NOT NULL,
                resolution_status VARCHAR(50) DEFAULT 'Open',
                reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (parcel_id) REFERENCES "HEX_Leads"(parcel_id) ON DELETE CASCADE
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS "HEX_Uptime" (
                id SERIAL PRIMARY KEY,
                service_name VARCHAR(100) NOT NULL,
                uptime_percentage NUMERIC(5, 2) NOT NULL,
                last_ping TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
    conn.close()
    print("SUCCESS: HEXGROWTH Monolithic SQL Brain initialized with 4-Tier cores.")

if __name__ == "__main__":
    init_cores()
