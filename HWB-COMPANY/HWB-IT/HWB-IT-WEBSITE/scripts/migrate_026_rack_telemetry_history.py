"""
Migration 026: SigmaFidelity™ 7-Rack Historical Telemetry & Statistical Process Control (SPC) Ledger
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & HWB-QMS-11.2 Telemetry SOP
Authority: Humberto Dominguez (CEO) - Approved 09/24/2026
Architect: George (Systems Architect & mbB)
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

def run_migration(db_url: str = None):
    target_url = db_url or DB_URL
    print("\n==================================================================", flush=True)
    print("  Applying Migration 026: 7-Rack Historical Telemetry & SPC Ledger", flush=True)
    print("==================================================================", flush=True)

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor() as cur:
            # 1. Provision Table: RackTelemetryHistory
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "RackTelemetryHistory" (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(100),
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    rack_number INTEGER NOT NULL,
                    rack_name VARCHAR(100) NOT NULL,
                    metric_category VARCHAR(100) NOT NULL,
                    score_value NUMERIC(8, 2),
                    secondary_value NUMERIC(8, 2),
                    status_tag VARCHAR(50) DEFAULT 'HEALTHY',
                    details_json JSONB,
                    recorded_by VARCHAR(100) DEFAULT 'George (Systems Architect)'
                );

                CREATE INDEX IF NOT EXISTS idx_rack_telemetry_timestamp ON "RackTelemetryHistory"(timestamp);
                CREATE INDEX IF NOT EXISTS idx_rack_telemetry_rack_num ON "RackTelemetryHistory"(rack_number);
                CREATE INDEX IF NOT EXISTS idx_rack_telemetry_category ON "RackTelemetryHistory"(metric_category);
                CREATE INDEX IF NOT EXISTS idx_rack_telemetry_session ON "RackTelemetryHistory"(session_id);
            ''')

            # 2. Record migration in schema_migrations if not present
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "schema_migrations" (
                    version VARCHAR(100) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                );
                INSERT INTO "schema_migrations" (version, description)
                VALUES ('026_rack_telemetry_historical_snapshots', 'Historical snapshot ledger for 7-rack telemetry, memory rot, Six Sigma SPC, and Pareto distributions')
                ON CONFLICT (version) DO NOTHING;
            ''')

        conn.commit()
        print("  -> Table 'RackTelemetryHistory' successfully created with indices.", flush=True)
        print("  -> Migration 026 recorded in schema_migrations.", flush=True)
    except Exception as e:
        conn.rollback()
        print(f"  -> [ERROR] Migration 026 failed: {e}", flush=True)
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
