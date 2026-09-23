"""
SigmaFidelity™ Autonomous Statewide Texas Contract Hunter & Portal Crawler
Standard: HWB-QMS-7.8, HWB-QMS-8.9 & 2026-07-22 Statewide Mandate
Authority: George (Systems Architect & mbB) | Approved: Humberto Dominguez (CEO)

Mission:
Actively hunt, crawl, extract, and ingest public janitorial, custodial, and commercial
facility maintenance contracts across the ENTIRE STATE OF TEXAS:
- Dallas-Fort Worth Metroplex (Dallas, Fort Worth, Arlington, Plano, Collin, NTTA)
- IonWave Metroplex & ISD Fleet (Denton, Garland, Carrollton, Mansfield ISD, Midlothian, Plano, Irving)
- Independent School Districts (Dallas ISD, Austin ISD, Lewisville ISD, Denton ISD, Plano ISD, Frisco ISD, Mansfield ISD, Richardson ISD, Allen ISD, Keller ISD, Arlington ISD)
- Central Texas (Austin, Travis County, Williamson County, Round Rock, Waco)
- Greater Houston (City of Houston, Harris County, Fort Bend County, Brazoria County, Galveston)
- South Texas (San Antonio, Bexar County, Corpus Christi, Rio Grande Valley)
- West & North Texas (Midland-Odessa, Lubbock, Amarillo, El Paso)
- Texas Higher Education Systems (UT System, UT Dallas)

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
from pathlib import Path
from dotenv import load_dotenv

# Load Institutional Secrets
load_dotenv('.env')

DB_URL = os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db')

# Verified Statewide Texas Bonfire Portal Fleet (17 High-Volume Hubs)
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
        "agency_name": "Dallas Independent School District (Dallas ISD)",
        "region": "DFW Metroplex / Dallas",
        "url": "https://dallasisd.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "Dallas ISD Bonfire"
    },
    {
        "agency_name": "City of McKinney",
        "region": "DFW / Collin County (HWB HQ)",
        "url": "https://mckinneytexas.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "City of McKinney Bonfire"
    },
    {
        "agency_name": "City of Frisco",
        "region": "DFW / Collin & Denton",
        "url": "https://friscotexas.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "City of Frisco Bonfire"
    },
    {
        "agency_name": "City of Richardson",
        "region": "DFW / Dallas & Collin",
        "url": "https://cor.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "City of Richardson Bonfire"
    },
    {
        "agency_name": "Harris County (Greater Houston)",
        "region": "Houston Gulf Coast",
        "url": "https://harriscountytx.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "Harris County Bonfire"
    },
    {
        "agency_name": "Fort Bend County",
        "region": "Houston Metro / Sugar Land",
        "url": "https://fortbendcountytx.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "Fort Bend County Bonfire"
    },
    {
        "agency_name": "Brazoria County",
        "region": "Houston Gulf Coast / Pearland",
        "url": "https://brazoriacounty.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "Brazoria County Bonfire"
    },
    {
        "agency_name": "City of San Antonio",
        "region": "South Texas / San Antonio",
        "url": "https://sanantonio.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "City of San Antonio Bonfire"
    },
    {
        "agency_name": "Bexar County",
        "region": "South Texas / San Antonio",
        "url": "https://bexar.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "Bexar County Bonfire"
    },
    {
        "agency_name": "City of Round Rock",
        "region": "Central Texas / Austin Metro",
        "url": "https://roundrocktexas.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "City of Round Rock Bonfire"
    },
    {
        "agency_name": "Austin Independent School District",
        "region": "Central Texas / Austin",
        "url": "https://austinisd.bonfirehub.com/portal/?tab=openOpportunities",
        "portal_name": "Austin ISD Bonfire"
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

# Verified North Texas & Regional IonWave Portal Fleet (18 Municipal & ISD Portals)
TEXAS_IONWAVE_PORTALS = [
    {
        "agency_name": "City of Denton",
        "region": "DFW / Denton County",
        "url": "https://dentontx.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "City of Denton IonWave"
    },
    {
        "agency_name": "City of Garland",
        "region": "DFW / Dallas County",
        "url": "https://garlandtx.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "City of Garland IonWave"
    },
    {
        "agency_name": "City of Carrollton",
        "region": "DFW / Dallas & Denton",
        "url": "https://carrolltonbids.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "City of Carrollton IonWave"
    },
    {
        "agency_name": "Mansfield Independent School District",
        "region": "DFW / Tarrant & Johnson",
        "url": "https://misd.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "Mansfield ISD IonWave"
    },
    {
        "agency_name": "Central Texas Purchasing Alliance (CTPA) / Midlothian ISD",
        "region": "DFW & Central Texas (30+ ISDs)",
        "url": "https://ctpa.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "CTPA IonWave Alliance"
    },
    {
        "agency_name": "City of Plano",
        "region": "DFW / Collin County",
        "url": "https://planotx.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "City of Plano IonWave"
    },
    {
        "agency_name": "City of Irving",
        "region": "DFW / Dallas County",
        "url": "https://cityofirving.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "City of Irving IonWave"
    },
    {
        "agency_name": "Plano Independent School District",
        "region": "DFW / Collin County",
        "url": "https://pisd.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "Plano ISD IonWave"
    },
    {
        "agency_name": "Frisco Independent School District",
        "region": "DFW / Collin & Denton",
        "url": "https://fisd.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "Frisco ISD IonWave"
    },
    {
        "agency_name": "McKinney Independent School District",
        "region": "DFW / Collin County",
        "url": "https://mckinneyisd.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "McKinney ISD IonWave"
    },
    {
        "agency_name": "Lewisville Independent School District",
        "region": "DFW / Denton County",
        "url": "https://lisd.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "Lewisville ISD IonWave"
    },
    {
        "agency_name": "Denton Independent School District",
        "region": "DFW / Denton County",
        "url": "https://dentonisd.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "Denton ISD IonWave"
    },
    {
        "agency_name": "Richardson Independent School District",
        "region": "DFW / Dallas County",
        "url": "https://risd.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "Richardson ISD IonWave"
    },
    {
        "agency_name": "Allen Independent School District",
        "region": "DFW / Collin County",
        "url": "https://allenisd.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "Allen ISD IonWave"
    },
    {
        "agency_name": "Coppell Independent School District",
        "region": "DFW / Dallas County",
        "url": "https://coppellisd.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "Coppell ISD IonWave"
    },
    {
        "agency_name": "Keller Independent School District",
        "region": "DFW / Tarrant County",
        "url": "https://kellerisd.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "Keller ISD IonWave"
    },
    {
        "agency_name": "Arlington Independent School District",
        "region": "DFW / Tarrant County",
        "url": "https://aisd.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "Arlington ISD IonWave"
    },
    {
        "agency_name": "Collin County Government",
        "region": "DFW / Collin County",
        "url": "https://collincountytx.ionwave.net/SourcingEvents.aspx?SourceType=1",
        "portal_name": "Collin County IonWave"
    }
]

# Statewide Search Filters & Precision Vocabulary
TARGET_KEYWORDS = [
    'janitorial', 'custodial', 'day porter', 'porter services',
    'floor care', 'carpet extraction', 'carpet cleaning',
    'sanitization', 'disinfection', 'window washing', 'pressure wash',
    'power wash', 'facility maintenance', 'facilities maintenance',
    'terminal cleaning', 'post-construction clean', 'restroom cleaning',
    'building cleaning', 'office cleaning', 'custodial supplies'
]

# Industrial Disqualification Filter (Prevents False Positives from Public Works/Machinery)
NEGATIVE_KEYWORDS = [
    'sewer', 'culvert', 'grease trap', 'fleet', 'vehicle', 'truck',
    'street sweeper', 'hvac duct', 'duct cleaning', 'heavy equipment',
    'parts only', 'stormwater', 'catch basin', 'dry cleaner',
    'laundry service', 'water reclamation', 'wastewater', 'pipe cleaning'
]

def is_custodial_opportunity(title: str, description: str = "") -> bool:
    """
    Evaluates whether a solicitation represents commercial custodial/janitorial work.
    Applies strict industrial negative filtering to eliminate municipal public works machinery.
    """
    combined = f"{title} {description}".lower()

    # 1. Industrial Disqualification Check
    for neg in NEGATIVE_KEYWORDS:
        if re.search(r'\b' + re.escape(neg) + r'\b', combined):
            return False

    # 2. Scope Inclusion Check
    for pos in TARGET_KEYWORDS:
        if pos in combined:
            return True

    return False

def execute_psql_query(sql: str) -> bool:
    """Executes SQL via docker exec or direct psycopg2 connection."""
    # First try direct psycopg2 if running inside container
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        conn.close()
        return True
    except Exception:
        pass

    # Fallback to docker exec on host
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
        else:
            print(f"[HUNTER DB ERROR] docker exec stderr: {proc.stderr}")
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
    
    print(f"[HUNTER BONFIRE] Scouting {agency_name} ({region})...")
    opportunities = []

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=25000)
            except Exception:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    time.sleep(3)
                except Exception as e:
                    print(f"[HUNTER BONFIRE] Navigation timeout for {agency_name}: {e}")
                    browser.close()
                    return []

            try:
                page.wait_for_selector('table tbody tr', timeout=6000)
            except Exception:
                print(f"[HUNTER BONFIRE] No active table rows found for {agency_name}.")
                browser.close()
                return []

            rows = page.query_selector_all('table tbody tr')
            print(f"[HUNTER BONFIRE] Found {len(rows)} raw listings on {agency_name} portal.")

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
                
                link_el = r.query_selector('a[href*="/opportunities/"]')
                opp_link = ""
                if link_el:
                    href = link_el.get_attribute('href')
                    if href:
                        opp_link = href if href.startswith('http') else f"https://{portal_info['url'].split('/')[2]}{href}"

                if is_custodial_opportunity(title):
                    print(f"🎯 [HUNTER HIT - BONFIRE] Matched Janitorial in {region}: [{ref_num}] {title} (Closes: {close_date})")
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
        print(f"[HUNTER BONFIRE] Error scouting {agency_name}: {e}")

    return opportunities

def crawl_ionwave_portal(portal_info: Dict[str, str], headless: bool = True) -> List[Dict[str, Any]]:
    """
    Crawls an IonWave electronic procurement portal (eBid) using Playwright.
    Extracts live open sourcing events from Telerik RadGrid structures.
    """
    agency_name = portal_info["agency_name"]
    url = portal_info["url"]
    region = portal_info["region"]
    portal_name = portal_info["portal_name"]
    
    print(f"[HUNTER IONWAVE] Scouting {agency_name} ({region})...")
    opportunities = []

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception as e:
                print(f"[HUNTER IONWAVE] Navigation timeout for {agency_name}: {e}")
                browser.close()
                return []

            time.sleep(2)  # RadGrid AJAX stabilization
            rows = page.query_selector_all('tr.rgRow, tr.rgAltRow')
            print(f"[HUNTER IONWAVE] Found {len(rows)} raw sourcing events on {agency_name} portal.")

            for r in rows:
                cells = r.query_selector_all('td')
                if len(cells) < 4:
                    continue

                ref_num = cells[1].inner_text().strip()
                title = cells[2].inner_text().strip()
                bid_type = cells[3].inner_text().strip() if len(cells) > 3 else "RFP"
                close_date = cells[6].inner_text().strip() if len(cells) > 6 else ""

                link_el = r.query_selector('a[href*="SourcingEventDetail.aspx"]')
                opp_link = ""
                if link_el:
                    href = link_el.get_attribute('href')
                    if href:
                        opp_link = href if href.startswith('http') else f"https://{url.split('/')[2]}/{href}"

                if is_custodial_opportunity(title):
                    print(f"🎯 [HUNTER HIT - IONWAVE] Matched Janitorial in {region}: [{ref_num}] {title} (Closes: {close_date})")
                    opportunities.append({
                        "solicitation_number": ref_num or f"IONWAVE-{abs(hash(title)) % 1000000}",
                        "title": title,
                        "agency_name": agency_name,
                        "region": region,
                        "portal_name": portal_name,
                        "status_badge": "Open Sourcing Event",
                        "close_date_raw": close_date,
                        "rfp_url": opp_link or url,
                        "scouted_date": datetime.datetime.now().isoformat()
                    })

            browser.close()
    except Exception as e:
        print(f"[HUNTER IONWAVE] Error scouting {agency_name}: {e}")

    return opportunities

def clean_database_false_positives():
    """
    Cleans up any historically ingested records that fail the negative keyword filter.
    Example: 'RFP Sewer Cleaning Equipment' (Fort Worth #17).
    """
    cleanup_sql = """
    DELETE FROM "InstitutionalBids"
    WHERE title ILIKE '%sewer%'
       OR title ILIKE '%culvert%'
       OR title ILIKE '%grease trap%'
       OR title ILIKE '%street sweeper%'
       OR title ILIKE '%heavy equipment%';
    """
    execute_psql_query(cleanup_sql)

def ingest_opportunities_to_database(opportunities: List[Dict[str, Any]]) -> int:
    """
    Ingests newly discovered Texas statewide opportunities into PostgreSQL InstitutionalBids.
    """
    # Clean up any legacy false positives
    clean_database_false_positives()

    if not opportunities:
        print("[HUNTER] No new custodial opportunities matched in this cycle.")
        return 0

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
            notes = EXCLUDED.notes,
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

def harvest_solicitation_attachments(opp: Dict[str, Any], project_root: Optional[Any] = None) -> List[str]:
    """
    Creates institutional quote workspace and attempts attachment harvesting.
    Triggers solicitation_scope_parser on downloaded RFP specifications.
    """
    from pathlib import Path
    import re
    
    curr = Path(__file__).resolve().parent
    root = project_root or (curr.parent if curr.name == "scripts" else curr.parent.parent)
    
    agency_clean = re.sub(r'[^A-Za-z0-9]', '-', opp.get("agency_name", "TEXAS-AGENCY")).strip('-').upper()[:25]
    sol_clean = re.sub(r'[^A-Za-z0-9]', '-', opp.get("solicitation_number", "BID")).strip('-').upper()[:25]
    
    save_dir = root / "HWB-COMPANY" / "HWB-QUOTES" / f"{agency_clean}_{sol_clean}"
    save_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_file = save_dir / "PORTAL_STAGING_MANIFEST.json"
    manifest_data = {
        "solicitation_number": opp.get("solicitation_number"),
        "title": opp.get("title"),
        "agency_name": opp.get("agency_name"),
        "region": opp.get("region"),
        "portal_name": opp.get("portal_name"),
        "rfp_url": opp.get("rfp_url"),
        "close_date": opp.get("close_date_raw"),
        "scouted_date": opp.get("scouted_date"),
        "staging_path": str(save_dir),
        "harvest_status": "Staging Directory Created / Ready for Scope Takeoff"
    }
    with open(manifest_file, "w") as f:
        json.dump(manifest_data, f, indent=2)
        
    downloaded_files = []
    rfp_url = opp.get("rfp_url", "")
    
    if any(ext in rfp_url.lower() for ext in [".pdf", ".doc", ".xlsx"]):
        try:
            import requests
            fname = rfp_url.split("/")[-1].split("?")[0] or "solicitation_spec.pdf"
            target_file = save_dir / fname
            resp = requests.get(rfp_url, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(target_file, "wb") as f:
                    f.write(resp.content)
                downloaded_files.append(str(target_file))
                print(f"[HARVESTER] Downloaded primary document: {fname}")
        except Exception as e:
            print(f"[HARVESTER] Direct download failed for {rfp_url}: {e}")

    for pdf in save_dir.glob("*.pdf"):
        if str(pdf) not in downloaded_files:
            downloaded_files.append(str(pdf))

    if downloaded_files:
        try:
            import sys
            parser_script = root / "scripts" / "solicitation_scope_parser.py"
            if not parser_script.exists():
                parser_script = root / "HWB-COMPANY" / "HWB-IT" / "HWB-IT-WEBSITE" / "scripts" / "solicitation_scope_parser.py"
            for pdf_path in downloaded_files:
                subprocess.run([sys.executable, str(parser_script), "--file", pdf_path], check=False)
        except Exception as e:
            print(f"[HARVESTER] Scope parser trigger failed: {e}")

    return downloaded_files

def run_statewide_hunter_cycle(portal_filter: str = "all", harvest_only: bool = False):
    """
    Master execution entrypoint for the Statewide Texas Hunter Engine.
    Crawls both Bonfire (17 hubs) and IonWave (18 portals) across Texas.
    Harvests attachments and triggers autonomous scope takeoff parsing.
    """
    print("================================================================================")
    print("🏹  SigmaFidelity™ Statewide Texas Contract Hunter & Proposal Factory")
    print(f"🕒  Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📍  Territory: Entire State of Texas (DFW, Central, Houston, South, West, ISDs)")
    print("================================================================================")

    all_opportunities = []

    if not harvest_only:
        # 1. Crawl Bonfire Network
        if portal_filter in ["all", "bonfire"]:
            print(f"\n--- Phase 1: Scouting Texas Bonfire Network ({len(TEXAS_BONFIRE_PORTALS)} Portals) ---")
            for portal in TEXAS_BONFIRE_PORTALS:
                opps = crawl_bonfire_portal(portal)
                all_opportunities.extend(opps)
                time.sleep(1.5)  # Polite pause between Bonfire hubs

        # 2. Crawl IonWave Network (DFW Municipalities & ISDs)
        if portal_filter in ["all", "ionwave"]:
            print(f"\n--- Phase 2: Scouting Texas IonWave Network ({len(TEXAS_IONWAVE_PORTALS)} Portals) ---")
            for portal in TEXAS_IONWAVE_PORTALS:
                opps = crawl_ionwave_portal(portal)
                all_opportunities.extend(opps)
                time.sleep(2.0)  # Polite pause between IonWave endpoints

        print(f"\n[HUNTER SUMMARY] Discovered {len(all_opportunities)} matching custodial opportunities statewide.")

        # 3. Ingest to PostgreSQL
        ingested = ingest_opportunities_to_database(all_opportunities)
        print(f"[HUNTER DB] {ingested} opportunities staged in InstitutionalBids.")

    # 4. Phase 3: Harvest Attachments & Execute Scope Parsing
    print(f"\n--- Phase 3: Automated Attachment Harvesting & Scope Takeoff Parsing ---")
    for opp in all_opportunities:
        harvest_solicitation_attachments(opp)

    # 5. Full Repository Scope Takeoff Synchronization
    print(f"\n--- Phase 4: Full Institutional Repository Takeoff Synchronization ---")
    try:
        import sys
        root = Path(__file__).resolve().parent.parent if Path(__file__).resolve().parent.name == "scripts" else Path(__file__).resolve().parent
        parser_script = root / "scripts" / "solicitation_scope_parser.py"
        subprocess.run([sys.executable, str(parser_script), "--sync-all"], check=False)
    except Exception as e:
        print(f"[HUNTER SUMMARY] Scope synchronizer trigger failed: {e}")

    print("================================================================================")
    print("🏁  Statewide Hunter & Proposal Factory Cycle Complete.")
    print("================================================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SigmaFidelity Statewide Texas Contract Hunter")
    parser.add_argument("--portal", choices=["all", "bonfire", "ionwave"], default="all", help="Target portal network")
    parser.add_argument("--harvest-only", action="store_true", help="Skip crawling and execute harvesting/sync on existing records")
    args = parser.parse_args()
    
    run_statewide_hunter_cycle(portal_filter=args.portal, harvest_only=args.harvest_only)
