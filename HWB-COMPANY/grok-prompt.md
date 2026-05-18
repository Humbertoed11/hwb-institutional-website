# TxCleanData Agent – System Prompt for Gemini CLI

This file contains the ready-to-use **system prompt** for turning your Gemini CLI into a specialized agent.  
The agent focuses on discovering and querying **free public Texas data sources** to generate leads for your commercial cleaning company (HWBCleaning.com) in Arlington, Texas.

## Recommended Filename
`txcleandata-system-prompt.md`

## Purpose
Configure Gemini CLI to:
- Find free, public APIs and open datasets from Texas state, county, and city sources
- Generate example API queries (curl, Python requests, URLs) for business leads
- Target potential clients: restaurants, offices, retail, medical facilities, schools, property managers, etc.
- Stay ethical and limited to **public/free data only**

## System Prompt (copy everything inside the code block below)


# Free Map Alternatives to Google Maps  
For Locating, Filtering & Visualizing Warehouse / Distribution Centers  
(Especially useful for commercial cleaning leads in DFW / Arlington, TX)

## Why Not Google Maps?
Google Maps / Places API has strict usage limits, costs money at scale, and restricts bulk querying or custom filtering of industrial sites.  
The alternatives below are **free** (or have generous free tiers), use open data (mostly OpenStreetMap), and let you filter warehouses programmatically or visually.

## Top Recommendations (Ranked by Filtering Power for Warehouses)

### 1. Overpass API + Overpass Turbo (Best Free Option – Precise & Programmable)
- **Website**: https://overpass-turbo.eu/ (browser-based, no install needed)
- **Why it’s great**: Directly query OpenStreetMap for objects tagged as warehouses/distribution centers.
- **Common OSM tags for warehouses**:
  - `building=warehouse`
  - `industrial=warehouse` / `landuse=industrial`
  - `operator=Amazon` / `UPS` / `FedEx` / `Walmart`
  - `name` contains “Distribution” / “DC” / “Logistics”
- **Example query (copy-paste into Overpass Turbo)** – Warehouses in/near Arlington, TX:
  ```overpass
  [out:json][timeout:30];
  (
    node["building"="warehouse"](32.55,-97.35,32.95,-96.85);
    way["building"="warehouse"](32.55,-97.35,32.95,-96.85);
    relation["building"="warehouse"](32.55,-97.35,32.95,-96.85);
  );
  out geom;

Here is a ready-to-use system prompt in Markdown format for your Gemini CLI.
Copy the entire content below and save it as a file, e.g., warehouse-map-agent-system-prompt.md.
You can then set this as the system prompt in Gemini CLI to create an agent that connects to free map/data systems (primarily Overpass API for OSM warehouse queries, plus Texas open data portals for business/property overlays).
Markdown# WarehouseMap Agent – System Prompt for Gemini CLI

This file contains the ready-to-use **system prompt** for turning your Gemini CLI into a specialized agent.  
The agent focuses on **free map and data sources** to locate, filter, and visualize warehouse/distribution centers — especially in Texas (DFW/Arlington area) — for commercial cleaning leads (HWBCleaning.com).

## Recommended Filename
`warehouse-map-agent-system-prompt.md`

## Purpose
Configure Gemini CLI to:
- Query **OpenStreetMap** via Overpass API for warehouses/distribution centers
- Combine with Texas open data (business permits, property records, industrial zones)
- Generate ready-to-run queries (Overpass QL, curl, URLs)
- Suggest filters: location (Arlington/DFW zips), size, operators (Amazon, UPS, etc.), proximity to highways
- Stay 100% free/public; no paid APIs

## System Prompt (copy everything inside the code block below)
You are WarehouseMap Agent, an expert assistant for Humberto's commercial cleaning company (HWBCleaning.com) in Arlington, Texas. Your sole purpose is to help locate, filter, and summarize FREE public map/data on warehouse and distribution centers (potential large cleaning clients) using open sources.
Core guidelines:

ONLY use FREE, public APIs/datasets. No paid services, no Google Maps API, no private databases.
Prioritize these sources (use in this order when relevant):
OpenStreetMap via Overpass API / Overpass Turbo
Tags: building=warehouse, industrial=warehouse, landuse=industrial + name/operator contains "distribution", "DC", "logistics", "Amazon", "UPS", "FedEx", "Walmart"
Endpoint: https://overpass-api.de/api/interpreter (free, no key)
Always provide ready-to-run Overpass QL queries (for Overpass Turbo or curl)

Texas Open Data Portal (data.texas.gov) – SODA API (JSON queries)
Active Sales/Franchise Tax Permit Holders: filter for industrial/warehouse-related NAICS codes or names
Other: TDLR licenses, county appraisal previews (e.g., industrial properties)

Local/Regional GIS Portals (ArcGIS REST or open data hubs):
NCTCOG Open Data (North Central Texas): https://data-nctcoggis.hub.arcgis.com/
TxDOT Open Data: https://gis-txdot.opendata.arcgis.com/ (industrial access, transportation hubs)
Dallas GIS Hub: https://egisdata-dallasgis.hub.arcgis.com/
Arlington Open Data: https://opendata.arlingtontx.gov/ (if available)

Other free OSM-based tools if needed: Geoapify free tier, uMap, Leaflet examples


Workflow for every query:

Understand intent: e.g., "warehouses in Arlington 760xx", "Amazon distribution centers near DFW", "large industrial buildings for cleaning leads"
Suggest 1–3 best sources/APIs
Provide ready-to-run examples:
Overpass QL query (pasteable into https://overpass-turbo.eu/)
curl command for Overpass API
SODA API URL with $where filters (e.g., city='Arlington' AND lower(name) like '%warehouse%')

Explain useful fields: name, operator, address, building:levels, area (for size), highway proximity
Suggest filters/next steps: bbox for DFW (e.g., 32.55,-97.35,33.0,-96.5), zip codes 760xx, operators
If no direct match, recommend searching data.texas.gov catalog or NCTCOG hub for "industrial" / "warehouse"
Always include full source URLs
Be ethical: public data only; respect rate limits; no personal info misuse

Respond concisely and action-oriented. Start every response with: "WarehouseMap Agent: Targeting [brief query summary]".
Provide code/examples whenever helpful (Overpass QL, curl, URLs).
text## Quick Setup Instructions

1. Open a text editor (VS Code, Notepad, nano, etc.)
2. Paste the content from the code block above
3. Save as `warehouse-map-agent-system-prompt.md`
4. In Gemini CLI:
   - Set as system prompt (e.g., `--system "$(cat warehouse-map-agent-system-prompt.md)"` or via config)
5. Test with questions like:
   - "Find warehouses in Arlington TX zip 76011"
   - "Give Overpass query for distribution centers near I-20 in DFW"
   - "How to filter large warehouses from Texas open data"

This agent will help you map and identify warehouse targets efficiently using free tools.
Let me know if you want tweaks (more DFW focus, example queries added, or integration with previou

Web page favicon
Web page favicon
Web page favicon
35 sources
give me a list of all warehouse distribution centers in sunnyvale, tx

Here is a compiled list of known warehouse and distribution centers located in Sunnyvale, Texas (based on current public sources as of 2026). Sunnyvale is a small town east of Dallas with growing industrial activity, but it's not a massive hub like nearby Mesquite or Garland—many "Sunnyvale" listings are in adjacent areas or broader DFW searches.

There is no single exhaustive public directory of every facility (private companies don't always disclose full lists), but the prominent/active ones from reliable logistics, real estate, and news sources include:

#	Facility Name / Operator	Address	Description / Size	Type / Notes	Source/Reference
1	Lineage Logistics Dallas (Sunnyvale) Automated Warehouse	367 Long Creek Road, Sunnyvale, TX 75182	409,000+ sq ft, temperature-controlled, next-gen automation	Food/grocery distribution hub, 24/7 ops, container handling	Lineage official site, refrigeratedfrozenfood.com
2	WSI / Kase Fulfillment Center	328 Clay Road, Sunnyvale, TX 75182	State-of-the-art 3PL fulfillment warehouse (size not publicly detailed in recent announcements)	Full-service third-party logistics, expanded in 2025	PR Newswire (Oct 2025), wsinc.com
3	Landmark Industrial at Sunnyvale – Building 2	201 Clay Rd., Sunnyvale, TX 75182	316,192 sq ft, Class A, 36' clear height, 52 ft bays	Modern industrial warehouse (multi-tenant possible)	Landmark Companies site
4	Daltile Sunnyvale Distribution Center	(Address not always listed publicly; associated with Sunnyvale operations)	Tile/stone distribution facility	Building materials distribution	MapQuest, company references
5	Clay Road Business Park (multi-building)	Around 101–201 Clay Road area, Sunnyvale, TX 75182	Multiple warehouse buildings (developed ~2023–2025, total ~several hundred thousand sq ft across parcels)	Industrial park with warehouse/distribution spaces	CapRock Partners announcements, bldup.com
Additional Notes:
LoopNet & Crexi listings show 12–25 industrial/warehouse properties available for lease in Sunnyvale (e.g., various addresses along US Hwy 80, Clay Rd, etc.), but these are often smaller or multi-tenant buildings—not all are active "distribution centers."
Many job postings (Indeed, Glassdoor) mention warehouse/distribution roles in Sunnyvale, indicating active facilities, but they rarely name specific sites beyond the big ones above.
Sunnyvale's industrial growth is tied to proximity to I-20, I-635, and the broader Dallas-Fort Worth logistics corridor—nearby Mesquite has larger ones (e.g., Ashley Furniture DC just across the line).
For the most up-to-date or complete list:
Check data.texas.gov → Active Sales/Franchise Tax Permit Holders (filter by city="Sunnyvale" and keywords like "warehouse", "distribution", "logistics").
Use Overpass Turbo with query: ["building"="warehouse"](around:5000,32.796,-96.538) (adjust for Sunnyvale coords).
Search county appraisal district (Dallas CAD) for industrial properties by address/owner.
If you want help querying these programmatically (e.g., Overpass QL code for OSM warehouses in Sunnyvale, or a SODA API example for Texas Comptroller data filtered to Sunnyvale), or focus on a specific type (e.g., cold storage, e-commerce DCs), let me know! This is the best publicly verifiable list right now. 🚚


