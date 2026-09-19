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

LEAD_SOURCES = [
    {"value": "Texas CCL API", "label": "Texas CCL API (Active State Feed)"},
    {"value": "Texas Childcare Registry", "label": "Texas Childcare Registry (Master Import)"},
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
    "ceo_direct_phone": "(214) 799-5935",
    "official_email": "hdominguez@hwbcleaning.com",
    "sales_email": "sales@hwbcleaning.com",
    "website_url": "https://www.hwbcleaning.com",
    "official_logo_path": "img/hwb_commercial_cleaning_logo.png",
    "official_logo_transparent_path": "img/hwb_commercial_cleaning_logo_transparent.png",
    "official_logo_url": "https://www.hwbcleaning.com/static/img/hwb_commercial_cleaning_logo.png",
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
