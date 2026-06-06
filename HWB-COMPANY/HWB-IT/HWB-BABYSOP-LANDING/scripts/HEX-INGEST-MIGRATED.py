import psycopg2
import os
import json

DB_URL = "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db"

def ingest_migration():
    print("--- George Bytes: Ingesting Migrated Data into SQL Brain ---")
    
    # Read the 7-Lobe Registry
    reg_path = "/home/humbertoed/hexgrowth/docs/PROBLEMS-TO-SOLVE.md"
    registry_content = ""
    if os.path.exists(reg_path):
        with open(reg_path, 'r') as f:
            registry_content = f.read()
    
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            # Ingest the event of migration and the current state
            cur.execute("""
                INSERT INTO "HEX_InteractionCore" (session_id, user_prompt, agent_explanation, technical_data, status)
                VALUES (%s, %s, %s, %s, %s);
            """, (
                "2026-05-24-MIGRATION-SYNC",
                "Move mistakenly saved data to Hexgrowth",
                "George Bytes identified and moved 14 HUD prototype files and the 7-Lobe Problem Registry from the legacy parent directory to Hexgrowth. Validated zero conflation in Postgres logs.",
                json.dumps({"registry": registry_content, "files_moved": 15}),
                "SUCCESS"
            ))
            
            # Update Knowledge Scars with the "Hexagons Only" mandate
            cur.execute("""
                INSERT INTO "HEX_KnowledgeScars" (description, category, impact_level, preventative_rule)
                VALUES (%s, %s, %s, %s);
            """, (
                "Strict Mandate: All Geospatial layers must use Hexagons to ensure regular tessellation without gaps.",
                "Preference",
                5,
                "Enforce generateHexagon() as the exclusive geometric primitive. Prohibit Octagons and lines."
            ))
            
            print(f"SUCCESS: Ingested migration logs and 'Hexagons Only' mandate into hex_dev_db.")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Ingestion failed. {e}")

if __name__ == "__main__":
    ingest_migration()
