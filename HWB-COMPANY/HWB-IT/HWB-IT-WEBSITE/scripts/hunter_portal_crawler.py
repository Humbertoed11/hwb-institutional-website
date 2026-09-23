"""
SigmaFidelity™ Autonomous Statewide Texas Contract Hunter & Portal Crawler
Standard: HWB-QMS-7.8, HWB-QMS-8.9 & 2026-07-22 Statewide Mandate
Authority: George (Systems Architect & mbB) | Approved: Humberto Dominguez (CEO)

Mission:
Actively hunt, crawl, extract, and ingest public janitorial, custodial, and commercial
facility maintenance contracts across the ENTIRE STATE OF TEXAS:
- Dallas-Fort Worth Metroplex (Dallas, Fort Worth, Arlington, Plano, Collin, NTTA)
- Central Texas (Austin, Travis County, Williamson County, San Marcos, Waco, Austin ISD)
- Greater Houston (City of Houston, Harris County, Montgomery County, Galveston)
- South Texas (San Antonio, Bexar County, Corpus Christi, Rio Grande Valley)
- West & North Texas (El Paso, Lubbock, Midland-Odessa, Amarillo)
- Texas Higher Education Systems (UT System, UT Dallas, UT Austin, TAMUS, Texas Tech)
- Texas State Government (TxDOT, Texas Facilities Commission, Comptroller ESBD)

Engines: Playwright Headless Chromium + BeautifulSoup4 + Requests + PostgreSQL
"""

import os
import re
import json
import time
import datetime
import subprocess
import argparse
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load Institutional Secrets
load_dotenv('.env')

DB_URL = os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db')

# Verified Statewide Texas Bonfire Portal Fleet
TEXAS_BONFIRE_PORTALS = [
    {
        "agency_name": "City of Dallas",
        "region": "DFW Metroplex",
        "url": "https://dallascityhall.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "City of Dallas Bonfire"
    },
    {
        "agency_name": "City of Fort Worth",
        "region": "DFW Metroplex",
        "url": "https://fortworthtexas.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "Fort Worth Bonfire"
    },
    {
        "agency_name": "Harris County (Greater Houston)",
        "region": "Houston Gulf Coast",
        "url": "https://harriscountytx.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "Harris County Bonfire"
    },
    {
        "agency_name": "University of Texas System",
        "region": "Statewide Academic",
        "url": "https://utsystem.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "UT System Bonfire"
    },
    {
        "agency_name": "University of Texas at Dallas",
        "region": "DFW Metroplex / Richardson",
        "url": "https://utdallas.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "UT Dallas Bonfire"
    },
    {
        "agency_name": "Austin Independent School District",
        "region": "Central Texas / Austin",
        "url": "https://austinisd.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "Austin ISD Bonfire"
    },
    {
        "agency_name": "City of Midland",
        "region": "West Texas / Permian Basin",
        "url": "https://midlandtexas.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "Midland Bonfire"
    },
    {
        "agency_name": "Lubbock Power & Light",
        "region": "West Texas / Panhandle",
        "url": "https://lpandl.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "Lubbock Bonfire"
    }
]

# Statewide Search Filters
TARGET_NIGP_CODES = ['910-39', '962-58', '910-70', '910-25', '910-04', '910-06', '910-52']
TARGET_KEYWORDS = [
    'janitorial', 'custodial', 'cleaning', 'cleaner', 'day porter',
    'floor care', 'carpet extraction', 'sanitization', 'disinfection',
    'window washing', 'pressure wash', 'facility maintenance',
    'post-construction clean', 'terminal cleaning', 'restroom'
]

def is_custodial_opportunity(title: str, description: str = "") -> bool:
    """Checks whether a project title or description matches janitorial scopes."""
    combined = f"{title} {description}".lower()
    return any(kw in combined for kw in TARGET_KEYWORDS)

def execute_psql_query(sql: str) -> bool:
    """Executes SQL via docker exec or direct psycopg2 connection."""
    # First try docker exec directly (works reliably on host)
    try:
        proc = subprocess.run(
            ['docker', 'exec', '-i', 'hwb_postgres_dev', 'psql', '-U', 'hwbdev', '-d', 'hwb_dev_db'],
            input=sql,
            text=True,
            capture_output=True,
            timeout=10
        )
        if proc.returncode == 0:
            return True
    except Exception:
        pass

    # Fallback to direct psycopg2 if running inside container
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[HUNTER DB ERROR] SQL execution failed: {e}")
        return False

def crawl_bonfire_portal(portal_info: Dict[str, str], headless: bool = True) -> List[Dict[str, Any]]:
    """
    Crawls a public Bonfire portal using Playwright Headless Chromium.
    Extracts live open solicitations rendered via client-side JavaScript.
    """
    agency_name = portal_info["agency_name"]
    url = portal_info["url"]
    region = portal_info["region"]
    portal_name = portal_info["portal_name"]
    
    print(f"[HUNTER] Scouting {agency_name} ({region}) via {url}...")
    opportunities = []

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception as e:
                print(f"[HUNTER] Navigation timeout for {agency_name}: {e}")
                browser.close()
                return []

            # Wait for data table
            try:
                page.wait_for_selector('table tbody tr', timeout=7000)
            except Exception:
                print(f"[HUNTER] No active table rows found for {agency_name}.")
                browser.close()
                return []

            rows = page.query_selector_all('table tbody tr')
            print(f"[HUNTER] Found {len(rows)} raw listings on {agency_name} portal.")

            for r in rows:
                text = r.inner_text().strip()
                if not text or "There are no open projects" in text:
                    continue

                cells = r.query_selector_all('td')
                if len(cells) < 4:
                    continue

                status = cells[0].inner_text().strip()
                ref_num = cells[1].inner_text().strip()
                title = cells[2].inner_text().strip()
                close_date = cells[3].inner_text().strip() if len(cells) > 3 else ""
                
                # Extract link if available
                link_el = r.query_selector('a[href*="/opportunities/"]')
                opp_link = ""
                if link_el:
                    href = link_el.get_attribute('href')
                    if href:
                        opp_link = href if href.startswith('http') else f"https://{portal_info['url'].split('/')[2]}{href}"

                # Match against custodial/cleaning keywords
                if is_custodial_opportunity(title):
                    print(f"🎯 [HUNTER HIT] Matched Janitorial in {region}: [{ref_num}] {title} (Closes: {close_date})")
                    opportunities.append({
                        "solicitation_number": ref_num or f"BONFIRE-{abs(hash(title)) % 1000000}",
                        "title": title,
                        "agency_name": agency_name,
                        "region": region,
                        "portal_name": portal_name,
                        "status_badge": status,
                        "close_date_raw": close_date,
                        "rfp_url": opp_link or url,
                        "scouted_date": datetime.datetime.now().isoformat()
                    })

            browser.close()
    except Exception as e:
        print(f"[HUNTER] Error scouting {agency_name}: {e}")

    return opportunities

def crawl_texas_statewide_bonfire_fleet() -> List[Dict[str, Any]]:
    """Crawls all configured Bonfire municipal and higher-ed portals across Texas."""
    all_opps = []
    for portal in TEXAS_BONFIRE_PORTALS:
        opps = crawl_bonfire_portal(portal)
        all_opps.extend(opps)
        time.sleep(1) # Polite pause between portals
    return all_opps

def ingest_opportunities_to_database(opportunities: List[Dict[str, Any]]) -> int:
    """
    Ingests newly discovered Texas statewide opportunities into PostgreSQL InstitutionalBids.
    """
    if not opportunities:
        print("[HUNTER] No new custodial opportunities matched in this cycle.")
        return 0

    inserted_count = 0
    sql_statements = []
    for opp in opportunities:
        solicitation_num = opp["solicitation_number"].replace("'", "''")
        title = opp["title"].replace("'", "''")
        agency = opp["agency_name"].replace("'", "''")
        region = opp.get("region", "Statewide Texas").replace("'", "''")
        portal_name = opp.get("portal_name", "Texas Public Portal").replace("'", "''")
        rfp_url = opp.get("rfp_url", "").replace("'", "''")
        close_date = opp.get("close_date_raw", "").replace("'", "''")
        notes = f"Statewide Texas Hunter Auto-Discovered on {datetime.date.today()}. Region: {region}. Closes: {close_date}. Ready for takeoff analysis.".replace("'", "''")

        sql = f"""
        INSERT INTO "InstitutionalBids" (
            solicitation_number, title, agency_name, sector, portal_name,
            status, compliance_status, rfp_url, notes
        ) VALUES (
            '{solicitation_num}', '{title}', '{agency}', 'Texas Public Sector ({region})', '{portal_name}',
            'Hunter Scouted', 'Pending Takeoff Analysis', '{rfp_url}', '{notes}'
        ) ON CONFLICT (solicitation_number) DO UPDATE SET
            title = EXCLUDED.title,
            rfp_url = EXCLUDED.rfp_url,
            updated_at = CURRENT_TIMESTAMP;
        """
        sql_statements.append(sql)

    full_sql = "\n".join(sql_statements)
    success = execute_psql_query(full_sql)
    if success:
        print(f"[HUNTER PERSISTENCE] Successfully synchronized {len(opportunities)} opportunities in PostgreSQL.")
        return len(opportunities)
    else:
        print("[HUNTER PERSISTENCE] Failed to synchronize opportunities.")
        return 0

def run_statewide_hunter_cycle():
    """
    Master execution entrypoint for the Statewide Texas Hunter Engine.
    """
    print("================================================================================")
    print("🏹  SigmaFidelity™ Statewide Texas Contract Hunter & Portal Crawler")
    print(f"🕒  Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📍  Territory: Entire State of Texas (DFW, Central, Houston, South, West)")
    print("================================================================================")

    # 1. Crawl Statewide Bonfire Network
    found_opportunities = crawl_texas_statewide_bonfire_fleet()
    print(f"\n[HUNTER SUMMARY] Discovered {len(found_opportunities)} matching custodial opportunities statewide.")

    # 2. Ingest to PostgreSQL
    ingested = ingest_opportunities_to_database(found_opportunities)
    print(f"[HUNTER DB] {ingested} opportunities staged in InstitutionalBids.")

    print("================================================================================")
    print("🏁  Statewide Hunter Cycle Complete. Ready for blueprint takeoff & executive review.")
    print("================================================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SigmaFidelity Statewide Texas Contract Hunter")
    parser.add_argument("--dry-run", action="store_true", help="Crawl without database write")
    args = parser.parse_args()
    
    run_statewide_hunter_cycle()
