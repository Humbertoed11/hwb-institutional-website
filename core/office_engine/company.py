"""
Office Engine: Multi-Tenant Company Profiles
Allows the engine to dynamically brand Word, Excel, and PowerPoint documents
for HWB Cleaning Services, Hexgrowth, BabySOP, or any future enterprise.
"""

from typing import Optional, Dict

class CompanyProfile:
    def __init__(
        self,
        key: str,
        name: str,
        legal_name: str,
        tagline: str,
        address: str,
        phone: str,
        email: str,
        website: str,
        primary_officer: str = "Humberto Dominguez",
        officer_title: str = "Chief Executive Officer",
        primary_color_hex: Optional[str] = None,
        secondary_color_hex: Optional[str] = None
    ):
        self.key = key
        self.name = name
        self.legal_name = legal_name
        self.tagline = tagline
        self.address = address
        self.phone = phone
        self.email = email
        self.website = website
        self.primary_officer = primary_officer
        self.officer_title = officer_title
        self.primary_color_hex = primary_color_hex
        self.secondary_color_hex = secondary_color_hex

    @property
    def footer_text(self) -> str:
        parts = [self.legal_name, self.website]
        if self.phone:
            parts.append(self.phone)
        return " | ".join(parts)


COMPANIES: Dict[str, CompanyProfile] = {
    "HWB": CompanyProfile(
        key="HWB",
        name="HWB Cleaning Services",
        legal_name="HWB Cleaning Services LLC",
        tagline="Commercial Facility Maintenance & Childcare Hygiene Standards",
        address="10925 Estate Ln., Suite 225, Dallas, TX 75238",
        phone="972-800-7808",
        email="hdominguez@hwbcleaning.com",
        website="www.hwbcleaning.com",
        primary_officer="Humberto Dominguez",
        officer_title="Chief Executive Officer",
        primary_color_hex="0F172A",
        secondary_color_hex="0284C7"
    ),
    "HEXGROWTH": CompanyProfile(
        key="HEXGROWTH",
        name="Hexgrowth",
        legal_name="Hexgrowth LLC",
        tagline="Autonomous AI Engineering & Enterprise Growth Systems",
        address="Dallas, TX",
        phone="972-800-7808",
        email="humberto@hexgrowth.com",
        website="www.hexgrowth.com",
        primary_officer="Humberto Dominguez",
        officer_title="Founder & Managing Director",
        primary_color_hex="0A0A0A",
        secondary_color_hex="6366F1" # Indigo Accent
    ),
    "BABYSOP": CompanyProfile(
        key="BABYSOP",
        name="BabySOP",
        legal_name="BabySOP Systems LLC",
        tagline="Childcare Compliance Operating Systems & Regulatory Governance",
        address="Dallas, TX",
        phone="972-800-7808",
        email="compliance@babysop.com",
        website="www.babysop.com",
        primary_officer="Humberto Dominguez",
        officer_title="Chief Executive Officer",
        primary_color_hex="065F46", # Deep Emerald Green
        secondary_color_hex="0D9488" # Teal Accent
    )
}

def get_company(company_key_or_obj) -> CompanyProfile:
    """Resolves a company profile from a key ('HWB', 'HEXGROWTH', 'BABYSOP') or returns the object."""
    if isinstance(company_key_or_obj, CompanyProfile):
        return company_key_or_obj
    key = str(company_key_or_obj).upper()
    return COMPANIES.get(key, COMPANIES["HWB"])
