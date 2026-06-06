import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def perform_neural_handshake():
    print("--- George Bytes: Initiating Neural Handshake Protocol ---")
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # Attempt to retrieve from HEX_SystemState (from Step 2 DDL)
        # Fallback to legacy HEX_SystemCore if HEX_SystemState is not populated yet
        state_data = None
        session_id = None
        source_table = None
        
        try:
            cursor.execute('SELECT session_id, state_data FROM "HEX_SystemState" ORDER BY updated_at DESC LIMIT 1;')
            row = cursor.fetchone()
            if row:
                session_id, state_data = row[0], row[1]
                source_table = "HEX_SystemState"
        except Exception as e:
            # Table might not exist or error occurred, rollback transactions
            conn.rollback()

        if not state_data:
            try:
                cursor.execute('SELECT session_id, state_data FROM "HEX_SystemCore" ORDER BY updated_at DESC LIMIT 1;')
                row = cursor.fetchone()
                if row:
                    session_id, state_data = row[0], row[1]
                    source_table = "HEX_SystemCore"
            except Exception as e:
                conn.rollback()

        if state_data:
            if isinstance(state_data, str):
                state_data = json.loads(state_data)
            
            # Format and output the state parameters in QMS-11.2 High-Fidelity Terminal layout
            print(f"SUCCESS: System State retrieved from database table [{source_table}].")
            print(f"Active Session: {session_id}")
            print(f"| Parameter | State |")
            print(f"| :--- | :--- |")
            params = state_data.get("parameters", {})
            for key, val in params.items():
                print(f"| {key} | {val} |")
                
            # Log successful handshake to Telemetry
            try:
                cursor.execute("""
                    INSERT INTO "HEX_Telemetry" (action_name, status, technical_data)
                    VALUES (%s, %s, %s)
                """, ("Neural_Handshake", "SUCCESS", json.dumps({"session_id": session_id, "table": source_table})))
                conn.commit()
            except Exception as ex:
                conn.rollback()
        else:
            print("WARNING: No active session state found in database. Initializing fresh workspace state.")
            
        conn.close()
    except Exception as e:
        print(f"FAILURE: Neural Handshake failed. {e}")

if __name__ == "__main__":
    perform_neural_handshake()
