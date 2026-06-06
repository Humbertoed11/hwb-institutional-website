import os
import argparse
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def log_manual_scar():
    parser = argparse.ArgumentParser(description="HEXGROWTH Knowledge Scars Logger CLI")
    parser.add_argument("--desc", required=True, help="Description of the mistake or logical bug")
    parser.add_argument("--cat", default="General", help="Category (e.g. database, UI, scraper)")
    parser.add_argument("--impact", type=int, default=3, help="Impact rating level (1 to 5)")
    parser.add_argument("--rule", default="", help="Preventative/foresight rule to avoid repetition")
    parser.add_argument("--status", default="Pending", help="Resolution status (Pending, Resolved)")
    
    args = parser.parse_args()
    
    print("--- George Bytes: CLI Ingestion of Knowledge Scar ---")
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO "HEX_KnowledgeScars" (description, category, status, impact_level, implemented_fix, preventative_rule)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (args.desc, args.cat, args.status, args.impact, None if args.status == "Pending" else "CLI Resolved", args.rule))
        
        scar_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        print(f"SUCCESS: Knowledge Scar logged successfully with ID: {scar_id}")
    except Exception as e:
        print(f"FAILURE: Failed to log Knowledge Scar. {e}")

if __name__ == "__main__":
    log_manual_scar()
