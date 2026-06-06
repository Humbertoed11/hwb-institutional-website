import os
import re
from typing import Dict, Any, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db"
)

def get_db_connection() -> psycopg2.extensions.connection:
    """Returns a connection to the PostgreSQL database."""
    return psycopg2.connect(DB_URL)

def run_scout_phase(
    group_url: str,
    group_name: str
) -> Tuple[int, str]:
    """Simulates Scout Brain (Lobe 11) discovery and connection check.

    Returns the registered source ID and status.
    """
    print("\n[LOBE 11 - SCOUT BRAIN] Starting connection verification...")
    print(f"Target Portal: {group_name} ({group_url})")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Register the Facebook page/group in the scout registry if needed
            cur.execute("""
                INSERT INTO "HEX_Scout_Registry" (
                    municipality_name, department_name, source_type,
                    endpoint_or_contact, scouting_status, latency_ms,
                    scouted_notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (endpoint_or_contact) DO UPDATE
                SET last_scouted = CURRENT_TIMESTAMP,
                    scouting_status = 'Active',
                    latency_ms = 195
                RETURNING id, scouting_status;
            """, (
                "Collin County", "Social Feed Scanner",
                "Facebook Group API", group_url, "Active",
                195, "Monitors Facebook postings for off-market land sales."
            ))
            res = cur.fetchone()
            conn.commit()
            print("SUCCESS: Connection test passed. Latency: 195ms.")
            return res[0], res[1]
    finally:
        conn.close()

def run_pulse_phase(
    raw_content: str,
    post_url: str
) -> Tuple[str, float]:
    """Simulates Pulse Brain (Lobe 6) sanitization and sentiment analysis.

    Returns the sanitized content and computed opportunity score.
    """
    print("\n[LOBE 6 - PULSE BRAIN] Fetching and sanitizing data stream...")
    
    # 1. Sanitization: remove HTML/script markers and normalize whitespace
    sanitized_text: str = re.sub(r"<[^>]*>", "", raw_content)
    sanitized_text = re.sub(r"\s+", " ", sanitized_text).strip()
    print("SUCCESS: Input text sanitized. Checked for SQL injection safety.")
    
    # 2. Opportunity scoring: look for positive keywords
    opportunity_keywords = ["acres", "sale", "owner", "commercial", "prime"]
    match_count: int = sum(
        1 for w in opportunity_keywords if w in sanitized_text.lower()
    )
    
    # Base score calculated out of 10.0
    score: float = round(min(10.0, 3.0 + (match_count * 1.5)), 2)
    print(f"Calculated Pulse Opportunity Score: {score} / 10.0")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Find an H3 address from Grid_Res11 to associate with the post
            cur.execute('SELECT h3_address FROM "HEX_Grid_Res11" LIMIT 1;')
            h3_row = cur.fetchone()
            h3_cell: str = h3_row[0] if h3_row else "8b26c8280100fff"
            
            cur.execute("""
                INSERT INTO "HEX_PulseOpportunities" (
                    h3_address, platform, post_url, post_content,
                    sentiment_score
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (post_url) DO UPDATE
                SET sentiment_score = EXCLUDED.sentiment_score,
                    post_content = EXCLUDED.post_content
                RETURNING h3_address;
            """, (h3_cell, "Facebook", post_url, sanitized_text, score))
            h3_cell = cur.fetchone()[0]
            conn.commit()
            print(f"Saved opportunity to database linked to H3 Cell: {h3_cell}")
            return h3_cell, score
    finally:
        conn.close()

def run_inference_phase(
    h3_cell: str,
    post_content: str
) -> str:
    """Simulates Inference Brain (Lobe 8) logic.

    Checks L1 zoning, L3 power, and L4 environment viability, then promotes
    to a lead if conditions pass. Returns the new lead parcel ID.
    """
    print("\n[LOBE 8 - INFERENCE BRAIN] Commencing cross-lobe validation...")
    
    # 1. Parse contact info and acreage
    name_match = re.search(r"Contact\s+([A-Za-z\s]+)\s+at", post_content)
    phone_match = re.search(r"\b\d{3}-\d{3}-\d{4}\b", post_content)
    acres_match = re.search(r"(\d+)\s+acres", post_content)
    
    owner_name: str = name_match.group(1).strip() if name_match else "Unknown"
    owner_phone: str = phone_match.group(0) if phone_match else "Unknown"
    acres: str = acres_match.group(1) if acres_match else "Unknown"
    
    print(f"Parsed Details -> Owner: {owner_name}, Phone: {owner_phone}")
    print(f"Target Land Size: {acres} Acres")
    
    # 2. Check Zoning (L1), Utilities (L3), Soil (L4)
    print("Auditing zoning via Lobe 1 (City Brain)... [Zoning: Z-COMMERCIAL]")
    print("Auditing utilities via Lobe 3 (Power Brain)... [Capacity: OK]")
    print("Auditing soil layers via Lobe 4 (Legal/Env Brain)... [Soil Class: STABLE]")
    
    parcel_id: str = f"HEX-FB-{h3_cell}"
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "HEX_Leads" (
                    parcel_id, owner_name, owner_contact, status, lead_source
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (parcel_id) DO UPDATE
                SET status = 'New',
                    owner_name = EXCLUDED.owner_name,
                    owner_contact = EXCLUDED.owner_contact
                RETURNING parcel_id;
            """, (
                parcel_id, owner_name, owner_phone, "New", "Facebook Monitor"
            ))
            res = cur.fetchone()
            
            # Seed Market Value estimation
            cur.execute("""
                INSERT INTO "HEX_MarketValue" (
                    parcel_id, estimated_value, asking_price,
                    underwritten_value, compositions, assessed_date
                )
                VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
                ON CONFLICT DO NOTHING;
            """, (
                parcel_id, 350000.00, 395000.00, 320000.00,
                '{"note": "Simulated deal value calculation"}'
            ))
            
            conn.commit()
            print(f"PROMOTED: Parcel {parcel_id} registered in HEX_Leads.")
            return res[0]
    finally:
        conn.close()

def run_alpha_phase(
    parcel_id: str,
    h3_cell: str,
    score: float,
    content: str
) -> None:
    """Simulates Alpha Brain (Lobe 10) report generation."""
    print("\n[LOBE 10 - ALPHA BRAIN] Generating feasibility summary...")
    
    report_text = f"""
=====================================================================
            HEXGROWTH ALPHA FEASIBILITY REPORT (SIMULATED)
=====================================================================
REPORT ID: HEX-PULSE-SIM-101
Target Cell: {h3_cell}
Source: Facebook Posting / Off-Market Lead
Opportunity Score: {score} / 10.0
Assigned Parcel ID: {parcel_id}

[LEAD PROFILE]
Contact Name: John Doe
Contact Info: 214-555-0199
Source Post: "{content}"

[ZONING AND UTILITIES ANALYSIS]
* City Zoning (L1): Commercial - Approved for redevelopment
* Utilities Spine (L3): Capacity matches site specifications
* Environmental (L4): Geotech soil checks stable; zero wetland overlap

[DECISION SUGGESTION]
Underwritten site value matches the asking parameters. Highly recommend 
initiating direct contact with the owner for a land survey.
=====================================================================
"""
    print(report_text)

def main() -> None:
    """Runs the full Facebook land deal simulation sequence."""
    print("--- HEXGROWTH: Initiating Facebook Deal Simulation Sequence ---")
    
    group_url = "https://facebook.com/groups/collin-county-land-deals"
    group_name = "Collin County Real Estate Group"
    raw_post = (
        "Owner selling 12 acres of prime commercial land in Collin County. "
        "Coordinates around 33.12, -96.54. Ready for redevelopment. "
        "Contact John Doe at 214-555-0199."
    )
    post_url = "https://facebook.com/groups/collin-county-land/posts/9912083"
    
    # 1. Scout Phase
    run_scout_phase(group_url, group_name)
    
    # 2. Pulse Phase
    h3_cell, score = run_pulse_phase(raw_post, post_url)
    
    # 3. Inference Phase
    parcel_id = run_inference_phase(h3_cell, raw_post)
    
    # 4. Alpha Phase
    run_alpha_phase(parcel_id, h3_cell, score, raw_post)
    
    print("--- Simulation Completed Successfully ---")

if __name__ == "__main__":
    main()
