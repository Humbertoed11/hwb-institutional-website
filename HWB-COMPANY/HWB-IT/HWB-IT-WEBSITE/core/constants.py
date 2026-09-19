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
