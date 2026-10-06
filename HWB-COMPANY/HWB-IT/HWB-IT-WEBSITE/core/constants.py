"""
SigmaFidelity™ Enterprise Constants & Taxonomies
Standard: HWB-QMS-7.6 Enterprise Architecture Standards
"""

FACILITY_TYPES = [
    {"value": "Child Care Center", "label": "Child Care Center"},
    {"value": "Office", "label": "Office Space"},
    {"value": "Medical", "label": "Medical / Clinical"},
    {"value": "Warehouse", "label": "Warehouse / Industrial"},
    {"value": "Automotive", "label": "Automotive / Dealership"},
    {"value": "Retail", "label": "Retail Space"},
    {"value": "Church", "label": "Church / Sanctuary"},
    {"value": "School", "label": "School / Educational"},
    {"value": "Post-Construction", "label": "Post-Construction"},
    {"value": "Other", "label": "Other Commercial"}
]

INDUSTRIES = [
    {"value": "Child Care", "label": "Child Care & Early Learning"},
    {"value": "Automotive", "label": "Automotive Sales & Services"},
    {"value": "Education", "label": "Education & K-12 Academics"},
    {"value": "Corporate / Office", "label": "Corporate & Professional Office"},
    {"value": "Healthcare / Medical", "label": "Healthcare & Medical Clinical"},
    {"value": "Industrial / Logistics", "label": "Industrial & Logistics / Warehouse"},
    {"value": "Retail & Hospitality", "label": "Retail, Wholesale & Hospitality"},
    {"value": "Religious / Nonprofit", "label": "Religious / Places of Worship"},
    {"value": "Construction", "label": "Construction & Post-Finishout"},
    {"value": "Commercial Property", "label": "General Commercial Property"}
]

LEAD_SOURCES = [
    {"value": "Texas CCL API", "label": "Texas CCL API (Active State Feed)"},
    {"value": "Texas Childcare Registry", "label": "Texas Childcare Registry (Master Import)"},
    {"value": "Texas Commercial Registry", "label": "Texas Commercial Registry (B2B Directory)"},
    {"value": "Website Quote Form", "label": "Website Quote Form (Inbound Web)"},
    {"value": "Google", "label": "Google Search / Organic SEO"},
    {"value": "Referral", "label": "Referral / Word-of-Mouth"},
    {"value": "Cold Call", "label": "Outbound Outreach"},
    {"value": "Flyer", "label": "Direct Mail / Flyer"},
    {"value": "Direct Lead", "label": "Direct Inquiry"},
    {"value": "Other", "label": "Other Channel"}
]

PRIORITY_LEVELS = [
    {"value": "Needs Call Now", "label": "🔥 Needs Call Now (Critical)"},
    {"value": "High", "label": "High Priority"},
    {"value": "Follow up soon", "label": "Follow Up Soon (Standard)"},
    {"value": "Just looking", "label": "Just Looking (Low)"},
    {"value": "Normal", "label": "Normal"}
]

# --- Verified Corporate Identity (Single Source of Truth) ---
# Source: Capability Statement 2026 (HWB-COMPANY/HWB-QUOTES/1 hwb-capabiltiy statement-2026--single-sheet.docx)
CORPORATE_INFO = {
    "name": "HWB Cleaning Services LLC",
    "legal_name": "HWB Cleaning Services LLC",
    "short_name": "HWB Cleaning",
    "president": "Mirna Rondinella",
    "ceo": "Humberto Dominguez",
    "tagline": "Proper Training + The Right Tools + Respect for Your Space = The SigmaQuality Clean",
    "mission": "It’s not just about cleaning anymore; It is about the human experience that we all depend upon. We know what to do, how to do it and why we are here.",
    "values": "Integrity, communication, attention to detail are our company values.",
    "address_street": "3342 FM 1827 Ste 8d",
    "address_city": "McKinney",
    "address_state": "TX",
    "address_zip": "75071",
    "address_full": "3342 FM 1827 Ste 8d, McKinney, TX 75071",
    "office_phone": "214-586-0257",
    "office_phone_formatted": "(214)-586-0257",
    "ceo_direct_phone": "(972) 800-7808",
    "official_email": "hdominguez@hwbcleaning.com",
    "sales_email": "sales@hwbcleaning.com",
    "website_url": "https://www.hwbcleaning.com",
    "official_logo_path": "logo_standard.png",
    "official_logo_transparent_path": "img/logo_standard_transparent.png",
    "official_logo_url": "https://www.hwbcleaning.com/static/logo_standard.png",
    "texas_charter_no": "802920409",
    "federal_tax_id": "82-4377459",
    "sales_tax_id": "32005785756",
    "duns": "08-283-0635",
    "cage_sam": "082830635",
    "insurance_policy": "GHF000742",
    "insurance_emr": ".43",
    "insurance_agency": "Insurance Risk Consultants",
    "insurance_agent": "Carlos Aguirre",
    "insurance_agent_phone": "682-667-3863",
    "sic_code": "7349-01 Janitorial Services",
    "naics_code": "561720 Janitorial Services",
    "unspsc_code": "7611 Cleaning & Janitorial S.",
    "service_area": "DFW Metroplex and the entire State of Texas",
    "core_competencies": [
        "Client satisfaction driven",
        "Fast problem resolution",
        "Year round staff training",
        "Cost control",
        "Green cleaning practices",
        "Commercial/industrial safety programs",
        "Technology driven supervision",
        "24/7 cleaning operations"
    ],
    "past_performances": [
        "6,000,000 sq.ft. of commercial/academic/industrial space cleaned",
        "150,000 sq. ft. of strip and wax floor completed",
        "3 academic facility disinfection programs setup",
        "2 Industrial safety department programs created for clients",
        "35 new crews trained/updated on SOP official documents"
    ],
    "differentiators": [
        "Crews hired live within 5 to 10 minutes of client mitigating absentee levels due to weather inclement or travel problems",
        "Personal supervisor assigned to accounts",
        "Use of sustainable products, processes and green programs",
        "We do what we say we are going to do. Period."
    ]
}

# --- SigmaFidelity™ Institutional Module Registry & Micro-Copy Architecture ---
# Standard: HWB-QMS-1.0 & HWB-QMS-7.6
# Standardized Single-Word Titles & 4-Verb Operational Descriptors
MODULE_REGISTRY = {
    "executive": {
        "title": "Command",
        "action_phrase": "Manage team accounts, track performance, review emails, and approve social posts.",
        "sop_reference": "HWB-QMS-1.1",
        "icon": "fas fa-crown"
    },
    "sales_desk": {
        "title": "Cadence",
        "action_phrase": "Call prospective clients, write call notes, book building walkthroughs, and set calendar appointments.",
        "sop_reference": "HWB-CAD-WT-001",
        "icon": "fas fa-phone-volume"
    },
    "leads": {
        "title": "Leads",
        "action_phrase": "Browse the lead pool, view building details, find decision-makers, and assign accounts to call.",
        "sop_reference": "HWB-QMS-11.6",
        "icon": "fas fa-building"
    },
    "accounts": {
        "title": "Clients",
        "action_phrase": "View active clients, check cleaning schedules, send monthly bills, and read customer notes.",
        "sop_reference": "HWB-QMS-8.2",
        "icon": "fas fa-handshake"
    },
    "construction_bids": {
        "title": "Construction",
        "action_phrase": "Check building floor plans, measure room sizes, calculate job costs, and create price quotes.",
        "sop_reference": "HWB-QMS-7.7",
        "icon": "fas fa-hard-hat"
    },
    "general_contractors": {
        "title": "Contractors",
        "action_phrase": "Find general contractors, save site manager phone numbers, track project questions, and review past bids.",
        "sop_reference": "HWB-QMS-7.7",
        "icon": "fas fa-city"
    },
    "institutional_bids": {
        "title": "Institutions",
        "action_phrase": "Find city and school cleaning jobs, check pay requirements, track bid paperwork, and submit price proposals.",
        "sop_reference": "HWB-QMS-11.6",
        "icon": "fas fa-landmark"
    },
    "programs": {
        "title": "Certifications",
        "action_phrase": "Track small business licenses, verify government badges, check program rules, and win special contracts.",
        "sop_reference": "HWB-QMS-11.6",
        "icon": "fas fa-shield-halved"
    },
    "workforce": {
        "title": "Workforce",
        "action_phrase": "Manage cleaning crew members, schedule work shifts, track clock-in times, and review finished cleaning jobs.",
        "sop_reference": "HWB-QMS-8.1",
        "icon": "fas fa-id-card-clip"
    },
    "safety": {
        "title": "Safety",
        "action_phrase": "Log work injuries, check cleaning chemical guides, review safety checklists, and keep workers safe.",
        "sop_reference": "HWB-EHS-001",
        "icon": "fas fa-shield-alt"
    },
    "monitor": {
        "title": "Dispatch",
        "action_phrase": "Send cleaners to buildings, watch work shifts live, check crew locations, and solve job problems.",
        "sop_reference": "HWB-QMS-8.1",
        "icon": "fas fa-clipboard-check"
    },
    "scope": {
        "title": "Scopes",
        "action_phrase": "List building rooms, pick cleaning tasks, figure out crew hours, and build work plans.",
        "sop_reference": "HWB-QMS-7.7",
        "icon": "fas fa-tasks"
    },
    "it_department": {
        "title": "Systems",
        "action_phrase": "Check server health, test system speed, block bad web traffic, and keep passwords fresh.",
        "sop_reference": "HWB-QMS-7.6",
        "icon": "fas fa-server"
    },
    "outbox": {
        "title": "Outbox",
        "action_phrase": "Check draft emails, confirm recipient names, review letter templates, and send approved emails.",
        "sop_reference": "HWB-QMS-4.0",
        "icon": "fas fa-envelope-open-text"
    },
    "social": {
        "title": "Broadcast",
        "action_phrase": "Read drafted social posts, review work site photos, check written text, and post online.",
        "sop_reference": "HWB-QMS-7.5",
        "icon": "fas fa-share-nodes"
    },
    "qms": {
        "title": "Quality",
        "action_phrase": "Read step-by-step cleaning guides, check inspection scores, fix cleaning mistakes, and keep quality high.",
        "sop_reference": "HWB-QMS-10.1",
        "icon": "fas fa-award"
    }
}
