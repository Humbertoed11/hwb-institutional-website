import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def setup_accountability_db():
    print("--- George Bytes: Initiating Accountability Brain Table Creation ---")
    
    # Define 100 detailed accountability responsibilities
    lobes_distribution = [
        # L1 City Brain (11 responsibilities)
        ("L1 City Brain", "Zoning Compliance", "Validate municipal zoning shapefiles for Dallas and Decatur against raw GIS sources.", "Compare boundary coordinates with official shapefiles", "Weekly"),
        ("L1 City Brain", "City Council Scraper", "Assert that city council vote scraping schedules are active and successfully executed.", "Check council meeting agenda extraction logs", "Daily"),
        ("L1 City Brain", "Permit Map Integrity", "Audit the accuracy of new building permit plot points against municipal address indexes.", "Verify parcel address joins with permit logs", "Weekly"),
        ("L1 City Brain", "Historic District Rules", "Verify that historical district overlay parameters match local heritage preservation codes.", "Check historic overlay parameters against city codes", "Monthly"),
        ("L1 City Brain", "Zoning Setbacks", "Ensure setback boundary rules match municipal code limits for multi-family residential zoning.", "Validate setback logic calculations", "Monthly"),
        ("L1 City Brain", "Building Height Caps", "Verify height limitation rules for all target parcel zones are correctly indexed.", "Cross-reference height cap parameters with city ordinances", "Monthly"),
        ("L1 City Brain", "Parking Requirements", "Confirm minimum parking ratios for commercial and retail zones reflect updated city bylaws.", "Verify parking space calculators", "Monthly"),
        ("L1 City Brain", "School District Boundaries", "Ensure school district zoning maps match official TEA (Texas Education Agency) records.", "Compare district boundaries with TEA shapefiles", "Quarterly"),
        ("L1 City Brain", "Variance Tracking", "Log municipal zoning variance approvals and update the exception database.", "Check zoning variance application logs", "Weekly"),
        ("L1 City Brain", "Land Use Maps", "Verify current land use maps align with actual county appraisal district codes.", "Join land use categories with appraisal databases", "Weekly"),
        ("L1 City Brain", "Zoning Penalties", "Identify zoning infraction logs and map potential delay penalties to active parcels.", "Scan county infraction registries", "Weekly"),

        # L2 TxDOT Brain (11 responsibilities)
        ("L2 TxDOT Brain", "Lane Capacity", "Verify lane capacities and freeway transit volumes match latest TxDOT annual highway logs.", "Check TxDOT traffic count database API integration", "Monthly"),
        ("L2 TxDOT Brain", "Speed Log Freshness", "Assert speed logs from traffic monitors are updated in real-time without latency gaps.", "Check average traffic speed API response timestamp", "Daily"),
        ("L2 TxDOT Brain", "Corridor Indexes", "Audit shipping corridor traffic congestion indexes for prime logistics hubs.", "Calculate daily commute time variance", "Daily"),
        ("L2 TxDOT Brain", "Road Repair Logs", "Scan highway maintenance schedules to calculate shipping delay risk metrics.", "Scrape TxDOT construction schedule RSS feed", "Weekly"),
        ("L2 TxDOT Brain", "Bridge Load Limits", "Verify maximum bridge axle weight limits along key logistics egress routes.", "Cross-reference load limits with county shipping codes", "Monthly"),
        ("L2 TxDOT Brain", "Highway Exit Mapping", "Audit exit ramp locations and freeway accessibility metrics for warehouse targets.", "Perform GIS line intersection validation", "Monthly"),
        ("L2 TxDOT Brain", "Commute Calculations", "Verify distance-decay calculations used for commuter access scores are mathematically correct.", "Run commute algorithm tests", "Weekly"),
        ("L2 TxDOT Brain", "Public Transit Stops", "Index local bus and rail stops to calculate pedestrian transit accessibility.", "Count transit stations within a 500m radius", "Monthly"),
        ("L2 TxDOT Brain", "Egress Obstructions", "Identify physical barriers or medians that block left-turn egress from target sites.", "Check roadway median GIS layers", "Monthly"),
        ("L2 TxDOT Brain", "Truck Route Restrictions", "Audit heavy truck transit restriction zones along municipal roads.", "Verify restriction overlays with local transport departments", "Monthly"),
        ("L2 TxDOT Brain", "Traffic Signal Delays", "Validate average traffic light wait times at major intersections near target hubs.", "Check traffic flow latency sensors", "Weekly"),

        # L3 Power Brain (11 responsibilities)
        ("L3 Power Brain", "Substation Capacities", "Confirm substation power reserves match local utility company capacity charts.", "Query utility load reports", "Monthly"),
        ("L3 Power Brain", "Fiber Line Routing", "Audit high-speed fiber line proximity metrics along main logistics roadways.", "Join parcel maps with fiber routing tables", "Monthly"),
        ("L3 Power Brain", "Utility Easements", "Verify utility easement setbacks are subtracted from the buildable area of target sites.", "Validate easement GIS footprints", "Monthly"),
        ("L3 Power Brain", "Gas Pipeline Proximity", "Scan high-pressure natural gas lines to enforce pipeline safety setbacks.", "Check gas utility maps", "Monthly"),
        ("L3 Power Brain", "Grid Outage Logs", "Scrape grid stability reports to compute average annual downtime metrics.", "Analyze grid event history data", "Weekly"),
        ("L3 Power Brain", "Battery Storage Rules", "Enforce battery backup rules for commercial sites based on grid load protocols.", "Verify battery storage compliance checks", "Monthly"),
        ("L3 Power Brain", "Energy Rate Feeds", "Verify commercial electricity rate feeds are updated dynamically from grid operators.", "Check utility tariff API responses", "Daily"),
        ("L3 Power Brain", "Water Hookup Access", "Verify public water mains are adjacent to target sites to prevent well-drilling costs.", "Check municipal water utility records", "Monthly"),
        ("L3 Power Brain", "Sewer Line Capacity", "Audit wastewater flow capacity limits for high-density multi-family zones.", "Check city sewer flow sensor data", "Monthly"),
        ("L3 Power Brain", "Transformer Health", "Index transformer failure events to calculate local grid failure risks.", "Analyze transformer maintenance records", "Quarterly"),
        ("L3 Power Brain", "Green Energy Options", "Check availability of solar or wind grid offsets for sustainable builds.", "Scrape green energy options database", "Monthly"),

        # L4 Legal/Env Brain (11 responsibilities)
        ("L4 Legal/Env Brain", "Title History Audits", "Verify title records show clear history with no outstanding ownership disputes.", "Run automated database query for unresolved titles", "Weekly"),
        ("L4 Legal/Env Brain", "Swelling Clay Index", "Calculate swelling clay soil risk values based on regional geotech surveys.", "Join parcel coordinates with USDA soil databases", "Monthly"),
        ("L4 Legal/Env Brain", "Wetland Overlaps", "Assert that wetland boundaries from environmental maps do not clip buildable zones.", "Intersect parcel shape with USFWS wetland maps", "Monthly"),
        ("L4 Legal/Env Brain", "Deed Restrictions", "Audit deed restrictions to flag restrictions on building height or density.", "Scrape county deed registry data", "Weekly"),
        ("L4 Legal/Env Brain", "EPA Site Proximity", "Check EPA registries to calculate distance from registered toxic cleanup zones.", "Verify proximity to EPA Superfund targets", "Monthly"),
        ("L4 Legal/Env Brain", "Flood Plain Mapping", "Verify 100-year flood plain boundaries match FEMA flood hazard maps.", "Compare flood layers with FEMA GIS updates", "Monthly"),
        ("L4 Legal/Env Brain", "Endangered Species Habitats", "Check state wildlife registries to flag target land clipping protected habitats.", "Cross-reference with TPWD species registries", "Monthly"),
        ("L4 Legal/Env Brain", "Oil and Gas Lease Rights", "Audit active subsurface mineral leases that could block surface rights.", "Check Texas Railroad Commission mineral lease logs", "Monthly"),
        ("L4 Legal/Env Brain", "Soil Pier Calculations", "Check if local soil profile requires deep pier construction methods.", "Analyze soil bearing capacity data", "Quarterly"),
        ("L4 Legal/Env Brain", "Noise Pollution Zones", "Verify airport noise contour levels do not overlap residential parcel targets.", "Check airport noise contour overlays", "Monthly"),
        ("L4 Legal/Env Brain", "Historical Landmarks", "Ensure site boundaries do not clip national historical landmark zones.", "Cross-reference with landmark database", "Monthly"),

        # L5 Ranger Brain (11 responsibilities)
        ("L5 Ranger Brain", "Override Audit Trail", "Verify manual override logs track user credentials, reasons, and timestamps.", "Check HEX_Telemetry override registries", "Daily"),
        ("L5 Ranger Brain", "Mobile App Uplink", "Assert ranger field audit data is uploaded and synced to main app servers.", "Check mobile sync logs", "Daily"),
        ("L5 Ranger Brain", "Photo Resolution Audit", "Verify ground-truth photos uploaded by field agents meet resolution guidelines.", "Check file size and dimensions of uploads", "Weekly"),
        ("L5 Ranger Brain", "Climate Hazard Layers", "Verify tornado, freeze, and wind damage layers match latest NOAA datasets.", "Scrape NOAA event records", "Monthly"),
        ("L5 Ranger Brain", "Fire Station Proximity", "Audit fire station distance calculations to ensure accurate insurance risk scoring.", "Calculate travel distance to nearest fire station", "Monthly"),
        ("L5 Ranger Brain", "Crime Rate Indexes", "Verify neighborhood safety metrics align with recent local law enforcement reports.", "Scrape city police data", "Weekly"),
        ("L5 Ranger Brain", "Wildfire Risk Zones", "Check land location against state forest service wildfire risk hazard maps.", "Compare maps with Texas Forest Service layers", "Monthly"),
        ("L5 Ranger Brain", "Drone Survey Ingestion", "Verify coordinates of drone survey flights match the land grid.", "Check drone flight log files", "Weekly"),
        ("L5 Ranger Brain", "Ranger Route Audits", "Track ranger travel logs to check schedule completion of target parcels.", "Analyze ranger GPS travel data", "Daily"),
        ("L5 Ranger Brain", "Land Boundary Discrepancies", "Identify differences between visual fence lines and legal plat boundaries.", "Compare satellite maps with legal boundaries", "Weekly"),
        ("L5 Ranger Brain", "Hazardous Tree Count", "Count damaged trees near planned building envelopes using visual surveys.", "Check tree survey logs", "Monthly"),

        # L6 Pulse Brain (11 responsibilities)
        ("L6 Pulse Brain", "Mood Index Scraper", "Assert that social media sentiment scraper routines are online and returning data.", "Check forum crawler success logs", "Daily"),
        ("L6 Pulse Brain", "Town Meeting Schedule", "Ensure town meeting calendars are scraped to flag upcoming public debates.", "Scrape city planning council portals", "Daily"),
        ("L6 Pulse Brain", "Local News Scrapers", "Audit local news feeds to flag community opposition to high-density builds.", "Scan news feeds for planning dispute keywords", "Daily"),
        ("L6 Pulse Brain", "Public Sentiment Index", "Verify local forum community sentiment scores are mathematically normalized.", "Verify sentiment formula output", "Weekly"),
        ("L6 Pulse Brain", "Competitor Activity Radar", "Audit competitor parcel watchlist activity to identify market trends.", "Check competitor search frequency logs", "Weekly"),
        ("L6 Pulse Brain", "NIMBY Group Monitoring", "Scan local neighborhood groups to flag organized opposition to development.", "Check facebook and nextdoor group scrapers", "Daily"),
        ("L6 Pulse Brain", "Retail Tenant Desirability", "Verify local resident requests for new retailers match target lists.", "Analyze retail survey logs", "Weekly"),
        ("L6 Pulse Brain", "Demographic Shifts", "Audit annual census changes to calculate long-term neighborhood income trends.", "Read census updates", "Annual"),
        ("L6 Pulse Brain", "Public Space Usage", "Audit park and sidewalk foot traffic counts using public camera sensors.", "Check pedestrian count data logs", "Weekly"),
        ("L6 Pulse Brain", "Community Benefit Deals", "Verify commitments made to local neighborhood associations are logged.", "Check community benefit agreements", "Monthly"),
        ("L6 Pulse Brain", "Local Election Outcomes", "Track city council election outcomes to predict political shifts in zoning.", "Update city council voter profiles", "Quarterly"),

        # L7 Finance Brain (11 responsibilities)
        ("L7 Finance Brain", "LTV Calculations", "Verify Loan-to-Value underwriting formulas match bank risk policies.", "Run calculation assertions on loan algorithms", "Weekly"),
        ("L7 Finance Brain", "Interest Rate Feeds", "Assert that mortgage and commercial interest rate feeds are current.", "Check treasury and bank API response dates", "Daily"),
        ("L7 Finance Brain", "Construction Cost Index", "Audit construction materials cost index feeds for accurate pro-forma budgets.", "Verify Turner construction index data", "Monthly"),
        ("L7 Finance Brain", "Appraisal CAD Values", "Validate CAD (County Appraisal District) land valuations against transaction records.", "Query CAD database table", "Weekly"),
        ("L7 Finance Brain", "DSCR Verification", "Ensure Debt Service Coverage Ratio calculators enforce safety thresholds.", "Verify DSCR logic calculations", "Weekly"),
        ("L7 Finance Brain", "Tax Rate Variations", "Verify property tax rates for all municipal jurisdictions are updated.", "Cross-reference municipal tax schedules", "Monthly"),
        ("L7 Finance Brain", "Cash Flow Forecasts", "Assert discount rate variables reflect actual cost of capital assumptions.", "Run cash flow logic tests", "Weekly"),
        ("L7 Finance Brain", "Market Value Comps", "Ensure transaction records used for pricing comparisons are under 180 days old.", "Verify appraisal comps dates", "Weekly"),
        ("L7 Finance Brain", "Impact Fee Calculations", "Verify municipal development impact fee estimates match city schedules.", "Compare estimated impact fees with city rates", "Monthly"),
        ("L7 Finance Brain", "Insurance Premium Indexes", "Verify insurance cost estimates reflect current regional catastrophe data.", "Check insurance index API response", "Monthly"),
        ("L7 Finance Brain", "Capital Yield Benchmarks", "Update regional capitalization rate averages by commercial property type.", "Check cap rate averages database", "Weekly"),

        # L8 Inference Brain (12 responsibilities)
        ("L8 Inference Brain", "Reasoning Telemetry", "Ensure abductive, inductive, and deductive inference steps are logged.", "Check HEX_Telemetry inference logs", "Daily"),
        ("L8 Inference Brain", "Anomaly Alerts", "Assert that abductive anomalies are logged when zoning changes without price rises.", "Verify anomaly alert criteria logic", "Daily"),
        ("L8 Inference Brain", "Daily Sync Completeness", "Verify the daily inference sync script completes without database timeouts.", "Check daily sync task logs", "Daily"),
        ("L8 Inference Brain", "Confidence Index Accuracy", "Ensure confidence score formulas do not generate values outside [0.0, 1.0].", "Run bounds tests on scoring code", "Weekly"),
        ("L8 Inference Brain", "Deduction Filter Integrity", "Verify deductive filtering does not drop viable development targets.", "Check filters on known positive control sites", "Weekly"),
        ("L8 Inference Brain", "Inductive Price Benchmarks", "Verify inductive algorithms recalculate land value trends correctly.", "Verify inductive calculation logic", "Weekly"),
        ("L8 Inference Brain", "Double Inference Safeguards", "Prevent multiple inference loops from creating duplicate lead entries.", "Check database unique constraints on leads", "Daily"),
        ("L8 Inference Brain", "Scoring Weight Drift", "Check scoring parameters to ensure weights sum to exactly 1.0.", "Sum system weight parameters", "Weekly"),
        ("L8 Inference Brain", "Abduction Trigger Logic", "Validate abduction trigger conditions when social interest spikes.", "Check trigger logic checks", "Weekly"),
        ("L8 Inference Brain", "Historical Compares", "Compare current inference states with previous days to verify direction.", "Calculate direction shifts", "Daily"),
        ("L8 Inference Brain", "System Reset Checks", "Ensure inference algorithms restore state correctly after container restarts.", "Check system state restore logs", "Daily"),
        ("L8 Inference Brain", "Inference Run Times", "Track query execution times to keep inference runs under 180 seconds.", "Analyze sync log runtimes", "Daily"),

        # L9 Audit/Accountability Brain (11 responsibilities)
        ("L9 Audit/Accountability Brain", "Model Drift Audits", "Audit Lobe 8 prediction models against final property acquisition prices.", "Compute mean squared error of predictions", "Monthly"),
        ("L9 Audit/Accountability Brain", "Override Logging Audits", "Scan Lobe 5 logs to flag unauthorized human score adjustments.", "Compare audits log with override lists", "Daily"),
        ("L9 Audit/Accountability Brain", "Data Freshness Monitor", "Enforce warning flags when raw databases have not updated in 90 days.", "Verify database last_updated timestamps", "Daily"),
        ("L9 Audit/Accountability Brain", "Sentinel Backup Validation", "Verify database recovery backups complete successfully every hour.", "Check backup script output logs", "Daily"),
        ("L9 Audit/Accountability Brain", "ISO Compliance Checks", "Assert document metadata and timestamps match disk files (ISO 7.5.3).", "Verify realign_timestamps.py output", "Daily"),
        ("L9 Audit/Accountability Brain", "Error Event Hardening", "Verify code exceptions are logged in the Knowledge Scars database.", "Check HEX_KnowledgeScars error codes", "Daily"),
        ("L9 Audit/Accountability Brain", "Access Control Audits", "Scan user access logs to check for unauthorized administrative actions.", "Audit HEX_Telemetry user login paths", "Daily"),
        ("L9 Audit/Accountability Brain", "Disk Usage Warnings", "Audit disk space limits to prevent log storage runaway.", "Verify system disk usage thresholds", "Hourly"),
        ("L9 Audit/Accountability Brain", "Token Saver Validation", "Verify system prompts comply with token limit guidelines.", "Monitor prompt token count averages", "Daily"),
        ("L9 Audit/Accountability Brain", "Uptime Monitoring Loop", "Run active ping tests to ensure all server endpoints return 200 OK.", "Perform HTTP status endpoint tests", "Daily"),
        ("L9 Audit/Accountability Brain", "QMS Master Index Parity", "Verify all manuals in the static directory are in qms_index.json.", "Run index validation checks", "Daily")
    ]

    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # 1. Create the Accountability Brain table
        cursor.execute("""
            DROP TABLE IF EXISTS "HEX_AccountabilityBrain";
            CREATE TABLE "HEX_AccountabilityBrain" (
                id SERIAL PRIMARY KEY,
                responsibility_id VARCHAR(50) UNIQUE NOT NULL,
                lobe VARCHAR(50) NOT NULL,
                category VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                verification_method TEXT NOT NULL,
                target_frequency VARCHAR(50) NOT NULL,
                last_run TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'PENDING'
            );
        """)
        print("SUCCESS: Table 'HEX_AccountabilityBrain' created successfully.")
        
        # 2. Insert 100 accountability records
        inserted_count = 0
        for i, record in enumerate(lobes_distribution, 1):
            resp_id = f"ACC-{i:03d}"
            lobe, category, description, verification_method, target_frequency = record
            
            cursor.execute("""
                INSERT INTO "HEX_AccountabilityBrain" 
                (responsibility_id, lobe, category, description, verification_method, target_frequency, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'PENDING')
            """, (resp_id, lobe, category, description, verification_method, target_frequency))
            inserted_count += 1
            
        conn.commit()
        conn.close()
        print(f"SUCCESS: Inserted {inserted_count} accountability responsibilities into database.")
    except Exception as e:
        print(f"FAILURE: Failed to set up accountability database. {e}")

if __name__ == '__main__':
    setup_accountability_db()
