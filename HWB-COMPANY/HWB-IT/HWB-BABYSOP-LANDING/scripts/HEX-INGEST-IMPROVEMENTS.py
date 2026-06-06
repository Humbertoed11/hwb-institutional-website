import os
from typing import List, Dict, Any
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db"
)

def get_improvements() -> List[Dict[str, Any]]:
    """Returns the list of 10 structured system improvements."""
    return [
        {
            "description": (
                "Facebook simulation uses mock H3 cells instead of parsing "
                "actual latitude and longitude coordinates from post text."
            ),
            "category": "GEOSPATIAL",
            "status": "Planned",
            "impact_level": 4,
            "implemented_fix": "None (Staged for development)",
            "preventative_rule": (
                "Use regex latitude/longitude extractor to query PostGIS "
                "in simulation runs."
            )
        },
        {
            "description": (
                "L1 zoning, L3 utility, and L4 environmental checks in "
                "Facebook deal validation are text-only print statements "
                "rather than actual table queries."
            ),
            "category": "LOBE_INTEGRATION",
            "status": "Planned",
            "impact_level": 5,
            "implemented_fix": "None (Staged for development)",
            "preventative_rule": (
                "Enforce active checks against HEX_Grid_Res11 and "
                "HEX_Lobe_Infrastructure tables before lead promotion."
            )
        },
        {
            "description": (
                "Simple regex patterns fail on decimals, custom text formatting, "
                "or raw numbers for acreage and phone contacts."
            ),
            "category": "DATA_PARSING",
            "status": "Planned",
            "impact_level": 3,
            "implemented_fix": "None (Staged for development)",
            "preventative_rule": (
                "Implement multi-pattern regex matching to normalize names, "
                "phone numbers, and decimals."
            )
        },
        {
            "description": (
                "Underwritten values for off-market deals use a static seed "
                "value instead of dynamic market comparables."
            ),
            "category": "VALUATION",
            "status": "Planned",
            "impact_level": 4,
            "implemented_fix": "None (Staged for development)",
            "preventative_rule": (
                "Perform comparable valuation check using historical average "
                "prices from HEX_MarketValue."
            )
        },
        {
            "description": (
                "Scout Brain simulations do not account for request headers, "
                "rate limits, or credentials expiration on social media platforms."
            ),
            "category": "DATA_INGESTION",
            "status": "Planned",
            "impact_level": 4,
            "implemented_fix": "None (Staged for development)",
            "preventative_rule": (
                "Simulate random user-agent delays and rotation of access "
                "headers in connection checks."
            )
        },
        {
            "description": (
                "System creates duplicate leads if the same land posting is "
                "scraped from multiple groups or dates."
            ),
            "category": "DATA_INTEGRITY",
            "status": "Planned",
            "impact_level": 4,
            "implemented_fix": "None (Staged for development)",
            "preventative_rule": (
                "Query database for matching phone contact or H3 cell before "
                "creating new entries in HEX_Leads."
            )
        },
        {
            "description": (
                "Facebook simulation only reads raw post text, ignoring "
                "land surveys and maps attached as images."
            ),
            "category": "IMAGE_OCR",
            "status": "Planned",
            "impact_level": 3,
            "implemented_fix": "None (Staged for development)",
            "preventative_rule": (
                "Simulate OCR trigger on image attachments to parse text fields."
            )
        },
        {
            "description": (
                "No automated messaging is triggered when high-opportunity "
                "leads are promoted to active status."
            ),
            "category": "WORKFLOW",
            "status": "Planned",
            "impact_level": 3,
            "implemented_fix": "None (Staged for development)",
            "preventative_rule": (
                "Insert official email notifications into PendingOutbox when "
                "lead scores exceed 8.5."
            )
        },
        {
            "description": (
                "Simulation runs do not write evaluation statistics back to "
                "Accountability Brain tables."
            ),
            "category": "ACCOUNTABILITY",
            "status": "Planned",
            "impact_level": 3,
            "implemented_fix": "None (Staged for development)",
            "preventative_rule": (
                "Update HEX_AccountabilityBrain last_run timestamps and "
                "performance statistics after simulation syncs."
            )
        },
        {
            "description": (
                "Database queries in simulator run without explicit transaction "
                "rollbacks, risking incomplete database states."
            ),
            "category": "DATABASE",
            "status": "Planned",
            "impact_level": 4,
            "implemented_fix": "None (Staged for development)",
            "preventative_rule": (
                "Wrap ingestion queries in transaction blocks (commit/rollback) "
                "to preserve data integrity."
            )
        }
    ]

def ingest_improvements(
    conn: psycopg2.extensions.connection,
    improvements: List[Dict[str, Any]]
) -> int:
    """Inserts the improvements list into the HEX_KnowledgeScars table."""
    inserted: int = 0
    with conn.cursor() as cur:
        for imp in improvements:
            # Check if this description already exists to avoid duplicates
            cur.execute("""
                SELECT id FROM "HEX_KnowledgeScars"
                WHERE description = %s AND category = %s;
            """, (imp["description"], imp["category"]))
            if cur.fetchone():
                continue
                
            cur.execute("""
                INSERT INTO "HEX_KnowledgeScars" (
                    description, category, status, impact_level,
                    implemented_fix, preventative_rule
                )
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (
                imp["description"], imp["category"], imp["status"],
                imp["impact_level"], imp["implemented_fix"],
                imp["preventative_rule"]
            ))
            inserted += 1
    conn.commit()
    return inserted

def main() -> None:
    """Runs the database ingestion script."""
    print("--- George Bytes: Ingesting Deal Wizard Improvements to database brain ---")
    try:
        conn = psycopg2.connect(DB_URL)
        improvements = get_improvements()
        count = ingest_improvements(conn, improvements)
        print(f"SUCCESS: Ingested {count} new system improvements into HEX_KnowledgeScars.")
        conn.close()
    except Exception as e:
        print(f"FAILURE: Ingestion failed. {e}")

if __name__ == "__main__":
    main()
